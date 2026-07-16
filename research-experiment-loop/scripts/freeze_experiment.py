#!/usr/bin/env python3
"""Freeze an active experiment's runtime provenance before outcome inspection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_state_lib import (
    append_jsonl,
    canonical_repo,
    experiment_records,
    git_snapshot,
    latest_experiment_state,
    load_yaml,
    next_id,
    resolve_project_path,
    resolve_experiment_id,
    sha256_file,
    update_project_state,
    utc_now,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--experiment-id")
    parser.add_argument("--expanded-config", type=Path, required=True)
    parser.add_argument("--data-slice", required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    parser.add_argument("--seed-policy")
    parser.add_argument("--repeat-policy")
    parser.add_argument("--forbidden-input", action="append", default=[])
    parser.add_argument("--completion-signal", action="append", default=[])
    parser.add_argument("--command")
    args = parser.parse_args()

    root = args.root.resolve()
    experiment_id = resolve_experiment_id(root, args.experiment_id)
    experiments, events = experiment_records(root)
    experiment = experiments[experiment_id]
    if latest_experiment_state(experiment, events).get("status") in {
        "complete",
        "archived",
        "blocked",
    }:
        raise SystemExit(f"Experiment is already terminal: {experiment_id}")
    config = resolve_project_path(root, args.expanded_config)
    output_path = resolve_project_path(root, args.output_path)
    if not config.is_file():
        raise SystemExit(f"Expanded config does not exist: {config}")
    if output_path.exists():
        raise SystemExit(f"Refusing to freeze onto an existing output path: {output_path}")

    cycle_class = str(experiment.get("cycle_class") or "formal")
    seed_policy = args.seed_policy
    repeat_policy = args.repeat_policy
    if cycle_class == "formal" and (not seed_policy or not repeat_policy):
        raise SystemExit("A formal experiment requires --seed-policy and --repeat-policy")
    seed_policy = seed_policy or "deterministic or not applicable"
    repeat_policy = repeat_policy or "one discriminating diagnostic probe"
    completion_signals = args.completion_signal or list(experiment.get("completion_signals") or [])
    if not completion_signals:
        raise SystemExit("At least one completion signal is required in the card or freeze command")

    state = load_yaml(root / "research" / "project_state.yaml")
    profile_path = root / "research" / "profile.yaml"
    profile = load_yaml(profile_path) if profile_path.exists() else {}
    forbidden_inputs = args.forbidden_input or list(profile.get("forbidden_inputs") or [])
    snapshot = git_snapshot(canonical_repo(root, state))
    if not snapshot["tracked_clean"]:
        raise SystemExit("Refusing to freeze provenance with tracked Git changes")

    registry = root / "research" / "experiments.jsonl"
    event = {
        "record_type": "experiment_event",
        "schema_version": 2,
        "id": next_id(registry, "EVT"),
        "experiment_id": experiment_id,
        "created_at": utc_now(),
        "event_type": "provenance_freeze",
        "status": "frozen",
        "outcomes_seen": False,
        "provenance": {
            "analysis_repo": snapshot["repo"],
            "analysis_branch": snapshot["branch"],
            "analysis_commit": snapshot["commit"],
            "analysis_tracked_clean": snapshot["tracked_clean"],
            "expanded_config": str(config),
            "expanded_config_sha256": sha256_file(config),
            "data_slice": args.data_slice,
            "output_path": str(output_path),
            "output_exists_at_freeze": output_path.exists(),
            "seed_policy": seed_policy,
            "repeat_policy": repeat_policy,
            "forbidden_inputs": forbidden_inputs,
            "command": args.command,
            "completion_signals": completion_signals,
        },
    }
    append_jsonl(registry, event)
    update_project_state(
        root,
        canonical_repo={
            "path": snapshot["repo"],
            "branch": snapshot["branch"],
            "commit": snapshot["commit"],
            "tracked_clean_at_snapshot": snapshot["tracked_clean"],
        },
    )
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
