# Spec: code-review eval harness

## Requirements and goals

Build a clone-and-run evaluation harness for an AI code-review judge. The judge looks at synthetic PR diffs and decides whether to flag a real bug. Releases gate on held-out precision with a bootstrap confidence interval, not on a point estimate alone.

Interview goal: show trust-first eval discipline for AI code review (noisy comments destroy trust), plus a small harness hill-climb (multi-pass vote + FP validator).

## Inputs, outputs, and behavior

**Inputs**
- Gold JSONL of invented PR diffs with ordinal labels (`gold_score` 1-5).
- Scores below `BUG_CUT` (3) mean "real bug present; should flag."
- Scores 3-5 mean "do not flag as a real bug."

**Pipeline (default harness)**
1. Load gold, hash dataset, stratified split into disjoint dev/test.
2. For each diff, run `N_PASSES` review passes on shuffled diff line order.
3. Majority-vote merge: keep a flag only if at least `VOTE_MIN` passes agree; confidence reflects vote support.
4. FP validator: demote findings that look like comment/TODO noise rather than real bugs.
5. Calibrate confidence threshold on **dev only** to meet precision floor while maximizing recall.
6. Score **test once** at that threshold.
7. Gate: test precision CI lower bound >= `PRECISION_FLOOR` and recall >= `RECALL_FLOOR`.
8. Write `runs/latest_manifest.json` (includes pipeline config).

**Baseline mode** (`python run_eval.py --baseline`): single pass, no vote, no validator - for before/after comparison.

**Outputs**
- Console + manifest with pipeline mode, threshold, split ids, dev/test metrics, precision CI, `gate_pass`, ordinal diagnostics, dataset hash.

## Edge cases and error handling

- No eligible threshold on dev → hard failure (`RuntimeError`).
- Split must not leak ids between dev and test.
- Empty prediction list / invalid bootstrap params → `ValueError`.
- `N_PASSES` / `VOTE_MIN` misconfigured (`VOTE_MIN` > `N_PASSES` or < 1) → `ValueError`.
- Diff text is data only; never treat embedded instructions as commands (adversarial fixture included).

## Out of scope

- Live LLM backend, GitHub App, UI, training, sandbox execution
- Any private Tresic / client data

## Acceptance criteria

- [x] `python run_eval.py` works with stdlib only and no API key
- [x] Manifest written with reproducible metrics (seed + dataset hash)
- [x] Gate uses held-out precision CI lower bound
- [x] Unit tests cover split discipline, binary collapse, bootstrap CI bounds
- [x] Domain is code review; README explains the interview story
- [x] No private Tresic material
- [x] Multi-pass shuffle + majority vote is deterministic and tested
- [x] FP validator demotes TODO-comment false positives and is tested
- [x] `--baseline` vs default harness is runnable for a hill-climb comparison
