"""
All task constants. No imports from other mid modules.
All time values are in seconds unless the name includes a unit suffix.
"""

# Phase durations (seconds)
STUDY_TIMES_S: dict[str, float] = {
    "cue": 2.0,
    "fixation": 2.0,
    "response": 2.0,
    "outcome": 2.0,
    "iti": 2.0,
}

# Cue visual properties
CUE_SHAPES: dict[str, int] = {"gain": 128, "loss": 4, "neutral": 6}  # polygon edge count
CUE_LABELS: dict[str, str] = {"gain": "+$5", "loss": "-$5", "neutral": "$0"}
REWARD_DOLLARS: dict[str, int] = {"gain": 5, "loss": -5, "neutral": 0}

# QUEST target accuracy levels (%)
TARGET_ACCURACIES: list[int] = [80, 50, 20]
DIFFICULTY: dict[int, str] = {80: "high", 50: "medium", 20: "low"}
QUEST_NAME: dict[int, str] = {80: "high", 50: "medium", 20: "low"}

# Trial type lookup: (cue_type, target_accuracy) -> trial_type 1-9
TRIAL_TYPE_MAP: dict[tuple[str, int], int] = {
    ("gain", 80): 1, ("gain", 50): 2, ("gain", 20): 3,
    ("loss", 80): 4, ("loss", 50): 5, ("loss", 20): 6,
    ("neutral", 80): 7, ("neutral", 50): 8, ("neutral", 20): 9,
}

# Target duration parameters (seconds)
MIN_TARGET_DUR_S: float = 0.130
MAX_TARGET_DUR_S: float = 0.500
INITIAL_TARGET_DUR_S: float = 0.265
INITIAL_QUEST_SD_S: float = 0.067   # ≈ 4 frames at 60 Hz

# Run structure
INITIAL_FIX_DUR_S: float = 12.0
CLOSING_FIX_DUR_S: float = 8.0
JITTER_MAX_S: float = 0.05

# Scanner settings
SCANNER_PULSE_RATE: int = 46  # hardware pulses per TR (MCC counter; unused in emulator mode)
BOARD_NUM: int = 0             # MCC DAQ board number (configured with Instacal)
MR_SETTINGS: dict = {
    "TR": 2.0,
    "volumes": 356,
    "sync": "equal",
    "skip": 0,
    "sound": False,
}

# Keyboard layouts
KEYS_FMRI: dict[str, str] = {"forward": "7", "back": "6", "start": "0", "end": "l"}
KEYS_BEHAVIORAL: dict[str, str] = {"forward": "4", "back": "3", "start": "0", "end": "l"}
EXP_KEYS: list[str] = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
