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
