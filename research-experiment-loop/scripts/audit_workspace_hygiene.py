#!/usr/bin/env python3
"""Read-only audit of Git and workspace hygiene for a research control repo."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


BRANCH_PATTERN = re.compile(
    r"^(main|master|(?:exp/EXP-\d{4}|fix|docs|infra|release|feat)/[A-Za-z0-9][A-Za-z0-9._-]*)$"
)
SOURCE_SUFFIXES = {
    ".c",
    ".cc",
    ".cfg",
    ".cpp",
    ".cu",
    ".h",
    ".hpp",
    ".ini",
    ".java",
    ".jl",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".rs",
    ".sh",
    ".toml",
    ".ts",
    ".yaml",
    ".yml",
}
CACHE_NAMES = {
    ".ipynb_checkpoints",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}
STAGING_ROOTS = {"staging"}


def git(root: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode, result.stdout.strip()


def split_lines(value: str) -> list[str]:
    return [line for line in value.splitlines() if line.strip()]


def shallow_cache_paths(root: Path, max_depth: int = 3) -> list[str]:
    found: list[str] = []
    for current, directories, _ in os.walk(root):
        relative = Path(current).relative_to(root)
        depth = len(relative.parts)
        directories[:] = [name for name in directories if name != ".git"]
        if depth >= max_depth:
            directories[:] = []
            continue
        for name in list(directories):
            if name in CACHE_NAMES:
                found.append(str(relative / name))
                directories.remove(name)
    return sorted(found)


def is_staging_path(value: str) -> bool:
    first = Path(value).parts[0] if Path(value).parts else ""
    return first in STAGING_ROOTS or first.startswith("docs_from_")


def is_cache_path(value: str) -> bool:
    return any(part in CACHE_NAMES for part in Path(value).parts)


def tracked_large_files(root: Path, threshold: int) -> list[dict[str, Any]]:
    code, output = git(root, "ls-files", "-z")
    if code:
        return []
    result = []
    for value in output.split("\0"):
        if not value:
            continue
        path = root / value
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size > threshold:
            result.append({"path": value, "bytes": size})
    return sorted(result, key=lambda item: int(item["bytes"]), reverse=True)


def audit(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {"root": str(root)}
    if not root.is_dir():
        errors.append(f"workspace root does not exist: {root}")
        return {"ok": False, "strict_ok": False, "errors": errors, "warnings": warnings, **details}

    code, git_root_value = git(root, "rev-parse", "--show-toplevel")
    if code:
        errors.append("workspace root is not inside a Git repository")
        return {"ok": False, "strict_ok": False, "errors": errors, "warnings": warnings, **details}
    git_root = Path(git_root_value).resolve()
    details["git_root"] = str(git_root)
    if git_root != root:
        warnings.append(f"workspace root is nested inside Git root: {git_root}")

    _, branch = git(root, "branch", "--show-current")
    _, commit = git(root, "rev-parse", "HEAD")
    _, tracked_status = git(root, "status", "--porcelain", "--untracked-files=no")
    _, untracked_output = git(root, "ls-files", "--others", "--exclude-standard")
    _, remotes_output = git(root, "remote")
    untracked = split_lines(untracked_output)
    untracked_source = sorted(
        value
        for value in untracked
        if Path(value).suffix.lower() in SOURCE_SUFFIXES
        and not is_cache_path(value)
        and not is_staging_path(value)
    )
    untracked_staging = sorted({Path(value).parts[0] for value in untracked if is_staging_path(value)})
    remotes = split_lines(remotes_output)
    details.update(
        {
            "branch": branch or "detached",
            "commit": commit or None,
            "tracked_dirty": bool(tracked_status),
            "untracked_count": len(untracked),
            "untracked_source_like": untracked_source,
            "unignored_staging_roots": untracked_staging,
            "remotes": remotes,
        }
    )
    if not branch:
        warnings.append("Git HEAD is detached")
    elif not BRANCH_PATTERN.fullmatch(branch):
        warnings.append(f"branch name does not match the recommended contract: {branch}")
    if tracked_status:
        warnings.append("tracked worktree is dirty")
    if untracked_source:
        preview = ", ".join(untracked_source[:8])
        suffix = " ..." if len(untracked_source) > 8 else ""
        warnings.append(f"untracked source-like files: {preview}{suffix}")
    if untracked_staging:
        warnings.append(
            f"mutable staging roots are not ignored: {', '.join(untracked_staging)}"
        )
    if not remotes:
        warnings.append("Git repository has no remote")
    elif "origin" not in remotes:
        warnings.append("Git repository has no origin remote")
    if not (root / ".gitignore").is_file():
        warnings.append("workspace root has no .gitignore")

    top_dirs = sorted(path.name for path in root.iterdir() if path.is_dir() and path.name != ".git")
    top_files = sorted(path.name for path in root.iterdir() if path.is_file())
    cache_paths = shallow_cache_paths(root)
    large_files = tracked_large_files(root, args.max_tracked_bytes)
    details.update(
        {
            "top_level_directories": top_dirs,
            "top_level_files": top_files,
            "cache_directories": cache_paths,
            "large_tracked_files": large_files,
            "thresholds": {
                "max_root_dirs": args.max_root_dirs,
                "max_root_files": args.max_root_files,
                "max_tracked_bytes": args.max_tracked_bytes,
            },
        }
    )
    if len(top_dirs) > args.max_root_dirs:
        warnings.append(
            f"top-level directory count {len(top_dirs)} exceeds advisory limit {args.max_root_dirs}"
        )
    if len(top_files) > args.max_root_files:
        warnings.append(
            f"top-level file count {len(top_files)} exceeds advisory limit {args.max_root_files}"
        )
    if cache_paths:
        warnings.append(f"cache directories present near root: {', '.join(cache_paths[:8])}")
    if large_files:
        warnings.append(
            f"{len(large_files)} tracked files exceed {args.max_tracked_bytes} bytes"
        )

    return {
        "ok": not errors,
        "strict_ok": not errors and not warnings,
        "errors": errors,
        "warnings": warnings,
        **details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--strict", action="store_true", help="Treat advisory warnings as failure")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--max-root-dirs", type=int, default=12)
    parser.add_argument("--max-root-files", type=int, default=20)
    parser.add_argument("--max-tracked-bytes", type=int, default=10 * 1024 * 1024)
    args = parser.parse_args()
    if min(args.max_root_dirs, args.max_root_files, args.max_tracked_bytes) < 1:
        raise SystemExit("Workspace hygiene thresholds must be positive")

    result = audit(args)
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Workspace hygiene: {result['root']}")
        print(f"Git: {result.get('branch', '-')} @ {result.get('commit', '-')}")
        print(f"Errors: {len(result['errors'])}; warnings: {len(result['warnings'])}")
        for error in result["errors"]:
            print(f"ERROR: {error}")
        for warning in result["warnings"]:
            print(f"WARN: {warning}")
    return int(bool(result["errors"] or (args.strict and result["warnings"])))


if __name__ == "__main__":
    raise SystemExit(main())
