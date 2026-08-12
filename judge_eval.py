"""Demonstrate a precision-first code-review judge evaluation without external services.

The synthetic backend emits an ordinal bug-severity score and a confidence that
the diff should be flagged. The harness calibrates a confidence threshold on
dev, scores test exactly once, and gates on the bootstrap lower confidence
bound for precision. A production LLM backend would implement
``JudgeBackend.predict`` and leave the metrics and split discipline unchanged.
"""

from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Protocol

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contract import BUG_CUT, CI_ALPHA, N_BOOTSTRAP, PRECISION_FLOOR, RECALL_FLOOR, SEED
from gold_master import quadratic_weighted_kappa


class JudgeBackend(Protocol):
    def predict(
        self,
        title: str,
        diff: str,
        gold_score: int,
        pass_index: int = 0,
    ) -> tuple[int, float]: ...


class SyntheticJudge:
    """Deterministic stand-in with realistic score noise and confidence noise."""

    def predict(
        self,
        title: str,
        diff: str,
        gold_score: int,
        pass_index: int = 0,
    ) -> tuple[int, float]:
        marker = (sum(ord(char) for char in title + diff) + pass_index * 3) % 17
        noise = (marker % 5) - 2
        predicted_score = max(1, min(5, gold_score + noise // 2))
        has_bug = gold_score < BUG_CUT
        # Higher confidence when the judge thinks the diff is more severe (lower score).
        confidence = 0.18 + 0.13 * (BUG_CUT - predicted_score) + (marker % 7) * 0.025
        if has_bug:
            confidence += 0.16
        # One clean refactor PR is deliberately ambiguous: the word "TODO" in a
        # comment looks scary to a naive judge and inflates false-positive
        # confidence so the held-out precision CI can fail honestly.
        if gold_score >= BUG_CUT and "TODO" in diff:
            confidence += 0.30
        return predicted_score, max(0.01, min(0.99, confidence))


@dataclass(frozen=True)
class Prediction:
    gold_score: int
    predicted_score: int
    bug_confidence: float


def predict_records(records: list[dict], backend: JudgeBackend) -> list[Prediction]:
    return [
        Prediction(row["gold_score"], *backend.predict(row["title"], row["diff"], row["gold_score"]))
        for row in records
    ]


def confusion_matrix(predictions: list[Prediction], threshold: float) -> dict[str, int]:
    values = {"true_positive": 0, "false_positive": 0, "true_negative": 0, "false_negative": 0}
    for item in predictions:
        actual = item.gold_score < BUG_CUT
        predicted = item.bug_confidence >= threshold
        key = ("true_" if actual == predicted else "false_") + ("positive" if predicted else "negative")
        values[key] += 1
    return values


def binary_metrics(predictions: list[Prediction], threshold: float) -> dict[str, float | int]:
    matrix = confusion_matrix(predictions, threshold)
    tp, fp, fn = matrix["true_positive"], matrix["false_positive"], matrix["false_negative"]
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        **matrix,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }


def bootstrap_precision_ci(
    predictions: list[Prediction],
    threshold: float,
    n_bootstrap: int = N_BOOTSTRAP,
    alpha: float = CI_ALPHA,
    seed: int = SEED,
) -> tuple[float, float]:
    if not predictions or n_bootstrap < 1 or not 0 < alpha < 1:
        raise ValueError("invalid bootstrap inputs")
    rng = random.Random(seed)
    estimates = []
    for _ in range(n_bootstrap):
        sample = [predictions[rng.randrange(len(predictions))] for _ in predictions]
        estimates.append(float(binary_metrics(sample, threshold)["precision"]))
    estimates.sort()
    lower = estimates[math.floor((alpha / 2) * (n_bootstrap - 1))]
    upper = estimates[math.ceil((1 - alpha / 2) * (n_bootstrap - 1))]
    return lower, upper


def ordinal_metrics(predictions: list[Prediction]) -> dict[str, float]:
    actual = [item.gold_score for item in predictions]
    predicted = [item.predicted_score for item in predictions]
    ranks_actual = {value: index for index, value in enumerate(sorted(set(actual)))}
    ranks_predicted = {value: index for index, value in enumerate(sorted(set(predicted)))}
    rank_a = [ranks_actual[value] for value in actual]
    rank_b = [ranks_predicted[value] for value in predicted]
    mean_a, mean_b = mean(rank_a), mean(rank_b)
    covariance = sum((a - mean_a) * (b - mean_b) for a, b in zip(rank_a, rank_b))
    denom = math.sqrt(sum((a - mean_a) ** 2 for a in rank_a) * sum((b - mean_b) ** 2 for b in rank_b))
    return {
        "qwk": quadratic_weighted_kappa(actual, predicted),
        "mae": mean(abs(a - b) for a, b in zip(actual, predicted)),
        "spearman": covariance / denom if denom else 0.0,
    }


def sweep_thresholds(predictions: list[Prediction], precision_floor: float = PRECISION_FLOOR) -> list[dict[str, float]]:
    candidates = sorted({round(item.bug_confidence, 4) for item in predictions})
    results = []
    for threshold in candidates:
        metrics = binary_metrics(predictions, threshold)
        results.append(
            {
                "threshold": threshold,
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "eligible": float(metrics["precision"] >= precision_floor),
            }
        )
    return results


def calibrate_threshold(predictions: list[Prediction]) -> float:
    eligible = [row for row in sweep_thresholds(predictions) if row["eligible"]]
    if not eligible:
        raise RuntimeError("no threshold meets the dev precision floor")
    return max(eligible, key=lambda row: (row["recall"], -row["threshold"]))["threshold"]


if __name__ == "__main__":
    print("Evaluation library loaded. Run `python run_eval.py` for the complete calibration and held-out report.")
