---
name: research-experiment-loop
description: Run reproducible scientific or engineering experiment cycles with preregistered hypotheses, frozen code provenance, machine-readable registries, offline-to-online evidence ladders, visual review artifacts, symmetric positive/negative verdicts, and insight follow-up. Use when starting or resuming research experiments, planning autonomous GPU work, auditing old results, organizing experiment state, investigating a surprising result, or deciding whether evidence is strong enough to promote a method.
---

# Research Experiment Loop

Use this skill to turn exploratory research into small, auditable experiment cycles without suppressing useful intuition.

## Start Here

1. Read the nearest `AGENTS.md` and existing project control docs first.
2. Run `scripts/audit_research_state.py --root <project>` when a `research/` registry exists.
3. If no registry exists, run `scripts/init_research_state.py`; never overwrite existing control docs by default.
4. Create one falsifiable experiment with `scripts/new_experiment.py` before changing runtime code or launching GPU work.
5. Follow the evidence ladder and update the same experiment record through verdict.

Project instructions always override this generic workflow.

## Choose A Lane

- **Planned lane**: closes a known matrix gap or tests a mechanism already named in the plan.
- **Breakthrough lane**: investigates a surprising large effect, visual anomaly, contradiction, or result that changes the likely research direction.

Do not demote a breakthrough lead merely because it was unplanned. Record its alternative explanations and define the cheapest discriminating test.

## Run One Cycle

### 1. Recover State

- Identify the canonical repo, branch, commit, dirty state, active experiment, current best baseline, and promotion gate.
- Distinguish historical clues from fingerprinted evidence.
- Do not batch-clean untracked research artifacts.

### 2. Preregister

Write one sentence each for the question, hypothesis, independent variable, controls, primary metric, tail metric, visual evidence, alternative explanations, and stop conditions.

If the experiment cannot distinguish at least two explanations, redesign it before running.

### 3. Freeze Provenance

- Bind dump, analysis, and online validation to one tracked code state.
- Record expanded config, data slice, seed/repetition policy, output path, and forbidden priors.
- If source changes, commit or otherwise fingerprint it before regenerating evidence.

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

Create a compact figure or sheet at the project's stable review path. Link the original artifacts rather than copying entire result trees. Explicitly record whether the user reviewed it.

### 7. Judge Symmetrically

Apply the same provenance and evidence threshold to expected and unexpected results. Before claiming a signal is intrinsically weak, separate:

- signal information;
- calibration;
- temporal/reference alignment;
- consumer semantics;
- closed-loop feedback.

### 8. Close Or Escalate

Record observations separately from interpretation, list alternatives, set a verdict, update artifact links, and choose exactly one next discriminating experiment. Promote only when the project-specific gate is met.

## Use Subagents Deliberately

Subagents may act as read-only scout, blind visual observer, mechanism red-team, provenance auditor, or synthesis reviewer. Give each a narrow question and immutable inputs. The main agent retains code changes, evidence merging, and final scientific judgment.

## Resources

- `references/research-cycle.md`: detailed execution and long-run autonomy loop.
- `references/evidence-and-verdicts.md`: evidence quartet, tail analysis, and verdict rules.
- `references/project-contract.md`: directory, JSONL, review, Git, and subagent conventions.
- `scripts/init_research_state.py`: non-destructive project bootstrap.
- `scripts/new_experiment.py`: experiment registration and card generation.
- `scripts/audit_research_state.py`: schema, references, paths, and Git audit.
