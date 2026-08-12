# Code Review Eval Harness

Portfolio project: evaluate an AI judge that decides whether a pull-request diff
should be flagged for a real bug. A point-estimate precision can hide sampling
uncertainty, so the harness calibrates a threshold on development data and
gates held-out precision on a bootstrap confidence interval.

The default pipeline adds a small Bugbot-style hill-climb: multi-pass review on
shuffled diffs, majority vote, and an FP validator that demotes TODO-comment
noise. Use `--baseline` to compare against a single-pass judge.

## Quickstart

```text
python run_eval.py
python run_eval.py --baseline
python -m unittest discover -s tests -v
```

Stdlib only. No install step. No API key.

## What is here

- `contract.py` - thresholds, floors, seeds, bootstrap and harness knobs
- `judge_eval.py` - swappable backend, synthetic judge, metrics, CI gate helpers
- `review_pipeline.py` - multi-pass shuffle, majority vote, FP validator
- `gold_master.py` - load, stratified split, agreement diagnostics
- `run_eval.py` - end-to-end orchestration and run manifest
- `rubric.json` - invented 1-5 severity rubric for code review
- `data/` - synthetic labeled PR diffs
- `docs/methodology.md` - statistical design and harness hill-climb
- `specs/code-review-eval.md` - requirements and acceptance criteria
- `tests/` - split discipline, vote/validator, bootstrap bounds

### Plugging in a real backend

Implement `JudgeBackend.predict(title, diff, gold_score, pass_index=0)` so it
returns `(ordinal_score, bug_confidence)`. Replace `SyntheticJudge` in
`run_eval.py`; calibration, held-out scoring, metrics, and the confidence gate
stay the same. The `gold_score` argument is only for the synthetic fixture.

## Interview line

Noisy review comments destroy trust, so releases gate on held-out precision
with bootstrap CIs. Multi-pass vote + an FP validator are hill-climbed against
a labeled diff set; `--baseline` shows the before.

## Results

Default harness vs baseline on the same gold split:

| Mode | Test precision | Precision CI | `gate_pass` |
|---|---|---|---|
| `--baseline` | 0.857 (1 FP) | [0.5, 1.0] | false |
| harness (default) | 1.0 (0 FP) | [1.0, 1.0] | true |

The FP validator kills the TODO-comment false positive; the CI gate then clears.
That is the measurable harness hill-climb.

This repository contains no client, vendor, or real repository data. Diffs and
labels are entirely invented.
