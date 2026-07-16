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
    append_jsonl,
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
    parser.add_argument("--action-status", choices=("occurred", "absent", "not_applicable"), required=True)
    parser.add_argument(
        "--completion-status", choices=("confirmed", "failed", "not_applicable"), required=True
    )
    parser.add_argument("--human-confirmation", choices=sorted(VALID_CONFIRMATIONS), required=True)
    parser.add_argument("--scoreboard-status", choices=CHECKLIST_VALUES, required=True)
    parser.add_argument("--claim-status", choices=CHECKLIST_VALUES, required=True)
    args = parser.parse_args()

    if not args.observation:
        raise SystemExit("At least one --observation is required")
    if not args.limitation:
        raise SystemExit("At least one --limitation is required")
    if args.decision == "promote" and "pending" in (args.scoreboard_status, args.claim_status):
        raise SystemExit("A promoted experiment cannot close with pending scoreboard or claim status")
    if args.decision == "promote" and args.action_status != "occurred":
        raise SystemExit("A promoted experiment must confirm that the expected action occurred")
    if args.decision == "promote" and args.completion_status != "confirmed":
        raise SystemExit("A promoted experiment must confirm its completion signals")
    if args.action_status == "absent" and args.decision not in {"inconclusive", "invalid_provenance"}:
        raise SystemExit("An absent expected action cannot support a positive or negative method verdict")
    if args.completion_status == "failed" and args.decision not in {"inconclusive", "invalid_provenance"}:
        raise SystemExit("Failed completion signals require inconclusive or invalid_provenance")

    root = args.root.resolve()
    experiment_id = resolve_experiment_id(root, args.experiment_id)
    experiments, events = experiment_records(root)
    latest = latest_experiment_state(experiments[experiment_id], events)
    if latest.get("status") in TERMINAL_EXPERIMENT_STATUSES:
        raise SystemExit(f"Experiment is already terminal: {experiment_id}")
    if int(experiments[experiment_id].get("schema_version", 1)) >= 2 and not any(
        event.get("event_type") == "provenance_freeze"
        for event in events
        if event.get("experiment_id") == experiment_id
    ):
        raise SystemExit("A v2 experiment must be frozen before closure")

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
    event = {
        "record_type": "experiment_event",
        "schema_version": 2,
        "id": next_id(registry, "EVT"),
        "experiment_id": experiment_id,
        "created_at": utc_now(),
        "event_type": "closure",
        "status": "complete",
        "verdict": args.verdict,
        "decision": args.decision,
        "observations": args.observation,
        "interpretation": args.interpretation,
        "limitations": args.limitation,
        "artifacts": args.artifact_id,
        "next": args.next,
        "expected_action_status": args.action_status,
        "completion_signal_status": args.completion_status,
        "human_visual_confirmation": args.human_confirmation,
        "closure_checklist": {
            "scoreboard": args.scoreboard_status,
            "claim_registry": args.claim_status,
            "artifacts_registered": bool(args.artifact_id),
            "human_review": args.human_confirmation,
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
                f"- 预期动作：`{args.action_status}`；完成信号：`{args.completion_status}`\n"
                f"- 观察：{'；'.join(args.observation)}\n"
                f"- 限制：{'；'.join(args.limitation)}\n"
                f"- 下一步：{args.next}\n"
                f"- 人工确认：`{args.human_confirmation}`\n"
                f"- Scoreboard：`{args.scoreboard_status}`；Claim registry：`{args.claim_status}`\n"
            )

    update_project_state(root, active_experiment_id=None)
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
