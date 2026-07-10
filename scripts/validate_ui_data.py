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

    for dataset in root.get("datasets", []):
        dataset_path = public_path(dataset["path"])
        if not dataset_path.exists():
            errors.append(f"Missing dataset index: {dataset_path}")
            continue
        dataset_index = load(dataset_path)
        for category in dataset_index.get("categories", []):
            category_path = public_path(category["path"])
            if not category_path.exists():
                errors.append(f"Missing category index: {category_path}")
                continue
            category_index = load(category_path)
            for problem in category_index.get("problems", []):
                pair_path = public_path(problem["file"])
                pair_count += 1
                if not pair_path.exists():
                    errors.append(f"Missing pair JSON: {pair_path}")

    if errors:
        print("[FAIL]")
        for error in errors[:100]:
            print(" -", error)
        raise SystemExit(1)

    print(f"[OK] {len(root.get('datasets', []))} datasets, {pair_count} pair files validated")


if __name__ == "__main__":
    main()
