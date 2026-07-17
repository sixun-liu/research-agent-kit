#!/usr/bin/env python3
"""Close an experiment, append its verdict event, and clear active state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_state_lib import (
    TERMINAL_EXPERIMENT_STATUSES,
    VALID_CONFIRMATIONS,
    VALID_DECISIONS,
    VALID_PROGRESS_TYPES,
    append_jsonl,
    elapsed_hours,
    experiment_records,
    latest_experiment_state,
    load_jsonl,
    next_id,
    resolve_experiment_id,
    update_project_state,
    utc_now,
)


CHECKLIST_VALUES = ("updated", "not_required", "pending")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--experiment-id")
    parser.add_argument("--verdict", required=True, help="Project-specific compact verdict code")
    parser.add_argument("--decision", choices=sorted(VALID_DECISIONS), required=True)
    parser.add_argument("--observation", action="append", default=[])
    parser.add_argument("--interpretation", required=True)
    parser.add_argument("--limitation", action="append", default=[])
    parser.add_argument("--artifact-id", action="append", default=[])
    parser.add_argument("--next", required=True)
    parser.add_argument("--progress-type", choices=sorted(VALID_PROGRESS_TYPES), required=True)
    parser.add_argument("--progress-note")
    parser.add_argument("--failure-axis")
    parser.add_argument("--wall-hours", type=float)
    parser.add_argument("--compute-hours", type=float)
    parser.add_argument("--theory-output")
    parser.add_argument("--practice-output")
    parser.add_argument("--action-status", choices=("occurred", "absent", "not_applicable"))
    parser.add_argument(
        "--completion-status", choices=("confirmed", "failed", "not_applicable")
    )
    parser.add_argument("--human-confirmation", choices=sorted(VALID_CONFIRMATIONS))
    parser.add_argument("--scoreboard-status", choices=CHECKLIST_VALUES)
    parser.add_argument("--claim-status", choices=CHECKLIST_VALUES)
    args = parser.parse_args()

    if not args.observation:
        raise SystemExit("At least one --observation is required")
    if args.wall_hours is not None and args.wall_hours < 0:
        raise SystemExit("--wall-hours must be non-negative")
    if args.compute_hours is not None and args.compute_hours < 0:
        raise SystemExit("--wall-hours and --compute-hours must be non-negative")
    if args.decision == "negative" and not args.failure_axis:
        raise SystemExit("A negative decision requires --failure-axis")

    root = args.root.resolve()
    experiment_id = resolve_experiment_id(root, args.experiment_id)
    experiments, events = experiment_records(root)
    experiment = experiments[experiment_id]
    latest = latest_experiment_state(experiment, events)
    if latest.get("status") in TERMINAL_EXPERIMENT_STATUSES:
        raise SystemExit(f"Experiment is already terminal: {experiment_id}")
    if int(experiment.get("schema_version", 1)) >= 2 and not any(
        event.get("event_type") == "provenance_freeze"
        for event in events
        if event.get("experiment_id") == experiment_id
    ):
        raise SystemExit("A v2 experiment must be frozen before closure")
    cycle_class = str(experiment.get("cycle_class") or "formal")
    if args.decision == "promote" and not experiment.get("formal_claim_eligible", True):
        raise SystemExit(f"A {cycle_class} cycle is diagnostic-only and cannot be promoted")
    if cycle_class in {"formal", "replication"} and any(
        value is None
        for value in (args.human_confirmation, args.scoreboard_status, args.claim_status)
    ):
        raise SystemExit(
            "A formal or replication cycle requires --human-confirmation, --scoreboard-status, and --claim-status"
        )
    limitations = list(args.limitation)
    if not limitations:
        default_limitations = {
            "probe": "Diagnostic probe; insufficient for a formal performance claim.",
            "oracle": "Debug-only oracle evidence; forbidden from runtime or headline claims.",
            "instrumentation": "Instrumentation result; method efficacy was not evaluated.",
        }
        default_limitation = default_limitations.get(cycle_class)
        if not default_limitation:
            raise SystemExit("At least one --limitation is required for a formal or replication cycle")
        limitations = [default_limitation]

    experiment_events = [
        event for event in events if event.get("experiment_id") == experiment_id
    ]
    checkpoints = sorted(
        [event for event in experiment_events if event.get("event_type") == "checkpoint"],
        key=lambda value: str(value.get("created_at", "")),
    )
    last_checkpoint = checkpoints[-1] if checkpoints else {}
    action_status = args.action_status or last_checkpoint.get("expected_action_status")
    completion_status = args.completion_status or last_checkpoint.get("completion_signal_status")
    if action_status not in {"occurred", "absent", "not_applicable"}:
        raise SystemExit("Resolve --action-status explicitly or in the latest checkpoint")
    if completion_status not in {"confirmed", "failed", "not_applicable"}:
        raise SystemExit("Resolve --completion-status explicitly or in the latest checkpoint")
    if args.decision == "promote" and action_status != "occurred":
        raise SystemExit("A promoted experiment must confirm that the expected action occurred")
    if args.decision == "promote" and completion_status != "confirmed":
        raise SystemExit("A promoted experiment must confirm its completion signals")
    if action_status == "absent" and args.decision not in {
        "inconclusive",
        "invalid_provenance",
    }:
        raise SystemExit("An absent expected action cannot support a positive or negative method verdict")
    if completion_status == "failed" and args.decision not in {
        "inconclusive",
        "invalid_provenance",
    }:
        raise SystemExit("Failed completion signals require inconclusive or invalid_provenance")
    checkpoint_compute = sum(
        float(event.get("compute_hours_delta") or 0.0)
        for event in experiment_events
        if event.get("event_type") == "checkpoint"
    )
    wall_hours = (
        args.wall_hours
        if args.wall_hours is not None
        else elapsed_hours(str(experiment.get("created_at")))
    )
    compute_hours = args.compute_hours if args.compute_hours is not None else checkpoint_compute
    progress_note = args.progress_note or args.interpretation
    work_mode = experiment.get("work_mode")
    theory_output = args.theory_output or (
        args.interpretation if work_mode in {"theory", "mixed"} else None
    )
    practice_output = args.practice_output or (
        " ".join(args.observation) if work_mode in {"practice", "instrumentation", "mixed"} else None
    )
    if work_mode == "theory" and not theory_output:
        raise SystemExit("A theory cycle must record a theory output")
    if work_mode in {"practice", "instrumentation"} and not practice_output:
        raise SystemExit(f"A {work_mode} cycle must record a practice output")
    if work_mode == "mixed" and (not theory_output or not practice_output):
        raise SystemExit("A mixed cycle must record both theory and practice outputs")
    human_confirmation = args.human_confirmation or "not_required"
    scoreboard_status = args.scoreboard_status or "not_required"
    claim_status = args.claim_status or "not_required"
    if args.decision == "promote" and "pending" in (scoreboard_status, claim_status):
        raise SystemExit("A promoted experiment cannot close with pending scoreboard or claim status")

    artifacts = {
        str(record.get("id"))
        for record in load_jsonl(root / "research" / "artifacts.jsonl")
        if record.get("record_type") == "artifact"
    }
    unknown_artifacts = sorted(set(args.artifact_id) - artifacts)
    if unknown_artifacts:
        raise SystemExit(f"Unknown artifact ids: {', '.join(unknown_artifacts)}")
    if args.decision == "promote" and not args.artifact_id:
        raise SystemExit("A promoted experiment must register at least one artifact")

    registry = root / "research" / "experiments.jsonl"
    closed_at = utc_now()
    event = {
        "record_type": "experiment_event",
        "schema_version": 2,
        "id": next_id(registry, "EVT"),
        "experiment_id": experiment_id,
        "created_at": closed_at,
        "event_type": "closure",
        "status": "complete",
        "verdict": args.verdict,
        "decision": args.decision,
        "observations": args.observation,
        "interpretation": args.interpretation,
        "limitations": limitations,
        "artifacts": args.artifact_id,
        "next": args.next,
        "progress_type": args.progress_type,
        "progress_note": progress_note,
        "failure_axis": args.failure_axis,
        "wall_hours": wall_hours,
        "compute_hours": compute_hours,
        "time_accounting": {
            "wall": "explicit" if args.wall_hours is not None else "elapsed_from_preregistration",
            "compute": "explicit" if args.compute_hours is not None else "checkpoint_sum",
        },
        "theory_output": theory_output,
        "practice_output": practice_output,
        "expected_action_status": action_status,
        "completion_signal_status": completion_status,
        "human_visual_confirmation": human_confirmation,
        "closure_checklist": {
            "scoreboard": scoreboard_status,
            "claim_registry": claim_status,
            "artifacts_registered": bool(args.artifact_id),
            "human_review": human_confirmation,
        },
    }
    append_jsonl(registry, event)

    card = root / "research" / "cards" / f"{experiment_id}.md"
    if card.exists():
        with card.open("a", encoding="utf-8") as handle:
            handle.write(
                "\n## 最终裁决\n\n"
                f"- Verdict：`{args.verdict}`\n"
                f"- Decision：`{args.decision}`\n"
                f"- 解释：{args.interpretation}\n"
                f"- 预期动作：`{action_status}`；完成信号：`{completion_status}`\n"
                f"- 进展：`{args.progress_type}`，{progress_note}\n"
                f"- 耗时：wall `{wall_hours:.3f}h`；compute `{compute_hours:.3f}h`\n"
                f"- 观察：{'；'.join(args.observation)}\n"
                f"- 限制：{'；'.join(limitations)}\n"
                f"- 下一步：{args.next}\n"
                f"- 人工确认：`{human_confirmation}`\n"
                f"- Scoreboard：`{scoreboard_status}`；Claim registry：`{claim_status}`\n"
            )

    update_project_state(root, active_experiment_id=None)
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
