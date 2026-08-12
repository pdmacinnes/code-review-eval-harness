"""Run the complete synthetic evaluation and write a reproducible manifest."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from contract import PRECISION_FLOOR, RECALL_FLOOR, SEED
from gold_master import dataset_hash, inter_annotator_agreement, load_jsonl, stratified_split
from judge_eval import (
    SyntheticJudge,
    binary_metrics,
    bootstrap_precision_ci,
    calibrate_threshold,
    ordinal_metrics,
    predict_records,
)


def main() -> None:
    records = load_jsonl(ROOT / "data" / "sample_gold.jsonl")
    dev, test = stratified_split(records)
    backend = SyntheticJudge()
    dev_predictions = predict_records(dev, backend)
    test_predictions = predict_records(test, backend)
    threshold = calibrate_threshold(dev_predictions)
    dev_metrics = binary_metrics(dev_predictions, threshold)
    test_metrics = binary_metrics(test_predictions, threshold)
    ci_low, ci_high = bootstrap_precision_ci(test_predictions, threshold)
    gate_pass = ci_low >= PRECISION_FLOOR and test_metrics["recall"] >= RECALL_FLOOR
    manifest = {
        "model_version": "synthetic-review-judge-v1",
        "domain": "code-review",
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
