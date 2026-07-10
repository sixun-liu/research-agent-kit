#!/usr/bin/env python3
"""Audit research registries, references, artifacts, review paths, and Git state."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


REGISTRIES = ("experiments.jsonl", "insights.jsonl", "claims.jsonl", "artifacts.jsonl")
VALID_CONFIRMATIONS = {"pending", "confirmed", "disagreed", "not_required"}


def load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("PyYAML is required to audit project_state.yaml") from exc
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("project_state.yaml must contain a mapping")
    return value


def load_jsonl(path: Path, errors: list[str]) -> list[dict]:
    records: list[dict] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{number}: invalid JSON: {exc}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{path}:{number}: record must be an object")
            continue
        records.append(value)
    return records


def git(repo: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    root = args.root.resolve()
    research = root / "research"
    errors: list[str] = []
    warnings: list[str] = []
    state_path = research / "project_state.yaml"
    if not state_path.exists():
        errors.append(f"missing {state_path}")
        state: dict = {}
    else:
        try:
            state = load_yaml(state_path)
        except Exception as exc:
            errors.append(f"invalid {state_path}: {exc}")
            state = {}

    all_records: dict[str, list[dict]] = {}
    ids: dict[str, str] = {}
    for filename in REGISTRIES:
        path = research / filename
        if not path.exists():
            errors.append(f"missing {path}")
            continue
        records = load_jsonl(path, errors)
        all_records[filename] = records
        if not records or records[0].get("record_type") != "registry_meta":
            errors.append(f"{path}: first record must be registry_meta")
        for record in records[1:]:
            record_id = record.get("id")
            if not record_id:
                errors.append(f"{path}: non-meta record lacks id")
            elif record_id in ids:
                errors.append(f"duplicate id {record_id}: {ids[record_id]} and {path}")
            else:
                ids[str(record_id)] = str(path)

    experiments = {
        record.get("id"): record
        for record in all_records.get("experiments.jsonl", [])[1:]
        if record.get("record_type") == "experiment"
    }
    active_id = state.get("active_experiment_id")
    if active_id and active_id not in experiments:
        errors.append(f"active_experiment_id {active_id} is not registered")
    if active_id:
        card = research / "cards" / f"{active_id}.md"
        if not card.exists():
            errors.append(f"active experiment card missing: {card}")

    for experiment_id, record in experiments.items():
        confirmation = record.get("human_visual_confirmation")
        if confirmation not in VALID_CONFIRMATIONS:
            errors.append(f"{experiment_id}: invalid human_visual_confirmation {confirmation!r}")
        review = record.get("human_review_path")
        if review and not Path(review).exists():
            errors.append(f"{experiment_id}: missing human review path {review}")
        if record.get("status") == "complete" and record.get("verdict") is None:
            errors.append(f"{experiment_id}: complete experiment lacks verdict")

    for artifact in all_records.get("artifacts.jsonl", [])[1:]:
        experiment_id = artifact.get("experiment_id")
        if experiment_id and experiment_id not in experiments:
            errors.append(f"{artifact.get('id')}: unknown experiment_id {experiment_id}")
        path_value = artifact.get("path")
        if artifact.get("exists_at_registration") and path_value and not Path(path_value).exists():
            errors.append(f"{artifact.get('id')}: registered artifact missing: {path_value}")

    repo_value = state.get("canonical_repo", {}).get("path") if isinstance(state.get("canonical_repo"), dict) else None
    if repo_value:
        repo = Path(repo_value)
        code, commit = git(repo, "rev-parse", "HEAD")
        if code:
            errors.append(f"canonical repo is not a Git repository: {repo}")
        else:
            expected = str(state.get("canonical_repo", {}).get("commit", ""))
            if expected and expected != "unknown" and commit != expected:
                warnings.append(f"canonical repo commit drift: recorded {expected}, current {commit}")
            _, tracked = git(repo, "status", "--porcelain", "--untracked-files=no")
            if tracked:
                warnings.append("canonical repo has tracked changes")
    else:
        warnings.append("canonical_repo.path is not recorded")

    result = {
        "root": str(root),
        "active_experiment_id": active_id,
        "record_counts": {name: len(rows) for name, rows in all_records.items()},
        "errors": errors,
        "warnings": warnings,
        "ok": not errors and (not warnings or not args.strict),
    }
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Research state: {root}")
        print(f"Active experiment: {active_id or 'none'}")
        print(f"Errors: {len(errors)}; warnings: {len(warnings)}")
        for value in errors:
            print(f"ERROR: {value}")
        for value in warnings:
            print(f"WARN: {value}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
