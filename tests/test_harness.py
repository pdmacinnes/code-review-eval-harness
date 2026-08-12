import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contract import BUG_CUT, TODO_FP_PENALTY
from gold_master import stratified_split
from judge_eval import Prediction, SyntheticJudge, binary_metrics, bootstrap_precision_ci
from review_pipeline import merge_pass_votes, shuffle_diff_lines, validate_finding


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

    def test_shuffle_is_deterministic_and_preserves_headers(self):
        diff = "--- a/x.py\n+++ b/x.py\n@@\n line_a\n line_b\n line_c\n"
        first = shuffle_diff_lines(diff, 42)
        second = shuffle_diff_lines(diff, 42)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("--- a/x.py\n+++ b/x.py\n@@\n"))
        self.assertEqual(sorted(first.splitlines()), sorted(diff.splitlines()))

    def test_majority_vote_requires_quorum(self):
        score, conf, votes = merge_pass_votes([2, 2, 4, 5, 5], [0.8, 0.7, 0.2, 0.1, 0.1], vote_min=3)
        self.assertEqual(votes, 2)
        self.assertLess(conf, 0.45)
        _, conf_ok, votes_ok = merge_pass_votes([1, 1, 2, 4, 5], [0.9, 0.8, 0.7, 0.1, 0.1], vote_min=3)
        self.assertEqual(votes_ok, 3)
        self.assertGreater(conf_ok, conf)

    def test_validator_demotes_todo_only_false_positives(self):
        score, conf = validate_finding(
            "Cleanup",
            "--- a/a.py\n+++ b/a.py\n+# TODO: revisit later\n",
            4,
            0.80,
        )
        self.assertAlmostEqual(conf, 0.80 * TODO_FP_PENALTY)
        _, strong = validate_finding(
            "Auth bug",
            "--- a/a.py\n+++ b/a.py\n+    return session['user']\n",
            1,
            0.80,
        )
        self.assertEqual(strong, 0.80)

    def test_synthetic_judge_accepts_pass_index(self):
        judge = SyntheticJudge()
        a = judge.predict("t", "diff line", 2, pass_index=0)
        b = judge.predict("t", "diff line", 2, pass_index=1)
        self.assertEqual(len(a), 2)
        self.assertEqual(len(b), 2)


if __name__ == "__main__":
    unittest.main()
