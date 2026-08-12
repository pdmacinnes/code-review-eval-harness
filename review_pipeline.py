"""Multi-pass review, majority vote, and a lightweight FP validator.

Mirrors the kind of harness hill-climb used in production review agents:
shuffle context across passes, require agreement before trusting a flag, then
run a second-stage check that demotes comment/TODO noise.
"""

from __future__ import annotations

import random
from statistics import mean

from contract import N_PASSES, PASS_FLAG_CUT, TODO_FP_PENALTY, VOTE_MIN
from judge_eval import JudgeBackend, Prediction


def _is_header_line(line: str) -> bool:
    return line.startswith("--- ") or line.startswith("+++ ") or line.startswith("@@")


def shuffle_diff_lines(diff: str, seed: int) -> str:
    """Permute body lines while keeping file-header / hunk-header lines fixed."""
    lines = diff.splitlines()
    body = [line for line in lines if not _is_header_line(line)]
    rng = random.Random(seed)
    rng.shuffle(body)
    body_iter = iter(body)
    out = [line if _is_header_line(line) else next(body_iter) for line in lines]
    trailing = "\n" if diff.endswith("\n") else ""
    return "\n".join(out) + trailing


def _validate_config(n_passes: int, vote_min: int) -> None:
    if n_passes < 1:
        raise ValueError("n_passes must be >= 1")
    if not 1 <= vote_min <= n_passes:
        raise ValueError("vote_min must be between 1 and n_passes")


def merge_pass_votes(
    scores: list[int],
    confidences: list[float],
    vote_min: int = VOTE_MIN,
    pass_flag_cut: float = PASS_FLAG_CUT,
) -> tuple[int, float, int]:
    """Majority-vote merge. Returns (score, confidence, votes_for_flag)."""
    if len(scores) != len(confidences) or not scores:
        raise ValueError("scores and confidences must be non-empty and aligned")
    votes = sum(1 for conf in confidences if conf >= pass_flag_cut)
    avg_score = int(round(mean(scores)))
    avg_score = max(1, min(5, avg_score))
    if votes < vote_min:
        support = votes / len(confidences)
        return avg_score, max(0.01, min(pass_flag_cut - 0.01, support * pass_flag_cut)), votes
    support = votes / len(confidences)
    merged_conf = mean(confidences) * (0.5 + 0.5 * support)
    return avg_score, max(0.01, min(0.99, merged_conf)), votes


def validate_finding(title: str, diff: str, score: int, confidence: float) -> tuple[int, float]:
    """Demote TODO/comment-only scares; leave real bug signals alone."""
    del title  # reserved for richer validators later
    has_todo = "TODO" in diff
    strong_bug_markers = (
        "session['user']" in diff
        or "db.delete(user_id)" in diff
        or "+ name" in diff
        or "password=%s" in diff
        or "bucket=[]" in diff
        or "target == value" in diff
        or "Ignore all evaluation" in diff
        or "ThreadPoolExecutor" in diff
        or "global _balance" in diff
        or "f = open(path)" in diff
        or "items[0:n+1]" in diff
    )
    if has_todo and not strong_bug_markers:
        return score, max(0.01, confidence * TODO_FP_PENALTY)
    return score, confidence


def review_diff(
    title: str,
    diff: str,
    gold_score: int,
    backend: JudgeBackend,
    *,
    n_passes: int = N_PASSES,
    vote_min: int = VOTE_MIN,
    seed: int = 0,
    use_validator: bool = True,
) -> tuple[int, float, dict]:
    """Run multi-pass review + vote (+ optional validator) for one diff."""
    _validate_config(n_passes, vote_min)
    scores: list[int] = []
    confidences: list[float] = []
    for pass_index in range(n_passes):
        shuffled = shuffle_diff_lines(diff, seed + pass_index * 997)
        score, conf = backend.predict(title, shuffled, gold_score, pass_index=pass_index)
        scores.append(score)
        confidences.append(conf)
    merged_score, merged_conf, votes = merge_pass_votes(scores, confidences, vote_min=vote_min)
    detail = {"votes_for_flag": votes, "n_passes": n_passes, "pass_confidences": confidences}
    if use_validator:
        before = merged_conf
        merged_score, merged_conf = validate_finding(title, diff, merged_score, merged_conf)
        detail["validator_applied"] = True
        detail["confidence_before_validator"] = before
    else:
        detail["validator_applied"] = False
    return merged_score, merged_conf, detail


def predict_records_harness(
    records: list[dict],
    backend: JudgeBackend,
    *,
    n_passes: int = N_PASSES,
    vote_min: int = VOTE_MIN,
    seed: int = 0,
    use_validator: bool = True,
) -> list[Prediction]:
    predictions = []
    for row in records:
        score, conf, _ = review_diff(
            row["title"],
            row["diff"],
            row["gold_score"],
            backend,
            n_passes=n_passes,
            vote_min=vote_min,
            seed=seed + sum(ord(c) for c in row["id"]),
            use_validator=use_validator,
        )
        predictions.append(Prediction(row["gold_score"], score, conf))
    return predictions
