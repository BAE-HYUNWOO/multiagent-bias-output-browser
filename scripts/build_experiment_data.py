#!/usr/bin/env python3
"""Add experiment-aware static data to the existing output browser.

The script deliberately reads only the small, publishable subset of outputs.zip.
It never extracts raw_calls, errors, call-usage logs, or trash runs.

The existing main experiment under public/data is treated as the canonical
question metadata source. New experiment trees are built in a temporary
directory, validated, and only then swapped into public/data/experiments.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import tempfile
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MAIN_STAGES = [
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

NEUTRAL_STAGES_MEMBER = "outputs/neutral_agent_ablation/split001/stages.jsonl"
NEUTRAL_SUMMARY_MEMBER = (
    "outputs/neutral_agent_ablation/split001/comparison_summary_vs_original.csv"
)
NEUTRAL_PAIRED_MEMBER = (
    "outputs/neutral_agent_ablation/split001/paired_comparison_vs_original.csv"
)
REPEAT_STAGES_MEMBER = (
    "outputs/sufficiency_repeatability/"
    "scope_all_amb_dis5_seed20260721/combined_stages.jsonl"
)
REPEAT_SAMPLE_MEMBER = (
    "outputs/sufficiency_repeatability/"
    "scope_all_amb_dis5_seed20260721/sample_data/"
    "bbq_cbbq_kobbq_pair20_split001.csv"
)
REPEAT_SUMMARY_MEMBER = (
    "outputs/sufficiency_repeatability/"
    "scope_all_amb_dis5_seed20260721/stability_overall_by_model_condition.csv"
)
REPEAT_DATASET_SUMMARY_MEMBER = (
    "outputs/sufficiency_repeatability/"
    "scope_all_amb_dis5_seed20260721/"
    "stability_by_model_dataset_context_condition.csv"
)
REPEAT_ITEM_STABILITY_MEMBER = (
    "outputs/sufficiency_repeatability/"
    "scope_all_amb_dis5_seed20260721/item_model_judge_stability.csv"
)
PROMPT_PREFIX = "outputs/actual_prompts_single_neutral_all_languages/"
MULTI_PROMPT_PREFIX = (
    "outputs/sufficiency_repeatability/scope_all_amb_dis5_seed20260721/"
    "actual_prompts_all_languages/"
)
SINGLE_NEUTRAL_PROMPTS_MEMBER = (
    PROMPT_PREFIX + "actual_single_neutral_all_languages_qwen3_8b.json"
)
MULTI_PROMPTS_MEMBER = (
    MULTI_PROMPT_PREFIX + "actual_prompts_all_languages_run01_qwen3_8b.json"
)


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


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def slugify(value: str) -> str:
    result = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return result or "item-" + hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def pair_key(split: str, dataset: str, category: str, pair_id: str) -> str:
    value = f"{split}|{dataset}|{category}|{pair_id}"
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:14]


def answer_letter(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if text in {"A", "B", "C"}:
        return text
    if text in {"0", "1", "2"}:
        return {"0": "A", "1": "B", "2": "C"}[text]
    match = re.search(r"(?:^|[^A-Z])([ABC])(?:[^A-Z]|$)", text)
    return match.group(1) if match else None


def number(value: Any) -> int | float | None:
    if value in (None, ""):
        return None
    try:
        result = float(value)
        return int(result) if result.is_integer() else result
    except (TypeError, ValueError):
        return None


def typed_csv_value(value: str) -> Any:
    text = value.strip()
    if text == "":
        return ""
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    candidate = number(text)
    return candidate if candidate is not None else text


class ZipSource:
    def __init__(self, path: Path):
        self.path = path
        self.archive = zipfile.ZipFile(path)
        self.members = {
            info.filename.replace("\\", "/").lstrip("./"): info.filename
            for info in self.archive.infolist()
            if not info.is_dir()
        }

    def close(self) -> None:
        self.archive.close()

    def resolve(self, expected: str) -> str:
        normalized = expected.replace("\\", "/").lstrip("./")
        if normalized in self.members:
            return self.members[normalized]
        matches = [
            original
            for clean, original in self.members.items()
            if clean.endswith("/" + normalized) or clean == normalized
        ]
        if len(matches) != 1:
            raise FileNotFoundError(
                f"outputs.zip member not found or ambiguous: {expected} "
                f"(matches={len(matches)})"
            )
        return matches[0]

    def text(self, member: str) -> io.TextIOWrapper:
        return io.TextIOWrapper(
            self.archive.open(self.resolve(member)),
            encoding="utf-8-sig",
            newline="",
        )

    def jsonl(self, member: str) -> Iterable[dict[str, Any]]:
        with self.text(member) as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL: {member}:{line_no}") from exc
                if isinstance(value, dict):
                    yield value

    def csv_rows(self, member: str) -> list[dict[str, str]]:
        with self.text(member) as handle:
            return list(csv.DictReader(handle))

    def json_value(self, member: str) -> Any:
        with self.text(member) as handle:
            return json.load(handle)

    def copy_member(self, member: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.archive.open(self.resolve(member)) as source, destination.open("wb") as target:
            shutil.copyfileobj(source, target)


def resolve_public_path(public: Path, url: str) -> Path:
    return public / url.lstrip("/")


def load_main_metadata(public: Path) -> dict[str, dict[str, Any]]:
    """Recover all 1,560 question records from the already-published main UI."""
    root_path = public / "data" / "index.json"
    if not root_path.exists():
        raise FileNotFoundError(
            "public/data/index.json is missing. Start from a fresh GitHub download "
            "of multiagent-bias-output-browser before running this script."
        )

    metadata: dict[str, dict[str, Any]] = {}
    root = read_json(root_path)
    for dataset_summary in root.get("datasets", []):
        dataset_index = read_json(resolve_public_path(public, dataset_summary["path"]))
        for category_summary in dataset_index.get("categories", []):
            category_index = read_json(resolve_public_path(public, category_summary["path"]))
            for problem in category_index.get("problems", []):
                pair = read_json(resolve_public_path(public, problem["file"]))
                for context_type, variant in pair.get("variants", {}).items():
                    item_id = str(variant.get("item_id", "")).strip()
                    if not item_id:
                        continue
                    metadata[item_id] = {
                        "split": str(pair.get("split", "001")),
                        "item_id": item_id,
                        "pair_id": str(pair.get("pair_id", item_id)),
                        "dataset": str(pair.get("dataset", "Unknown")),
                        "category": str(pair.get("category", "Unknown")),
                        "context_type": context_type,
                        "context": str(variant.get("context", "")),
                        "question": str(variant.get("question", "")),
                        "options": {
                            "A": str(variant.get("options", {}).get("A", "")),
                            "B": str(variant.get("options", {}).get("B", "")),
                            "C": str(variant.get("options", {}).get("C", "")),
                        },
                        "correct_answer": answer_letter(variant.get("correct_answer")),
                        "stereotype_answer": answer_letter(
                            variant.get("stereotype_answer")
                        ),
                        "anti_stereotype_answer": answer_letter(
                            variant.get("anti_stereotype_answer")
                        ),
                        "unknown_answer": answer_letter(variant.get("unknown_answer")),
                    }
    if len(metadata) != 1560:
        raise ValueError(
            f"Expected 1,560 main question records, recovered {len(metadata):,}."
        )
    return metadata


def metadata_from_sample(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = row.get("item_id", "").strip()
        if not item_id:
            continue
        result[item_id] = {
            "split": row.get("split", "001").strip() or "001",
            "item_id": item_id,
            "pair_id": row.get("pair_id", "").strip() or item_id,
            "dataset": row.get("dataset", "Unknown").strip() or "Unknown",
            "category": row.get("category", "Unknown").strip() or "Unknown",
            "context_type": row.get("context_type", "ambiguous").strip(),
            "context": row.get("context", ""),
            "question": row.get("question", ""),
            "options": {
                "A": row.get("A", ""),
                "B": row.get("B", ""),
                "C": row.get("C", ""),
            },
            "correct_answer": answer_letter(
                row.get("gold_answer") or row.get("correct_answer")
            ),
            "stereotype_answer": answer_letter(row.get("stereotype_answer")),
            "anti_stereotype_answer": answer_letter(
                row.get("anti_stereotype_answer")
            ),
            "unknown_answer": answer_letter(row.get("unknown_answer")),
        }
    return result


def stage_record(obj: dict[str, Any]) -> dict[str, Any] | None:
    item_id = str(obj.get("item_id", "")).strip()
    model = str(obj.get("model", "")).strip()
    stage = str(obj.get("stage", "")).strip()
    if not item_id or not model or not stage or obj.get("status") not in (None, "done"):
        return None
    nested = obj.get("result") if isinstance(obj.get("result"), dict) else {}
    return {
        "item_id": item_id,
        "model": model,
        "stage": stage,
        "run": str(obj.get("run", "") or ""),
        "answer": answer_letter(nested.get("a", obj.get("a"))),
        "reason": str(nested.get("r", obj.get("r", "")) or "").strip(),
        "display_role": str(obj.get("actual_agent_role", "") or stage),
        "prompt_tokens": number(obj.get("prompt_tokens")),
        "completion_tokens": number(obj.get("completion_tokens")),
        "total_cost_usd": number(obj.get("total_cost_usd")),
    }


def load_stages(
    rows: Iterable[dict[str, Any]], *, expected_run: str | None = None
) -> tuple[dict[tuple[str, str], dict[str, dict[str, Any]]], int]:
    stages: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    count = 0
    for obj in rows:
        record = stage_record(obj)
        if record is None:
            continue
        if expected_run is not None and record["run"] != expected_run:
            continue
        stages[(record["item_id"], record["model"])][record["stage"]] = record
        count += 1
    return stages, count


def stage_payload(
    record: dict[str, Any] | None, correct_answer: str | None
) -> dict[str, Any] | None:
    if record is None:
        return None
    answer = record.get("answer")
    return {
        "stage": record["stage"],
        "display_role": record.get("display_role") or record["stage"],
        "answer": answer,
        "reason": record.get("reason", ""),
        "correct": answer == correct_answer if answer and correct_answer else None,
        "prompt_tokens": record.get("prompt_tokens"),
        "completion_tokens": record.get("completion_tokens"),
        "total_cost_usd": record.get("total_cost_usd"),
    }


def model_result(
    stage_map: dict[str, dict[str, Any]], correct_answer: str | None
) -> dict[str, Any]:
    return {
        "single_agent": {
            "final": stage_payload(stage_map.get("single_agent"), correct_answer)
        },
        "multi_agent_no_revision": {
            "stages": [
                value
                for value in (
                    stage_payload(stage_map.get(name), correct_answer)
                    for name in ROUND1
                )
                if value
            ],
            "final": stage_payload(
                stage_map.get("judge_no_revision"), correct_answer
            ),
        },
        "multi_agent_with_revision": {
            "stages": [
                value
                for value in (
                    stage_payload(stage_map.get(name), correct_answer)
                    for name in ROUND1 + ROUND2
                )
                if value
            ],
            "final": stage_payload(
                stage_map.get("judge_with_revision"), correct_answer
            ),
        },
    }


def build_tree(
    destination: Path,
    *,
    url_prefix: str,
    experiment_id: str,
    experiment_label: str,
    metadata: dict[str, dict[str, Any]],
    stages: dict[tuple[str, str], dict[str, dict[str, Any]]],
    stage_count: int,
    available_conditions: list[str],
    run: str | None = None,
    available_runs: list[str] | None = None,
) -> dict[str, Any]:
    item_models: dict[str, set[str]] = defaultdict(set)
    for item_id, model in stages:
        item_models[item_id].add(model)

    missing = sorted(item_id for item_id in item_models if item_id not in metadata)
    if missing:
        raise ValueError(
            f"{experiment_id}: metadata missing for {len(missing):,} stage item(s), "
            f"first={missing[0]}"
        )

    pair_groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for item_id in sorted(item_models):
        meta = metadata[item_id]
        pair_groups[
            (
                meta["split"],
                meta["dataset"],
                meta["category"],
                meta["pair_id"],
            )
        ].append(meta)

    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    all_models: set[str] = set()

    for (split, dataset, category, pair_id), metas in sorted(pair_groups.items()):
        variants: dict[str, Any] = {}
        pair_models: set[str] = set()
        has_disagreement = False
        for meta in sorted(metas, key=lambda value: value["context_type"]):
            models = sorted(item_models[meta["item_id"]])
            pair_models.update(models)
            all_models.update(models)
            results: dict[str, Any] = {}
            for model in models:
                result = model_result(
                    stages[(meta["item_id"], model)], meta["correct_answer"]
                )
                results[model] = result
                final_answers = {
                    final["answer"]
                    for final in (
                        result["single_agent"]["final"],
                        result["multi_agent_no_revision"]["final"],
                        result["multi_agent_with_revision"]["final"],
                    )
                    if final and final.get("answer")
                }
                has_disagreement = has_disagreement or len(final_answers) > 1

            variants[meta["context_type"]] = {
                "item_id": meta["item_id"],
                "context_type": meta["context_type"],
                "context": meta["context"],
                "question": meta["question"],
                "options": meta["options"],
                "correct_answer": meta["correct_answer"],
                "stereotype_answer": meta["stereotype_answer"],
                "anti_stereotype_answer": meta["anti_stereotype_answer"],
                "unknown_answer": meta["unknown_answer"],
                "results": results,
            }

        grouped[dataset][category].append(
            {
                "version": 2,
                "key": pair_key(split, dataset, category, pair_id),
                "split": split,
                "dataset": dataset,
                "category": category,
                "pair_id": pair_id,
                "experiment_id": experiment_id,
                "run": run,
                "variants": variants,
                "models": sorted(pair_models),
                "has_condition_disagreement": has_disagreement,
            }
        )

    root_datasets: list[dict[str, Any]] = []
    total_categories = total_pairs = total_items = 0
    for dataset, categories in sorted(grouped.items()):
        dataset_slug = slugify(dataset)
        dataset_dir = destination / dataset_slug
        category_summaries: list[dict[str, Any]] = []
        dataset_models: set[str] = set()
        dataset_pairs = dataset_items = 0

        for category, pairs in sorted(categories.items()):
            category_slug = slugify(category)
            category_dir = dataset_dir / category_slug
            pair_dir = category_dir / "pairs"
            pair_dir.mkdir(parents=True, exist_ok=True)
            problems: list[dict[str, Any]] = []
            category_models: set[str] = set()
            item_count = 0

            for pair in sorted(pairs, key=lambda value: value["pair_id"]):
                filename = f"{pair['key']}.json"
                write_json(pair_dir / filename, pair, compact=True)
                category_models.update(pair["models"])
                item_count += len(pair["variants"])
                problems.append(
                    {
                        "key": pair["key"],
                        "pair_id": pair["pair_id"],
                        "split": pair["split"],
                        "title": pair["pair_id"],
                        "file": (
                            f"{url_prefix}/{dataset_slug}/{category_slug}/pairs/"
                            f"{filename}"
                        ),
                        "variants": {
                            context_type: {
                                "item_id": variant["item_id"],
                                "preview": re.sub(
                                    r"\s+", " ", variant["question"]
                                ).strip()[:135],
                            }
                            for context_type, variant in pair["variants"].items()
                        },
                        "models": pair["models"],
                        "has_condition_disagreement": pair[
                            "has_condition_disagreement"
                        ],
                    }
                )

            category_index = {
                "dataset": dataset,
                "category": category,
                "pair_count": len(pairs),
                "item_count": item_count,
                "models": sorted(category_models),
                "download": None,
                "problems": problems,
            }
            write_json(category_dir / "index.json", category_index)
            category_summaries.append(
                {
                    "name": category,
                    "slug": category_slug,
                    "path": f"{url_prefix}/{dataset_slug}/{category_slug}/index.json",
                    "pair_count": len(pairs),
                    "item_count": item_count,
                    "models": sorted(category_models),
                    "download": None,
                }
            )
            dataset_models.update(category_models)
            dataset_pairs += len(pairs)
            dataset_items += item_count

        dataset_index = {
            "dataset": dataset,
            "label": dataset,
            "category_count": len(category_summaries),
            "pair_count": dataset_pairs,
            "item_count": dataset_items,
            "models": sorted(dataset_models),
            "download": None,
            "categories": category_summaries,
        }
        write_json(dataset_dir / "index.json", dataset_index)
        root_datasets.append(
            {
                "id": dataset_slug,
                "label": dataset,
                "path": f"{url_prefix}/{dataset_slug}/index.json",
                "category_count": len(category_summaries),
                "pair_count": dataset_pairs,
                "item_count": dataset_items,
                "models": sorted(dataset_models),
            }
        )
        total_categories += len(category_summaries)
        total_pairs += dataset_pairs
        total_items += dataset_items

    root = {
        "version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "experiment_id": experiment_id,
        "experiment_label": experiment_label,
        "run": run,
        "available_runs": available_runs or [],
        "available_conditions": available_conditions,
        "datasets": root_datasets,
        "models": sorted(all_models),
        "totals": {
            "categories": total_categories,
            "pairs": total_pairs,
            "items": total_items,
            "stage_records": stage_count,
        },
    }
    write_json(destination / "index.json", root)
    return root


def csv_as_json(source: ZipSource, member: str) -> list[dict[str, Any]]:
    return [
        {key: typed_csv_value(value) for key, value in row.items()}
        for row in source.csv_rows(member)
    ]


def build_prompt_examples(source: ZipSource) -> dict[str, Any]:
    single_neutral = source.json_value(SINGLE_NEUTRAL_PROMPTS_MEMBER)
    multi_agent = source.json_value(MULTI_PROMPTS_MEMBER)
    multi_by_language = {
        language["language_code"]: language
        for language in multi_agent.get("languages", [])
    }
    languages: list[dict[str, Any]] = []

    for language in single_neutral.get("languages", []):
        language_code = language["language_code"]
        multi_language = multi_by_language.get(language_code)
        if not multi_language:
            raise ValueError(
                f"Missing multi-agent prompt example for language: {language_code}"
            )

        cards: list[dict[str, Any]] = []

        def add_card(
            *,
            group: str,
            label: str,
            stage: str,
            agent: str,
            experiment: str,
            system_prompt: str,
            user_prompt: str,
            output: Any,
            order: int,
        ) -> None:
            cards.append(
                {
                    "group": group,
                    "label": label,
                    "stage": stage,
                    "agent": agent,
                    "experiment": experiment,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "actual_output": output,
                    "order": order,
                }
            )

        single_sections = language.get("sections", [])
        single = next(
            (
                section
                for section in single_sections
                if section.get("agent") == "single_agent"
            ),
            None,
        )
        if single:
            add_card(
                group="single",
                label="Single Agent",
                stage=single.get("stage", "single_agent"),
                agent=single.get("agent", "single_agent"),
                experiment=single.get("experiment", "original"),
                system_prompt=single.get("system_prompt", ""),
                user_prompt=single.get("actually_sent_user_prompt")
                or single.get("reconstructed_user_prompt", ""),
                output=single.get("actual_successful_parsed_output"),
                order=1,
            )

        for stage in multi_language.get("stages", []):
            add_card(
                group="multi_agent",
                label=stage.get("label", stage.get("stage", "")),
                stage=stage.get("stage", ""),
                agent=stage.get("stage", ""),
                experiment="sufficiency_repeatability_run_1",
                system_prompt=stage.get(
                    "system_prompt", multi_language.get("system_prompt", "")
                ),
                user_prompt=stage.get("user_prompt", ""),
                output=stage.get("actual_successful_parsed_output"),
                order=100 + int(stage.get("order", 0)),
            )

        neutral_sections = [
            section
            for section in single_sections
            if section.get("agent") in {"neutral_agent", "neutral_agent_revision"}
        ]
        for index, section in enumerate(neutral_sections, 1):
            add_card(
                group="neutral_agent",
                label=(
                    "Neutral Agent — Round 1"
                    if section.get("agent") == "neutral_agent"
                    else "Neutral Agent — With Revision"
                ),
                stage=section.get("stage", ""),
                agent=section.get("agent", ""),
                experiment=section.get("experiment", "neutral_agent_ablation"),
                system_prompt=section.get("system_prompt", ""),
                user_prompt=section.get("actually_sent_user_prompt")
                or section.get("reconstructed_user_prompt", ""),
                output=section.get("actual_successful_parsed_output"),
                order=200 + index,
            )

        languages.append(
            {
                "language": language["language"],
                "language_code": language_code,
                "dataset": language["dataset"],
                "model": language["model"],
                "model_id": language["model_id"],
                "item": language["item"],
                "cards": sorted(cards, key=lambda card: card["order"]),
            }
        )

    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": single_neutral.get("model", "qwen3_8b"),
        "languages": languages,
    }


def zip_directory(source: Path, destination: Path, prefix: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=7
    ) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, (Path(prefix) / path.relative_to(source)).as_posix())


def validate_tree(path: Path, expected_items: int, expected_stages: int) -> None:
    root = read_json(path / "index.json")
    if root["totals"]["items"] != expected_items:
        raise ValueError(
            f"{path.name}: expected {expected_items:,} items, "
            f"got {root['totals']['items']:,}"
        )
    if root["totals"]["stage_records"] != expected_stages:
        raise ValueError(
            f"{path.name}: expected {expected_stages:,} stages, "
            f"got {root['totals']['stage_records']:,}"
        )
    for dataset in root["datasets"]:
        dataset_dir = path / slugify(dataset["label"])
        dataset_index = read_json(dataset_dir / "index.json")
        for category in dataset_index["categories"]:
            category_path = dataset_dir / category["slug"] / "index.json"
            category_index = read_json(category_path)
            for problem in category_index["problems"]:
                pair_file = (
                    path
                    / slugify(dataset["label"])
                    / category["slug"]
                    / "pairs"
                    / Path(problem["file"]).name
                )
                if not pair_file.exists():
                    raise FileNotFoundError(f"Missing generated pair file: {pair_file}")


def safe_replace_directory(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = destination.with_name(destination.name + ".previous")
    if backup.exists():
        shutil.rmtree(backup)
    if destination.exists():
        destination.rename(backup)
    try:
        source.rename(destination)
    except Exception:
        if backup.exists() and not destination.exists():
            backup.rename(destination)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def build(root: Path, outputs_zip: Path) -> None:
    public = root / "public"
    public_data = public / "data"
    public_downloads = public / "downloads"
    main_metadata = load_main_metadata(public)
    source = ZipSource(outputs_zip)

    try:
        neutral_stages, neutral_stage_count = load_stages(
            source.jsonl(NEUTRAL_STAGES_MEMBER)
        )
        if neutral_stage_count != 37440:
            raise ValueError(
                f"Neutral ablation expected 37,440 stages, got {neutral_stage_count:,}"
            )

        repeat_rows = list(source.jsonl(REPEAT_STAGES_MEMBER))
        repeat_metadata = metadata_from_sample(source.csv_rows(REPEAT_SAMPLE_MEMBER))
        if len(repeat_metadata) != 390:
            raise ValueError(
                f"Repeatability sample expected 390 items, got {len(repeat_metadata):,}"
            )

        with tempfile.TemporaryDirectory(
            prefix="experiment-build-", dir=root
        ) as temp_name:
            temp = Path(temp_name)
            temp_data = temp / "data" / "experiments"
            temp_downloads = temp / "downloads"
            prompt_examples_file = temp / "prompt_examples.json"

            neutral_dir = temp_data / "neutral_agent_ablation"
            neutral_root = build_tree(
                neutral_dir,
                url_prefix="/data/experiments/neutral_agent_ablation",
                experiment_id="neutral_agent_ablation",
                experiment_label="Neutral Agent Ablation",
                metadata=main_metadata,
                stages=neutral_stages,
                stage_count=neutral_stage_count,
                available_conditions=[
                    "multi_agent_no_revision",
                    "multi_agent_with_revision",
                ],
            )
            neutral_summary = {
                "kind": "neutral_agent_ablation",
                "rows": csv_as_json(source, NEUTRAL_SUMMARY_MEMBER),
            }
            write_json(neutral_dir / "summary.json", neutral_summary)
            source.copy_member(
                NEUTRAL_SUMMARY_MEMBER,
                temp_downloads / "neutral_agent_ablation" / "comparison_summary.csv",
            )
            source.copy_member(
                NEUTRAL_PAIRED_MEMBER,
                temp_downloads
                / "neutral_agent_ablation"
                / "paired_comparison_vs_original.csv",
            )

            repeat_roots: dict[str, dict[str, Any]] = {}
            for run in ("1", "2", "3"):
                run_stages, run_stage_count = load_stages(
                    repeat_rows, expected_run=run
                )
                if run_stage_count != 18720:
                    raise ValueError(
                        f"Repeatability run {run} expected 18,720 stages, "
                        f"got {run_stage_count:,}"
                    )
                run_dir = temp_data / "sufficiency_repeatability" / f"run{run}"
                repeat_roots[run] = build_tree(
                    run_dir,
                    url_prefix=(
                        "/data/experiments/sufficiency_repeatability/"
                        f"run{run}"
                    ),
                    experiment_id="sufficiency_repeatability",
                    experiment_label="Sufficiency Repeatability",
                    metadata=repeat_metadata,
                    stages=run_stages,
                    stage_count=run_stage_count,
                    available_conditions=[
                        "multi_agent_no_revision",
                        "multi_agent_with_revision",
                    ],
                    run=run,
                    available_runs=["1", "2", "3"],
                )

            repeat_base = temp_data / "sufficiency_repeatability"
            repeat_summary = {
                "kind": "sufficiency_repeatability",
                "rows": csv_as_json(source, REPEAT_SUMMARY_MEMBER),
                "dataset_rows": csv_as_json(
                    source, REPEAT_DATASET_SUMMARY_MEMBER
                ),
            }
            write_json(repeat_base / "summary.json", repeat_summary)
            source.copy_member(
                REPEAT_SUMMARY_MEMBER,
                temp_downloads
                / "sufficiency_repeatability"
                / "stability_overall.csv",
            )
            source.copy_member(
                REPEAT_DATASET_SUMMARY_MEMBER,
                temp_downloads
                / "sufficiency_repeatability"
                / "stability_by_dataset_context.csv",
            )
            source.copy_member(
                REPEAT_ITEM_STABILITY_MEMBER,
                temp_downloads
                / "sufficiency_repeatability"
                / "item_model_judge_stability.csv",
            )

            prompt_examples = build_prompt_examples(source)
            write_json(prompt_examples_file, prompt_examples)

            prompt_dir = temp_downloads / "prompt_examples"
            for clean_member, original in source.members.items():
                if clean_member.startswith(PROMPT_PREFIX):
                    relative = Path(clean_member).relative_to(PROMPT_PREFIX)
                    destination = prompt_dir / "single_neutral" / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with source.archive.open(original) as input_handle, destination.open(
                        "wb"
                    ) as output_handle:
                        shutil.copyfileobj(input_handle, output_handle)
                elif clean_member.startswith(MULTI_PROMPT_PREFIX):
                    relative = Path(clean_member).relative_to(MULTI_PROMPT_PREFIX)
                    destination = prompt_dir / "multi_agent" / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with source.archive.open(original) as input_handle, destination.open(
                        "wb"
                    ) as output_handle:
                        shutil.copyfileobj(input_handle, output_handle)

            neutral_zip = temp_downloads / "neutral_agent_ablation_processed.zip"
            repeat_zip = temp_downloads / "sufficiency_repeatability_processed.zip"
            prompts_zip = temp_downloads / "prompt_examples.zip"
            zip_directory(neutral_dir, neutral_zip, "neutral_agent_ablation")
            zip_directory(
                repeat_base, repeat_zip, "sufficiency_repeatability"
            )
            zip_directory(prompt_dir, prompts_zip, "prompt_examples")
            with zipfile.ZipFile(
                neutral_zip, "a", compression=zipfile.ZIP_DEFLATED, compresslevel=7
            ) as archive:
                for path in sorted(
                    (temp_downloads / "neutral_agent_ablation").glob("*.csv")
                ):
                    archive.write(
                        path,
                        (
                            Path("neutral_agent_ablation")
                            / "tables"
                            / path.name
                        ).as_posix(),
                    )
            with zipfile.ZipFile(
                repeat_zip, "a", compression=zipfile.ZIP_DEFLATED, compresslevel=7
            ) as archive:
                for path in sorted(
                    (temp_downloads / "sufficiency_repeatability").glob("*.csv")
                ):
                    archive.write(
                        path,
                        (
                            Path("sufficiency_repeatability")
                            / "tables"
                            / path.name
                        ).as_posix(),
                    )

            validate_tree(neutral_dir, expected_items=780, expected_stages=37440)
            for run in ("1", "2", "3"):
                validate_tree(
                    repeat_base / f"run{run}",
                    expected_items=390,
                    expected_stages=18720,
                )

            experiments_manifest = {
                "version": 1,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "experiments": [
                    {
                        "id": "main",
                        "label": "Main Experiment",
                        "description": (
                            "Single Agent and Multi-Agent outputs for all "
                            "1,560 BBQ, CBBQ, and KoBBQ questions."
                        ),
                        "path": "/data/index.json",
                        "summary_path": None,
                        "available_conditions": [
                            "single_agent",
                            "multi_agent_no_revision",
                            "multi_agent_with_revision",
                        ],
                        "runs": [],
                        "download": "/downloads/all_processed_results.zip",
                    },
                    {
                        "id": "neutral_agent_ablation",
                        "label": "Neutral Agent Ablation",
                        "description": (
                            "Disambiguated-only ablation replacing the "
                            "Sufficiency Agent with a Neutral Agent."
                        ),
                        "path": "/data/experiments/neutral_agent_ablation/index.json",
                        "summary_path": (
                            "/data/experiments/neutral_agent_ablation/summary.json"
                        ),
                        "available_conditions": neutral_root[
                            "available_conditions"
                        ],
                        "runs": [],
                        "download": (
                            "/downloads/neutral_agent_ablation_processed.zip"
                        ),
                    },
                    {
                        "id": "sufficiency_repeatability",
                        "label": "Sufficiency Repeatability",
                        "description": (
                            "Three repeated runs on 390 sampled questions "
                            "to measure answer stability."
                        ),
                        "path": None,
                        "summary_path": (
                            "/data/experiments/sufficiency_repeatability/"
                            "summary.json"
                        ),
                        "available_conditions": [
                            "multi_agent_no_revision",
                            "multi_agent_with_revision",
                        ],
                        "runs": [
                            {
                                "id": run,
                                "label": f"Run {run}",
                                "path": (
                                    "/data/experiments/"
                                    "sufficiency_repeatability/"
                                    f"run{run}/index.json"
                                ),
                            }
                            for run in ("1", "2", "3")
                        ],
                        "default_run": "1",
                        "download": (
                            "/downloads/"
                            "sufficiency_repeatability_processed.zip"
                        ),
                    },
                ],
                "prompt_examples_download": "/downloads/prompt_examples.zip",
                "prompt_examples_path": "/data/prompt_examples.json",
            }

            final_experiments_dir = public_data / "experiments"
            safe_replace_directory(temp_data, final_experiments_dir)
            prompt_examples_file.replace(public_data / "prompt_examples.json")
            public_downloads.mkdir(parents=True, exist_ok=True)
            for path in list(temp_downloads.iterdir()):
                destination = public_downloads / path.name
                if path.is_dir():
                    safe_replace_directory(path, destination)
                else:
                    path.replace(destination)
            write_json(public_data / "experiments.json", experiments_manifest)

            old_manifest_path = public_downloads / "manifest.json"
            old_manifest = (
                read_json(old_manifest_path) if old_manifest_path.exists() else {}
            )
            old_manifest["experiments"] = {
                experiment["id"]: experiment.get("download")
                for experiment in experiments_manifest["experiments"]
            }
            old_manifest["prompt_examples"] = experiments_manifest[
                "prompt_examples_download"
            ]
            write_json(old_manifest_path, old_manifest)

        print("[DONE] Experiment-aware UI data generated")
        print("  main:          1,560 items (existing data preserved)")
        print("  neutral:         780 items / 37,440 stages")
        print("  repeatability:   390 items x 3 runs / 56,160 stages")
        print(f"  output:        {public_data}")
    finally:
        source.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root directory",
    )
    parser.add_argument(
        "--outputs-zip",
        type=Path,
        required=True,
        help="Path to the experiment outputs.zip",
    )
    args = parser.parse_args()
    outputs_zip = args.outputs_zip.expanduser().resolve()
    if not outputs_zip.is_file():
        raise SystemExit(f"outputs.zip not found: {outputs_zip}")
    build(args.root.resolve(), outputs_zip)


if __name__ == "__main__":
    main()
