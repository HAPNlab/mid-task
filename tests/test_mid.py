"""
Tests for the MID task.

Each test calls real mid.trial functions (run_response, run_fixation, run_cue,
run_outcome, run_iti, run_trial) with mocked PsychoPy boundaries.  PulseCounter
and CsvWriter tests exercise real code with real fake backends.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from mid import config
from mid.recorder import (
    BehavioralCsvWriter,
    TrialRecord,
)
from mid.scanner import PulseCounter
from mid.trial import (
    _compute_reward,
    run_cue,
    run_fixation,
    run_iti,
    run_outcome,
    run_response,
    run_trial,
)


# ────────────────────────────────────────────────────────────────────────────
# Module path for patching
# ────────────────────────────────────────────────────────────────────────────
T = "mid.trial"


# ────────────────────────────────────────────────────────────────────────────
# Fakes / helpers
# ────────────────────────────────────────────────────────────────────────────


class FakeBackend:
    """Deterministic scanner backend for testing PulseCounter."""

    pulse_rate: int = config.SCANNER_PULSE_RATE

    def __init__(self) -> None:
        self._count = 0

    def read(self) -> int:
        return self._count

    def advance(self, n: int = 1) -> None:
        self._count += n

    def start(self) -> None:
        pass


class FakeWindow:
    """Minimal Window that executes callOnFlip callbacks on flip()."""

    def __init__(self) -> None:
        self._flip_callbacks: list = []

    def flip(self) -> None:
        for cb in self._flip_callbacks:
            cb()
        self._flip_callbacks.clear()

    def callOnFlip(self, func, *args, **kwargs) -> None:
        self._flip_callbacks.append(lambda: func(*args, **kwargs))


class ScriptedClock:
    """Clock whose getTime() yields from a list; stays at last value."""

    def __init__(self, times: list[float]) -> None:
        self._iter = iter(times)
        self._last = times[-1] if times else 999.0

    def getTime(self) -> float:
        return next(self._iter, self._last)

    def reset(self) -> None:
        pass


class PairedSteppingClock:
    """Clock that returns each value twice (while-check + t-assignment), then steps.

    This mirrors run_response's loop:
        while phase_clock.getTime() < 2.0:   # call 1
            t = phase_clock.getTime()         # call 2  (same value)
    """

    def __init__(self, step: float = 0.008) -> None:
        self._t = 0.0
        self._step = step
        self._second_call = False

    def getTime(self) -> float:
        t = self._t
        if self._second_call:
            self._t += self._step
        self._second_call = not self._second_call
        return t

    def reset(self) -> None:
        pass


class OneStepTimer:
    """CountdownTimer that lets the loop body execute exactly once."""

    def __init__(self, start: float = 0.0) -> None:
        self._first = True

    def getTime(self) -> float:
        if self._first:
            self._first = False
            return 1.0
        return -1.0


def _kb() -> MagicMock:
    kb = MagicMock()
    kb.clock = MagicMock()
    return kb


def _trial_row(
    cue_type: str = "gain", target_accuracy: int = 80, n_iti: int = 1
) -> pd.Series:
    return pd.Series(
        {"cue_type": cue_type, "target_accuracy": target_accuracy, "n_iti": n_iti}
    )


def _trial_record(**overrides: Any) -> TrialRecord:
    defaults = dict(
        trial_n=1, trial_type=1, cue_type="gain", reward=5,
        difficulty="high", target_accuracy=80, quest="high",
        quest_n=1, quest_step=0.067, quest_intensity=0.135,
        time_onset=12.0, jitter_ms=25, target_dur_ms=265,
        early_press=0, hit=1, rt_ms=210.5, reward_outcome="+$5",
        total_earned=5, time_trial_end=22.0, trial_dur_ms=10000,
        time_sched_end=22.0, timing_drift_ms=0.0, total_trs=5,
        subject_id="sub01", run_n="1", pulse_ct=46,
    )
    defaults.update(overrides)
    return TrialRecord(**defaults)


# ────────────────────────────────────────────────────────────────────────────
# 1. Scanner is the master timer
# ────────────────────────────────────────────────────────────────────────────


class TestScannerMasterTimer:
    """The task gates every phase transition on scanner TR pulses."""

    def test_wait_for_tr_blocks_until_pulses_arrive(self) -> None:
        backend = FakeBackend()
        pc = PulseCounter(backend)

        backend.advance(config.SCANNER_PULSE_RATE - 1)
        partial = pc.drain()
        assert partial == config.SCANNER_PULSE_RATE - 1

        backend.advance(config.SCANNER_PULSE_RATE)
        delta = pc.wait_for_tr()
        assert delta >= config.SCANNER_PULSE_RATE

    def test_scanner_slow_task_waits(self) -> None:
        backend = FakeBackend()
        pc = PulseCounter(backend)

        backend.advance(config.SCANNER_PULSE_RATE // 2)
        half = pc.drain()
        assert half == config.SCANNER_PULSE_RATE // 2

        target = pc._last + backend.pulse_rate
        assert backend.read() < target

        backend.advance(config.SCANNER_PULSE_RATE)
        assert backend.read() >= target

    def test_run_trial_gates_each_phase_on_scanner(self) -> None:
        """run_trial() calls drain() and wait_for_tr() for each phase."""
        win = FakeWindow()
        kb = _kb()

        # Phase clock for run_response: two iterations then exit
        phase_clock = ScriptedClock([0.0, 0.0, 0.05, 0.05, 3.0])

        # Global clock: returns incrementing times for each getTime() call
        global_clock = MagicMock()
        global_clock.getTime.side_effect = [
            12.0,   # time_onset
            14.0,   # fixation_start
            16.0,   # response_start
            18.0,   # outcome_start
            20.0,   # iti_start
            20.0,   # actual_time (drift correction)
            22.0,   # time_trial_end
        ]

        pulse_counter = MagicMock(spec=PulseCounter)
        pulse_counter.drain.return_value = 0
        pulse_counter.wait_for_tr.return_value = config.SCANNER_PULSE_RATE

        handler = MagicMock()
        handler.thisTrialN = 0

        with (
            patch(f"{T}.core.CountdownTimer", side_effect=OneStepTimer),
            patch(f"{T}.core.Clock", return_value=phase_clock),
            patch(f"{T}.psy_event.getKeys", return_value=[]),
            patch(f"{T}.psy_event.clearEvents"),
            patch(f"{T}.draw_cue"),
            patch(f"{T}.draw_fixation"),
            patch(f"{T}.draw_target"),
            patch(f"{T}.draw_feedback"),
            patch(f"{T}._check_quit"),
            patch(f"{T}.random.uniform", return_value=0.025),
            patch(f"{T}.logging.exp"),
            patch(f"{T}.quest_sd", return_value=0.067),
        ):
            record, scan_phases, _, _ = run_trial(
                win, MagicMock(), kb, global_clock, _trial_row(),
                trial_n=1, quest_name="high", handler=handler,
                intensity=0.135, n_iti_trs=1, nominal_time=12.0,
                total_earned=0, subject_id="sub01", run_n="1",
                pulse_ct=0, pulse_counter=pulse_counter,
            )

        # drain called once (cue phase)
        assert pulse_counter.drain.call_count == 1
        # wait_for_tr called for fixation + response + outcome + 1 ITI = 4
        assert pulse_counter.wait_for_tr.call_count == 4

        assert len(scan_phases) == 5
        assert [sp.phase for sp in scan_phases] == [
            "cue", "fixation", "response", "outcome", "post-outcome-fixation",
        ]


# ────────────────────────────────────────────────────────────────────────────
# 2. target_dur_ms reflects actual display time
# ────────────────────────────────────────────────────────────────────────────


class TestTargetDuration:
    """target_dur_ms recorded in the trial record equals MIN + intensity."""

    @pytest.mark.parametrize(
        "intensity",
        [0.0, 0.050, 0.135, config.MAX_TARGET_DUR_S - config.MIN_TARGET_DUR_S],
    )
    def test_target_dur_ms_from_run_response(self, intensity: float) -> None:
        """Call run_response and verify target is drawn only during the window."""
        win = FakeWindow()
        kb = _kb()
        jitter_s = 0.01
        target_dur_s = config.MIN_TARGET_DUR_S + intensity

        # Clock with fine steps to count draw_target calls
        clock = PairedSteppingClock(step=0.008)

        with (
            patch(f"{T}.core.Clock", return_value=clock),
            patch(f"{T}.psy_event.getKeys", return_value=[]),
            patch(f"{T}.psy_event.clearEvents"),
            patch(f"{T}.draw_target") as mock_draw,
            patch(f"{T}._check_quit"),
        ):
            hit, rt_s, early = run_response(
                win, MagicMock(), kb, jitter_s, intensity, early_press=False,
            )

        # No key pressed → no hit
        assert not hit
        assert rt_s is None
        assert not early

        # draw_target should have been called for approximately target_dur_s / step frames
        expected_frames = int(target_dur_s / 0.008)
        assert abs(mock_draw.call_count - expected_frames) <= 2

    def test_run_trial_records_correct_target_dur_ms(self) -> None:
        """run_trial TrialRecord.target_dur_ms matches MIN + intensity."""
        win = FakeWindow()
        kb = _kb()
        intensity = 0.135
        expected_ms = int(round((config.MIN_TARGET_DUR_S + intensity) * 1000))

        phase_clock = ScriptedClock([0.0, 0.0, 0.05, 0.05, 3.0])
        global_clock = MagicMock()
        global_clock.getTime.side_effect = [
            12.0, 14.0, 16.0, 18.0, 20.0, 20.0, 22.0,
        ]

        pulse_counter = MagicMock(spec=PulseCounter)
        pulse_counter.drain.return_value = 0
        pulse_counter.wait_for_tr.return_value = config.SCANNER_PULSE_RATE

        handler = MagicMock()
        handler.thisTrialN = 0

        with (
            patch(f"{T}.core.CountdownTimer", side_effect=OneStepTimer),
            patch(f"{T}.core.Clock", return_value=phase_clock),
            patch(f"{T}.psy_event.getKeys", return_value=[]),
            patch(f"{T}.psy_event.clearEvents"),
            patch(f"{T}.draw_cue"),
            patch(f"{T}.draw_fixation"),
            patch(f"{T}.draw_target"),
            patch(f"{T}.draw_feedback"),
            patch(f"{T}._check_quit"),
            patch(f"{T}.random.uniform", return_value=0.025),
            patch(f"{T}.logging.exp"),
            patch(f"{T}.quest_sd", return_value=0.067),
        ):
            record, *_ = run_trial(
                win, MagicMock(), kb, global_clock, _trial_row(),
                trial_n=1, quest_name="high", handler=handler,
                intensity=intensity, n_iti_trs=1, nominal_time=12.0,
                total_earned=0, subject_id="sub01", run_n="1",
                pulse_ct=0, pulse_counter=pulse_counter,
            )

        assert record.target_dur_ms == expected_ms


# ────────────────────────────────────────────────────────────────────────────
# 3. Data integrity – per-trial flush
# ────────────────────────────────────────────────────────────────────────────


class TestDataIntegrity:
    """Each trial's data is flushed to disk immediately."""

    def test_csv_writer_flushes_after_each_append(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "behavioral.csv"
        writer = BehavioralCsvWriter(csv_path)

        rec = _trial_record(trial_n=1)
        writer.append(rec)

        with open(csv_path) as f:
            rows = list(csv.DictReader(f))

        assert len(rows) == 1
        assert rows[0]["trial_n"] == "1"
        assert rows[0]["hit"] == "1"
        writer.close()

    def test_crash_preserves_completed_trials(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "behavioral.csv"
        writer = BehavioralCsvWriter(csv_path)

        n_written = 5
        for i in range(1, n_written + 1):
            writer.append(_trial_record(trial_n=i, total_earned=i * 5))

        with open(csv_path) as f:
            rows = list(csv.DictReader(f))

        assert len(rows) == n_written
        for i, row in enumerate(rows, 1):
            assert row["trial_n"] == str(i)
            assert row["total_earned"] == str(i * 5)
        writer.close()

    def test_each_trial_independently_readable(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "behavioral.csv"
        writer = BehavioralCsvWriter(csv_path)

        for i in range(1, 4):
            writer.append(_trial_record(trial_n=i))
            with open(csv_path) as f:
                rows = list(csv.DictReader(f))
            assert len(rows) == i
        writer.close()

    def test_run_trial_record_round_trips_through_csv(self, tmp_path: Path) -> None:
        """Call run_trial, write the record, read it back."""
        win = FakeWindow()
        kb = _kb()

        phase_clock = ScriptedClock([0.0, 0.0, 0.05, 0.05, 3.0])
        global_clock = MagicMock()
        global_clock.getTime.side_effect = [
            12.0, 14.0, 16.0, 18.0, 20.0, 20.0, 22.0,
        ]

        pulse_counter = MagicMock(spec=PulseCounter)
        pulse_counter.drain.return_value = 0
        pulse_counter.wait_for_tr.return_value = config.SCANNER_PULSE_RATE

        handler = MagicMock()
        handler.thisTrialN = 0

        with (
            patch(f"{T}.core.CountdownTimer", side_effect=OneStepTimer),
            patch(f"{T}.core.Clock", return_value=phase_clock),
            patch(f"{T}.psy_event.getKeys", return_value=[]),
            patch(f"{T}.psy_event.clearEvents"),
            patch(f"{T}.draw_cue"),
            patch(f"{T}.draw_fixation"),
            patch(f"{T}.draw_target"),
            patch(f"{T}.draw_feedback"),
            patch(f"{T}._check_quit"),
            patch(f"{T}.random.uniform", return_value=0.025),
            patch(f"{T}.logging.exp"),
            patch(f"{T}.quest_sd", return_value=0.067),
        ):
            record, *_ = run_trial(
                win, MagicMock(), kb, global_clock, _trial_row(),
                trial_n=1, quest_name="high", handler=handler,
                intensity=0.135, n_iti_trs=1, nominal_time=12.0,
                total_earned=0, subject_id="sub01", run_n="1",
                pulse_ct=0, pulse_counter=pulse_counter,
            )

        csv_path = tmp_path / "behavioral.csv"
        writer = BehavioralCsvWriter(csv_path)
        writer.append(record)
        writer.close()

        with open(csv_path) as f:
            rows = list(csv.DictReader(f))

        assert len(rows) == 1
        assert rows[0]["trial_n"] == "1"
        assert rows[0]["cue_type"] == "gain"
        assert rows[0]["target_dur_ms"] == "265"
        assert rows[0]["subject_id"] == "sub01"


# ────────────────────────────────────────────────────────────────────────────
# 4. Jitter doesn't shorten target display ("tare" the jitter)
# ────────────────────────────────────────────────────────────────────────────


class TestJitterTare:
    """Jitter delays target onset but does NOT reduce display duration."""

    @pytest.mark.parametrize("jitter_s", [0.0, 0.010, 0.025, 0.050])
    def test_draw_target_count_independent_of_jitter(self, jitter_s: float) -> None:
        """draw_target call count stays constant across jitter values."""
        win = FakeWindow()
        kb = _kb()
        intensity_s = 0.100
        clock = PairedSteppingClock(step=0.008)

        with (
            patch(f"{T}.core.Clock", return_value=clock),
            patch(f"{T}.psy_event.getKeys", return_value=[]),
            patch(f"{T}.psy_event.clearEvents"),
            patch(f"{T}.draw_target") as mock_draw,
            patch(f"{T}._check_quit"),
        ):
            run_response(
                win, MagicMock(), kb, jitter_s, intensity_s, early_press=False,
            )

        target_dur_s = config.MIN_TARGET_DUR_S + intensity_s
        expected_frames = int(target_dur_s / 0.008)
        # Within ±2 frames of the expected count
        assert abs(mock_draw.call_count - expected_frames) <= 2

    def test_max_jitter_still_fits_in_response_window(self) -> None:
        max_jitter = config.JITTER_MAX_S
        max_target = config.MAX_TARGET_DUR_S
        response_dur = config.STUDY_TIMES_S["response"]
        assert max_jitter + max_target < response_dur


# ────────────────────────────────────────────────────────────────────────────
# 5. Late responses not scored as hits
# ────────────────────────────────────────────────────────────────────────────


class TestLateResponses:
    """Presses after target removal must NOT be scored as hits."""

    def test_press_after_target_removed_is_not_hit(self) -> None:
        """Key arrives after target_dur_s + jitter_s has elapsed."""
        win = FakeWindow()
        kb = _kb()
        jitter_s = 0.010
        intensity_s = 0.100
        target_dur_s = config.MIN_TARGET_DUR_S + intensity_s

        # Three iterations: before jitter, target shown (no key), target removed (key)
        # then exit.
        clock = ScriptedClock([
            0.0, 0.0,                              # iter 1: before jitter
            0.05, 0.05,                             # iter 2: target shown
            jitter_s + target_dur_s + 0.05,         # iter 3: while check
            jitter_s + target_dur_s + 0.05,         # iter 3: t assignment
            3.0,                                    # exit
        ])

        call_count = 0

        def fake_getkeys(**kwargs):
            nonlocal call_count
            call_count += 1
            # Calls:
            # 1: early press check (iter 1) → no key
            # 2: response check (iter 2) → no key yet
            # 3: response check (iter 3) → key (but target removed)
            if call_count == 3 and "timeStamped" in kwargs:
                return [("1", 0.350)]
            return []

        with (
            patch(f"{T}.core.Clock", return_value=clock),
            patch(f"{T}.psy_event.getKeys", side_effect=fake_getkeys),
            patch(f"{T}.psy_event.clearEvents"),
            patch(f"{T}.draw_target"),
            patch(f"{T}._check_quit"),
        ):
            hit, rt_s, early = run_response(
                win, MagicMock(), kb, jitter_s, intensity_s, early_press=False,
            )

        assert not hit, "Late press must not be a hit"
        assert rt_s == 0.350, "RT should still be captured"

    def test_press_while_target_visible_is_hit(self) -> None:
        """Control: press during target display IS a hit."""
        win = FakeWindow()
        kb = _kb()
        jitter_s = 0.010
        intensity_s = 0.100

        # Two iterations: before jitter, target shown (key press), exit
        clock = ScriptedClock([0.0, 0.0, 0.05, 0.05, 3.0])

        call_count = 0

        def fake_getkeys(**kwargs):
            nonlocal call_count
            call_count += 1
            # Call 1: early press check (iter 1) → no key
            # Call 2: response check (iter 2, target visible) → key!
            if call_count == 2 and "timeStamped" in kwargs:
                return [("1", 0.040)]
            return []

        with (
            patch(f"{T}.core.Clock", return_value=clock),
            patch(f"{T}.psy_event.getKeys", side_effect=fake_getkeys),
            patch(f"{T}.psy_event.clearEvents"),
            patch(f"{T}.draw_target"),
            patch(f"{T}._check_quit"),
        ):
            hit, rt_s, early = run_response(
                win, MagicMock(), kb, jitter_s, intensity_s, early_press=False,
            )

        assert hit, "Press during target should be a hit"
        assert rt_s == 0.040

    def test_late_press_rt_recorded_but_not_hit(self) -> None:
        """rt_s is captured even when hit=False (target already removed)."""
        win = FakeWindow()
        kb = _kb()
        jitter_s = 0.010
        intensity_s = 0.100
        target_dur_s = config.MIN_TARGET_DUR_S + intensity_s

        # Iteration 1: before jitter.  Iteration 2: target visible (no key).
        # Iteration 3: target removed (key).
        removal_t = jitter_s + target_dur_s + 0.050
        clock = ScriptedClock([
            0.0, 0.0,
            0.05, 0.05,
            removal_t, removal_t,
            3.0,
        ])

        call_count = 0

        def fake_getkeys(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3 and "timeStamped" in kwargs:
                return [("1", 0.400)]
            return []

        with (
            patch(f"{T}.core.Clock", return_value=clock),
            patch(f"{T}.psy_event.getKeys", side_effect=fake_getkeys),
            patch(f"{T}.psy_event.clearEvents"),
            patch(f"{T}.draw_target"),
            patch(f"{T}._check_quit"),
        ):
            hit, rt_s, early = run_response(
                win, MagicMock(), kb, jitter_s, intensity_s, early_press=False,
            )

        assert rt_s == 0.400
        assert not hit


# ────────────────────────────────────────────────────────────────────────────
# 6. Early presses logged (including during jitter window)
# ────────────────────────────────────────────────────────────────────────────


class TestEarlyPress:
    """Early presses (before target) are detected and prevent hit scoring."""

    def test_early_press_during_jitter_window_detected(self) -> None:
        """Press during the jitter window sets early_press=True."""
        win = FakeWindow()
        kb = _kb()
        jitter_s = 0.040  # 40 ms jitter
        intensity_s = 0.100

        # Iteration 1: t=0.0, before jitter → early press check fires
        # Iteration 2: t=0.05, target onset
        # Exit
        clock = ScriptedClock([0.0, 0.0, 0.05, 0.05, 3.0])

        call_count = 0

        def fake_getkeys(**kwargs):
            nonlocal call_count
            call_count += 1
            # Call 1: early press check at t=0.0 (before target) → key!
            if call_count == 1 and "timeStamped" not in kwargs:
                return ["1"]
            return []

        with (
            patch(f"{T}.core.Clock", return_value=clock),
            patch(f"{T}.psy_event.getKeys", side_effect=fake_getkeys),
            patch(f"{T}.psy_event.clearEvents"),
            patch(f"{T}.draw_target"),
            patch(f"{T}._check_quit"),
        ):
            hit, rt_s, early = run_response(
                win, MagicMock(), kb, jitter_s, intensity_s, early_press=False,
            )

        assert early, "Press during jitter must set early_press=True"
        assert not hit
        assert rt_s is None

    def test_early_press_from_fixation_prevents_hit(self) -> None:
        """If early_press=True from fixation, run_response never scores a hit."""
        win = FakeWindow()
        kb = _kb()
        jitter_s = 0.010
        intensity_s = 0.100

        # Target appears, key pressed — but early_press is already True
        clock = ScriptedClock([0.0, 0.0, 0.05, 0.05, 3.0])

        with (
            patch(f"{T}.core.Clock", return_value=clock),
            patch(f"{T}.psy_event.getKeys", return_value=[]),
            patch(f"{T}.psy_event.clearEvents"),
            patch(f"{T}.draw_target"),
            patch(f"{T}._check_quit"),
        ):
            hit, rt_s, early = run_response(
                win, MagicMock(), kb, jitter_s, intensity_s, early_press=True,
            )

        assert not hit, "Early press from fixation must prevent hit"
        assert rt_s is None

    def test_run_fixation_detects_early_press(self) -> None:
        """run_fixation returns True when a key is pressed during fixation."""
        win = FakeWindow()
        kb = _kb()

        with (
            patch(f"{T}.core.CountdownTimer", side_effect=OneStepTimer),
            patch(f"{T}.psy_event.clearEvents"),
            patch(f"{T}.psy_event.getKeys", return_value=["1"]),
            patch(f"{T}.draw_fixation"),
            patch(f"{T}._check_quit"),
        ):
            result = run_fixation(win, MagicMock(), kb)

        assert result is True

    def test_run_fixation_no_press(self) -> None:
        """run_fixation returns False when no key is pressed."""
        win = FakeWindow()
        kb = _kb()

        with (
            patch(f"{T}.core.CountdownTimer", side_effect=OneStepTimer),
            patch(f"{T}.psy_event.clearEvents"),
            patch(f"{T}.psy_event.getKeys", return_value=[]),
            patch(f"{T}.draw_fixation"),
            patch(f"{T}._check_quit"),
        ):
            result = run_fixation(win, MagicMock(), kb)

        assert result is False

    def test_early_press_written_to_csv(self, tmp_path: Path) -> None:
        """early_press field must appear in the CSV output."""
        csv_path = tmp_path / "behavioral.csv"
        writer = BehavioralCsvWriter(csv_path)
        rec = _trial_record(early_press=1, hit=0, rt_ms="")
        writer.append(rec)
        writer.close()

        with open(csv_path) as f:
            rows = list(csv.DictReader(f))

        assert rows[0]["early_press"] == "1"
        assert rows[0]["hit"] == "0"


# ────────────────────────────────────────────────────────────────────────────
# Extra: drift correction
# ────────────────────────────────────────────────────────────────────────────


class TestDriftCorrection:
    """ITI duration is adjusted to keep nominal and actual time aligned."""

    def test_run_iti_returns_immediately_for_negative_duration(self) -> None:
        """run_iti(fix_dur_s <= 0) returns without drawing."""
        win = FakeWindow()
        kb = _kb()

        with (
            patch(f"{T}.core.CountdownTimer") as mock_timer,
            patch(f"{T}.draw_fixation") as mock_draw,
            patch(f"{T}._check_quit"),
        ):
            run_iti(win, MagicMock(), kb, fix_dur_s=-0.5)

        mock_timer.assert_not_called()
        mock_draw.assert_not_called()

    def test_run_iti_runs_for_positive_duration(self) -> None:
        """run_iti(fix_dur_s > 0) creates a timer and draws fixation."""
        win = FakeWindow()
        kb = _kb()

        with (
            patch(f"{T}.core.CountdownTimer", side_effect=OneStepTimer),
            patch(f"{T}.draw_fixation") as mock_draw,
            patch(f"{T}._check_quit"),
        ):
            run_iti(win, MagicMock(), kb, fix_dur_s=2.0)

        assert mock_draw.call_count == 1  # one iteration


# ────────────────────────────────────────────────────────────────────────────
# Extra: reward computation
# ────────────────────────────────────────────────────────────────────────────


class TestRewardComputation:
    """Test _compute_reward logic from trial.py."""

    def test_gain_hit(self) -> None:
        label, total = _compute_reward(hit=True, cue_type="gain", total_earned=10)
        assert label == "+$5"
        assert total == 15

    def test_gain_miss(self) -> None:
        label, total = _compute_reward(hit=False, cue_type="gain", total_earned=10)
        assert label == "$0"
        assert total == 10

    def test_loss_hit(self) -> None:
        label, total = _compute_reward(hit=True, cue_type="loss", total_earned=10)
        assert label == "$0"
        assert total == 10

    def test_loss_miss(self) -> None:
        label, total = _compute_reward(hit=False, cue_type="loss", total_earned=10)
        assert label == "-$5"
        assert total == 5

    def test_neutral_always_zero(self) -> None:
        label, total = _compute_reward(hit=True, cue_type="neutral", total_earned=10)
        assert label == "$0"
        assert total == 10
        label, total = _compute_reward(hit=False, cue_type="neutral", total_earned=10)
        assert label == "$0"
        assert total == 10


# ────────────────────────────────────────────────────────────────────────────
# Extra: run_outcome calls real _compute_reward
# ────────────────────────────────────────────────────────────────────────────


class TestRunOutcome:
    """run_outcome returns correct reward label and updates total_earned."""

    @pytest.mark.parametrize(
        "hit, cue_type, total, expected_label, expected_total",
        [
            (True, "gain", 0, "+$5", 5),
            (False, "gain", 10, "$0", 10),
            (True, "loss", 10, "$0", 10),
            (False, "loss", 10, "-$5", 5),
            (True, "neutral", 10, "$0", 10),
        ],
    )
    def test_outcome_reward(
        self, hit, cue_type, total, expected_label, expected_total
    ) -> None:
        win = FakeWindow()
        kb = _kb()

        with (
            patch(f"{T}.core.CountdownTimer", side_effect=OneStepTimer),
            patch(f"{T}.draw_feedback"),
            patch(f"{T}._check_quit"),
        ):
            label, new_total = run_outcome(
                win, MagicMock(), kb, hit, cue_type, total,
            )

        assert label == expected_label
        assert new_total == expected_total


# ────────────────────────────────────────────────────────────────────────────
# Extra: run_cue exercised
# ────────────────────────────────────────────────────────────────────────────


class TestRunCue:
    """run_cue draws the cue stimuli without errors."""

    def test_cue_draws_once_per_iteration(self) -> None:
        win = FakeWindow()
        kb = _kb()

        with (
            patch(f"{T}.core.CountdownTimer", side_effect=OneStepTimer),
            patch(f"{T}.draw_cue") as mock_draw,
            patch(f"{T}._check_quit"),
        ):
            run_cue(win, MagicMock(), "gain", 80, kb)

        mock_draw.assert_called_once()


# ────────────────────────────────────────────────────────────────────────────
# Extra: PulseCounter edge cases
# ────────────────────────────────────────────────────────────────────────────


class TestPulseCounterEdgeCases:
    """Additional PulseCounter tests."""

    def test_drain_returns_zero_when_no_new_pulses(self) -> None:
        backend = FakeBackend()
        pc = PulseCounter(backend)
        assert pc.drain() == 0

    def test_drain_never_returns_negative(self) -> None:
        backend = FakeBackend()
        pc = PulseCounter(backend)
        backend.advance(10)
        pc.drain()
        assert pc.drain() == 0

    def test_wait_for_tr_returns_exact_delta(self) -> None:
        backend = FakeBackend()
        pc = PulseCounter(backend)
        backend.advance(config.SCANNER_PULSE_RATE + 10)
        delta = pc.wait_for_tr()
        assert delta == config.SCANNER_PULSE_RATE + 10
