#!/usr/bin/env python3
"""Append a preregistered experiment and create its human review card."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("PyYAML is required to update project_state.yaml") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid project state: {path}")
    return data


def next_id(path: Path) -> str:
    maximum = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        match = re.fullmatch(r"EXP-(\d+)", str(record.get("id", "")))
        if match:
            maximum = max(maximum, int(match.group(1)))
    return f"EXP-{maximum + 1:04d}"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "experiment"


def update_active_id(path: Path, experiment_id: str, now: str) -> None:
    text = path.read_text(encoding="utf-8")
    text, count = re.subn(r"(?m)^active_experiment_id:\s*.*$", f"active_experiment_id: {experiment_id}", text, count=1)
    if count != 1:
        raise SystemExit("project_state.yaml lacks a unique active_experiment_id field")
    text, _ = re.subn(r"(?m)^updated_at:\s*.*$", f'updated_at: "{now}"', text, count=1)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--slug")
    parser.add_argument("--question", required=True)
    parser.add_argument("--hypothesis", required=True)
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
    experiment_id = next_id(registry)
    now = utc_now()
    review_value = state.get("human_review", {}).get("root", root / "figures" / "review")
    review_root = Path(review_value)
    if not review_root.is_absolute():
        review_root = root / review_root
    review_dir = review_root / f"{experiment_id}-{args.slug or slugify(args.title)}"
    card_path = research / "cards" / f"{experiment_id}.md"
    if card_path.exists() or review_dir.exists():
        raise SystemExit(f"Refusing to overwrite {experiment_id} artifacts")

    repo = state.get("canonical_repo", {})
    record = {
        "record_type": "experiment",
        "schema_version": 1,
        "id": experiment_id,
        "title": args.title,
        "created_at": now,
        "updated_at": now,
        "status": "preregistered",
        "priority": args.priority,
        "lane": args.lane,
        "question": args.question,
        "hypothesis": args.hypothesis,
        "alternatives": args.alternative,
        "controls": args.control,
        "primary_metrics": args.metric,
        "stop_conditions": args.stop_condition,
        "evidence_plan": {"numerical": [], "spatial": [], "temporal": [], "causal": []},
        "provenance": {
            "analysis_repo": repo.get("path"),
            "analysis_branch": repo.get("branch"),
            "analysis_commit": repo.get("commit"),
            "analysis_tracked_clean": repo.get("tracked_clean_at_snapshot"),
        },
        "gpu_policy": "offline verdict required before launch",
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

状态：`preregistered`，GPU：`not approved`，人工看图：`pending`。

## 一句话问题

{args.question}

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
        f"# {experiment_id} Review\n\n实验卡：`{card_path}`。\n\n尚未生成紧凑图；用户确认：`pending`。\n",
        encoding="utf-8",
    )
    with registry.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    update_active_id(state_path, experiment_id, now)
    print(json.dumps({"id": experiment_id, "card": str(card_path), "review": str(review_dir)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
