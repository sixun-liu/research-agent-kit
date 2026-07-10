#!/usr/bin/env python3
"""Initialize a non-destructive machine-readable research control layer."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path


REGISTRIES = {
    "experiments.jsonl": "EXP",
    "insights.jsonl": "I",
    "claims.jsonl": "C",
    "artifacts.jsonl": "ART",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    args = parser.parse_args()

    root = args.root.resolve()
    repo = (args.repo or root).resolve()
    review = (args.review_root or (root / "figures" / "review")).resolve()
    research = root / "research"
    now = utc_now()
    branch = git_value(repo, "rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    commit = git_value(repo, "rev-parse", "HEAD") or "unknown"
    tracked_status = git_value(repo, "status", "--porcelain", "--untracked-files=no")
    tracked_clean = tracked_status == "" if tracked_status is not None else False

    created: list[str] = []
    skipped: list[str] = []
    state = f'''schema_version: 1
project_id: {json.dumps(args.project_id)}
updated_at: {json.dumps(now)}
language: {json.dumps(args.language)}
stage: initialized
active_experiment_id: null
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

    write_once(
        research / "README.md",
        "# 机器可读研究状态\n\nJSONL 每行一个记录；实验开始前建卡，结束后写 verdict。\n",
        created,
        skipped,
    )
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
