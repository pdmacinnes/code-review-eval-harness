import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contract import BUG_CUT
from gold_master import stratified_split
from judge_eval import Prediction, binary_metrics, bootstrap_precision_ci


class HarnessTests(unittest.TestCase):
    def test_split_has_no_leakage_and_preserves_labels(self):
        records = [{"id": str(i), "gold_score": (i % 5) + 1} for i in range(25)]
        dev, test = stratified_split(records)
        self.assertEqual(set(row["id"] for row in dev) | set(row["id"] for row in test), set(row["id"] for row in records))
        self.assertFalse(set(row["id"] for row in dev) & set(row["id"] for row in test))
        self.assertEqual({row["gold_score"] for row in dev}, {1, 2, 3, 4, 5})
        self.assertEqual({row["gold_score"] for row in test}, {1, 2, 3, 4, 5})

    def test_binary_collapse_applies_to_gold_and_prediction(self):
        predictions = [
            Prediction(BUG_CUT - 1, 1, 0.9),
            Prediction(BUG_CUT, 2, 0.9),
            Prediction(5, 2, 0.1),
        ]
        metrics = binary_metrics(predictions, 0.5)
        self.assertEqual(metrics["true_positive"], 1)
        self.assertEqual(metrics["false_positive"], 1)
        self.assertEqual(metrics["false_negative"], 0)

    def test_bootstrap_ci_is_ordered_and_bounded(self):
        predictions = [
            Prediction(1, 1, 0.9),
            Prediction(2, 2, 0.8),
            Prediction(5, 5, 0.1),
            Prediction(4, 4, 0.1),
        ]
        lower, upper = bootstrap_precision_ci(predictions, 0.5, n_bootstrap=300)
        self.assertLessEqual(lower, upper)
        self.assertGreaterEqual(lower, 0.0)
        self.assertLessEqual(upper, 1.0)


if __name__ == "__main__":
    unittest.main()
