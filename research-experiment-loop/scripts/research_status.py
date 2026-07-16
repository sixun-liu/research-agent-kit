#!/usr/bin/env python3
"""Show a read-only compact research control-plane status."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from research_state_lib import (
    TERMINAL_EXPERIMENT_STATUSES,
    TERMINAL_TASK_STATUSES,
    elapsed_hours,
    experiment_records,
    latest_experiment_state,
    latest_task_state,
    load_yaml,
    task_records,
)


def scheduler_status(root: Path) -> dict[str, Any]:
    scheduler = root / "research" / "scheduler.yaml"
    if not scheduler.exists():
        return {"available": False, "recommendations": [], "reason": "scheduler not configured"}
    script = Path(__file__).with_name("evaluate_research_scheduler.py")
    completed = subprocess.run(
        [sys.executable, str(script), "--root", str(root), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        return {
            "available": False,
            "recommendations": [],
            "reason": completed.stderr.strip() or completed.stdout.strip(),
        }
    value = json.loads(completed.stdout)
    value["available"] = True
    return value


def audit_status(root: Path) -> dict[str, Any]:
    script = Path(__file__).with_name("audit_research_state.py")
    completed = subprocess.run(
        [sys.executable, str(script), "--root", str(root), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    if not completed.stdout.strip():
        return {
            "available": False,
            "strict_ok": False,
            "errors": [completed.stderr.strip() or "audit produced no output"],
            "warnings": [],
        }
    value = json.loads(completed.stdout)
    value["available"] = True
    value["strict_ok"] = not value.get("errors") and not value.get("warnings")
    return value


def infer_next_action(
    active: dict[str, Any] | None,
    audit: dict[str, Any],
    orphan_open_experiments: list[str],
    open_tasks: list[dict[str, Any]],
    pending_reviews: list[str],
    recommendations: list[dict[str, Any]],
) -> dict[str, str]:
    if not audit.get("strict_ok", False):
        return {
            "action": "repair_audit",
            "reason": (
                "The control plane has audit errors or warnings that can invalidate evidence."
            ),
        }
    if active:
        if not active.get("provenance_frozen"):
            return {
                "action": "freeze_provenance",
                "reason": f"{active['id']} is active but has no provenance freeze.",
            }
        checkpoint = active.get("last_checkpoint") or {}
        if checkpoint.get("expected_action_status") == "absent":
            return {
                "action": "resolve_missing_action",
                "reason": "The latest checkpoint reports that the expected action is absent.",
            }
        if checkpoint.get("completion_signal_status") == "confirmed":
            return {
                "action": "observe_or_close",
                "reason": (
                    "The latest checkpoint confirmed completion; record observations or close."
                ),
            }
        return {
            "action": "run_or_checkpoint",
            "reason": (
                "Continue the cheapest discriminating evidence step and checkpoint at a boundary."
            ),
        }
    if orphan_open_experiments:
        return {
            "action": f"reconcile_orphan:{orphan_open_experiments[0]}",
            "reason": (
                "An experiment is nonterminal but is not registered as the active experiment."
            ),
        }
    if open_tasks:
        task = open_tasks[0]
        return {
            "action": f"resolve_task:{task['id']}",
            "reason": f"The highest-priority open scheduler task is {task['action_type']}.",
        }
    if pending_reviews:
        return {
            "action": f"human_review:{pending_reviews[0]}",
            "reason": "A closed formal experiment still needs human review.",
        }
    if recommendations:
        recommendation = recommendations[0]
        return {
            "action": f"review_interrupt:{recommendation.get('action_type')}",
            "reason": "The read-only scheduler has an unqueued recommendation.",
        }
    return {
        "action": "open_next_cycle_or_synthesize",
        "reason": "No active experiment or blocking control-plane debt remains.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    root = args.root.resolve()
    state = load_yaml(root / "research" / "project_state.yaml")
    experiments, events = experiment_records(root)
    events_by_experiment: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        events_by_experiment[str(event.get("experiment_id"))].append(event)

    active_id = state.get("active_experiment_id")
    active: dict[str, Any] | None = None
    if active_id and str(active_id) in experiments:
        experiment = experiments[str(active_id)]
        experiment_events = events_by_experiment[str(active_id)]
        checkpoints = sorted(
            [event for event in experiment_events if event.get("event_type") == "checkpoint"],
            key=lambda value: str(value.get("created_at", "")),
        )
        active = {
            "id": active_id,
            "title": experiment.get("title"),
            "cycle_class": experiment.get("cycle_class", "formal"),
            "work_mode": experiment.get("work_mode"),
            "status": latest_experiment_state(experiment, experiment_events).get("status"),
            "wall_hours": elapsed_hours(str(experiment.get("created_at"))),
            "checkpoint_count": len(checkpoints),
            "compute_hours_recorded": sum(
                float(event.get("compute_hours_delta") or 0.0) for event in checkpoints
            ),
            "last_checkpoint": checkpoints[-1] if checkpoints else None,
            "provenance_frozen": any(
                event.get("event_type") == "provenance_freeze" for event in experiment_events
            ),
        }

    tasks, task_events = task_records(root)
    task_events_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in task_events:
        task_events_by_id[str(event.get("task_id"))].append(event)
    open_tasks = []
    for task_id, task in tasks.items():
        latest = latest_task_state(task, task_events_by_id[task_id])
        if latest.get("status") not in TERMINAL_TASK_STATUSES:
            open_tasks.append(
                {
                    "id": task_id,
                    "action_type": task.get("action_type"),
                    "priority": task.get("priority"),
                    "status": latest.get("status"),
                    "resume_condition": latest.get("resume_condition"),
                }
            )
    open_tasks.sort(key=lambda value: (str(value.get("priority")), str(value.get("id"))))

    pending_reviews = []
    orphan_candidates: list[tuple[str, str]] = []
    legacy_open_statuses = {
        "active",
        "frozen",
        "offline_in_progress",
        "online_approved",
        "preregistered",
        "running",
    }
    for experiment_id, experiment in experiments.items():
        latest = latest_experiment_state(experiment, events_by_experiment[experiment_id])
        schema_version = int(experiment.get("schema_version", 1))
        status = str(latest.get("status") or "")
        is_open = (
            status not in TERMINAL_EXPERIMENT_STATUSES
            if schema_version >= 2
            else status in legacy_open_statuses
        )
        if is_open and experiment_id != str(active_id or ""):
            orphan_candidates.append(
                (str(latest.get("updated_at") or experiment.get("created_at") or ""), experiment_id)
            )
        if int(experiment.get("schema_version", 1)) < 3:
            continue
        if (
            latest.get("status") in TERMINAL_EXPERIMENT_STATUSES
            and latest.get("human_visual_confirmation") == "pending"
        ):
            pending_reviews.append(experiment_id)
    orphan_open_experiments = [
        experiment_id
        for _, experiment_id in sorted(orphan_candidates, reverse=True)
    ]

    scheduler = scheduler_status(root)
    recommendations = scheduler.get("recommendations", [])
    audit = audit_status(root)
    next_action = infer_next_action(
        active,
        audit,
        orphan_open_experiments,
        open_tasks,
        pending_reviews,
        recommendations,
    )
    result = {
        "root": str(root),
        "stage": state.get("stage"),
        "primary_problem": state.get("primary_problem"),
        "canonical_baseline_id": (
            state.get("canonical_baseline", {}).get("id")
            if isinstance(state.get("canonical_baseline"), dict)
            else None
        ),
        "active_experiment": active,
        "orphan_open_experiments": orphan_open_experiments,
        "open_tasks": open_tasks,
        "pending_human_reviews": pending_reviews,
        "scheduler_available": scheduler.get("available", False),
        "scheduler_reason": scheduler.get("reason"),
        "recommendations": recommendations,
        "audit": {
            "available": audit.get("available", False),
            "strict_ok": audit.get("strict_ok", False),
            "errors": audit.get("errors", []),
            "warnings": audit.get("warnings", []),
        },
        "next_action": next_action,
    }
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"Research status: {root}")
    print(f"Stage: {result['stage'] or 'unknown'}")
    print(f"Primary problem: {result['primary_problem'] or 'unassigned'}")
    print(f"Canonical baseline: {result['canonical_baseline_id'] or 'unassigned'}")
    if active:
        print(
            f"Active: {active['id']} [{active['cycle_class']}/{active['work_mode']}] "
            f"wall={active['wall_hours']:.2f}h compute={active['compute_hours_recorded']:.2f}h"
        )
        checkpoint = active.get("last_checkpoint")
        print(f"Last checkpoint: {checkpoint.get('note') if checkpoint else 'none'}")
    else:
        print("Active: none")
    print(f"Open scheduler tasks: {len(open_tasks)}")
    print(f"Orphan open experiments: {len(orphan_open_experiments)}")
    print(f"Pending human reviews: {len(pending_reviews)}")
    print(
        f"Strict audit: {'ok' if audit.get('strict_ok') else 'needs attention'} "
        f"({len(audit.get('errors', []))} errors, {len(audit.get('warnings', []))} warnings)"
    )
    if scheduler.get("available"):
        print(f"Scheduler recommendations: {len(recommendations)}")
        for recommendation in recommendations[:5]:
            print(
                f"- {recommendation.get('priority')} {recommendation.get('action_type')}: "
                f"{' '.join(recommendation.get('reasons', []))}"
            )
    else:
        print(f"Scheduler: unavailable ({scheduler.get('reason')})")
    print(f"Next action: {next_action['action']} - {next_action['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
