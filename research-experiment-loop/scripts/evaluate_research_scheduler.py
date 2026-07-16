#!/usr/bin/env python3
"""Evaluate cross-cycle research interrupts and optionally enqueue advisory tasks."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from research_state_lib import (
    TERMINAL_EXPERIMENT_STATUSES,
    TERMINAL_TASK_STATUSES,
    VALID_TASK_ACTIONS,
    append_jsonl,
    experiment_records,
    latest_experiment_state,
    latest_task_state,
    load_yaml,
    next_id,
    task_records,
    utc_now,
)


HANDLERS = {
    "INTEGRITY": {
        "contract": "停止解释结果；核对配置、provenance、预期动作、完成信号和首次分歧。",
        "patterns": ["known-answer-check", "first-divergence-audit"],
    },
    "BREAKTHROUGH": {
        "contract": "冻结现场并做异源红队、盲图检查和最低成本重复；只输出一个判别实验。",
        "patterns": ["blind-visual-review", "counterfactual-replay", "positive-negative-control"],
    },
    "REFLECT": {
        "contract": "检查共同失败机制、替代解释和是否解错一阶问题；输出一张因果图和一个最小实验。",
        "patterns": ["oracle-replacement", "surgical-intervention", "first-divergence-audit"],
    },
    "INTUITION": {
        "contract": (
            "脱离当前参数邻域做盲数据漫游或跨领域类比；最多保留三个互斥假说，"
            "最后只选择一个最低成本判别 probe。"
        ),
        "patterns": ["blind-visual-review", "boundary-case-analysis", "canary"],
    },
    "THEORY_SYNC": {
        "contract": "从连续实践中提炼机制，并给出至少一个会改变下一实验结果的可证伪预测。",
        "patterns": ["mechanism-model", "dimensional-analysis", "boundary-case-analysis"],
    },
    "PRACTICE_SYNC": {
        "contract": "选择最低成本干预验证最新理论预测；优先旧产物、回放或局部手术刀。",
        "patterns": ["counterfactual-replay", "surgical-intervention", "canary"],
    },
    "SYNTHESIS": {
        "contract": "更新主要矛盾、canonical baseline、active candidate、parked lanes 和阶段退出门。",
        "patterns": ["claim-evidence-matrix", "baseline-convergence-table"],
    },
    "EFFICIENCY_REVIEW": {
        "contract": "审计时间花在哪里，寻找复用、缓存、回放、早停和更低成本判别层；只固化重复收益。",
        "patterns": ["cost-ladder-audit", "snapshot-replay", "early-stop-beacon"],
    },
    "HUMAN_REVIEW": {
        "contract": "生成紧凑对比和原始上下文，明确需要人判断的语义问题，不用自动指标代判。",
        "patterns": ["compact-review", "blind-visual-review", "raw-context-sheet"],
    },
}


def add_recommendation(
    recommendations: dict[str, dict[str, Any]],
    action_type: str,
    reason: str,
    source_ids: list[str],
    priorities: dict[str, str],
) -> None:
    if action_type not in VALID_TASK_ACTIONS:
        raise ValueError(f"Unknown action type: {action_type}")
    value = recommendations.setdefault(
        action_type,
        {
            "action_type": action_type,
            "priority": priorities.get(action_type, "P3"),
            "reasons": [],
            "source_ids": [],
            "handler_contract": HANDLERS[action_type]["contract"],
            "suggested_patterns": HANDLERS[action_type]["patterns"],
        },
    )
    if reason not in value["reasons"]:
        value["reasons"].append(reason)
    value["source_ids"] = sorted(set(value["source_ids"] + source_ids))


def valid_negative(event: dict[str, Any]) -> bool:
    return (
        event.get("decision") == "negative"
        and event.get("expected_action_status") in {"occurred", "not_applicable"}
        and event.get("completion_signal_status") in {"confirmed", "not_applicable"}
    )


def enqueue_recommendations(
    root: Path,
    recommendations: list[dict[str, Any]],
    discussion_root: Path,
) -> list[str]:
    registry = root / "research" / "tasks.jsonl"
    queued_ids: list[str] = []
    discussion_root.mkdir(parents=True, exist_ok=True)
    for recommendation in recommendations:
        task_id = next_id(registry, "TASK")
        card = discussion_root / f"{task_id}-{recommendation['action_type'].lower()}.md"
        record = {
            "record_type": "research_task",
            "schema_version": 1,
            "id": task_id,
            "created_at": utc_now(),
            "status": "queued",
            "discussion_path": str(card),
            **recommendation,
        }
        append_jsonl(registry, record)
        card.write_text(
            f"# {task_id}: {recommendation['action_type']}\n\n"
            f"优先级：`{recommendation['priority']}`\n\n"
            "## 触发原因\n\n"
            + "\n".join(f"- {reason}" for reason in recommendation["reasons"])
            + "\n\n## 处理契约\n\n"
            + recommendation["handler_contract"]
            + "\n\n## 建议模式\n\n"
            + "\n".join(f"- `{name}`" for name in recommendation["suggested_patterns"])
            + "\n\n## 来源\n\n"
            + "\n".join(f"- `{value}`" for value in recommendation["source_ids"])
            + "\n",
            encoding="utf-8",
        )
        queued_ids.append(task_id)
    return queued_ids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--enqueue", action="store_true", help="Append non-duplicate advisory tasks")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    root = args.root.resolve()
    scheduler_path = root / "research" / "scheduler.yaml"
    if not scheduler_path.exists():
        raise SystemExit("Scheduler config is missing; migrate the project at a stage boundary")
    config = load_yaml(scheduler_path)
    if not config.get("enabled", True):
        result = {"root": str(root), "enabled": False, "recommendations": [], "enqueued": []}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    thresholds = config.get("thresholds", {})
    priorities = config.get("priorities", {})
    experiments, events = experiment_records(root)
    closures = sorted(
        [event for event in events if event.get("event_type") == "closure"],
        key=lambda value: str(value.get("created_at", "")),
    )
    observations = [event for event in events if event.get("event_type") == "postrun_observation"]
    tasks, task_events = task_records(root)
    task_events_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in task_events:
        task_events_by_id[str(event.get("task_id"))].append(event)
    latest_tasks = {
        task_id: latest_task_state(task, task_events_by_id[task_id])
        for task_id, task in tasks.items()
    }
    open_actions = {
        task.get("action_type")
        for task in latest_tasks.values()
        if task.get("status") not in TERMINAL_TASK_STATUSES
    }
    handled_sources = {
        str(source_id)
        for task in tasks.values()
        for source_id in task.get("source_ids", []) or []
    }

    recommendations: dict[str, dict[str, Any]] = {}

    active_id = load_yaml(root / "research" / "project_state.yaml").get("active_experiment_id")
    if active_id:
        active_events = [event for event in events if event.get("experiment_id") == active_id]
        has_freeze = any(event.get("event_type") == "provenance_freeze" for event in active_events)
        has_observation = any(event.get("event_type") == "postrun_observation" for event in active_events)
        if has_observation and not has_freeze:
            add_recommendation(
                recommendations,
                "INTEGRITY",
                f"{active_id} 已产生结果观察但没有 provenance freeze。",
                [str(active_id)],
                priorities,
            )

    for event in closures:
        if event.get("decision") == "invalid_provenance":
            add_recommendation(
                recommendations,
                "INTEGRITY",
                f"{event.get('experiment_id')} 因 provenance/instrumentation 无效结案。",
                [str(event.get("id"))],
                priorities,
            )

    unexpected = [
        event
        for event in observations
        if event.get("unexpected") and str(event.get("id")) not in handled_sources
    ]
    if unexpected:
        add_recommendation(
            recommendations,
            "BREAKTHROUGH",
            f"发现 {len(unexpected)} 条尚未处理的反直觉观察。",
            [str(event.get("id")) for event in unexpected],
            priorities,
        )

    family_closures: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for closure in closures:
        experiment = experiments.get(str(closure.get("experiment_id")), {})
        family = str(experiment.get("hypothesis_family") or "unclassified")
        family_closures[family].append(closure)
    negative_threshold = int(thresholds.get("valid_negative_streak", 3))
    for family, values in family_closures.items():
        streak: list[dict[str, Any]] = []
        for event in reversed(values):
            if not valid_negative(event):
                break
            streak.append(event)
        if len(streak) >= negative_threshold:
            axes = sorted({str(event.get("failure_axis") or "unspecified") for event in streak})
            add_recommendation(
                recommendations,
                "REFLECT",
                f"假说族 {family} 连续 {len(streak)} 次有效负结果；失败轴：{', '.join(axes)}。",
                [str(event.get("id")) for event in streak],
                priorities,
            )

    no_progress: list[dict[str, Any]] = []
    for event in reversed(closures):
        if event.get("progress_type") not in {None, "none"}:
            break
        no_progress.append(event)
    no_progress_cycles = int(thresholds.get("no_progress_cycles", 3))
    no_progress_wall = sum(float(event.get("wall_hours") or 0.0) for event in no_progress)
    no_progress_compute = sum(float(event.get("compute_hours") or 0.0) for event in no_progress)
    stagnated = (
        len(no_progress) >= no_progress_cycles
        or no_progress_wall >= float(thresholds.get("no_progress_wall_hours", 3.0))
        or no_progress_compute >= float(thresholds.get("no_progress_compute_hours", 2.0))
    )
    if stagnated and no_progress:
        source_ids = [str(event.get("id")) for event in no_progress]
        reason = (
            f"连续 {len(no_progress)} 个结案未记录实质进展，累计 wall={no_progress_wall:.2f}h、"
            f"compute={no_progress_compute:.2f}h。"
        )
        add_recommendation(recommendations, "REFLECT", reason, source_ids, priorities)
        add_recommendation(recommendations, "INTUITION", reason, source_ids, priorities)
        add_recommendation(recommendations, "EFFICIENCY_REVIEW", reason, source_ids, priorities)

    trailing_mode = None
    mode_streak = 0
    for closure in reversed(closures):
        experiment = experiments.get(str(closure.get("experiment_id")), {})
        mode = experiment.get("work_mode")
        if mode not in {"theory", "practice"}:
            break
        if trailing_mode is None:
            trailing_mode = mode
        if mode != trailing_mode:
            break
        mode_streak += 1
    if trailing_mode == "theory" and mode_streak >= int(thresholds.get("theory_only_streak", 2)):
        add_recommendation(
            recommendations,
            "PRACTICE_SYNC",
            f"连续 {mode_streak} 个理论循环没有实践干预。",
            [str(event.get("id")) for event in closures[-mode_streak:]],
            priorities,
        )
    if trailing_mode == "practice" and mode_streak >= int(thresholds.get("practice_only_streak", 3)):
        add_recommendation(
            recommendations,
            "THEORY_SYNC",
            f"连续 {mode_streak} 个实践循环没有理论综合。",
            [str(event.get("id")) for event in closures[-mode_streak:]],
            priorities,
        )

    completed_synthesis = [
        event
        for event in task_events
        if event.get("status") == "complete"
        and tasks.get(str(event.get("task_id")), {}).get("action_type") == "SYNTHESIS"
    ]
    synthesis_baseline = max(
        [int(event.get("closed_experiment_count") or 0) for event in completed_synthesis] or [0]
    )
    cycles_since_synthesis = len(closures) - synthesis_baseline
    if cycles_since_synthesis >= int(thresholds.get("cycles_without_synthesis", 5)):
        add_recommendation(
            recommendations,
            "SYNTHESIS",
            f"自上次综合后已完成 {cycles_since_synthesis} 个实验循环。",
            [str(event.get("id")) for event in closures[synthesis_baseline:]],
            priorities,
        )

    pending_reviews: list[str] = []
    for experiment_id, experiment in experiments.items():
        latest = latest_experiment_state(experiment, events)
        if int(experiment.get("schema_version", 1)) < 3:
            continue
        if (
            latest.get("status") in TERMINAL_EXPERIMENT_STATUSES
            and latest.get("human_visual_confirmation") == "pending"
        ):
            pending_reviews.append(experiment_id)
    if len(pending_reviews) >= int(thresholds.get("pending_human_reviews", 2)):
        add_recommendation(
            recommendations,
            "HUMAN_REVIEW",
            f"有 {len(pending_reviews)} 个已结案实验等待人工审查。",
            pending_reviews,
            priorities,
        )

    ordered = sorted(
        [
            value
            for key, value in recommendations.items()
            if key not in open_actions
            and not set(value["source_ids"]).issubset(handled_sources)
        ],
        key=lambda value: (value["priority"], value["action_type"]),
    )
    discussion_value = config.get("discussion_root", "discussion/scheduler")
    discussion_root = Path(str(discussion_value))
    if not discussion_root.is_absolute():
        discussion_root = root / discussion_root
    enqueued = enqueue_recommendations(root, ordered, discussion_root) if args.enqueue else []
    result = {
        "root": str(root),
        "mode": config.get("mode", "advisory"),
        "closed_experiments": len(closures),
        "open_task_actions": sorted(value for value in open_actions if value),
        "recommendations": ordered,
        "enqueued": enqueued,
    }
    if args.json_output or args.enqueue:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Research scheduler: {root}")
        print(f"Recommendations: {len(ordered)}")
        for value in ordered:
            print(f"{value['priority']} {value['action_type']}: {' '.join(value['reasons'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
