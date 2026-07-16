#!/usr/bin/env python3
"""Register or supersede a machine-readable research claim."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_state_lib import VALID_CONFIRMATIONS, append_jsonl, load_jsonl, next_id, utc_now


CLAIM_STATUSES = (
    "hypothesis",
    "supported-working-claim",
    "replicated",
    "paper-ready",
    "retracted",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--status", choices=CLAIM_STATUSES, required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--claim", required=True)
    parser.add_argument("--evidence-id", action="append", default=[])
    parser.add_argument("--limitation", action="append", default=[])
    parser.add_argument("--counterevidence", action="append", default=[])
    parser.add_argument("--supersedes")
    parser.add_argument("--human-confirmation", choices=sorted(VALID_CONFIRMATIONS), required=True)
    args = parser.parse_args()

    if not args.evidence_id and args.status != "hypothesis":
        raise SystemExit("A non-hypothesis claim requires at least one --evidence-id")
    if not args.limitation:
        raise SystemExit("At least one --limitation is required")

    root = args.root.resolve()
    research = root / "research"
    registry_paths = [
        research / "experiments.jsonl",
        research / "insights.jsonl",
        research / "artifacts.jsonl",
        research / "claims.jsonl",
    ]
    known_ids = {
        str(record.get("id"))
        for path in registry_paths
        for record in load_jsonl(path)
        if record.get("id")
    }
    unknown = sorted(set(args.evidence_id) - known_ids)
    if unknown:
        raise SystemExit(f"Unknown evidence ids: {', '.join(unknown)}")
    if args.supersedes and (not args.supersedes.startswith("C-") or args.supersedes not in known_ids):
        raise SystemExit(f"Unknown superseded claim: {args.supersedes}")
    if args.status == "paper-ready":
        if not any(value.startswith("EXP-") for value in args.evidence_id):
            raise SystemExit("A paper-ready claim requires experiment evidence")
        if not any(value.startswith("ART-") for value in args.evidence_id):
            raise SystemExit("A paper-ready claim requires artifact evidence")
        if args.human_confirmation == "pending":
            raise SystemExit("A paper-ready claim cannot have pending human confirmation")

    registry = research / "claims.jsonl"
    record = {
        "record_type": "claim",
        "schema_version": 2,
        "id": next_id(registry, "C"),
        "created_at": utc_now(),
        "status": args.status,
        "scope": args.scope,
        "claim": args.claim,
        "evidence_ids": args.evidence_id,
        "limitations": args.limitation,
        "counterevidence": args.counterevidence,
        "supersedes": args.supersedes,
        "paper_ready": args.status == "paper-ready",
        "human_visual_confirmation": args.human_confirmation,
    }
    append_jsonl(registry, record)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
