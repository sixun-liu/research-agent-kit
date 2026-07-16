#!/usr/bin/env python3
"""Append a preregistered experiment and create its human review card."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from research_state_lib import (
    append_jsonl,
    canonical_repo,
    git_snapshot,
    load_jsonl,
    load_yaml,
    next_id,
    update_project_state,
    utc_now,
)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "experiment"


def require_list(name: str, values: list[str]) -> None:
    if not values:
        raise SystemExit(f"At least one --{name} is required")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--slug")
    parser.add_argument("--question", required=True)
    parser.add_argument("--hypothesis", required=True)
    parser.add_argument("--primary-problem")
    parser.add_argument("--baseline-id")
    parser.add_argument("--hypothesis-family", required=True)
    parser.add_argument("--work-mode", choices=("theory", "practice", "mixed", "instrumentation"), required=True)
    parser.add_argument("--independent-variable", required=True)
    parser.add_argument("--expected-action", required=True)
    parser.add_argument("--completion-signal", action="append", default=[])
    parser.add_argument("--claim-id", action="append", default=[])
    parser.add_argument("--lane", choices=("planned", "breakthrough_followup"), default="planned")
    parser.add_argument("--priority", choices=("low", "normal", "high"), default="normal")
    parser.add_argument("--alternative", action="append", default=[])
    parser.add_argument("--control", action="append", default=[])
    parser.add_argument("--metric", action="append", default=[])
    parser.add_argument("--stop-condition", action="append", default=[])
    args = parser.parse_args()

    root = args.root.resolve()
    research = root / "research"
    state_path = research / "project_state.yaml"
    registry = research / "experiments.jsonl"
    if not state_path.exists() or not registry.exists():
        raise SystemExit("Research state is missing; run init_research_state.py first")

    state = load_yaml(state_path)
    if state.get("active_experiment_id"):
        raise SystemExit(
            f"Active experiment {state['active_experiment_id']} must be closed or blocked before creating another"
        )
    require_list("alternative", args.alternative)
    require_list("control", args.control)
    require_list("metric", args.metric)
    require_list("stop-condition", args.stop_condition)
    require_list("completion-signal", args.completion_signal)

    experiment_id = next_id(registry, "EXP")
    now = utc_now()
    review_value = state.get("human_review", {}).get("root", root / "figures" / "review")
    review_root = Path(review_value)
    if not review_root.is_absolute():
        review_root = root / review_root
    review_dir = review_root / f"{experiment_id}-{args.slug or slugify(args.title)}"
    card_path = research / "cards" / f"{experiment_id}.md"
    if card_path.exists() or review_dir.exists():
        raise SystemExit(f"Refusing to overwrite {experiment_id} artifacts")

    snapshot = git_snapshot(canonical_repo(root, state))
    if not snapshot["tracked_clean"]:
        raise SystemExit("Refusing to preregister against a canonical repo with tracked changes")
    baseline = state.get("canonical_baseline", {})
    if not isinstance(baseline, dict):
        baseline = {}
    primary_problem = args.primary_problem or state.get("primary_problem")
    baseline_id = args.baseline_id or baseline.get("id")
    if not primary_problem:
        raise SystemExit("A primary problem is required in project state or --primary-problem")
    if not baseline_id:
        raise SystemExit("A canonical baseline id is required in project state or --baseline-id")
    known_claims = {
        str(record.get("id"))
        for record in load_jsonl(research / "claims.jsonl")
        if record.get("record_type") == "claim"
    }
    unknown_claims = sorted(set(args.claim_id) - known_claims)
    if unknown_claims:
        raise SystemExit(f"Unknown claim ids: {', '.join(unknown_claims)}")
    record = {
        "record_type": "experiment",
        "schema_version": 3,
        "id": experiment_id,
        "title": args.title,
        "created_at": now,
        "updated_at": now,
        "status": "preregistered",
        "priority": args.priority,
        "lane": args.lane,
        "stage": state.get("stage"),
        "primary_problem": primary_problem,
        "baseline_id": baseline_id,
        "hypothesis_family": args.hypothesis_family,
        "work_mode": args.work_mode,
        "question": args.question,
        "hypothesis": args.hypothesis,
        "independent_variable": args.independent_variable,
        "expected_action": args.expected_action,
        "completion_signals": args.completion_signal,
        "claim_ids": args.claim_id,
        "alternatives": args.alternative,
        "controls": args.control,
        "primary_metrics": args.metric,
        "stop_conditions": args.stop_condition,
        "evidence_plan": {"numerical": [], "spatial": [], "temporal": [], "causal": []},
        "provenance": {
            "analysis_repo": snapshot["repo"],
            "analysis_branch": snapshot["branch"],
            "analysis_commit": snapshot["commit"],
            "analysis_tracked_clean": snapshot["tracked_clean"],
        },
        "compute_policy": "lowest-cost evidence required before expensive launch",
        "human_review_path": str(review_dir),
        "human_visual_confirmation": "pending",
        "verdict": None,
    }

    card_path.parent.mkdir(parents=True, exist_ok=True)
    alternatives = "\n".join(f"- {item}" for item in args.alternative) or "- 待补充"
    controls = "\n".join(f"- {item}" for item in args.control) or "- 待补充"
    metrics = "\n".join(f"- {item}" for item in args.metric) or "- 待补充"
    stops = "\n".join(f"- {item}" for item in args.stop_condition) or "- 待补充"
    card_path.write_text(
        f"""# {experiment_id}：{args.title}

状态：`preregistered`，高成本运行：`not approved`，人工看图：`pending`。

## 一句话问题

{args.question}

## 阶段与基座

- 阶段：`{state.get('stage')}`
- 当前主要矛盾：{primary_problem or '待补充'}
- Canonical baseline：`{baseline_id or 'unassigned'}`
- 假说族：`{args.hypothesis_family}`；工作模式：`{args.work_mode}`
- 唯一变量：{args.independent_variable}
- 预期动作：{args.expected_action}
- 完成正向信号：{'；'.join(args.completion_signal)}

## 假说

{args.hypothesis}

## 替代解释

{alternatives}

## 控制项

{controls}

## 主指标

{metrics}

## 证据四联

- 数值/概率：
- 空间/视觉：
- 时序/上尾：
- 因果干预：

## 停止条件

{stops}

## 人工审查

`{review_dir}`
""",
        encoding="utf-8",
    )
    review_dir.mkdir(parents=True)
    (review_dir / "README.md").write_text(
        f"# {experiment_id} Review\n\n实验卡：`{card_path}`。\n\n"
        "尚未生成紧凑图；用户确认：`pending`。\n",
        encoding="utf-8",
    )
    append_jsonl(registry, record)
    update_project_state(root, active_experiment_id=experiment_id)
    print(
        json.dumps(
            {"id": experiment_id, "card": str(card_path), "review": str(review_dir)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
