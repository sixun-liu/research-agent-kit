---
name: research-experiment-loop
description: Run reproducible scientific or engineering research with explicit project stages, canonical baselines, preregistered hypotheses, frozen provenance, machine-readable registries, cross-cycle interrupt scheduling, theory-practice balance, offline-to-online evidence ladders, visual review artifacts, symmetric verdicts, and claim closure. Use when starting or resuming research experiments, planning autonomous compute work, auditing old results, detecting stagnation or repeated failures, balancing theory with practice, converging competing method routes, investigating surprising results, transferring a research workflow to a new project, or deciding whether evidence is strong enough to promote a method or paper claim.
---

# Research Experiment Loop

Use this skill to turn exploratory research into small, auditable experiment cycles without suppressing useful intuition.

## Start Here

1. Read the nearest `AGENTS.md` and existing project control docs first.
2. Run `scripts/research_status.py --root <project>` for a compact recovery view, then run
   `scripts/audit_research_state.py --root <project>` when a `research/` registry exists.
3. If no registry exists, run `scripts/init_research_state.py`; supply the north star, primary problem,
   canonical baseline, evaluation protocol, and at least one stage-exit gate.
4. Use `scripts/set_project_stage.py` only at an experiment boundary. Keep one canonical baseline, one
   primary problem, and one active candidate; park unrelated lanes explicitly.
5. Create one falsifiable experiment with `scripts/new_experiment.py` before changing runtime code or
   launching compute. Use `--template probe|oracle|instrumentation` for diagnostic-only work; only
   `formal` cycles may be promoted.

Project instructions always override this generic workflow.

## Choose A Lane

- **Planned lane**: closes a known matrix gap or tests a mechanism already named in the plan.
- **Breakthrough lane**: investigates a surprising large effect, visual anomaly, contradiction, or result that changes the likely research direction.

Do not demote a breakthrough lead merely because it was unplanned. Record its alternative explanations and define the cheapest discriminating test.

## Run One Cycle

### 1. Recover State

- Identify the canonical repo, branch, commit, dirty state, active experiment, current best baseline, and promotion gate.
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
- `references/evidence-and-verdicts.md`: evidence quartet, tail analysis, and verdict rules.
- `references/project-contract.md`: directory, JSONL, review, Git, and subagent conventions.
- `references/stage-and-lifecycle.md`: stage transitions, canonical baselines, lifecycle commands, and domain profiles.
- `references/research-scheduler.md`: cross-cycle triggers, priorities, task contracts, and creativity guardrails.
- `references/method-patterns.md`: reusable Oracle, surgical, replay, fault-injection, canary, and control patterns.
- `scripts/init_research_state.py`: non-destructive project bootstrap.
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
- `scripts/research_status.py`: read-only compact project, experiment, review, task, and scheduler view.
- `scripts/audit_research_state.py`: schema, references, paths, and Git audit.
