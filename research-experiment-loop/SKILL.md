---
name: research-experiment-loop
description: Understand papers, reproduce published results, and run reproducible scientific or engineering research with explicit project stages, canonical baselines, preregistered hypotheses, frozen provenance, machine-readable registries, cross-cycle interrupt scheduling, theory-practice balance, offline-to-online evidence ladders, visual review artifacts, symmetric verdicts, and claim closure. Use when starting paper study or replication, resuming research experiments, planning autonomous compute work, auditing old results, detecting stagnation or repeated failures, balancing theory with practice, converging competing method routes, investigating surprising results, transferring a research workflow to a new project, or deciding whether evidence is strong enough to promote a method or paper claim.
---

# Research Experiment Loop

Use this skill to turn exploratory research into small, auditable experiment cycles without suppressing useful intuition.

## Start Here

1. Read the nearest `AGENTS.md` and existing project control docs first.
2. When creating, Git-initializing, naming, or reorganizing a project, read
   `references/git-and-naming.md` and `references/workspace-layout.md`. Run the read-only workspace
   hygiene audit before and after a boundary move.
3. For paper-led work, read `references/literature-workflow.md` and
   `references/paper-reproduction.md`. Keep collaborator deliveries in a staging inbox, snapshot
   verified materials into `references/`, and start in `understanding`. Freeze the baseline only
   after paper version, code lineage, target claim, protocol, reference artifact, and cost envelope
   are known, then enter `reproduction`.
4. Run `scripts/researchctl.py status` from the project root for a compact recovery view, then run
   `scripts/audit_research_state.py --root <project>` when a `research/` registry exists.
5. If no registry exists, run `scripts/init_research_state.py`; supply the north star, primary problem,
   canonical baseline, evaluation protocol, and at least one stage-exit gate.
6. Use `scripts/set_project_stage.py` only at an experiment boundary. Keep one canonical baseline, one
   primary problem, and one active candidate; park unrelated lanes explicitly.
7. Paper reading and protocol recovery are control tasks, not experiments. Before reproduction compute,
   create a `replication` cycle. Before exploratory method changes, create one falsifiable experiment.
   Use `--template probe|oracle|instrumentation` for diagnostic-only work; only formal or replication
   cycles may be promoted.
8. Treat workflow changes as separate control work. Follow `references/workflow-evolution.md`; never
   auto-upgrade an active or frozen experiment, and require explicit user approval for changes to
   schema, provenance, verdict semantics, lifecycle, or agent authority.
9. Treat Markdown control files as event-triggered human views, not a second state machine. Read
   `references/control-docs.md` when creating or reorganizing `CURRENT_STATE`, `PLAN`, `TODO`,
   `DEVLOG`, `RESULTS_SCOREBOARD`, or daily reports; run `researchctl docs` after meaningful updates.

Project instructions always override this generic workflow.

## Choose A Lane

- **Planned lane**: closes a known matrix gap or tests a mechanism already named in the plan.
- **Breakthrough lane**: investigates a surprising large effect, visual anomaly, contradiction, or result that changes the likely research direction.

Do not demote a breakthrough lead merely because it was unplanned. Record its alternative explanations and define the cheapest discriminating test.

## Run One Cycle

### 1. Recover State

- Identify the canonical repo, branch, commit, dirty state, active experiment, current best baseline, and promotion gate.
- Distinguish the control, runtime, workflow, third-party, and artifact-store roles; do not collapse
  their provenance into one repo field.
- Confirm the current stage, north star, primary problem, canonical baseline ID, and parked lanes.
- Distinguish historical clues from fingerprinted evidence.
- Do not batch-clean untracked research artifacts.

### 2. Preregister

Write one sentence each for the question, hypothesis, independent variable, controls, primary metric, tail metric, visual evidence, alternative explanations, and stop conditions.

If the experiment cannot distinguish at least two explanations, redesign it before running.

### 3. Freeze Provenance

- Run `scripts/freeze_experiment.py` before outcome inspection.
- Bind dump, analysis, and online validation to one tracked code state.
- Record expanded config, data slice, seed/repetition policy, output path, and forbidden priors.
- If source changes, commit or otherwise fingerprint it before regenerating evidence.
- Formal and replication cycles require a tracked-clean source state. Once frozen, do not rewrite,
  squash, or force-push the referenced history.
- Diagnostic templates inherit completion signals and project forbidden inputs. Formal cycles still
  require explicit seed and repetition policy.

### 4. Use The Evidence Ladder

Proceed in this order unless the preceding level cannot answer the question:

1. existing-artifact audit;
2. offline probe or simulation;
3. tracking-only or smallest runtime smoke;
4. full mapping/end-to-end run;
5. safety-set or benchmark expansion.

Do not use full runs to answer a question already settled offline.

### 5. Collect The Evidence Quartet

- numerical/probabilistic;
- spatial/visual;
- temporal/tail;
- causal intervention.

Read `references/evidence-and-verdicts.md` before making a strong positive or negative claim.

