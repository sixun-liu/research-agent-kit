#!/usr/bin/env python3
"""Initialize a non-destructive machine-readable research control layer."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from research_state_lib import REGISTRIES, VALID_STAGES, utc_now


def git_value(repo: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def write_once(path: Path, content: str, created: list[str], skipped: list[str]) -> None:
    if path.exists():
        skipped.append(str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(str(path))


def render_template(path: Path, values: dict[str, str]) -> str:
    content = path.read_text(encoding="utf-8")
    for key, value in values.items():
        content = content.replace("{{" + key + "}}", value)
    unresolved = sorted(set(re.findall(r"\{\{([a-z_]+)\}\}", content)))
    if unresolved:
        raise SystemExit(f"Unresolved template values in {path}: {', '.join(unresolved)}")
    return content


def dump_yaml(value: dict) -> str:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("PyYAML is required for research state commands") from exc
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=1000)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Project root")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--repo", type=Path, help="Canonical Git repository; defaults to root")
    parser.add_argument("--review-root", type=Path, help="Human review directory; defaults to <root>/figures/review")
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--created-by", default="unassigned", help="Stable maintainer role for control docs")
    parser.add_argument("--domain", default="generic")
    parser.add_argument("--stage", choices=sorted(VALID_STAGES), default="exploration")
    parser.add_argument("--north-star", required=True)
    parser.add_argument("--primary-problem", required=True)
    parser.add_argument("--baseline-id")
    parser.add_argument("--baseline-name")
    parser.add_argument("--baseline-config")
    parser.add_argument("--evaluation-protocol")
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
    baseline_values = (
        args.baseline_id,
        args.baseline_name,
        args.baseline_config,
        args.evaluation_protocol,
    )
    if any(baseline_values) and not all(baseline_values):
        raise SystemExit("Baseline arguments must be supplied together")
    if args.stage != "understanding" and not all(baseline_values):
        raise SystemExit(
            "A canonical baseline is required after the understanding stage"
        )

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
    template_root = Path(__file__).resolve().parents[1] / "assets" / "project-template"
    write_once(
        root / ".gitignore",
        (template_root / "GITIGNORE").read_text(encoding="utf-8"),
        created,
        skipped,
    )
    for directory in (
        root / "configs" / "baselines",
        root / "configs" / "experiments",
        root / "scripts" / "run",
        root / "scripts" / "analyze",
        root / "scripts" / "admin",
        root / "tests",
        root / "references" / "papers",
        root / "references" / "implementations",
        root / "references" / "understanding",
        root / "references" / "surveys",
        root / "references" / "manifests",
        root / "discussion" / "claude",
        root / "discussion" / "codex",
        root / "discussion" / "archive",
        root / "reports" / "daily",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    baseline = (
        {
            "id": args.baseline_id,
            "name": args.baseline_name,
            "repo_commit": commit,
            "config": args.baseline_config,
            "evaluation_protocol": args.evaluation_protocol,
        }
        if all(baseline_values)
        else None
    )
    state = f'''schema_version: 4
project_id: {json.dumps(args.project_id)}
updated_at: {json.dumps(now)}
updated_by: {json.dumps(args.created_by)}
language: {json.dumps(args.language)}
stage: {json.dumps(args.stage)}
north_star: {json.dumps(args.north_star)}
primary_problem: {json.dumps(args.primary_problem)}
active_experiment_id: null
active_candidate: null
canonical_baseline: {json.dumps(baseline, ensure_ascii=False)}
parked_lanes: []
stage_exit_gates: {json.dumps(args.stage_exit_gate, ensure_ascii=False)}
repository_manifest: research/repositories.yaml
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
    control_top = git_value(root, "rev-parse", "--show-toplevel")
    control_path = Path(control_top).resolve() if control_top else root
    runtime_top = git_value(repo, "rev-parse", "--show-toplevel")
    runtime_path = Path(runtime_top).resolve() if runtime_top else repo
    repositories = {
        "control": {
            "path": str(control_path),
            "remote": git_value(control_path, "remote", "get-url", "origin"),
            "commit_source": "git-rev-parse-head",
            "required_clean": True,
        },
        "runtime": {
            "path": str(runtime_path),
            "remote": git_value(runtime_path, "remote", "get-url", "origin"),
            "commit_source": "git-rev-parse-head",
            "required_clean": True,
        },
    }
    repository_manifest = {
        "schema_version": 2,
        "updated_at": now,
        "repositories": repositories,
        "third_party": {},
        "stores": {
            "human_review": str(review),
        },
    }
    write_once(
        research / "repositories.yaml",
        dump_yaml(repository_manifest),
        created,
        skipped,
    )
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
    next_action = (
        "完成论文版本、主张、代码谱系和评测协议对账。"
        if args.stage == "understanding"
        else "建立首个可证伪实验。"
    )
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
        root / "references" / "INDEX.md",
        "# Reference Index\n\n稳定论文、实现谱系、已核理解快照、调研综合和 ingestion manifest 的统一入口。\n",
        created,
        skipped,
    )
    write_once(
        root / "discussion" / "INDEX.md",
        "# Discussion Index\n\n未收敛协作笔记和红队草稿；正典事实仍以 references 与 research registry 为准。\n",
        created,
        skipped,
    )
    write_once(
        root / "reports" / "daily" / "INDEX.md",
        "# Daily Reports\n\n面向人的日报由 DEVLOG 和已登记证据生成；机器事实仍以 registry 为准。\n",
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
    scheduler_template = (template_root / "SCHEDULER.yaml").read_text(encoding="utf-8")
    write_once(research / "scheduler.yaml", scheduler_template, created, skipped)
    (research / "cards").mkdir(parents=True, exist_ok=True)
    exit_gates = "\n".join(f"- [ ] {value}" for value in args.stage_exit_gate)
    doc_template_root = template_root / "control-docs"
    template_values = {
        "updated_at": now,
        "date": now[:10],
        "maintainer": args.created_by,
        "stage": args.stage,
        "north_star": args.north_star,
        "primary_problem": args.primary_problem,
        "next_action": next_action,
        "exit_gates": exit_gates,
    }
    for filename in (
        "CURRENT_STATE.md",
        "PLAN.md",
        "TODO.md",
        "DEVLOG.md",
        "RESULTS_SCOREBOARD.md",
    ):
        write_once(
            root / filename,
            render_template(doc_template_root / f"{filename}.tmpl", template_values),
            created,
            skipped,
        )
    write_once(
        root / "reports" / "daily" / "TEMPLATE.md",
        render_template(doc_template_root / "DAILY_REPORT.md.tmpl", template_values),
        created,
        skipped,
    )
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
