# Methodology

## The contract

The judge emits an ordinal severity score from 1 to 5 and a confidence that the
diff should be flagged as containing a real bug. For the contract metric, both
the human score and the operational decision collapse at `BUG_CUT`: scores
below 3 are positives (flag), while scores 3 through 5 are negatives.

Precision is the lead metric because a false positive becomes a noisy review
comment. Recall still matters, but missing some bugs is the tolerated error
relative to eroding trust with junk flags.

## Dev/test discipline

The dataset is stratified into disjoint development and test sets with a fixed
seed. Candidate confidence thresholds are swept on development only. The chosen
threshold is applied to test exactly once. No test result participates in
threshold selection.

## Why the lower confidence bound is the gate

Precision is `TP / (TP + FP)`, but it is not equally informative at every sample
size. A result of 0.90 on 9 flagged items has more sampling uncertainty than
0.90 on 900. The bootstrap interval exposes that uncertainty. The gate requires
the held-out lower bound to clear the precision floor, rather than allowing a
point estimate to pass on optimism alone.

## Baseline vs harness hill-climb

**Baseline** (`python run_eval.py --baseline`): one pass per diff. The synthetic
backend deliberately inflates confidence on a clean refactor that contains a
`TODO` comment (`pr-014`). That false positive shows up on held-out data and
widens the precision CI so a point estimate can look fine while the gate fails.

**Harness** (default): five passes on shuffled diff line order, majority vote
(`VOTE_MIN` of `N_PASSES`), then an FP validator that multiplies confidence by
`TODO_FP_PENALTY` when the only scary signal is a TODO comment. Real bug markers
are left alone. This is the interviewable "I changed the harness and measured
it" step - same gold, same gate, different review pipeline.

Re-run both commands and compare `runs/latest_manifest.json` fields under
`pipeline`, `test.metrics`, and `test.precision_ci`.

## Selection bias

Sweeping many thresholds on noisy development data and publishing the maximum
as if it were pre-specified is max-over-noisy-measurements bias. The sweep is
calibration only; the final report uses one selected threshold on held-out data.

## Ordinal diagnostics and label quality

Binary precision, recall, F1, and the confusion matrix answer the ship/no-ship
question. Quadratic weighted kappa, MAE, and Spearman retain ordinal detail
(confusing a 4 with a 5 is different from confusing a 4 with a 1). A second
annotator score lets agreement be measured separately from judge quality.
