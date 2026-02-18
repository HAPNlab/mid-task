"""
QuestHandler construction and management.
All staircase intensities are in seconds (not frames).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from psychopy import data

from mid import config


def build_staircases(sequence_df: pd.DataFrame) -> dict[str, data.QuestHandler]:
    """
    Build one QuestHandler per accuracy level.

    Intensity represents additional duration above MIN_TARGET_DUR_S (in seconds).
    Actual target duration = MIN_TARGET_DUR_S + intensity.
    """
    max_intensity = config.MAX_TARGET_DUR_S - config.MIN_TARGET_DUR_S
    initial_intensity = config.INITIAL_TARGET_DUR_S - config.MIN_TARGET_DUR_S

    handlers: dict[str, data.QuestHandler] = {}
    for acc, name in zip(config.TARGET_ACCURACIES, ["high", "medium", "low"]):
        n_trials = int((sequence_df["target_accuracy"] == acc).sum())
        handlers[name] = data.QuestHandler(
            startVal=initial_intensity,
            startValSd=config.INITIAL_STAIR_SD_S,
            pThreshold=acc / 100,
            gamma=0.01,
            nTrials=n_trials,
            minVal=0.0,
            maxVal=max_intensity,
            name=name,
        )
    return handlers


def get_active_staircase(
    row: pd.Series, staircases: dict[str, data.QuestHandler]
) -> tuple[str, data.QuestHandler]:
    """Return (stair_name, handler) for the given trial row."""
    acc = int(row["target_accuracy"])
    name = config.STAIR_NAME[acc]
    return name, staircases[name]


def next_intensity(handler: data.QuestHandler) -> float:
    """Advance handler and return clipped intensity (seconds)."""
    raw = next(handler)
    max_intensity = config.MAX_TARGET_DUR_S - config.MIN_TARGET_DUR_S
    return float(np.clip(raw, 0.0, max_intensity))


def stair_sd(handler: data.QuestHandler) -> float:
    """Return SD of the posterior distribution as a step-size proxy."""
    try:
        return float(handler.sd())
    except Exception:
        return 0.0
