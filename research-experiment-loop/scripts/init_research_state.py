#!/usr/bin/env python3
"""Initialize a non-destructive machine-readable research control layer."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from research_state_lib import REGISTRIES, VALID_STAGES, utc_now


def git_value(repo: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def write_once(path: Path, content: str, created: list[str], skipped: list[str]) -> None:
    if path.exists():
        skipped.append(str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(str(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Project root")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--repo", type=Path, help="Canonical Git repository; defaults to root")
    parser.add_argument("--review-root", type=Path, help="Human review directory; defaults to <root>/figures/review")
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--domain", default="generic")
    parser.add_argument("--stage", choices=sorted(VALID_STAGES), default="exploration")
    parser.add_argument("--north-star", required=True)
    parser.add_argument("--primary-problem", required=True)
    parser.add_argument("--baseline-id", required=True)
    parser.add_argument("--baseline-name", required=True)
    parser.add_argument("--baseline-config", required=True)
    parser.add_argument("--evaluation-protocol", required=True)
    parser.add_argument("--stage-exit-gate", action="append", default=[])
    parser.add_argument("--primary-metric", action="append", default=[])
    parser.add_argument("--tail-metric", action="append", default=[])
    parser.add_argument("--forbidden-input", action="append", default=[])
    parser.add_argument("--promotion-gate", action="append", default=[])
    parser.add_argument("--review-requirement", action="append", default=[])
    args = parser.parse_args()
    if not args.stage_exit_gate:
        raise SystemExit("At least one --stage-exit-gate is required")
    if not args.primary_metric:
        raise SystemExit("At least one --primary-metric is required")
    if not args.promotion_gate:
        raise SystemExit("At least one --promotion-gate is required")

    root = args.root.resolve()
    repo = (args.repo or root).resolve()
    review = (args.review_root or (root / "figures" / "review")).resolve()
    research = root / "research"
    now = utc_now()
    branch = git_value(repo, "rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    commit = git_value(repo, "rev-parse", "HEAD") or "unknown"
    tracked_status = git_value(repo, "status", "--porcelain", "--untracked-files=no")
    tracked_clean = tracked_status == "" if tracked_status is not None else False
    if branch == "unknown" or commit == "unknown":
        raise SystemExit(f"Canonical repo is not a committed Git repository: {repo}")
    if not tracked_clean:
        raise SystemExit("Refusing to initialize against a canonical repo with tracked changes")

    created: list[str] = []
    skipped: list[str] = []
    state = f'''schema_version: 3
project_id: {json.dumps(args.project_id)}
updated_at: {json.dumps(now)}
language: {json.dumps(args.language)}
stage: {json.dumps(args.stage)}
north_star: {json.dumps(args.north_star)}
primary_problem: {json.dumps(args.primary_problem)}
active_experiment_id: null
active_candidate: null
canonical_baseline:
  id: {json.dumps(args.baseline_id)}
  name: {json.dumps(args.baseline_name)}
  repo_commit: {json.dumps(commit)}
  config: {json.dumps(args.baseline_config)}
  evaluation_protocol: {json.dumps(args.evaluation_protocol)}
parked_lanes: []
stage_exit_gates: {json.dumps(args.stage_exit_gate, ensure_ascii=False)}
canonical_repo:
  path: {json.dumps(str(repo))}
  branch: {json.dumps(branch)}
  commit: {json.dumps(commit)}
  tracked_clean_at_snapshot: {str(tracked_clean).lower()}
human_review:
  root: {json.dumps(str(review))}
  latest: {json.dumps(str(review / "LATEST.md"))}
'''
    write_once(research / "project_state.yaml", state, created, skipped)
    for filename, prefix in REGISTRIES.items():
        meta = {
            "record_type": "registry_meta",
            "schema_version": 1,
            "registry": filename.removesuffix(".jsonl"),
            "created_at": now,
            "id_prefix": prefix,
        }
        write_once(research / filename, json.dumps(meta, ensure_ascii=False) + "\n", created, skipped)
    task_meta = {
        "record_type": "registry_meta",
        "schema_version": 1,
        "registry": "tasks",
        "created_at": now,
        "id_prefix": "TASK",
    }
    write_once(
        research / "tasks.jsonl",
        json.dumps(task_meta, ensure_ascii=False) + "\n",
        created,
        skipped,
    )

    write_once(
        research / "README.md",
        "# 机器可读研究状态\n\nJSONL 每行一个记录；实验开始前建卡，结束后写 verdict。\n",
        created,
        skipped,
    )
    write_once(
        research / "profile.yaml",
        "\n".join(
            [
                "schema_version: 1",
                f"domain: {json.dumps(args.domain)}",
                f"primary_metrics: {json.dumps(args.primary_metric, ensure_ascii=False)}",
                f"tail_metrics: {json.dumps(args.tail_metric, ensure_ascii=False)}",
                f"forbidden_inputs: {json.dumps(args.forbidden_input, ensure_ascii=False)}",
                f"promotion_gates: {json.dumps(args.promotion_gate, ensure_ascii=False)}",
                f"review_requirements: {json.dumps(args.review_requirement, ensure_ascii=False)}",
                "",
            ]
        ),
        created,
        skipped,
    )
    scheduler_template = (
        Path(__file__).resolve().parents[1] / "assets" / "project-template" / "SCHEDULER.yaml"
    ).read_text(encoding="utf-8")
    write_once(research / "scheduler.yaml", scheduler_template, created, skipped)
    (research / "cards").mkdir(parents=True, exist_ok=True)
    write_once(
        review / "index.md",
        "# 人工审查入口\n\n尚无实验。只有生成真实图后才创建 `LATEST.png`。\n",
        created,
        skipped,
    )
    write_once(
        review / "LATEST.md",
        "# 当前人工审查项\n\n尚无 active experiment。\n\n用户肉眼确认：`not_required`。\n",
        created,
        skipped,
    )

    print(json.dumps({"root": str(root), "created": created, "skipped": skipped}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
