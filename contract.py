"""Single source of truth for the evaluation contract."""

# Keeping contract constants together prevents silent desynchronization between
# calibration, scoring, tests, and the published run manifest.
SEED = 271828
PRECISION_FLOOR = 0.80
# Deliberately permissive here to isolate the precision-CI failure mode.
RECALL_FLOOR = 0.25
# Scores strictly below BUG_CUT are the positive class: "flag a real bug."
BUG_CUT = 3
N_BOOTSTRAP = 4000
CI_ALPHA = 0.05
# Harness hill-climb knobs (multi-pass vote + FP validator).
N_PASSES = 5
VOTE_MIN = 3
# Soft per-pass flag line used only inside voting; final ship gate still
# calibrates a threshold on merged confidence.
PASS_FLAG_CUT = 0.45
# Multiply merged confidence when the only scary signal is a TODO comment.
TODO_FP_PENALTY = 0.35
