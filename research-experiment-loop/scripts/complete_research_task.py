#!/usr/bin/env python3
"""Resolve, defer, waive, or merge an advisory research scheduler task."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_state_lib import (
    TERMINAL_TASK_STATUSES,
    VALID_TASK_EVENT_STATUSES,
    append_jsonl,
    experiment_records,
    latest_task_state,
    load_jsonl,
    load_yaml,
    next_id,
    task_records,
    utc_now,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--status", choices=sorted(VALID_TASK_EVENT_STATUSES), required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--artifact-id", action="append", default=[])
    parser.add_argument("--insight-id", action="append", default=[])
    parser.add_argument("--next")
    parser.add_argument("--resume-condition")
    parser.add_argument("--merge-into")
    args = parser.parse_args()

    root = args.root.resolve()
    tasks, events = task_records(root)
    if args.task_id not in tasks:
        raise SystemExit(f"Unknown task id: {args.task_id}")
    latest = latest_task_state(tasks[args.task_id], events)
    if latest.get("status") in TERMINAL_TASK_STATUSES:
        raise SystemExit(f"Task is already terminal: {args.task_id}")
    if args.status == "deferred" and not args.resume_condition:
        raise SystemExit("A deferred task requires --resume-condition")
    if args.status == "merged":
        if not args.merge_into:
            raise SystemExit("A merged task requires --merge-into")
        if args.merge_into == args.task_id or args.merge_into not in tasks:
            raise SystemExit(f"Invalid merge target: {args.merge_into}")
        target = latest_task_state(tasks[args.merge_into], events)
        if target.get("status") in TERMINAL_TASK_STATUSES:
            raise SystemExit(f"Merge target is terminal: {args.merge_into}")

    research = root / "research"
    known_artifacts = {
        str(record.get("id"))
        for record in load_jsonl(research / "artifacts.jsonl")
        if record.get("record_type") == "artifact"
    }
    known_insights = {
        str(record.get("id"))
        for record in load_jsonl(research / "insights.jsonl")
        if record.get("record_type") == "insight"
    }
    unknown_artifacts = sorted(set(args.artifact_id) - known_artifacts)
    unknown_insights = sorted(set(args.insight_id) - known_insights)
    if unknown_artifacts:
        raise SystemExit(f"Unknown artifact ids: {', '.join(unknown_artifacts)}")
    if unknown_insights:
        raise SystemExit(f"Unknown insight ids: {', '.join(unknown_insights)}")

    _, experiment_events = experiment_records(root)
    closed_count = sum(
        event.get("event_type") == "closure" for event in experiment_events
    )
    registry = research / "tasks.jsonl"
    event = {
        "record_type": "task_event",
        "schema_version": 1,
        "id": next_id(registry, "TEVT"),
        "task_id": args.task_id,
        "created_at": utc_now(),
        "status": args.status,
        "result": args.result,
        "artifact_ids": args.artifact_id,
        "insight_ids": args.insight_id,
        "next": args.next,
        "resume_condition": args.resume_condition,
        "merge_into": args.merge_into,
        "closed_experiment_count": closed_count,
    }
    append_jsonl(registry, event)

    scheduler = load_yaml(research / "scheduler.yaml")
    discussion_root = Path(str(scheduler.get("discussion_root", "discussion/scheduler")))
    if not discussion_root.is_absolute():
        discussion_root = root / discussion_root
    cards = list(discussion_root.glob(f"{args.task_id}-*.md")) if discussion_root.exists() else []
    for card in cards:
        with card.open("a", encoding="utf-8") as handle:
            handle.write(
                "\n## 结案\n\n"
                f"- 状态：`{args.status}`\n"
                f"- 结果：{args.result}\n"
                f"- 下一步：{args.next or 'none'}\n"
                f"- 恢复条件：{args.resume_condition or 'none'}\n"
                f"- 合并到：`{args.merge_into or 'none'}`\n"
            )
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