### 6. Produce A Human Review Artifact

Create a compact figure or sheet at the project's stable review path. Link the original artifacts rather than copying entire result trees. Explicitly record whether the user reviewed it. Register actual artifacts with `scripts/register_artifact.py`; do not register placeholders.

### 7. Judge Symmetrically

Apply the same provenance and evidence threshold to expected and unexpected results. Before claiming a signal is intrinsically weak, separate:

- signal information;
- calibration;
- temporal/reference alignment;
- consumer semantics;
- closed-loop feedback.

### 8. Close Or Escalate

Use `scripts/record_observation.py` for the post-run data walk. Record observations separately from interpretation, including unexpected spatial or tail behavior even when it was outside the hypothesis.

Close with `scripts/close_experiment.py`: verify that the expected action and completion signals occurred, then set the scientific decision, limitations, artifacts, human-review state, scoreboard/claim closure, and exactly one next discriminating question. An absent action cannot support a method verdict. Run the strict audit after closure. Promote only when the project-specific gate is met.

### 9. Evaluate Cross-Cycle Interrupts

Run `scripts/evaluate_research_scheduler.py` after closure. Keep it read-only by default. It may
recommend integrity review, breakthrough audit, reflection, constrained intuition, theory/practice
synchronization, synthesis, efficiency review, or human review. Use `--enqueue` only after checking
the reasons; queued tasks never launch experiments or modify method code. Complete them with
`scripts/complete_research_task.py`.

For a long active run, append a cheap `scripts/record_checkpoint.py` event at a meaningful boundary.
The scheduler may then detect wall/compute stagnation before closure. A checkpoint never stops the
process or authorizes a scientific verdict.

## Use Subagents Deliberately

Subagents may act as read-only scout, blind visual observer, mechanism red-team, provenance auditor, or synthesis reviewer. Give each a narrow question and immutable inputs. The main agent retains code changes, evidence merging, and final scientific judgment.

## Resources

- `references/research-cycle.md`: detailed execution and long-run autonomy loop.
- `references/literature-workflow.md`: literature search, screening, anchored extraction, synthesis,
  stable reference ingestion, claim promotion, and external research-workflow adapters.
- `references/paper-reproduction.md`: paper understanding, code lineage, protocol recovery, result
  replication, cost gates, and the transition into open-ended research.
- `references/evidence-and-verdicts.md`: evidence quartet, tail analysis, and verdict rules.
- `references/project-contract.md`: directory, JSONL, review, Git, and subagent conventions.
- `references/git-and-naming.md`: repo roles, branch/freeze/merge rules, identifiers, run tags, and unit-safe variable names.
- `references/workspace-layout.md`: control-repo/data-root layout, directory width/depth heuristics, staging, and archival rules.
- `references/workflow-evolution.md`: governed workflow feedback, versioning, migration, rollback, and explicit adoption.
- `references/control-docs.md`: low-burden document ownership, templates, update triggers, attribution, and audit rules.
- `references/gpf-research-implementation-adapter.md`: bounded mapping from the Claude GPF research-implementation workflow into this lifecycle.
- `references/stage-and-lifecycle.md`: stage transitions, canonical baselines, lifecycle commands, and domain profiles.
- `references/research-scheduler.md`: cross-cycle triggers, priorities, task contracts, and creativity guardrails.
- `references/method-patterns.md`: reusable Oracle, surgical, replay, fault-injection, canary, and control patterns.
- `scripts/init_research_state.py`: non-destructive project bootstrap.
- `scripts/researchctl.py`: unified command dispatcher plus dynamic list/show/find/next index.
- `scripts/set_project_stage.py`: freeze the current stage, primary problem, baseline, and exit gates.
- `scripts/new_experiment.py`: experiment registration and card generation.
- `scripts/freeze_experiment.py`: result-blind provenance freeze.
- `scripts/record_checkpoint.py`: low-friction active-run progress and compute accounting.
- `scripts/record_observation.py`: post-run data-walk observations.
- `scripts/register_artifact.py`: artifact provenance registration.
- `scripts/register_claim.py`: evidence-linked claim registration or supersession.
- `scripts/close_experiment.py`: closure event and active-state cleanup.
- `scripts/evaluate_research_scheduler.py`: read-only interrupt evaluation and explicit advisory enqueue.
- `scripts/complete_research_task.py`: advisory task closure with artifact/insight links.
- `scripts/reconcile_experiment.py`: explicit orphan adoption or evidence-backed legacy state repair.
- `scripts/relocate_project.py`: commit-checked project relocation with historical path aliases.
- `scripts/research_status.py`: read-only compact project, experiment, review, task, and scheduler view.
- `scripts/audit_research_state.py`: schema, references, paths, and Git audit.
- `scripts/audit_workspace_hygiene.py`: read-only Git, naming, large-file, cache, and root-layout audit.
- `scripts/audit_control_docs.py`: read-only metadata, structure, TODO, DEVLOG, stage, and review-pointer audit.
