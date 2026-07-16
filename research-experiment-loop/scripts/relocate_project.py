#!/usr/bin/env python3
"""Relocate a research control plane without rewriting append-only registries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research_state_lib import git_snapshot, load_yaml, utc_now, write_yaml


def remap_scalar(value: str, aliases: list[tuple[Path, Path]]) -> str:
    if not value.startswith("/"):
        return value
    path = Path(value).resolve()
    for source, target in sorted(aliases, key=lambda pair: len(pair[0].parts), reverse=True):
        try:
            relative = path.relative_to(source)
        except ValueError:
            continue
        return str((target / relative).resolve())
    return value


def remap_state(value: Any, aliases: list[tuple[Path, Path]]) -> Any:
    if isinstance(value, dict):
        return {key: remap_state(item, aliases) for key, item in value.items()}
    if isinstance(value, list):
        return [remap_state(item, aliases) for item in value]
    if isinstance(value, str):
        return remap_scalar(value, aliases)
    return value


def portable_scalar(value: str, root: Path) -> str:
    if not value.startswith("/"):
        return value
    path = Path(value).resolve()
    try:
        relative = path.relative_to(root)
    except ValueError:
        return value
    return str(relative) if relative.parts else "."


def portable_state(value: Any, root: Path) -> Any:
    if isinstance(value, dict):
        return {key: portable_state(item, root) for key, item in value.items()}
    if isinstance(value, list):
        return [portable_state(item, root) for item in value]
    if isinstance(value, str):
        return portable_scalar(value, root)
    return value


def infer_old_root(root: Path, old_repo: Path, new_repo: Path) -> Path | None:
    if new_repo == root:
        return old_repo
    if new_repo.parent == root:
        return old_repo.parent
    return None


def alias_record(source: Path, target: Path) -> dict[str, str]:
    return {"from": str(source.resolve()), "to": str(target.resolve())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="New research control-plane root")
    parser.add_argument("--repo", type=Path, required=True, help="Canonical repo at its new path")
    parser.add_argument("--old-root", type=Path, help="Previous control-plane root if inference is ambiguous")
    parser.add_argument("--review-root", type=Path, help="Override the new human-review directory")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    state_path = root / "research" / "project_state.yaml"
    if not state_path.is_file():
        raise SystemExit(f"Research state does not exist: {state_path}")
    state = load_yaml(state_path)
    if state.get("active_experiment_id"):
        raise SystemExit("Relocation is only allowed at an experiment boundary")

    repo = args.repo.expanduser()
    if not repo.is_absolute():
        repo = root / repo
    repo = repo.resolve()
    snapshot = git_snapshot(repo)
    if not snapshot["tracked_clean"]:
        raise SystemExit("Refusing to relocate to a canonical repo with tracked changes")

    canonical = state.get("canonical_repo", {})
    if not isinstance(canonical, dict) or not canonical.get("path"):
        raise SystemExit("project_state.yaml lacks canonical_repo.path")
    old_repo_value = Path(str(canonical["path"])).expanduser()
    old_repo = (
        old_repo_value.resolve()
        if old_repo_value.is_absolute()
        else (root / old_repo_value).resolve()
    )
    expected_commit = str(canonical.get("commit") or "")
    if expected_commit and expected_commit != "unknown" and snapshot["commit"] != expected_commit:
        raise SystemExit(
            "Canonical commit mismatch: "
            f"state records {expected_commit}, new repo is {snapshot['commit']}. "
            "Checkout the recorded commit before relocation."
        )

    workspace = state.get("workspace", {})
    if not isinstance(workspace, dict):
        workspace = {}
    old_root_value = args.old_root or workspace.get("current_root")
    old_root = (
        Path(str(old_root_value)).expanduser().resolve()
        if old_root_value
        else infer_old_root(root, old_repo, repo)
    )
    if old_root is None:
        raise SystemExit("Cannot infer the previous project root; pass --old-root explicitly")

    aliases: list[tuple[Path, Path]] = []
    if old_repo != repo:
        aliases.append((old_repo, repo))
    if old_root != root and (old_root, root) not in aliases:
        aliases.append((old_root, root))
    updated = portable_state(remap_state(state, aliases), root)

    review = updated.get("human_review", {})
    if not isinstance(review, dict):
        review = {}
    if args.review_root:
        review_root = args.review_root.expanduser()
        if not review_root.is_absolute():
            review_root = root / review_root
        review_root = review_root.resolve()
    elif review.get("root"):
        review_value = Path(str(review["root"])).expanduser()
        review_root = (
            review_value.resolve()
            if review_value.is_absolute()
            else (root / review_value).resolve()
        )
    else:
        review_root = repo / "figures" / "review"
    review["root"] = portable_scalar(str(review_root), root)
    review["latest"] = portable_scalar(str(review_root / "LATEST.md"), root)
    updated["human_review"] = review

    old_aliases = workspace.get("path_aliases", [])
    alias_rows = [value for value in old_aliases if isinstance(value, dict)] if isinstance(old_aliases, list) else []
    historical_roots = workspace.get("historical_roots", [])
    history_rows = [str(value) for value in historical_roots] if isinstance(historical_roots, list) else []
    register_old_root = old_repo_value.is_absolute() or not history_rows
    if register_old_root and str(old_root) not in history_rows:
        history_rows.append(str(old_root))
    for source, target in aliases:
        try:
            source_relative = source.relative_to(old_root)
            target_relative = target.relative_to(root)
        except ValueError:
            source_relative = None
            target_relative = None
        if source_relative == target_relative:
            continue
        row = alias_record(source, target)
        if row not in alias_rows:
            alias_rows.append(row)
    updated["workspace"] = {
        "layout_version": 1,
        "historical_roots": history_rows,
        "path_aliases": alias_rows,
    }
    updated["canonical_repo"] = {
        "path": portable_scalar(snapshot["repo"], root),
        "branch": snapshot["branch"],
        "commit": snapshot["commit"],
        "tracked_clean_at_snapshot": snapshot["tracked_clean"],
    }
    updated["updated_at"] = state.get("updated_at")
    changed = updated != state
    if changed:
        updated["updated_at"] = utc_now()

    result = {
        "root": str(root),
        "canonical_repo": updated["canonical_repo"],
        "human_review": updated["human_review"],
        "historical_root_registered": str(old_root) if register_old_root else None,
        "path_aliases_added": updated["workspace"]["path_aliases"],
        "changed": changed,
        "dry_run": args.dry_run,
    }
    if not args.dry_run and changed:
        write_yaml(state_path, updated)

    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        action = "Would relocate" if args.dry_run else "Relocated"
        print(f"{action} research control plane: {root}")
        print(f"Canonical repo: {repo} @ {snapshot['commit'][:12]}")
        print(f"Human review: {review_root}")
        print(f"Historical path aliases added: {len(aliases)}")
        if not args.dry_run:
            print(f"Next: researchctl audit --root {root} --strict")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
