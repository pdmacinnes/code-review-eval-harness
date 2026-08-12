# Code Review Eval Harness

Portfolio project: evaluate an AI judge that decides whether a pull-request diff
should be flagged for a real bug. A point-estimate precision can hide sampling
uncertainty, so the harness calibrates a threshold on development data and
gates held-out precision on a bootstrap confidence interval.

Built to demonstrate rigorous evaluation methodology for AI code-review quality
roles - the same measurement discipline as a production review assistant that
cannot afford noisy comments.

## Quickstart

```text
python judge_eval.py
python run_eval.py
python -m unittest discover -s tests -v
```

Stdlib only. No install step. No API key.

## What is here

- `contract.py` - thresholds, floors, seeds, bootstrap settings
- `judge_eval.py` - swappable backend, synthetic judge, metrics, CI gate helpers
- `gold_master.py` - load, stratified split, agreement diagnostics
- `run_eval.py` - end-to-end orchestration and run manifest
- `rubric.json` - invented 1-5 severity rubric for code review
- `data/` - synthetic labeled PR diffs
- `docs/methodology.md` - statistical design and the intentional failing gate
- `specs/code-review-eval.md` - requirements and acceptance criteria
- `tests/` - split discipline, binary collapse, bootstrap bounds

### Plugging in a real backend

Implement `JudgeBackend.predict(title, diff, gold_score)` so it returns
`(ordinal_score, bug_confidence)`. Replace `SyntheticJudge` in `run_eval.py`;
calibration, held-out scoring, metrics, and the confidence gate stay the same.
The `gold_score` argument is only for the dependency-free synthetic fixture.

## Interview line

Noisy review comments destroy trust, so releases gate on held-out precision
with bootstrap CIs. Harness changes are hill-climbed against a labeled diff set.

## Results

Run `python run_eval.py` to print the reproducible synthetic result and write
`runs/latest_manifest.json`. Key lines from the fixture:

```text
threshold: 0.23
dev precision: 1.00
test precision: 0.857
test precision CI: [0.5, 1.0]
gate_pass: false
```

Development clears the floor; the held-out lower bound does not. That is a
measurement-integrity demonstration, not a harness malfunction.

This repository contains no client, vendor, or real repository data. Diffs and
labels are entirely invented.
