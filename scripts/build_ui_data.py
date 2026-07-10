#!/usr/bin/env python3
"""Build static UI JSON and downloadable archives from experiment outputs.

No third-party Python packages are required.

Expected local inputs:
  source_data/outputs/split001/stages.jsonl
  source_data/outputs/split001/item_level_results.csv
  source_data/splits/bbq_cbbq_kobbq_pair20_split001.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
import tempfile
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

STAGE_ORDER = [
    "single_agent",
    "context_agent_r1",
    "option_agent_r1",
    "sufficiency_agent_r1",
    "judge_no_revision",
    "context_agent_r2",
    "option_agent_r2",
    "sufficiency_agent_r2",
    "judge_with_revision",
]

ROUND1 = ["context_agent_r1", "option_agent_r1", "sufficiency_agent_r1"]
ROUND2 = ["context_agent_r2", "option_agent_r2", "sufficiency_agent_r2"]

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "item_id": ("item_id", "global_id", "qid", "question_id", "id"),
    "pair_id": ("pair_id", "matched_pair_id", "pair", "pair_key"),
    "dataset": ("dataset", "dataset_name", "source_dataset"),
    "category": ("category", "bias_category", "dimension"),
    "language": ("language", "lang"),
    "context_type": ("context_type", "context_condition", "question_type", "type"),
    "context": ("context", "passage", "scenario"),
    "question": ("question", "query", "prompt_question"),
    "option_a": ("A", "a", "option_a", "answer_a", "ans_a", "option0", "answer0"),
    "option_b": ("B", "b", "option_b", "answer_b", "ans_b", "option1", "answer1"),
    "option_c": ("C", "c", "option_c", "answer_c", "ans_c", "option2", "answer2"),
    "correct_answer": ("correct_answer", "correct", "gold_answer", "label", "answer"),
    "stereotype_answer": ("stereotype_answer", "stereotype", "stereo_answer"),
    "anti_stereotype_answer": (
        "anti_stereotype_answer",
        "anti_stereotype",
        "antistereotype_answer",
        "anti_answer",
    ),
    "unknown_answer": ("unknown_answer", "unknown", "undetermined_answer"),
    "model": ("model", "model_name", "model_key"),
}


def norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def row_lookup(row: dict[str, Any], logical_name: str, default: str = "") -> str:
    aliases = FIELD_ALIASES.get(logical_name, (logical_name,))
    normalized = {norm_key(str(key)): value for key, value in row.items()}
    for alias in aliases:
        value = normalized.get(norm_key(alias))
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def first_value(obj: dict[str, Any], names: Iterable[str], default: Any = None) -> Any:
    normalized = {norm_key(str(key)): value for key, value in obj.items()}
    for name in names:
        value = normalized.get(norm_key(name))
        if value is not None:
            return value
    return default


def answer_letter(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if not text:
        return None
    direct = {"A": "A", "B": "B", "C": "C", "0": "A", "1": "B", "2": "C"}
    if text in direct:
        return direct[text]
    match = re.search(r"(?:^|[^A-Z])([ABC])(?:[^A-Z]|$)", text)
    return match.group(1) if match else None


def as_number(value: Any) -> int | float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except (TypeError, ValueError):
        return None


def canonical_dataset(value: str) -> str:
    compact = re.sub(r"[^A-Z]", "", value.upper())
    if compact == "BBQ":
        return "BBQ"
    if compact == "CBBQ":
        return "CBBQ"
    if compact in {"KOBBQ", "KBBQ"}:
        return "KoBBQ"
    return value.strip() or "Unknown"


def normalize_context_type(value: str, item_id: str = "") -> str:
    text = f"{value} {item_id}".lower()
    if any(token in text for token in ("disambiguated", "disambig", "_dis", "-dis", "nonamb")):
        return "disambiguated"
    if any(token in text for token in ("ambiguous", "ambig", "_amb", "-amb")):
        return "ambiguous"
    return "ambiguous"


def infer_pair_id(item_id: str) -> str:
    patterns = [
        r"(?i)(?:[_-](?:ambiguous|disambiguated|ambig|disambig|amb|dis))$",
        r"(?i)(?:[_-](?:ambiguous|disambiguated|ambig|disambig|amb|dis)[_-]?\d*)$",
    ]
    value = item_id
    for pattern in patterns:
        value = re.sub(pattern, "", value)
    return value or item_id


def slugify(value: str) -> str:
    ascii_part = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    if ascii_part:
        return ascii_part
    return "item-" + hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:14]


def split_id_from_name(value: str) -> str:
    match = re.search(r"split[_-]?(\d+)", value, flags=re.IGNORECASE)
    return match.group(1).zfill(3) if match else value


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(
            value,
            handle,
            ensure_ascii=False,
            indent=None if compact else 2,
            separators=(",", ":") if compact else None,
        )
        handle.write("\n")


def preview_text(value: str, limit: int = 135) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


@dataclass
class ItemMeta:
    split: str
    item_id: str
    pair_id: str
    dataset: str
    category: str
    language: str
    context_type: str
    context: str
    question: str
    options: dict[str, str]
    correct_answer: str | None
    stereotype_answer: str | None
    anti_stereotype_answer: str | None
    unknown_answer: str | None

    @classmethod
    def from_row(cls, split: str, row: dict[str, Any], fallback: "ItemMeta | None" = None) -> "ItemMeta | None":
        item_id = row_lookup(row, "item_id", fallback.item_id if fallback else "")
        if not item_id:
            return None
        pair_id = row_lookup(row, "pair_id", fallback.pair_id if fallback else "") or infer_pair_id(item_id)
        dataset = canonical_dataset(row_lookup(row, "dataset", fallback.dataset if fallback else "Unknown"))
        category = row_lookup(row, "category", fallback.category if fallback else "Unknown") or "Unknown"
        context_type = normalize_context_type(
            row_lookup(row, "context_type", fallback.context_type if fallback else ""),
            item_id,
        )
        return cls(
            split=split,
            item_id=item_id,
            pair_id=pair_id,
            dataset=dataset,
            category=category,
            language=row_lookup(row, "language", fallback.language if fallback else ""),
            context_type=context_type,
            context=row_lookup(row, "context", fallback.context if fallback else ""),
            question=row_lookup(row, "question", fallback.question if fallback else ""),
            options={
                "A": row_lookup(row, "option_a", fallback.options.get("A", "") if fallback else ""),
                "B": row_lookup(row, "option_b", fallback.options.get("B", "") if fallback else ""),
                "C": row_lookup(row, "option_c", fallback.options.get("C", "") if fallback else ""),
            },
            correct_answer=answer_letter(row_lookup(row, "correct_answer", fallback.correct_answer or "" if fallback else "")),
            stereotype_answer=answer_letter(row_lookup(row, "stereotype_answer", fallback.stereotype_answer or "" if fallback else "")),
            anti_stereotype_answer=answer_letter(
                row_lookup(row, "anti_stereotype_answer", fallback.anti_stereotype_answer or "" if fallback else "")
            ),
            unknown_answer=answer_letter(row_lookup(row, "unknown_answer", fallback.unknown_answer or "" if fallback else "")),
        )


@dataclass
class StageRecord:
    split: str
    item_id: str
    model: str
    stage: str
    answer: str | None
    reason: str
    prompt_tokens: int | float | None
    completion_tokens: int | float | None
    total_cost_usd: int | float | None


@dataclass
class BuildState:
    items: dict[tuple[str, str], ItemMeta] = field(default_factory=dict)
    stages: dict[tuple[str, str, str], dict[str, StageRecord]] = field(default_factory=lambda: defaultdict(dict))
    stage_record_count: int = 0


def load_split_metadata(splits_dir: Path) -> dict[tuple[str, str], ItemMeta]:
    result: dict[tuple[str, str], ItemMeta] = {}
    for path in sorted(splits_dir.glob("*.csv")):
        split = split_id_from_name(path.name)
        try:
            rows = read_csv(path)
        except UnicodeDecodeError:
            print(f"[WARN] UTF-8로 읽지 못해 건너뜀: {path}", file=sys.stderr)
            continue
        for row in rows:
            meta = ItemMeta.from_row(split, row)
            if meta:
                result[(split, meta.item_id)] = meta
        print(f"[LOAD] split CSV {path.name}: {len(rows):,} rows")
    return result


def load_item_results(path: Path, split: str, state: BuildState) -> None:
    if not path.exists():
        print(f"[WARN] item_level_results.csv 없음: {path}")
        return
    rows = read_csv(path)
    for row in rows:
        item_id = row_lookup(row, "item_id")
        fallback = state.items.get((split, item_id)) if item_id else None
        meta = ItemMeta.from_row(split, row, fallback)
        if meta:
            state.items[(split, meta.item_id)] = meta
    print(f"[LOAD] {path.parent.name}/item_level_results.csv: {len(rows):,} rows")


def iter_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_no, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                print(f"[WARN] JSON parse 실패: {path.name}:{line_no}", file=sys.stderr)
                continue
            if isinstance(value, dict):
                yield line_no, value


def load_stages(path: Path, split: str, state: BuildState) -> None:
    if not path.exists():
        print(f"[WARN] stages.jsonl 없음: {path}")
        return
    count = 0
    for _line_no, obj in iter_jsonl(path):
        item_id = str(first_value(obj, ("item_id", "global_id", "qid", "question_id"), "")).strip()
        model = str(first_value(obj, ("model", "model_name", "model_key"), "")).strip()
        stage = str(first_value(obj, ("stage", "stage_name", "agent", "agent_name"), "")).strip()
        if not item_id or not model or not stage:
            continue
        # Stage outputs are stored under obj["result"] in the experiment JSONL,
        # e.g. {"result": {"a": "B", "r": "..."}}.  Older runs may
        # store the same fields at the top level, so support both layouts.
        nested_result = first_value(
            obj,
            ("result", "parsed_result", "parsed_output", "output"),
            {},
        )
        if isinstance(nested_result, str):
            try:
                parsed_result = json.loads(nested_result)
                nested_result = parsed_result if isinstance(parsed_result, dict) else {}
            except json.JSONDecodeError:
                nested_result = {}
        if not isinstance(nested_result, dict):
            nested_result = {}

        answer_value = first_value(obj, ("a", "answer", "selected_answer", "choice"))
        if answer_value in (None, ""):
            answer_value = first_value(
                nested_result,
                ("a", "answer", "selected_answer", "choice"),
            )
        answer = answer_letter(answer_value)

        reason = first_value(obj, ("r", "reason", "explanation", "rationale"), None)
        if reason in (None, ""):
            reason = first_value(
                nested_result,
                ("r", "reason", "explanation", "rationale"),
                "",
            )
        if isinstance(reason, (dict, list)):
            reason = json.dumps(reason, ensure_ascii=False)
        record = StageRecord(
            split=split,
            item_id=item_id,
            model=model,
            stage=stage,
            answer=answer,
            reason=str(reason or "").strip(),
            prompt_tokens=as_number(first_value(obj, ("prompt_tokens", "input_tokens", "in_tok"))),
            completion_tokens=as_number(first_value(obj, ("completion_tokens", "output_tokens", "out_tok"))),
            total_cost_usd=as_number(first_value(obj, ("total_cost_usd", "total_cost", "cost_usd"))),
        )
        state.stages[(split, item_id, model)][stage] = record
        state.stage_record_count += 1
        count += 1
    print(f"[LOAD] {path.parent.name}/stages.jsonl: {count:,} stage rows")


def stage_payload(record: StageRecord | None, correct_answer: str | None) -> dict[str, Any] | None:
    if record is None:
        return None
    return {
        "stage": record.stage,
        "answer": record.answer,
        "reason": record.reason,
        "correct": (record.answer == correct_answer) if record.answer and correct_answer else None,
        "prompt_tokens": record.prompt_tokens,
        "completion_tokens": record.completion_tokens,
        "total_cost_usd": record.total_cost_usd,
    }


def model_result(stage_map: dict[str, StageRecord], correct_answer: str | None) -> dict[str, Any]:
    single = stage_payload(stage_map.get("single_agent"), correct_answer)
    no_revision_stages = [stage_payload(stage_map.get(name), correct_answer) for name in ROUND1]
    no_revision_stages = [value for value in no_revision_stages if value]
    with_revision_names = ROUND1 + ROUND2
    with_revision_stages = [stage_payload(stage_map.get(name), correct_answer) for name in with_revision_names]
    with_revision_stages = [value for value in with_revision_stages if value]
    return {
        "single_agent": {"final": single},
        "multi_agent_no_revision": {
            "stages": no_revision_stages,
            "final": stage_payload(stage_map.get("judge_no_revision"), correct_answer),
        },
        "multi_agent_with_revision": {
            "stages": with_revision_stages,
            "final": stage_payload(stage_map.get("judge_with_revision"), correct_answer),
        },
    }


def final_answers(result: dict[str, Any]) -> set[str]:
    values = [
        result["single_agent"]["final"],
        result["multi_agent_no_revision"]["final"],
        result["multi_agent_with_revision"]["final"],
    ]
    return {str(value["answer"]) for value in values if value and value.get("answer")}


def make_variant(meta: ItemMeta, state: BuildState) -> tuple[dict[str, Any], bool, set[str]]:
    models = sorted(
        model
        for split, item_id, model in state.stages.keys()
        if split == meta.split and item_id == meta.item_id
    )
    results: dict[str, Any] = {}
    disagreement = False
    for model in models:
        result = model_result(state.stages[(meta.split, meta.item_id, model)], meta.correct_answer)
        results[model] = result
        if len(final_answers(result)) > 1:
            disagreement = True
    variant = {
        "item_id": meta.item_id,
        "context_type": meta.context_type,
        "context": meta.context,
        "question": meta.question,
        "options": meta.options,
        "correct_answer": meta.correct_answer,
        "stereotype_answer": meta.stereotype_answer,
        "anti_stereotype_answer": meta.anti_stereotype_answer,
        "unknown_answer": meta.unknown_answer,
        "results": results,
    }
    return variant, disagreement, set(models)


def csv_rows_for_pairs(pair_payloads: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    item_rows: list[dict[str, Any]] = []
    stage_rows: list[dict[str, Any]] = []
    for pair in pair_payloads:
        for context_type, variant in pair["variants"].items():
            base = {
                "split": pair["split"],
                "dataset": pair["dataset"],
                "category": pair["category"],
                "pair_id": pair["pair_id"],
                "item_id": variant["item_id"],
                "context_type": context_type,
                "context": variant["context"],
                "question": variant["question"],
                "option_a": variant["options"].get("A", ""),
                "option_b": variant["options"].get("B", ""),
                "option_c": variant["options"].get("C", ""),
                "correct_answer": variant["correct_answer"],
                "stereotype_answer": variant["stereotype_answer"],
                "anti_stereotype_answer": variant["anti_stereotype_answer"],
                "unknown_answer": variant["unknown_answer"],
            }
            for model, result in variant["results"].items():
                row = dict(base)
                row["model"] = model
                row["single_answer"] = (result["single_agent"]["final"] or {}).get("answer")
                row["no_revision_answer"] = (result["multi_agent_no_revision"]["final"] or {}).get("answer")
                row["with_revision_answer"] = (result["multi_agent_with_revision"]["final"] or {}).get("answer")
                row["single_correct"] = (result["single_agent"]["final"] or {}).get("correct")
                row["no_revision_correct"] = (result["multi_agent_no_revision"]["final"] or {}).get("correct")
                row["with_revision_correct"] = (result["multi_agent_with_revision"]["final"] or {}).get("correct")
                item_rows.append(row)

                seen: set[tuple[str, str]] = set()
                condition_groups = {
                    "single_agent": [result["single_agent"]["final"]],
                    "multi_agent_no_revision": result["multi_agent_no_revision"]["stages"]
                    + [result["multi_agent_no_revision"]["final"]],
                    "multi_agent_with_revision": result["multi_agent_with_revision"]["stages"]
                    + [result["multi_agent_with_revision"]["final"]],
                }
                for condition, stages in condition_groups.items():
                    for stage in stages:
                        if not stage:
                            continue
                        dedupe_key = (condition, stage["stage"])
                        if dedupe_key in seen:
                            continue
                        seen.add(dedupe_key)
                        stage_rows.append(
                            {
                                **{key: base[key] for key in ("split", "dataset", "category", "pair_id", "item_id", "context_type")},
                                "model": model,
                                "condition": condition,
                                "stage": stage["stage"],
                                "answer": stage["answer"],
                                "correct": stage["correct"],
                                "reason": stage["reason"],
                                "prompt_tokens": stage.get("prompt_tokens"),
                                "completion_tokens": stage.get("completion_tokens"),
                                "total_cost_usd": stage.get("total_cost_usd"),
                            }
                        )
    return item_rows, stage_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def zip_directory(source_dir: Path, zip_path: Path, prefix: str = "") -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=7) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                relative = path.relative_to(source_dir)
                archive_name = Path(prefix) / relative if prefix else relative
                archive.write(path, archive_name.as_posix())


def build(root: Path, include_raw_zip: bool) -> None:
    outputs_dir = root / "source_data" / "outputs"
    splits_dir = root / "source_data" / "splits"
    public_data = root / "public" / "data"
    downloads_dir = root / "public" / "downloads"

    site_config = public_data / "site_config.json"
    site_config_text = site_config.read_text(encoding="utf-8") if site_config.exists() else None
    if public_data.exists():
        shutil.rmtree(public_data)
    if downloads_dir.exists():
        shutil.rmtree(downloads_dir)
    public_data.mkdir(parents=True)
    downloads_dir.mkdir(parents=True)
    if site_config_text:
        site_config.write_text(site_config_text, encoding="utf-8")
    else:
        write_json(
            site_config,
            {
                "title": "Multi-Agent Bias Output Browser",
                "subtitle": "BBQ · CBBQ · KoBBQ datasets and model outputs",
                "raw_release_url": "",
            },
        )

    state = BuildState()
    state.items.update(load_split_metadata(splits_dir))

    output_folders = sorted(path for path in outputs_dir.glob("split*") if path.is_dir())
    if not output_folders:
        raise SystemExit(
            "source_data/outputs 아래에 split001 같은 결과 폴더가 없습니다. "
            "scripts/import_split001.ps1을 먼저 실행하세요."
        )

    for folder in output_folders:
        split = split_id_from_name(folder.name)
        load_item_results(folder / "item_level_results.csv", split, state)
        load_stages(folder / "stages.jsonl", split, state)

    pair_groups: dict[tuple[str, str, str, str], list[ItemMeta]] = defaultdict(list)
    for meta in state.items.values():
        pair_groups[(meta.split, meta.dataset, meta.category, meta.pair_id)].append(meta)

    dataset_category_pairs: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    all_models: set[str] = set()

    for (split, dataset, category, pair_id), metas in sorted(pair_groups.items()):
        variants: dict[str, Any] = {}
        pair_models: set[str] = set()
        disagreement = False
        for meta in sorted(metas, key=lambda value: value.context_type):
            variant, variant_disagreement, models = make_variant(meta, state)
            variants[meta.context_type] = variant
            disagreement = disagreement or variant_disagreement
            pair_models.update(models)
            all_models.update(models)
        if not pair_models:
            continue
        key = short_hash(f"{split}|{dataset}|{category}|{pair_id}")
        payload = {
            "version": 1,
            "key": key,
            "split": split,
            "dataset": dataset,
            "category": category,
            "pair_id": pair_id,
            "variants": variants,
            "models": sorted(pair_models),
        }
        payload["_has_condition_disagreement"] = disagreement
        dataset_category_pairs[dataset][category].append(payload)

    root_datasets: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "all_processed": "/downloads/all_processed_results.zip",
        "all_source_outputs": "/downloads/all_source_outputs.zip" if include_raw_zip else None,
        "datasets": {},
    }
    total_categories = total_pairs = total_items = 0

    with tempfile.TemporaryDirectory(prefix="bias_ui_build_") as temp_name:
        temp_root = Path(temp_name)
        all_download_root = temp_root / "all_processed_results"

        for dataset in sorted(dataset_category_pairs, key=lambda value: (value != "BBQ", value != "CBBQ", value)):
            dataset_slug = slugify(dataset)
            dataset_dir = public_data / dataset_slug
            dataset_dir.mkdir(parents=True, exist_ok=True)
            dataset_download_work = temp_root / f"dataset_{dataset_slug}"
            dataset_all_pairs: list[dict[str, Any]] = []
            category_summaries: list[dict[str, Any]] = []
            dataset_models: set[str] = set()
            dataset_items = 0

            manifest["datasets"][dataset] = {
                "file": f"/downloads/{dataset_slug}.zip",
                "categories": {},
            }

            for category in sorted(dataset_category_pairs[dataset]):
                category_slug = slugify(category)
                category_dir = dataset_dir / category_slug
                pairs_dir = category_dir / "pairs"
                pairs_dir.mkdir(parents=True, exist_ok=True)
                pairs = dataset_category_pairs[dataset][category]
                problem_summaries: list[dict[str, Any]] = []
                category_models: set[str] = set()
                item_count = 0

                for pair in sorted(pairs, key=lambda value: (value["split"], value["pair_id"])):
                    pair_file = pairs_dir / f"{pair['key']}.json"
                    disagreement = bool(pair.pop("_has_condition_disagreement", False))
                    write_json(pair_file, pair, compact=True)
                    item_count += len(pair["variants"])
                    category_models.update(pair["models"])
                    dataset_models.update(pair["models"])
                    dataset_all_pairs.append(pair)
                    previews = {
                        name: {
                            "item_id": variant["item_id"],
                            "preview": preview_text(variant["context"] or variant["question"]),
                        }
                        for name, variant in pair["variants"].items()
                    }
                    problem_summaries.append(
                        {
                            "key": pair["key"],
                            "pair_id": pair["pair_id"],
                            "split": pair["split"],
                            "title": f"{pair['pair_id']} · split{pair['split']}",
                            "file": f"/data/{dataset_slug}/{category_slug}/pairs/{pair['key']}.json",
                            "variants": previews,
                            "models": pair["models"],
                            "has_condition_disagreement": disagreement,
                        }
                    )

                category_download = f"/downloads/{dataset_slug}/{category_slug}.zip"
                category_index = {
                    "dataset": dataset,
                    "category": category,
                    "pair_count": len(pairs),
                    "item_count": item_count,
                    "models": sorted(category_models),
                    "download": category_download,
                    "problems": problem_summaries,
                }
                write_json(category_dir / "index.json", category_index)

                category_work = temp_root / f"category_{dataset_slug}_{category_slug}"
                item_rows, stage_rows = csv_rows_for_pairs(pairs)
                write_csv(category_work / "item_level_results.csv", item_rows)
                write_jsonl(category_work / "stage_outputs.jsonl", stage_rows)
                write_json(category_work / "problems.json", pairs)
                category_zip = downloads_dir / dataset_slug / f"{category_slug}.zip"
                zip_directory(category_work, category_zip, f"{dataset}_{category}")
                manifest["datasets"][dataset]["categories"][category] = category_download

                category_summaries.append(
                    {
                        "name": category,
                        "slug": category_slug,
                        "path": f"/data/{dataset_slug}/{category_slug}/index.json",
                        "pair_count": len(pairs),
                        "item_count": item_count,
                        "models": sorted(category_models),
                        "download": category_download,
                    }
                )
                dataset_items += item_count

            dataset_item_rows, dataset_stage_rows = csv_rows_for_pairs(dataset_all_pairs)
            write_csv(dataset_download_work / "item_level_results.csv", dataset_item_rows)
            write_jsonl(dataset_download_work / "stage_outputs.jsonl", dataset_stage_rows)
            write_json(dataset_download_work / "problems.json", dataset_all_pairs)
            zip_directory(dataset_download_work, downloads_dir / f"{dataset_slug}.zip", dataset)

            dataset_index = {
                "dataset": dataset,
                "label": dataset,
                "category_count": len(category_summaries),
                "pair_count": len(dataset_all_pairs),
                "item_count": dataset_items,
                "models": sorted(dataset_models),
                "download": f"/downloads/{dataset_slug}.zip",
                "categories": category_summaries,
            }
            write_json(dataset_dir / "index.json", dataset_index)
            root_datasets.append(
                {
                    "id": dataset_slug,
                    "label": dataset,
                    "path": f"/data/{dataset_slug}/index.json",
                    "category_count": len(category_summaries),
                    "pair_count": len(dataset_all_pairs),
                    "item_count": dataset_items,
                    "models": sorted(dataset_models),
                }
            )
            total_categories += len(category_summaries)
            total_pairs += len(dataset_all_pairs)
            total_items += dataset_items

            shutil.copytree(dataset_download_work, all_download_root / dataset, dirs_exist_ok=True)

        root_index = {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "datasets": root_datasets,
            "models": sorted(all_models),
            "totals": {
                "categories": total_categories,
                "pairs": total_pairs,
                "items": total_items,
                "stage_records": state.stage_record_count,
            },
        }
        write_json(public_data / "index.json", root_index)
        write_json(downloads_dir / "manifest.json", manifest)
        zip_directory(all_download_root, downloads_dir / "all_processed_results.zip")

    if include_raw_zip:
        zip_directory(root / "source_data", downloads_dir / "all_source_outputs.zip", "source_data")

    print("\n[DONE] UI data build complete")
    print(f"  datasets:   {len(root_datasets):,}")
    print(f"  categories: {total_categories:,}")
    print(f"  pairs:      {total_pairs:,}")
    print(f"  items:      {total_items:,}")
    print(f"  models:     {len(all_models):,}")
    print(f"  output:     {public_data}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root directory",
    )
    parser.add_argument(
        "--include-raw-zip",
        action="store_true",
        help="Also create a potentially very large ZIP containing source_data",
    )
    args = parser.parse_args()
    build(args.root.resolve(), args.include_raw_zip)


if __name__ == "__main__":
    main()
