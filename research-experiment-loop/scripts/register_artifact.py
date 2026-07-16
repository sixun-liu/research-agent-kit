#!/usr/bin/env python3
"""Register an existing research artifact with provenance metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_state_lib import (
    append_jsonl,
    canonical_repo,
    git_snapshot,
    load_yaml,
    next_id,
    resolve_project_path,
    resolve_experiment_id,
    sha256_file,
    utc_now,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--experiment-id")
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--kind", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--provenance-quality",
        choices=("fingerprinted", "historical_only", "derived_from_fingerprinted"),
        required=True,
    )
    parser.add_argument("--human-review", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    experiment_id = resolve_experiment_id(root, args.experiment_id)
    artifact_path = resolve_project_path(root, args.path)
    if not artifact_path.exists():
        raise SystemExit(f"Artifact does not exist: {artifact_path}")

    state = load_yaml(root / "research" / "project_state.yaml")
    snapshot = git_snapshot(canonical_repo(root, state))
    registry = root / "research" / "artifacts.jsonl"
    record = {
        "record_type": "artifact",
        "schema_version": 2,
        "id": next_id(registry, "ART"),
        "experiment_id": experiment_id,
        "created_at": utc_now(),
        "kind": args.kind,
        "title": args.title,
        "path": str(artifact_path),
        "is_directory": artifact_path.is_dir(),
        "sha256": sha256_file(artifact_path) if artifact_path.is_file() else None,
        "exists_at_registration": True,
        "provenance_quality": args.provenance_quality,
        "analysis_commit": snapshot["commit"],
        "analysis_tracked_clean": snapshot["tracked_clean"],
        "human_review": args.human_review,
    }
    append_jsonl(registry, record)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
