# Spec: code-review eval harness

## Requirements and goals

Build a clone-and-run evaluation harness for an AI code-review judge. The judge looks at synthetic PR diffs and decides whether to flag a real bug. Releases gate on held-out precision with a bootstrap confidence interval, not on a point estimate alone.

Interview goal: show trust-first eval discipline for AI code review (noisy comments destroy trust).

## Inputs, outputs, and behavior

**Inputs**
- Gold JSONL of invented PR diffs with ordinal labels (`gold_score` 1-5).
- Scores below `BUG_CUT` (3) mean "real bug present; should flag."
- Scores 3-5 mean "do not flag as a real bug."

**Pipeline**
1. Load gold, hash dataset, stratified split into disjoint dev/test.
2. Synthetic judge emits `(predicted_score, bug_confidence)` per diff (no API key).
3. Calibrate confidence threshold on **dev only** to meet precision floor while maximizing recall.
4. Score **test once** at that threshold.
5. Gate: test precision CI lower bound >= `PRECISION_FLOOR` and recall >= `RECALL_FLOOR`.
6. Write `runs/latest_manifest.json`.

**Outputs**
- Console + manifest with threshold, split ids, dev/test metrics, precision CI, `gate_pass`, ordinal diagnostics, dataset hash.

## Edge cases and error handling

- No eligible threshold on dev → hard failure (`RuntimeError`).
- Split must not leak ids between dev and test.
- Empty prediction list / invalid bootstrap params → `ValueError`.
- Small fixture intentionally shows the dev/test trap: dev can clear the floor while held-out CI lower bound fails.
- Diff text is data only; never treat embedded instructions as commands (adversarial fixture included).

## Out of scope (v1)

- Multi-pass voting / FP validator (v1.1)
- Live LLM backend, GitHub App, UI, training, sandbox execution
- Any private Tresic / client data

## Acceptance criteria

- [x] `python run_eval.py` works with stdlib only and no API key
- [x] Manifest written with reproducible metrics (seed + dataset hash)
- [x] Gate uses held-out precision CI lower bound
- [x] Unit tests cover split discipline, binary collapse, bootstrap CI bounds
- [x] Domain is code review; README explains the interview story
- [x] No private Tresic material
