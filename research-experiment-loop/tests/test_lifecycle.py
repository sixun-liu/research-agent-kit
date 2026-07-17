from __future__ import annotations

import json
import shutil
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

    def create_experiment(
        self,
        title: str = "Test candidate",
        family: str = "candidate-consumer",
        work_mode: str = "practice",
    ) -> dict:
        result = self.run_script(
            "new_experiment.py",
            "--root",
            str(self.root),
            "--title",
            title,
            "--question",
            "Does the candidate improve the frozen baseline?",
            "--hypothesis",
            "The candidate changes the intended action and improves the primary metric.",
            "--hypothesis-family",
            family,
            "--work-mode",
            work_mode,
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

    def run_negative_cycle(self, index: int, family: str = "stalled-family") -> str:
        experiment_id = self.create_experiment(
            title=f"Negative cycle {index}", family=family, work_mode="practice"
        )["id"]
        config = self.root / f"expanded-{index}.yaml"
        config.write_text(f"candidate: {index}\n", encoding="utf-8")
        self.run_script(
            "freeze_experiment.py",
            "--root",
            str(self.root),
            "--expanded-config",
            config.name,
            "--data-slice",
            "held-out split",
            "--output-path",
            f"outputs/negative-{index}",
            "--seed-policy",
            "fixed seed",
            "--repeat-policy",
            "single discriminating run",
            "--completion-signal",
            "result.json exists",
        )
        self.run_script(
            "close_experiment.py",
            "--root",
            str(self.root),
            "--verdict",
            f"negative-cycle-{index}",
            "--decision",
            "negative",
            "--observation",
            "The expected action occurred but the safety gate failed.",
            "--interpretation",
            "The current hypothesis family did not resolve the frozen failure.",
            "--limitation",
            "The conclusion is limited to the frozen protocol.",
            "--next",
            "Run the scheduler before choosing another experiment.",
            "--progress-type",
            "none",
            "--progress-note",
            "The primary gap did not shrink and no route was closed.",
            "--failure-axis",
            "tail-safety",
            "--wall-hours",
            "1.1",
            "--compute-hours",
            "0.8",
            "--practice-output",
            "A controlled intervention produced a valid negative result.",
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
        return experiment_id

    def test_grouped_help_and_command_help(self) -> None:
        overview = self.run_script("researchctl.py", "--help")
        self.assertIn("Recover and inspect", overview.stdout)
        self.assertIn("hygiene", overview.stdout)
        self.assertIn("docs", overview.stdout)
        self.assertIn("Typical cycle", overview.stdout)
        command = self.run_script("researchctl.py", "help", "new")
        self.assertIn("--template", command.stdout)
        self.assertIn("--hypothesis-family", command.stdout)
        self.assertIn("replication", command.stdout)

    def test_control_doc_templates_and_read_only_audit(self) -> None:
        self.initialize()
        before = {
            path.name: path.read_text(encoding="utf-8")
            for path in self.root.glob("*.md")
        }
        result = self.run_script(
            "researchctl.py", "docs", "--root", str(self.root), "--strict", "--json"
        )
        value = json.loads(result.stdout)
        self.assertTrue(value["strict_ok"])
        self.assertEqual(value["documents"]["TODO.md"]["completed_items"], 0)
        self.assertTrue((self.root / "reports" / "daily" / "TEMPLATE.md").is_file())
        after = {
            path.name: path.read_text(encoding="utf-8")
            for path in self.root.glob("*.md")
        }
        self.assertEqual(before, after)

        todo = self.root / "TODO.md"
        todo.write_text(
            todo.read_text(encoding="utf-8")
            + "\n".join(f"- [x] completed {index}" for index in range(4))
            + "\n",
            encoding="utf-8",
        )
        warning = self.run_script(
            "researchctl.py", "docs", "--root", str(self.root), "--json"
        )
        warning_value = json.loads(warning.stdout)
        self.assertTrue(warning_value["ok"])
        self.assertFalse(warning_value["strict_ok"])
        self.assertTrue(any("completed items" in item for item in warning_value["warnings"]))

    def test_understanding_stage_precedes_replication_baseline(self) -> None:
        self.run_script(
            "init_research_state.py",
            "--root",
            str(self.root),
            "--project-id",
            "paper-reproduction-test",
            "--repo",
            str(self.root),
            "--stage",
            "understanding",
            "--north-star",
            "Understand and reproduce one published result",
            "--primary-problem",
            "Resolve the paper, code, and evaluation protocol",
            "--stage-exit-gate",
            "claim-protocol matrix is complete",
            "--primary-metric",
            "protocol fields resolved",
            "--promotion-gate",
            "one feasible reproduction target is selected",
        )
        state_path = self.root / "research" / "project_state.yaml"
        state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["stage"], "understanding")
        self.assertIsNone(state["canonical_baseline"])

        audit = self.run_script(
            "audit_research_state.py", "--root", str(self.root), "--strict", "--json"
        )
        self.assertTrue(json.loads(audit.stdout)["ok"])
        status = self.run_script(
            "research_status.py", "--root", str(self.root), "--json"
        )
        self.assertEqual(
            json.loads(status.stdout)["next_action"]["action"],
            "complete_paper_protocol_audit",
        )

        self.run_script(
            "set_project_stage.py",
            "--root",
            str(self.root),
            "--stage",
            "reproduction",
            "--north-star",
            "Reproduce one published result",
            "--primary-problem",
            "Match the frozen reference curve",
            "--baseline-id",
            "BASE-PAPER-0001",
            "--baseline-name",
            "Author public reimplementation",
            "--baseline-config",
            "configs/paper.yaml",
            "--evaluation-protocol",
            "paper table protocol",
            "--stage-exit-gate",
            "one target result has a symmetric verdict",
        )
        result = self.run_script(
            "new_experiment.py",
            "--root",
            str(self.root),
            "--template",
            "replication",
            "--title",
            "Reproduce the paper baseline",
            "--question",
            "Does the author implementation reproduce the declared score?",
            "--hypothesis",
            "The frozen implementation reaches the published performance envelope.",
            "--hypothesis-family",
            "paper-baseline",
            "--reproduction-kind",
            "author_reimplementation",
            "--target-claim",
            "Table 1 baseline score",
            "--reference-artifact",
            "paper-table-1",
            "--protocol-match",
            "same task, budget, preprocessing, and evaluation",
            "--metric",
            "per-seed return and aggregate interval",
            "--stop-condition",
            "stop on protocol drift or non-finite training",
            "--completion-signal",
            "comparison artifact exists",
        )
        experiment_id = json.loads(result.stdout)["id"]
        records = [
            json.loads(line)
            for line in (self.root / "research" / "experiments.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        experiment = next(record for record in records if record.get("id") == experiment_id)
        self.assertEqual(experiment["cycle_class"], "replication")
        self.assertEqual(
            experiment["replication_target"]["kind"], "author_reimplementation"
        )

        config = self.root / "expanded-paper.yaml"
        config.write_text("task: paper-task\n", encoding="utf-8")
        missing_repeats = self.run_script(
            "freeze_experiment.py",
            "--root",
            str(self.root),
            "--expanded-config",
            config.name,
            "--data-slice",
            "paper task",
            "--output-path",
            "outputs/paper-baseline",
            check=False,
        )
        self.assertNotEqual(missing_repeats.returncode, 0)
        self.assertIn("seed-policy", missing_repeats.stderr)

    def test_full_lifecycle_and_strict_audit(self) -> None:
        self.initialize()
        self.assertTrue((self.root / ".gitignore").is_file())
        for directory in (
            "configs/baselines",
            "configs/experiments",
            "references/manifests",
            "discussion/claude",
            "reports/daily",
        ):
            self.assertTrue((self.root / directory).is_dir())
        for filename in (
            "CURRENT_STATE.md",
            "PLAN.md",
            "TODO.md",
            "DEVLOG.md",
            "RESULTS_SCOREBOARD.md",
        ):
            self.assertTrue((self.root / filename).is_file())
        self.assertIn(
            "机器状态请运行",
            (self.root / "CURRENT_STATE.md").read_text(encoding="utf-8"),
        )
        todo_path = self.root / "TODO.md"
        todo_path.write_text("# project-owned TODO\n", encoding="utf-8")
        self.initialize()
        self.assertEqual(todo_path.read_text(encoding="utf-8"), "# project-owned TODO\n")
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
            "--hypothesis-family",
            "duplicate",
            "--work-mode",
            "practice",
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
            "--progress-type",
            "route_closed",
            "--progress-note",
            "The unsafe consumer family was closed under the frozen protocol.",
            "--failure-axis",
            "tail-safety",
            "--wall-hours",
            "0.25",
            "--compute-hours",
            "0.10",
            "--practice-output",
            "The candidate action occurred and failed the predefined tail gate.",
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
            "--progress-type",
            "none",
            "--progress-note",
            "No valid experiment was performed.",
            "--wall-hours",
            "0",
            "--compute-hours",
            "0",
            "--practice-output",
            "No intervention was performed.",
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
        (self.root / "research" / "scheduler.yaml").unlink()
        (self.root / "research" / "tasks.jsonl").unlink()

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

    def test_workspace_hygiene_is_read_only_and_flags_untracked_source(self) -> None:
        self.initialize()
        self.run_command("git", "-C", str(self.root), "add", ".")
        self.run_command(
            "git", "-C", str(self.root), "commit", "-q", "-m", "initialize control plane"
        )
        scratch = self.root / "scratch.py"
        scratch.write_text("print('untracked')\n", encoding="utf-8")

        result = self.run_script(
            "researchctl.py", "hygiene", "--root", str(self.root), "--json"
        )
        value = json.loads(result.stdout)
        self.assertTrue(value["ok"])
        self.assertFalse(value["strict_ok"])
        self.assertIn("scratch.py", value["untracked_source_like"])
        self.assertTrue(any("no remote" in warning for warning in value["warnings"]))
        self.assertTrue(scratch.exists())

    def test_scheduler_detects_stagnation_and_avoids_duplicate_tasks(self) -> None:
        self.initialize()
        for index in range(1, 4):
            self.run_negative_cycle(index)

        tasks_path = self.root / "research" / "tasks.jsonl"
        tasks_before = tasks_path.read_text(encoding="utf-8")
        evaluated = self.run_script(
            "evaluate_research_scheduler.py", "--root", str(self.root), "--json"
        )
        self.assertEqual(tasks_path.read_text(encoding="utf-8"), tasks_before)
        self.assertFalse((self.root / "discussion" / "scheduler").exists())
        actions = {
            value["action_type"] for value in json.loads(evaluated.stdout)["recommendations"]
        }
        self.assertTrue(
            {"REFLECT", "INTUITION", "EFFICIENCY_REVIEW", "THEORY_SYNC"}.issubset(actions)
        )

        enqueued = self.run_script(
            "evaluate_research_scheduler.py", "--root", str(self.root), "--enqueue", "--json"
        )
        enqueued_ids = json.loads(enqueued.stdout)["enqueued"]
        self.assertGreaterEqual(len(enqueued_ids), 4)
        duplicate = self.run_script(
            "evaluate_research_scheduler.py", "--root", str(self.root), "--enqueue", "--json"
        )
        self.assertEqual(json.loads(duplicate.stdout)["enqueued"], [])

        tasks = [
            json.loads(line)
            for line in (self.root / "research" / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        reflect_id = next(
            record["id"]
            for record in tasks
            if record.get("record_type") == "research_task" and record.get("action_type") == "REFLECT"
        )
        intuition_id = next(
            record["id"]
            for record in tasks
            if record.get("record_type") == "research_task"
            and record.get("action_type") == "INTUITION"
        )
        efficiency_id = next(
            record["id"]
            for record in tasks
            if record.get("record_type") == "research_task"
            and record.get("action_type") == "EFFICIENCY_REVIEW"
        )
        self.run_script(
            "complete_research_task.py",
            "--root",
            str(self.root),
            "--task-id",
            intuition_id,
            "--status",
            "deferred",
            "--result",
            "Wait for the frozen replay artifact before leaving the local search region.",
            "--resume-condition",
            "The replay artifact is registered.",
        )
        self.run_script(
            "complete_research_task.py",
            "--root",
            str(self.root),
            "--task-id",
            efficiency_id,
            "--status",
            "merged",
            "--result",
            "The same first-divergence audit resolves both reflection and cost questions.",
            "--merge-into",
            reflect_id,
        )
        self.run_script(
            "complete_research_task.py",
            "--root",
            str(self.root),
            "--task-id",
            reflect_id,
            "--status",
            "complete",
            "--result",
            "The failures share one consumer-level tail mechanism.",
            "--next",
            "Design one offline first-divergence audit.",
        )
        audit = self.run_script(
            "audit_research_state.py", "--root", str(self.root), "--strict", "--json"
        )
        self.assertTrue(json.loads(audit.stdout)["ok"])

        status = self.run_script("research_status.py", "--root", str(self.root), "--json")
        open_tasks = {value["id"]: value for value in json.loads(status.stdout)["open_tasks"]}
        self.assertEqual(open_tasks[intuition_id]["status"], "deferred")
        self.assertNotIn(efficiency_id, open_tasks)

    def test_low_friction_probe_checkpoint_status_and_close(self) -> None:
        self.initialize()
        scheduler_path = self.root / "research" / "scheduler.yaml"
        scheduler = yaml.safe_load(scheduler_path.read_text(encoding="utf-8"))
        scheduler["stage_thresholds"] = {
            "attack": {
                "active_no_progress_wall_hours": 99.0,
                "active_no_progress_compute_hours": 0.2,
            }
        }
        scheduler_path.write_text(yaml.safe_dump(scheduler, sort_keys=False), encoding="utf-8")

        created = self.run_script(
            "new_experiment.py",
            "--root",
            str(self.root),
            "--template",
            "probe",
            "--title",
            "Cheap alignment probe",
            "--question",
            "Does the saved alignment explain the first divergence?",
            "--hypothesis",
            "A frozen replay will localize the divergence before the consumer.",
            "--hypothesis-family",
            "alignment-probe",
        )
        experiment_id = json.loads(created.stdout)["id"]
        experiment_rows = [
            json.loads(line)
            for line in (self.root / "research" / "experiments.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        experiment = next(record for record in experiment_rows if record.get("id") == experiment_id)
        self.assertEqual(experiment["cycle_class"], "probe")
        self.assertFalse(experiment["formal_claim_eligible"])
        self.assertEqual(experiment["work_mode"], "practice")

        config = self.root / "probe-expanded.yaml"
        config.write_text("probe: fixed\n", encoding="utf-8")
        self.run_script(
            "freeze_experiment.py",
            "--root",
            str(self.root),
            "--expanded-config",
            config.name,
            "--data-slice",
            "saved state",
            "--output-path",
            "outputs/alignment-probe",
        )
        self.run_script(
            "record_checkpoint.py",
            "--root",
            str(self.root),
            "--note",
            "Replay ran but did not reduce the active uncertainty.",
            "--compute-hours-delta",
            "0.25",
            "--action-status",
            "occurred",
            "--completion-status",
            "confirmed",
        )

        status = self.run_script("research_status.py", "--root", str(self.root), "--json")
        status_value = json.loads(status.stdout)
        self.assertEqual(status_value["active_experiment"]["checkpoint_count"], 1)
        self.assertEqual(status_value["active_experiment"]["compute_hours_recorded"], 0.25)
        self.assertTrue(status_value["audit"]["strict_ok"])
        self.assertEqual(status_value["next_action"]["action"], "observe_or_close")
        actions = {value["action_type"] for value in status_value["recommendations"]}
        self.assertTrue({"REFLECT", "INTUITION", "EFFICIENCY_REVIEW"}.issubset(actions))

        listed = self.run_script(
            "researchctl.py",
            "list",
            "experiments",
            "--root",
            str(self.root),
            "--family",
            "alignment-probe",
            "--json",
        )
        listed_rows = json.loads(listed.stdout)
        self.assertEqual([row["id"] for row in listed_rows], [experiment_id])
        shown = self.run_script(
            "researchctl.py", "show", experiment_id, "--root", str(self.root), "--json"
        )
        shown_value = json.loads(shown.stdout)
        self.assertGreaterEqual(shown_value["event_count"], 2)
        next_value = self.run_script(
            "researchctl.py", "next", "--root", str(self.root), "--json"
        )
        self.assertEqual(json.loads(next_value.stdout)["action"], "observe_or_close")

        rejected_promotion = self.run_script(
            "close_experiment.py",
            "--root",
            str(self.root),
            "--verdict",
            "invalid-probe-promotion",
            "--decision",
            "promote",
            "--observation",
            "The probe produced a useful diagnostic result.",
            "--interpretation",
            "Diagnostic evidence must be rerun as a formal cycle.",
            "--next",
            "Open a formal experiment if the mechanism remains promising.",
            "--progress-type",
            "uncertainty_reduction",
            "--scoreboard-status",
            "updated",
            "--claim-status",
            "updated",
            check=False,
        )
        self.assertNotEqual(rejected_promotion.returncode, 0)
        self.assertIn("diagnostic-only", rejected_promotion.stderr)

        closed = self.run_script(
            "close_experiment.py",
            "--root",
            str(self.root),
            "--verdict",
            "probe-reduces-one-alternative",
            "--decision",
            "needs_more_evidence",
            "--observation",
            "The replay ruled out a post-consumer divergence.",
            "--interpretation",
            "The next probe should inspect temporal alignment before the consumer.",
            "--next",
            "Run one first-divergence audit on the saved state.",
            "--progress-type",
            "uncertainty_reduction",
        )
        closure = json.loads(closed.stdout)
        self.assertEqual(closure["compute_hours"], 0.25)
        self.assertEqual(closure["closure_checklist"]["scoreboard"], "not_required")
        self.assertIn("Diagnostic probe", closure["limitations"][0])
        audit = self.run_script(
            "audit_research_state.py", "--root", str(self.root), "--strict", "--json"
        )
        self.assertTrue(json.loads(audit.stdout)["ok"])

    def test_scheduler_uses_wall_budget_before_cycle_budget(self) -> None:
        self.initialize()
        scheduler_path = self.root / "research" / "scheduler.yaml"
        scheduler = yaml.safe_load(scheduler_path.read_text(encoding="utf-8"))
        scheduler["thresholds"]["no_progress_cycles"] = 99
        scheduler["thresholds"]["no_progress_wall_hours"] = 1.0
        scheduler["thresholds"]["no_progress_compute_hours"] = 99.0
        scheduler_path.write_text(yaml.safe_dump(scheduler, sort_keys=False), encoding="utf-8")
        self.run_negative_cycle(1)

        evaluated = self.run_script(
            "evaluate_research_scheduler.py", "--root", str(self.root), "--json"
        )
        actions = {
            value["action_type"] for value in json.loads(evaluated.stdout)["recommendations"]
        }
        self.assertTrue({"REFLECT", "INTUITION", "EFFICIENCY_REVIEW"}.issubset(actions))

    def test_scheduler_detects_breakthrough_theory_imbalance_and_review_debt(self) -> None:
        self.initialize()
        scheduler_path = self.root / "research" / "scheduler.yaml"
        scheduler = yaml.safe_load(scheduler_path.read_text(encoding="utf-8"))
        scheduler["thresholds"]["theory_only_streak"] = 1
        scheduler["thresholds"]["cycles_without_synthesis"] = 1
        scheduler["thresholds"]["pending_human_reviews"] = 1
        scheduler_path.write_text(yaml.safe_dump(scheduler, sort_keys=False), encoding="utf-8")

        experiment_id = self.create_experiment(
            title="Theory cycle", family="mechanism-model", work_mode="theory"
        )["id"]
        config = self.root / "theory-expanded.yaml"
        config.write_text("analysis: fixed\n", encoding="utf-8")
        self.run_script(
            "freeze_experiment.py",
            "--root",
            str(self.root),
            "--expanded-config",
            config.name,
            "--data-slice",
            "existing artifacts",
            "--output-path",
            "outputs/theory-cycle",
            "--seed-policy",
            "not applicable",
            "--repeat-policy",
            "one deterministic audit",
            "--completion-signal",
            "analysis.json exists",
        )
        self.run_script(
            "record_observation.py",
            "--root",
            str(self.root),
            "--observation",
            "A counterexample appears outside the expected failure window.",
            "--unexpected",
            "--follow-up",
            "Use a blind artifact audit before changing the model.",
        )
        self.run_script(
            "close_experiment.py",
            "--root",
            str(self.root),
            "--verdict",
            "mechanism-needs-practice",
            "--decision",
            "needs_more_evidence",
            "--observation",
            "The theory produced a discriminating prediction and one counterexample.",
            "--interpretation",
            "The mechanism must be tested by a local intervention.",
            "--limitation",
            "No closed-loop intervention was run.",
            "--next",
            "Run one surgical intervention against the prediction.",
            "--progress-type",
            "uncertainty_reduction",
            "--progress-note",
            "The candidate explanations now make different predictions.",
            "--wall-hours",
            "0.4",
            "--compute-hours",
            "0",
            "--theory-output",
            "Prediction: only the localized failure window should respond to intervention.",
            "--action-status",
            "not_applicable",
            "--completion-status",
            "confirmed",
            "--human-confirmation",
            "pending",
            "--scoreboard-status",
            "updated",
            "--claim-status",
            "not_required",
        )
        evaluated = self.run_script(
            "evaluate_research_scheduler.py", "--root", str(self.root), "--json"
        )
        actions = {
            value["action_type"] for value in json.loads(evaluated.stdout)["recommendations"]
        }
        self.assertTrue(
            {"BREAKTHROUGH", "PRACTICE_SYNC", "SYNTHESIS", "HUMAN_REVIEW"}.issubset(actions)
        )
        self.assertEqual(experiment_id, "EXP-0001")

    def test_legacy_reconciliation_uses_event_time_not_file_order(self) -> None:
        self.initialize()
        registry = self.root / "research" / "experiments.jsonl"
        records = [
            {
                "record_type": "experiment",
                "schema_version": 1,
                "id": "EXP-9000",
                "title": "Out-of-order completed legacy experiment",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "status": "preregistered",
                "human_visual_confirmation": "not_required",
            },
            {
                "record_type": "experiment_event",
                "schema_version": 1,
                "id": "EVT-9000",
                "experiment_id": "EXP-9000",
                "created_at": "2026-01-03T00:00:00Z",
                "status": "complete",
                "verdict": "legacy-complete",
            },
            {
                "record_type": "experiment_event",
                "schema_version": 1,
                "id": "EVT-9001",
                "experiment_id": "EXP-9000",
                "created_at": "2026-01-02T00:00:00Z",
                "status": "offline_in_progress",
                "verdict": "backfilled-earlier-event",
            },
            {
                "record_type": "experiment",
                "schema_version": 1,
                "id": "EXP-9001",
                "title": "Orphan legacy experiment",
                "created_at": "2026-01-04T00:00:00Z",
                "updated_at": "2026-01-04T00:00:00Z",
                "status": "preregistered",
                "human_visual_confirmation": "not_required",
            },
        ]
        with registry.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, separators=(",", ":")) + "\n")
        card = self.root / "research" / "cards" / "EXP-9001.md"
        card.write_text("# EXP-9001\n\nExisting evidence says this cycle is complete.\n", encoding="utf-8")

        status = self.run_script("researchctl.py", "status", "--root", str(self.root), "--json")
        status_value = json.loads(status.stdout)
        self.assertNotIn("EXP-9000", status_value["orphan_open_experiments"])
        self.assertIn("EXP-9001", status_value["orphan_open_experiments"])

        self.run_script(
            "researchctl.py",
            "reconcile",
            "EXP-9001",
            "--root",
            str(self.root),
            "--adopt",
            "--reason",
            "Resume the newest legacy card before resolving its recorded result.",
        )
        state = yaml.safe_load((self.root / "research" / "project_state.yaml").read_text())
        self.assertEqual(state["active_experiment_id"], "EXP-9001")
        self.run_script(
            "researchctl.py",
            "reconcile",
            "EXP-9001",
            "--root",
            str(self.root),
            "--complete-legacy",
            "--verdict",
            "legacy-card-result-backfilled",
            "--reason",
            "The existing card already records the result; only machine state was missing.",
            "--evidence-path",
            str(card),
        )
        audit = self.run_script(
            "audit_research_state.py", "--root", str(self.root), "--strict", "--json"
        )
        self.assertTrue(json.loads(audit.stdout)["ok"])
        status = self.run_script("researchctl.py", "status", "--root", str(self.root), "--json")
        self.assertNotIn("EXP-9001", json.loads(status.stdout)["orphan_open_experiments"])

    def test_relocate_preserves_historical_paths_through_aliases(self) -> None:
        self.initialize()
        artifact = self.root / "review.png"
        artifact.write_bytes(b"portable-artifact")
        artifact_id = "ART-0001"
        with (self.root / "research" / "artifacts.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "record_type": "artifact",
                        "schema_version": 1,
                        "id": artifact_id,
                        "experiment_id": None,
                        "created_at": "2026-01-01T00:00:00Z",
                        "kind": "review",
                        "title": "Portable review",
                        "path": str(artifact),
                        "exists_at_registration": True,
                        "provenance_quality": "historical_only",
                    },
                    separators=(",", ":"),
                )
                + "\n"
            )

        relocated_root = Path(tempfile.mkdtemp(prefix="research-relocated-"))
        self.addCleanup(shutil.rmtree, relocated_root, True)
        shutil.copytree(self.root, relocated_root, dirs_exist_ok=True)
        artifact.unlink()

        relocated = self.run_script(
            "researchctl.py",
            "relocate",
            "--root",
            str(relocated_root),
            "--repo",
            str(relocated_root),
            "--json",
        )
        value = json.loads(relocated.stdout)
        self.assertEqual(value["canonical_repo"]["path"], ".")
        self.assertEqual(value["historical_root_registered"], str(self.root))
        self.assertEqual(value["path_aliases_added"], [])

        state = yaml.safe_load(
            (relocated_root / "research" / "project_state.yaml").read_text(encoding="utf-8")
        )
        self.assertIn(str(self.root), state["workspace"]["historical_roots"])
        self.assertEqual(state["canonical_repo"]["path"], ".")
        rows = [
            json.loads(line)
            for line in (relocated_root / "research" / "artifacts.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        stored = next(row for row in rows if row.get("id") == artifact_id)
        self.assertEqual(stored["path"], str(artifact))
        self.assertFalse(artifact.exists())
        self.assertTrue((relocated_root / "review.png").exists())

        audit = self.run_script(
            "audit_research_state.py",
            "--root",
            str(relocated_root),
            "--strict",
            "--json",
        )
        self.assertTrue(json.loads(audit.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
