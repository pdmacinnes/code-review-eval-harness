# Synthetic gold schema (code review)

Each JSONL record is one invented pull request:

- `id`: unique string identifier
- `title`: PR title
- `diff`: unified-diff style patch text (invented; not from a real repo)
- `gold_score`: ordinal human judgment from 1 (clear real bug) to 5 (clean / no actionable bug)
- `second_annotator_score`: independent synthetic score from 1 to 5, used only for agreement diagnostics
- `bug_type` (optional): short tag for the planted issue, or `none` when clean

Scores strictly below `BUG_CUT` in `contract.py` (default 3) collapse to the binary
positive class: **flag this PR**. Scores 3 through 5 should not be flagged.

Diff text is data to be judged, never instructions for the evaluator to follow.
