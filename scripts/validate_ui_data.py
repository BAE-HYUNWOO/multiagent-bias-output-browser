#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root directory",
    )
    args = parser.parse_args()
    public = args.root.resolve() / "public"

    def public_path(url: str) -> Path:
        return public / url.lstrip("/")

    root = load(public / "data" / "index.json")
    errors: list[str] = []
    pair_count = 0

    def validate_root(root_index: dict, label: str) -> int:
        local_pairs = 0
        for dataset in root_index.get("datasets", []):
            dataset_path = public_path(dataset["path"])
            if not dataset_path.exists():
                errors.append(f"{label}: missing dataset index: {dataset_path}")
                continue
            dataset_index = load(dataset_path)
            for category in dataset_index.get("categories", []):
                category_path = public_path(category["path"])
                if not category_path.exists():
                    errors.append(f"{label}: missing category index: {category_path}")
                    continue
                category_index = load(category_path)
                for problem in category_index.get("problems", []):
                    pair_path = public_path(problem["file"])
                    local_pairs += 1
                    if not pair_path.exists():
                        errors.append(f"{label}: missing pair JSON: {pair_path}")
        return local_pairs

    pair_count += validate_root(root, "main")

    experiment_manifest_path = public / "data" / "experiments.json"
    if not experiment_manifest_path.exists():
        errors.append(f"Missing experiment manifest: {experiment_manifest_path}")
    else:
        experiment_manifest = load(experiment_manifest_path)
        expected_items = {
            "main": 1560,
            "neutral_agent_ablation": 780,
            "sufficiency_repeatability": 390,
        }
        for experiment in experiment_manifest.get("experiments", []):
            experiment_id = experiment.get("id", "unknown")
            paths = [experiment.get("path")] if experiment.get("path") else []
            paths.extend(run["path"] for run in experiment.get("runs", []))
            for path in paths:
                root_path = public_path(path)
                if not root_path.exists():
                    errors.append(f"{experiment_id}: missing root index: {root_path}")
                    continue
                experiment_root = load(root_path)
                expected = expected_items.get(experiment_id)
                actual = experiment_root.get("totals", {}).get("items")
                if expected is not None and actual != expected:
                    errors.append(
                        f"{experiment_id}: expected {expected} items, found {actual}"
                    )
                if experiment_id != "main":
                    pair_count += validate_root(
                        experiment_root,
                        f"{experiment_id}/run-{experiment_root.get('run') or 'default'}",
                    )
            summary_path = experiment.get("summary_path")
            if summary_path and not public_path(summary_path).exists():
                errors.append(
                    f"{experiment_id}: missing summary: {public_path(summary_path)}"
                )

        prompt_examples_path = experiment_manifest.get("prompt_examples_path")
        if not prompt_examples_path:
            errors.append("Experiment manifest is missing prompt_examples_path")
        elif not public_path(prompt_examples_path).exists():
            errors.append(
                f"Missing prompt examples data: {public_path(prompt_examples_path)}"
            )
        else:
            prompt_examples = load(public_path(prompt_examples_path))
            languages = prompt_examples.get("languages", [])
            if len(languages) != 3:
                errors.append(
                    f"Prompt examples: expected 3 languages, found {len(languages)}"
                )
            for language in languages:
                cards = language.get("cards", [])
                if len(cards) != 11:
                    errors.append(
                        "Prompt examples: expected 11 cards for "
                        f"{language.get('language_code')}, found {len(cards)}"
                    )

    if errors:
        print("[FAIL]")
        for error in errors[:100]:
            print(" -", error)
        raise SystemExit(1)

    print(
        f"[OK] {len(root.get('datasets', []))} datasets, "
        f"{pair_count} pair files across all experiments validated"
    )


if __name__ == "__main__":
    main()
