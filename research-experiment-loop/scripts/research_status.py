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
    for experiment_id, experiment in experiments.items():
        if int(experiment.get("schema_version", 1)) < 3:
            continue
        latest = latest_experiment_state(experiment, events_by_experiment[experiment_id])
        if (
            latest.get("status") in TERMINAL_EXPERIMENT_STATUSES
            and latest.get("human_visual_confirmation") == "pending"
        ):
            pending_reviews.append(experiment_id)

    scheduler = scheduler_status(root)
    recommendations = scheduler.get("recommendations", [])
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
        "open_tasks": open_tasks,
        "pending_human_reviews": pending_reviews,
        "scheduler_available": scheduler.get("available", False),
        "scheduler_reason": scheduler.get("reason"),
        "recommendations": recommendations,
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
    print(f"Pending human reviews: {len(pending_reviews)}")
    if scheduler.get("available"):
        print(f"Scheduler recommendations: {len(recommendations)}")
        for recommendation in recommendations[:5]:
            print(
                f"- {recommendation.get('priority')} {recommendation.get('action_type')}: "
                f"{' '.join(recommendation.get('reasons', []))}"
            )
    else:
        print(f"Scheduler: unavailable ({scheduler.get('reason')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
