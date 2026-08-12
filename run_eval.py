"""Run the complete synthetic evaluation and write a reproducible manifest."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from contract import N_PASSES, PRECISION_FLOOR, RECALL_FLOOR, SEED, VOTE_MIN
from gold_master import dataset_hash, inter_annotator_agreement, load_jsonl, stratified_split
from judge_eval import (
    SyntheticJudge,
    binary_metrics,
    bootstrap_precision_ci,
    calibrate_threshold,
    ordinal_metrics,
    predict_records,
)
from review_pipeline import predict_records_harness


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the code-review eval harness.")
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Single-pass judge only (no multi-pass vote, no FP validator).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    records = load_jsonl(ROOT / "data" / "sample_gold.jsonl")
    dev, test = stratified_split(records)
    backend = SyntheticJudge()
    if args.baseline:
        pipeline = {"mode": "baseline", "n_passes": 1, "vote_min": 1, "validator": False}
        dev_predictions = predict_records(dev, backend)
        test_predictions = predict_records(test, backend)
        model_version = "synthetic-review-judge-v1-baseline"
    else:
        pipeline = {
            "mode": "harness",
            "n_passes": N_PASSES,
            "vote_min": VOTE_MIN,
            "validator": True,
        }
        dev_predictions = predict_records_harness(dev, backend, seed=SEED)
        test_predictions = predict_records_harness(test, backend, seed=SEED)
        model_version = "synthetic-review-judge-v1.1-harness"

    threshold = calibrate_threshold(dev_predictions)
    dev_metrics = binary_metrics(dev_predictions, threshold)
    test_metrics = binary_metrics(test_predictions, threshold)
    ci_low, ci_high = bootstrap_precision_ci(test_predictions, threshold)
    gate_pass = ci_low >= PRECISION_FLOOR and test_metrics["recall"] >= RECALL_FLOOR
    manifest = {
        "model_version": model_version,
        "domain": "code-review",
        "pipeline": pipeline,
        "threshold": threshold,
        "precision_floor": PRECISION_FLOOR,
        "recall_floor": RECALL_FLOOR,
        "seed": SEED,
        "dataset_hash": dataset_hash(records),
        "split": {"dev_ids": [row["id"] for row in dev], "test_ids": [row["id"] for row in test]},
        "dev": {"metrics": dev_metrics},
        "test": {
            "metrics": test_metrics,
            "precision_ci": [ci_low, ci_high],
            "gate_pass": gate_pass,
            "ordinal": ordinal_metrics(test_predictions),
        },
        "inter_annotator_qwk": inter_annotator_agreement(records),
        "test_scored_once": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    out_dir = ROOT / "runs"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "latest_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
