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

## The intentional failing gate

The synthetic backend deliberately inflates confidence on one otherwise clean
refactor that contains a `TODO` comment (`pr-014`, held out in test). On the
committed fixture, development calibration selects threshold `0.23` with
dev precision `1.00` and recall `1.00`. On untouched test data, precision is
`0.857` with recall `1.00`, but the 95% bootstrap interval is `[0.5, 1.0]`.
The lower bound fails the `0.80` gate, so `gate_pass` is `false`.

That is the measurement lesson: calibrate on dev, report on untouched test,
and do not ship on a point estimate alone. Re-run with `python run_eval.py`
to regenerate `runs/latest_manifest.json`.

## Selection bias

Sweeping many thresholds on noisy development data and publishing the maximum
as if it were pre-specified is max-over-noisy-measurements bias. The sweep is
calibration only; the final report uses one selected threshold on held-out data.

## Ordinal diagnostics and label quality

Binary precision, recall, F1, and the confusion matrix answer the ship/no-ship
question. Quadratic weighted kappa, MAE, and Spearman retain ordinal detail
(confusing a 4 with a 5 is different from confusing a 4 with a 1). A second
annotator score lets agreement be measured separately from judge quality.

## Out of scope for v1

Multi-pass voting and a second-stage false-positive validator are natural next
harness experiments (the kind of hill-climb a production review agent would
run). They are intentionally deferred so the measurement spine stays clear.
