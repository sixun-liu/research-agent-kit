from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"


class ResearchLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.run_command("git", "init", "-q", str(self.root))
        self.run_command("git", "-C", str(self.root), "config", "user.name", "research-test")
        self.run_command(
            "git", "-C", str(self.root), "config", "user.email", "research-test@example.invalid"
        )
        self.run_command("git", "-C", str(self.root), "commit", "--allow-empty", "-q", "-m", "init")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_command(self, *command: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, text=True, capture_output=True, check=check)

    def run_script(self, name: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.run_command(sys.executable, str(SCRIPTS / name), *args, check=check)

    def initialize(self) -> None:
        self.run_script(
            "init_research_state.py",
            "--root",
            str(self.root),
            "--project-id",
            "lifecycle-test",
            "--repo",
            str(self.root),
            "--stage",
            "attack",
            "--north-star",
            "Find a reproducible improvement",
            "--primary-problem",
            "Determine whether the candidate changes the intended mechanism",
            "--baseline-id",
            "BASE-0001",
            "--baseline-name",
            "Frozen baseline",
            "--baseline-config",
            "configs/baseline.yaml",
            "--evaluation-protocol",
            "exact held-out evaluation",
            "--stage-exit-gate",
            "candidate passes the safety set",
            "--primary-metric",
            "held-out primary score",
            "--tail-metric",
            "worst-case score",
            "--forbidden-input",
            "test labels at runtime",
            "--promotion-gate",
            "candidate does not regress the baseline",
            "--review-requirement",
            "compact comparison artifact",
        )

    def create_experiment(self) -> dict:
        result = self.run_script(
            "new_experiment.py",
            "--root",
            str(self.root),
            "--title",
            "Test candidate",
            "--question",
            "Does the candidate improve the frozen baseline?",
            "--hypothesis",
            "The candidate changes the intended action and improves the primary metric.",
            "--independent-variable",
            "candidate enabled versus disabled",
            "--expected-action",
            "the candidate action counter becomes nonzero",
            "--completion-signal",
            "result.json exists",
            "--alternative",
            "the effect is run variance",
            "--control",
            "same data and seed",
            "--metric",
            "primary metric and worst-case metric",
            "--stop-condition",
            "stop if the expected action is absent",
        )
        return json.loads(result.stdout)

    def test_full_lifecycle_and_strict_audit(self) -> None:
        self.initialize()
        self.run_script("audit_research_state.py", "--root", str(self.root), "--strict")
        created = self.create_experiment()
        self.assertEqual(created["id"], "EXP-0001")

        duplicate = self.run_script(
            "new_experiment.py",
            "--root",
            str(self.root),
            "--title",
            "Blocked duplicate",
            "--question",
            "Should not be created",
            "--hypothesis",
            "No",
            "--independent-variable",
            "none",
            "--expected-action",
            "none",
            "--completion-signal",
            "none",
            "--alternative",
            "none",
            "--control",
            "none",
            "--metric",
            "none",
            "--stop-condition",
            "none",
            check=False,
        )
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn("Active experiment", duplicate.stderr)

        config = self.root / "expanded.yaml"
        config.write_text("candidate: true\n", encoding="utf-8")
        self.run_script(
            "freeze_experiment.py",
            "--root",
            str(self.root),
            "--expanded-config",
            "expanded.yaml",
            "--data-slice",
            "held-out split",
            "--output-path",
            "outputs/exp-0001",
            "--seed-policy",
            "seed 1",
            "--repeat-policy",
            "one smoke then two repeats",
            "--forbidden-input",
            "test labels at runtime",
            "--completion-signal",
            "result.json exists",
        )

        artifact = self.root / "review.png"
        artifact.write_bytes(b"not-a-real-png-but-an-existing-artifact")
        registered = self.run_script(
            "register_artifact.py",
            "--root",
            str(self.root),
            "--path",
            "review.png",
            "--kind",
            "review_figure",
            "--title",
            "Compact review",
            "--provenance-quality",
            "fingerprinted",
            "--human-review",
        )
        artifact_id = json.loads(registered.stdout)["id"]

        self.run_script(
            "record_observation.py",
            "--root",
            str(self.root),
            "--observation",
            "The worst case moved to a different sample.",
            "--unexpected",
            "--follow-up",
            "Compare the shifted worst case with the frozen baseline.",
            "--artifact-id",
            artifact_id,
        )
        self.run_script(
            "close_experiment.py",
            "--root",
            str(self.root),
            "--verdict",
            "candidate_fails_tail_gate",
            "--decision",
            "negative",
            "--observation",
            "The primary metric improved but the tail gate failed.",
            "--interpretation",
            "The consumer is unsafe in the frozen protocol.",
            "--limitation",
            "Only one held-out split was tested.",
            "--artifact-id",
            artifact_id,
            "--next",
            "Return to an offline mechanism audit.",
            "--action-status",
            "occurred",
            "--completion-status",
            "confirmed",
            "--human-confirmation",
            "not_required",
            "--scoreboard-status",
            "updated",
            "--claim-status",
            "not_required",
        )
        claim = self.run_script(
            "register_claim.py",
            "--root",
            str(self.root),
            "--status",
            "paper-ready",
            "--scope",
            "held-out safety result",
            "--claim",
            "The frozen candidate fails the predefined tail gate.",
            "--evidence-id",
            "EXP-0001",
            "--evidence-id",
            artifact_id,
            "--limitation",
            "The claim is limited to the frozen held-out protocol.",
            "--human-confirmation",
            "not_required",
        )
        self.assertEqual(json.loads(claim.stdout)["id"], "C-0001")
        audit = self.run_script("audit_research_state.py", "--root", str(self.root), "--strict", "--json")
        result = json.loads(audit.stdout)
        self.assertTrue(result["ok"])
        self.assertIsNone(result["active_experiment_id"])

        state = yaml.safe_load((self.root / "research" / "project_state.yaml").read_text(encoding="utf-8"))
        self.assertIsNone(state["active_experiment_id"])
        card = (self.root / "research" / "cards" / "EXP-0001.md").read_text(encoding="utf-8")
        self.assertIn("candidate_fails_tail_gate", card)

        artifact.unlink()
        missing = self.run_script(
            "audit_research_state.py", "--root", str(self.root), "--strict", check=False
        )
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("registered artifact missing", missing.stdout)

    def test_stage_change_requires_boundary_and_close_requires_freeze(self) -> None:
        self.initialize()
        self.run_script(
            "set_project_stage.py",
            "--root",
            str(self.root),
            "--stage",
            "convergence",
            "--north-star",
            "Freeze the final method",
            "--primary-problem",
            "Close the safety matrix",
            "--baseline-id",
            "BASE-0002",
            "--baseline-name",
            "Convergence baseline",
            "--baseline-config",
            "configs/final.yaml",
            "--evaluation-protocol",
            "formal protocol",
            "--parked-lane",
            "unrelated idea",
            "--stage-exit-gate",
            "all primary conditions pass",
        )
        state = yaml.safe_load((self.root / "research" / "project_state.yaml").read_text(encoding="utf-8"))
        self.assertEqual(state["stage"], "convergence")
        self.assertEqual(state["canonical_baseline"]["id"], "BASE-0002")

        self.create_experiment()
        premature_close = self.run_script(
            "close_experiment.py",
            "--root",
            str(self.root),
            "--verdict",
            "premature",
            "--decision",
            "inconclusive",
            "--observation",
            "No result was run.",
            "--interpretation",
            "The lifecycle is incomplete.",
            "--limitation",
            "No frozen provenance.",
            "--next",
            "Freeze before running.",
            "--action-status",
            "not_applicable",
            "--completion-status",
            "not_applicable",
            "--human-confirmation",
            "not_required",
            "--scoreboard-status",
            "not_required",
            "--claim-status",
            "not_required",
            check=False,
        )
        self.assertNotEqual(premature_close.returncode, 0)
        self.assertIn("must be frozen", premature_close.stderr)

        blocked = self.run_script(
            "set_project_stage.py",
            "--root",
            str(self.root),
            "--stage",
            "writing",
            "--north-star",
            "Write",
            "--primary-problem",
            "Claims",
            "--baseline-id",
            "BASE-0002",
            "--baseline-name",
            "Convergence baseline",
            "--baseline-config",
            "configs/final.yaml",
            "--evaluation-protocol",
            "formal protocol",
            "--stage-exit-gate",
            "claims close",
            check=False,
        )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("experiment is active", blocked.stderr)

    def test_legacy_state_can_be_upgraded_at_a_stage_boundary(self) -> None:
        self.initialize()
        state_path = self.root / "research" / "project_state.yaml"
        state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        state["schema_version"] = 1
        for field in (
            "north_star",
            "primary_problem",
            "active_candidate",
            "canonical_baseline",
            "parked_lanes",
            "stage_exit_gates",
        ):
            state.pop(field, None)
        state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
        (self.root / "research" / "profile.yaml").unlink()

        self.run_script(
            "set_project_stage.py",
            "--root",
            str(self.root),
            "--stage",
            "convergence",
            "--north-star",
            "Converge one transferable method",
            "--primary-problem",
            "Close the cross-condition safety gap",
            "--baseline-id",
            "BASE-LEGACY",
            "--baseline-name",
            "Migrated baseline",
            "--baseline-config",
            "configs/migrated.yaml",
            "--evaluation-protocol",
            "formal evaluation",
            "--stage-exit-gate",
            "safety matrix closes",
            "--domain",
            "generic-compute",
            "--primary-metric",
            "formal score",
            "--promotion-gate",
            "no primary-condition regression",
        )
        audit = self.run_script(
            "audit_research_state.py", "--root", str(self.root), "--strict", "--json"
        )
        self.assertTrue(json.loads(audit.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
