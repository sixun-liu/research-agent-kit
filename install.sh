#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
codex_home="${CODEX_HOME:-$HOME/.codex}"
bin_dir="${RESEARCHCTL_BIN_DIR:-$HOME/.local/bin}"
check_only=false

usage() {
  cat <<'EOF'
Usage: ./install.sh [--check] [--codex-home PATH] [--bin-dir PATH]

Install non-destructive symlinks for:
  <codex-home>/skills/research-experiment-loop
  <bin-dir>/researchctl

Options:
  --check            Check dependencies and existing links without changing files.
  --codex-home PATH  Override CODEX_HOME (default: $CODEX_HOME or ~/.codex).
  --bin-dir PATH     Override CLI directory (default: ~/.local/bin).
  -h, --help         Show this help.
EOF
}

while (($#)); do
  case "$1" in
    --check)
      check_only=true
      shift
      ;;
    --codex-home)
      codex_home="$2"
      shift 2
      ;;
    --bin-dir)
      bin_dir="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

errors=0

require_command() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    printf 'ok: command %s -> %s\n' "$name" "$(command -v "$name")"
  else
    printf 'error: required command is missing: %s\n' "$name" >&2
    errors=$((errors + 1))
  fi
}

check_link() {
  local target="$1"
  local source="$2"
  local label="$3"

  if [[ -L "$target" ]]; then
    if [[ "$(readlink -f "$target")" == "$(readlink -f "$source")" ]]; then
      printf 'ok: %s -> %s\n' "$target" "$source"
    else
      printf 'error: %s already points to %s\n' "$target" "$(readlink "$target")" >&2
      errors=$((errors + 1))
    fi
  elif [[ -e "$target" ]]; then
    printf 'error: %s exists and is not the managed %s symlink\n' "$target" "$label" >&2
    errors=$((errors + 1))
  elif $check_only; then
    printf 'missing: %s (run ./install.sh to create it)\n' "$target"
    errors=$((errors + 1))
  else
    mkdir -p "$(dirname "$target")"
    ln -s "$source" "$target"
    printf 'created: %s -> %s\n' "$target" "$source"
  fi
}

require_command python3
require_command git
if python3 -c 'import yaml' >/dev/null 2>&1; then
  printf 'ok: Python module yaml (PyYAML)\n'
else
  printf 'error: PyYAML is missing; install it with: python3 -m pip install --user PyYAML\n' >&2
  errors=$((errors + 1))
fi

check_link \
  "$codex_home/skills/research-experiment-loop" \
  "$repo_root/research-experiment-loop" \
  "skill"
check_link \
  "$bin_dir/researchctl" \
  "$repo_root/bin/researchctl" \
  "CLI"

if [[ ":$PATH:" != *":$bin_dir:"* ]]; then
  printf 'note: add %s to PATH to invoke researchctl directly.\n' "$bin_dir"
fi

if ((errors)); then
  printf 'check failed: %d issue(s)\n' "$errors" >&2
  exit 1
fi

if $check_only; then
  printf 'installation check passed\n'
else
  printf 'installation complete\n'
fi
