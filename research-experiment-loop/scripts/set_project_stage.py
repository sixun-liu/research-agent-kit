#!/usr/bin/env python3
"""Set the project stage, primary problem, and canonical baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_state_lib import (
    VALID_STAGES,
    attribution_fields,
    load_yaml,
    primary_repository_snapshot,
    repository_snapshot_issues,
    repository_snapshots,
    update_project_state,
    utc_now,
    write_yaml,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--stage", choices=sorted(VALID_STAGES), required=True)
    parser.add_argument("--north-star", required=True)
    parser.add_argument("--primary-problem", required=True)
    parser.add_argument("--active-candidate")
    parser.add_argument("--baseline-id")
    parser.add_argument("--baseline-name")
    parser.add_argument("--baseline-config")
    parser.add_argument("--evaluation-protocol")
    parser.add_argument("--parked-lane", action="append", default=[])
    parser.add_argument("--stage-exit-gate", action="append", default=[])
    parser.add_argument("--domain")
    parser.add_argument("--primary-metric", action="append", default=[])
    parser.add_argument("--tail-metric", action="append", default=[])
    parser.add_argument("--forbidden-input", action="append", default=[])
    parser.add_argument("--promotion-gate", action="append", default=[])
    parser.add_argument("--review-requirement", action="append", default=[])
    parser.add_argument("--created-by")
    parser.add_argument("--approved-by")
    args = parser.parse_args()

    root = args.root.resolve()
    state_path = root / "research" / "project_state.yaml"
    if not state_path.exists():
        raise SystemExit("Research state is missing; run init_research_state.py first")
    state = load_yaml(state_path)
    if state.get("active_experiment_id"):
        raise SystemExit("Refusing to change project stage while an experiment is active")
    if not args.stage_exit_gate:
        raise SystemExit("At least one --stage-exit-gate is required")
    baseline_values = (
        args.baseline_id,
        args.baseline_name,
        args.baseline_config,
        args.evaluation_protocol,
    )
    if any(baseline_values) and not all(baseline_values):
        raise SystemExit("Baseline arguments must be supplied together")
    if args.stage != "understanding" and not all(baseline_values):
        raise SystemExit(
            "Entering reproduction or a later stage requires a freshly frozen canonical baseline"
        )

    snapshots = repository_snapshots(root, state)
    issues = repository_snapshot_issues(snapshots, require_clean=True)
    if issues:
        raise SystemExit("Refusing to freeze a canonical baseline: " + "; ".join(issues))
    snapshot = primary_repository_snapshot(snapshots)

    profile_path = root / "research" / "profile.yaml"
    if profile_path.exists():
        profile = load_yaml(profile_path)
    else:
        if not args.primary_metric or not args.promotion_gate:
            raise SystemExit(
                "Migrating a legacy project requires --primary-metric and --promotion-gate"
            )
        profile = {
            "schema_version": 1,
            "domain": args.domain or "generic",
            "primary_metrics": [],
            "tail_metrics": [],
            "forbidden_inputs": [],
            "promotion_gates": [],
            "review_requirements": [],
        }
    if args.domain:
        profile["domain"] = args.domain
    updates = {
        "primary_metrics": args.primary_metric,
        "tail_metrics": args.tail_metric,
        "forbidden_inputs": args.forbidden_input,
        "promotion_gates": args.promotion_gate,
        "review_requirements": args.review_requirement,
    }
    for field, values in updates.items():
        if values:
            profile[field] = values
    write_yaml(profile_path, profile)

    tasks_path = root / "research" / "tasks.jsonl"
    if not tasks_path.exists():
        tasks_path.write_text(
            json.dumps(
                {
                    "record_type": "registry_meta",
                    "schema_version": 1,
                    "registry": "tasks",
                    "created_at": utc_now(),
                    "id_prefix": "TASK",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    scheduler_path = root / "research" / "scheduler.yaml"
    if not scheduler_path.exists():
        scheduler_template = (
            Path(__file__).resolve().parents[1]
            / "assets"
            / "project-template"
            / "SCHEDULER.yaml"
        ).read_text(encoding="utf-8")
        scheduler_path.write_text(scheduler_template, encoding="utf-8")

    baseline = state.get("canonical_baseline")
    if all(baseline_values):
        baseline = {
            "id": args.baseline_id,
            "name": args.baseline_name,
            "repo_commit": snapshot["commit"],
            "config": args.baseline_config,
            "evaluation_protocol": args.evaluation_protocol,
        }
    attribution = attribution_fields(args.created_by, args.approved_by)
    updated = update_project_state(
        root,
        schema_version=max(int(state.get("schema_version", 1)), 4),
        stage=args.stage,
        north_star=args.north_star,
        primary_problem=args.primary_problem,
        active_candidate=args.active_candidate,
        canonical_baseline=baseline,
        parked_lanes=args.parked_lane,
        stage_exit_gates=args.stage_exit_gate,
        canonical_repo={
            "path": snapshot["repo"],
            "branch": snapshot["branch"],
            "commit": snapshot["commit"],
            "tracked_clean_at_snapshot": snapshot["tracked_clean"],
        },
        repository_snapshots=snapshots,
        updated_by=attribution.get("created_by"),
        approved_by=attribution.get("approved_by"),
    )
    print(
        json.dumps(
            {
                "stage": updated["stage"],
                "primary_problem": updated["primary_problem"],
                "canonical_baseline": updated["canonical_baseline"],
                "stage_exit_gates": updated["stage_exit_gates"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
