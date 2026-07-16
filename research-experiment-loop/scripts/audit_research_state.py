#!/usr/bin/env python3
"""Audit research registries, lifecycle closure, artifacts, stage, and Git state."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path

from research_state_lib import (
    REGISTRIES,
    TERMINAL_EXPERIMENT_STATUSES,
    VALID_CONFIRMATIONS,
    VALID_DECISIONS,
    VALID_PROGRESS_TYPES,
    VALID_STAGES,
    VALID_TASK_ACTIONS,
    VALID_WORK_MODES,
    latest_experiment_state,
    latest_task_state,
    load_yaml,
)


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


def nonempty_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(str(item).strip() for item in value)


def audit_v2_project(state: dict, research: Path, errors: list[str]) -> None:
    if state.get("stage") not in VALID_STAGES:
        errors.append(f"invalid project stage: {state.get('stage')!r}")
    for field in ("north_star", "primary_problem"):
        if not str(state.get(field) or "").strip():
            errors.append(f"project_state.yaml lacks {field}")
    baseline = state.get("canonical_baseline")
    if not isinstance(baseline, dict):
        errors.append("project_state.yaml lacks canonical_baseline mapping")
    else:
        for field in ("id", "name", "repo_commit", "config", "evaluation_protocol"):
            if not str(baseline.get(field) or "").strip():
                errors.append(f"canonical_baseline lacks {field}")
    if not nonempty_list(state.get("stage_exit_gates")):
        errors.append("project_state.yaml needs at least one stage_exit_gate")

    profile_path = research / "profile.yaml"
    if not profile_path.exists():
        errors.append(f"missing {profile_path}")
    else:
        try:
            profile = load_yaml(profile_path)
        except Exception as exc:
            errors.append(f"invalid {profile_path}: {exc}")
        else:
            if not str(profile.get("domain") or "").strip():
                errors.append("research/profile.yaml lacks domain")
            for field in (
                "primary_metrics",
                "tail_metrics",
                "forbidden_inputs",
                "promotion_gates",
                "review_requirements",
            ):
                if not isinstance(profile.get(field), list):
                    errors.append(f"research/profile.yaml field {field} must be a list")
            for field in ("primary_metrics", "promotion_gates"):
                if not nonempty_list(profile.get(field)):
                    errors.append(f"research/profile.yaml field {field} must be non-empty")


def audit_v3_project(research: Path, errors: list[str]) -> None:
    scheduler_path = research / "scheduler.yaml"
    tasks_path = research / "tasks.jsonl"
    if not scheduler_path.exists():
        errors.append(f"missing {scheduler_path}")
    else:
        try:
            scheduler = load_yaml(scheduler_path)
        except Exception as exc:
            errors.append(f"invalid {scheduler_path}: {exc}")
        else:
            if scheduler.get("mode") != "advisory":
                errors.append("research/scheduler.yaml mode must remain advisory")
            thresholds = scheduler.get("thresholds")
            if not isinstance(thresholds, dict):
                errors.append("research/scheduler.yaml lacks thresholds mapping")
            else:
                required = {
                    "valid_negative_streak",
                    "no_progress_cycles",
                    "no_progress_wall_hours",
                    "no_progress_compute_hours",
                    "theory_only_streak",
                    "practice_only_streak",
                    "cycles_without_synthesis",
                    "pending_human_reviews",
                }
                missing = sorted(required - thresholds.keys())
                if missing:
                    errors.append(f"research/scheduler.yaml lacks thresholds: {', '.join(missing)}")
                for name, value in thresholds.items():
                    if not isinstance(value, (int, float)) or value < 0:
                        errors.append(f"research/scheduler.yaml invalid threshold {name}: {value!r}")
                for name in (
                    "valid_negative_streak",
                    "no_progress_cycles",
                    "theory_only_streak",
                    "practice_only_streak",
                    "cycles_without_synthesis",
                    "pending_human_reviews",
                ):
                    if isinstance(thresholds.get(name), (int, float)) and thresholds[name] < 1:
                        errors.append(f"research/scheduler.yaml threshold {name} must be >= 1")
            priorities = scheduler.get("priorities")
            if not isinstance(priorities, dict):
                errors.append("research/scheduler.yaml lacks priorities mapping")
            else:
                missing = sorted(VALID_TASK_ACTIONS - priorities.keys())
                if missing:
                    errors.append(f"research/scheduler.yaml lacks priorities: {', '.join(missing)}")
                for action_type, priority in priorities.items():
                    if action_type in VALID_TASK_ACTIONS and priority not in {"P0", "P1", "P2", "P3", "P4"}:
                        errors.append(
                            f"research/scheduler.yaml invalid priority for {action_type}: {priority!r}"
                        )
            if not str(scheduler.get("discussion_root") or "").strip():
                errors.append("research/scheduler.yaml lacks discussion_root")
    if not tasks_path.exists():
        errors.append(f"missing {tasks_path}")


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

    state_schema = int(state.get("schema_version", 1)) if state else 1
    if state_schema >= 2:
        audit_v2_project(state, research, errors)
    if state_schema >= 3:
        audit_v3_project(research, errors)

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

    experiment_rows = all_records.get("experiments.jsonl", [])[1:]
    experiments = {
        str(record.get("id")): record
        for record in experiment_rows
        if record.get("record_type") == "experiment" and record.get("id")
    }
    events = [record for record in experiment_rows if record.get("record_type") == "experiment_event"]
    events_by_experiment: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        experiment_id = str(event.get("experiment_id") or "")
        if experiment_id not in experiments:
            errors.append(f"{event.get('id')}: unknown experiment_id {experiment_id!r}")
            continue
        events_by_experiment[experiment_id].append(event)

    active_id = state.get("active_experiment_id")
    if active_id and active_id not in experiments:
        errors.append(f"active_experiment_id {active_id} is not registered")
    if active_id:
        card = research / "cards" / f"{active_id}.md"
        if not card.exists():
            errors.append(f"active experiment card missing: {card}")

    open_v2: list[str] = []
    for experiment_id, record in experiments.items():
        latest = latest_experiment_state(record, events_by_experiment[experiment_id])
        confirmation = latest.get("human_visual_confirmation")
        if confirmation not in VALID_CONFIRMATIONS:
            errors.append(f"{experiment_id}: invalid human_visual_confirmation {confirmation!r}")
        review = record.get("human_review_path")
        if review and not Path(str(review)).exists():
            errors.append(f"{experiment_id}: missing human review path {review}")
        if latest.get("status") == "complete" and not latest.get("verdict"):
            errors.append(f"{experiment_id}: complete experiment lacks verdict")

        if int(record.get("schema_version", 1)) >= 2:
            for field in (
                "stage",
                "primary_problem",
                "baseline_id",
                "independent_variable",
                "expected_action",
            ):
                if not str(record.get(field) or "").strip():
                    errors.append(f"{experiment_id}: v2 experiment lacks {field}")
            for field in (
                "completion_signals",
                "alternatives",
                "controls",
                "primary_metrics",
                "stop_conditions",
            ):
                if not nonempty_list(record.get(field)):
                    errors.append(f"{experiment_id}: v2 experiment field {field} must be non-empty")
            for claim_id in record.get("claim_ids", []) or []:
                if not str(claim_id).startswith("C-") or claim_id not in ids:
                    errors.append(f"{experiment_id}: unknown claim id {claim_id}")
            if latest.get("status") not in TERMINAL_EXPERIMENT_STATUSES:
                open_v2.append(experiment_id)
            closure_events = [
                event for event in events_by_experiment[experiment_id] if event.get("event_type") == "closure"
            ]
            if latest.get("status") in TERMINAL_EXPERIMENT_STATUSES and not closure_events:
                errors.append(f"{experiment_id}: terminal v2 experiment lacks a closure event")
            if latest.get("status") in TERMINAL_EXPERIMENT_STATUSES and not any(
                event.get("event_type") == "provenance_freeze"
                for event in events_by_experiment[experiment_id]
            ):
                errors.append(f"{experiment_id}: terminal v2 experiment lacks a provenance freeze")
        if int(record.get("schema_version", 1)) >= 3:
            if not str(record.get("hypothesis_family") or "").strip():
                errors.append(f"{experiment_id}: v3 experiment lacks hypothesis_family")
            if record.get("work_mode") not in VALID_WORK_MODES:
                errors.append(f"{experiment_id}: invalid work_mode {record.get('work_mode')!r}")

    if active_id:
        latest_active = latest_experiment_state(experiments[active_id], events_by_experiment[active_id])
        if latest_active.get("status") in TERMINAL_EXPERIMENT_STATUSES:
            errors.append(f"active_experiment_id {active_id} is already terminal")
    if state_schema >= 2:
        if active_id is None and open_v2:
            errors.append(f"v2 experiments remain open while active_experiment_id is null: {', '.join(open_v2)}")
        if active_id and open_v2 != [active_id]:
            errors.append(f"active experiment does not match open v2 experiments: {open_v2}")

    artifact_records = [
        record
        for record in all_records.get("artifacts.jsonl", [])[1:]
        if record.get("record_type") == "artifact"
    ]
    artifact_ids = {str(record.get("id")) for record in artifact_records}
    for artifact in artifact_records:
        experiment_id = artifact.get("experiment_id")
        if experiment_id and experiment_id not in experiments:
            errors.append(f"{artifact.get('id')}: unknown experiment_id {experiment_id}")
        path_value = artifact.get("path")
        if artifact.get("exists_at_registration") and path_value and not Path(str(path_value)).exists():
            errors.append(f"{artifact.get('id')}: registered artifact missing: {path_value}")
        if (
            int(artifact.get("schema_version", 1)) >= 2
            and artifact.get("provenance_quality") == "fingerprinted"
            and not artifact.get("analysis_tracked_clean")
        ):
            errors.append(f"{artifact.get('id')}: fingerprinted artifact was registered from tracked-dirty code")

    for event in events:
        for artifact_id in event.get("artifacts", []) or []:
            if artifact_id not in artifact_ids:
                errors.append(f"{event.get('id')}: unknown artifact id {artifact_id}")
        if event.get("event_type") == "closure":
            decision = event.get("decision")
            if decision not in VALID_DECISIONS:
                errors.append(f"{event.get('id')}: invalid closure decision {decision!r}")
            action_status = event.get("expected_action_status")
            completion_status = event.get("completion_signal_status")
            if action_status not in {"occurred", "absent", "not_applicable"}:
                errors.append(f"{event.get('id')}: invalid expected_action_status {action_status!r}")
            if completion_status not in {"confirmed", "failed", "not_applicable"}:
                errors.append(f"{event.get('id')}: invalid completion_signal_status {completion_status!r}")
            if decision == "promote" and action_status != "occurred":
                errors.append(f"{event.get('experiment_id')}: promoted closure did not confirm expected action")
            if decision == "promote" and completion_status != "confirmed":
                errors.append(f"{event.get('experiment_id')}: promoted closure did not confirm completion signals")
            checklist = event.get("closure_checklist")
            if not isinstance(checklist, dict):
                errors.append(f"{event.get('id')}: closure event lacks closure_checklist")
            else:
                pending = [name for name, value in checklist.items() if value == "pending"]
                if pending:
                    warnings.append(f"{event.get('experiment_id')}: closure checklist pending: {', '.join(pending)}")
                if decision == "promote" and pending:
                    errors.append(f"{event.get('experiment_id')}: promoted closure has pending checklist items")
            experiment = experiments.get(str(event.get("experiment_id")), {})
            if int(experiment.get("schema_version", 1)) >= 3:
                if event.get("progress_type") not in VALID_PROGRESS_TYPES:
                    errors.append(f"{event.get('id')}: invalid progress_type {event.get('progress_type')!r}")
                if not str(event.get("progress_note") or "").strip():
                    errors.append(f"{event.get('id')}: v3 closure lacks progress_note")
                for field in ("wall_hours", "compute_hours"):
                    value = event.get(field)
                    if not isinstance(value, (int, float)) or value < 0:
                        errors.append(f"{event.get('id')}: invalid {field} {value!r}")
                if decision == "negative" and not str(event.get("failure_axis") or "").strip():
                    errors.append(f"{event.get('id')}: negative v3 closure lacks failure_axis")
                mode = experiment.get("work_mode")
                if mode == "theory" and not str(event.get("theory_output") or "").strip():
                    errors.append(f"{event.get('id')}: theory closure lacks theory_output")
                if mode in {"practice", "instrumentation"} and not str(
                    event.get("practice_output") or ""
                ).strip():
                    errors.append(f"{event.get('id')}: {mode} closure lacks practice_output")
                if mode == "mixed" and (
                    not str(event.get("theory_output") or "").strip()
                    or not str(event.get("practice_output") or "").strip()
                ):
                    errors.append(f"{event.get('id')}: mixed closure lacks theory/practice outputs")

    task_rows: list[dict] = []
    tasks_path = research / "tasks.jsonl"
    if tasks_path.exists():
        task_rows = load_jsonl(tasks_path, errors)
        if not task_rows or task_rows[0].get("record_type") != "registry_meta":
            errors.append(f"{tasks_path}: first record must be registry_meta")
    tasks = {
        str(record.get("id")): record
        for record in task_rows[1:]
        if record.get("record_type") == "research_task" and record.get("id")
    }
    task_events = [record for record in task_rows[1:] if record.get("record_type") == "task_event"]
    task_events_by_id: dict[str, list[dict]] = defaultdict(list)
    for record in task_rows[1:]:
        record_id = record.get("id")
        if not record_id:
            errors.append(f"{tasks_path}: non-meta record lacks id")
        elif record_id in ids:
            errors.append(f"duplicate id {record_id}: {ids[record_id]} and {tasks_path}")
        else:
            ids[str(record_id)] = str(tasks_path)
    for task_id, task in tasks.items():
        if task.get("action_type") not in VALID_TASK_ACTIONS:
            errors.append(f"{task_id}: invalid action_type {task.get('action_type')!r}")
        if task.get("status") != "queued":
            errors.append(f"{task_id}: initial task status must be queued")
        if not nonempty_list(task.get("reasons")) or not nonempty_list(task.get("source_ids")):
            errors.append(f"{task_id}: task requires reasons and source_ids")
        if not str(task.get("handler_contract") or "").strip():
            errors.append(f"{task_id}: task lacks handler_contract")
        if not nonempty_list(task.get("suggested_patterns")):
            errors.append(f"{task_id}: task lacks suggested_patterns")
        for source_id in task.get("source_ids", []) or []:
            if source_id not in ids:
                errors.append(f"{task_id}: unknown source id {source_id}")
        discussion_path = task.get("discussion_path")
        if discussion_path and not Path(str(discussion_path)).exists():
            errors.append(f"{task_id}: missing discussion card {discussion_path}")
    for event in task_events:
        task_id = str(event.get("task_id") or "")
        if task_id not in tasks:
            errors.append(f"{event.get('id')}: unknown task_id {task_id!r}")
            continue
        task_events_by_id[task_id].append(event)
        if event.get("status") not in {"complete", "cancelled"}:
            errors.append(f"{event.get('id')}: invalid task event status {event.get('status')!r}")
        if not str(event.get("result") or "").strip():
            errors.append(f"{event.get('id')}: task event lacks result")
        if not isinstance(event.get("closed_experiment_count"), int) or event.get(
            "closed_experiment_count"
        ) < 0:
            errors.append(f"{event.get('id')}: invalid closed_experiment_count")
        for field in ("artifact_ids", "insight_ids"):
            for linked_id in event.get(field, []) or []:
                if linked_id not in ids:
                    errors.append(f"{event.get('id')}: unknown linked id {linked_id}")
    open_actions: dict[str, list[str]] = defaultdict(list)
    for task_id, task in tasks.items():
        latest = latest_task_state(task, task_events_by_id[task_id])
        if latest.get("status") not in {"complete", "cancelled"}:
            open_actions[str(task.get("action_type"))].append(task_id)
    for action_type, task_ids in open_actions.items():
        if len(task_ids) > 1:
            warnings.append(f"duplicate open scheduler action {action_type}: {', '.join(task_ids)}")

    for claim in all_records.get("claims.jsonl", [])[1:]:
        if claim.get("record_type") != "claim":
            continue
        if int(claim.get("schema_version", 1)) >= 2:
            if claim.get("status") not in {
                "hypothesis",
                "supported-working-claim",
                "replicated",
                "paper-ready",
                "retracted",
            }:
                errors.append(f"{claim.get('id')}: invalid v2 claim status {claim.get('status')!r}")
            if claim.get("status") != "hypothesis" and not nonempty_list(claim.get("evidence_ids")):
                errors.append(f"{claim.get('id')}: non-hypothesis v2 claim lacks evidence_ids")
            for evidence_id in claim.get("evidence_ids", []) or []:
                if evidence_id not in ids:
                    errors.append(f"{claim.get('id')}: unknown evidence id {evidence_id}")
            supersedes = claim.get("supersedes")
            if supersedes and (not str(supersedes).startswith("C-") or supersedes not in ids):
                errors.append(f"{claim.get('id')}: unknown superseded claim {supersedes}")
            if not nonempty_list(claim.get("limitations")):
                errors.append(f"{claim.get('id')}: v2 claim lacks limitations")
        if claim.get("paper_ready"):
            evidence = claim.get("evidence_ids") or claim.get("evidence")
            if not nonempty_list(evidence):
                errors.append(f"{claim.get('id')}: paper-ready claim lacks evidence")
            if not nonempty_list(claim.get("limitations")):
                errors.append(f"{claim.get('id')}: paper-ready claim lacks limitations")
            if claim.get("human_visual_confirmation") == "pending":
                errors.append(f"{claim.get('id')}: paper-ready claim has pending human confirmation")

    repo_value = state.get("canonical_repo", {}).get("path") if isinstance(state.get("canonical_repo"), dict) else None
    if repo_value:
        repo = Path(str(repo_value))
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
        "project_stage": state.get("stage"),
        "canonical_baseline_id": (
            state.get("canonical_baseline", {}).get("id")
            if isinstance(state.get("canonical_baseline"), dict)
            else None
        ),
        "record_counts": {name: len(rows) for name, rows in all_records.items()},
        "errors": errors,
        "warnings": warnings,
        "ok": not errors and (not warnings or not args.strict),
    }
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Research state: {root}")
        print(f"Stage: {state.get('stage') or 'unknown'}")
        print(f"Canonical baseline: {result['canonical_baseline_id'] or 'unassigned'}")
        print(f"Active experiment: {active_id or 'none'}")
        print(f"Errors: {len(errors)}; warnings: {len(warnings)}")
        for value in errors:
            print(f"ERROR: {value}")
        for value in warnings:
            print(f"WARN: {value}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
