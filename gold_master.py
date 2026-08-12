"""Synthetic gold data, reproducible splitting, and label-quality diagnostics."""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from contract import SEED


def load_jsonl(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def dataset_hash(records: Iterable[dict]) -> str:
    payload = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in records)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stratified_split(records: list[dict], dev_fraction: float = 0.5, seed: int = SEED) -> tuple[list[dict], list[dict]]:
    """Split within each ordinal label, preserving label proportions."""
    if not 0 < dev_fraction < 1:
        raise ValueError("dev_fraction must be between zero and one")
    groups: dict[int, list[dict]] = defaultdict(list)
    for row in records:
        groups[int(row["gold_score"])].append(row)
    rng = random.Random(seed)
    dev, test = [], []
    for label in sorted(groups):
        group = groups[label][:]
        rng.shuffle(group)
        cut = max(1, min(len(group) - 1, round(len(group) * dev_fraction)))
        dev.extend(group[:cut])
        test.extend(group[cut:])
    dev.sort(key=lambda row: row["id"])
    test.sort(key=lambda row: row["id"])
    if set(row["id"] for row in dev) & set(row["id"] for row in test):
        raise AssertionError("split leakage detected")
    return dev, test


def quadratic_weighted_kappa(first: list[int], second: list[int], low: int = 1, high: int = 5) -> float:
    if len(first) != len(second) or not first:
        raise ValueError("QWK requires equally sized, non-empty lists")
    labels = list(range(low, high + 1))
    observed = [[0] * len(labels) for _ in labels]
    expected = [[0.0] * len(labels) for _ in labels]
    for a, b in zip(first, second):
        observed[a - low][b - low] += 1
    first_counts, second_counts = Counter(first), Counter(second)
    total = len(first)
    for i, a in enumerate(labels):
        for j, b in enumerate(labels):
            expected[i][j] = first_counts[a] * second_counts[b] / total
    numerator = denominator = 0.0
    span = high - low
    for i, a in enumerate(labels):
        for j, b in enumerate(labels):
            weight = ((a - b) / span) ** 2
            numerator += weight * observed[i][j]
            denominator += weight * expected[i][j]
    return 1.0 if denominator == 0 else 1.0 - numerator / denominator


def inter_annotator_agreement(records: list[dict]) -> float:
    # The synthetic second labels are intentionally close to the gold labels,
    # modeling a high-agreement annotation process without claiming real data.
    return quadratic_weighted_kappa(
        [int(row["gold_score"]) for row in records],
        [int(row["second_annotator_score"]) for row in records],
    )
