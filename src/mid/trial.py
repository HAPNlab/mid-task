"""
Phase functions and run_trial().
Uses psychopy.hardware.keyboard.Keyboard for accurate RT timestamping.
No rendering objects are built here; no data is written here.
"""
from __future__ import annotations

import random

import pandas as pd
from psychopy import core, event as psy_event, logging, visual
from psychopy.hardware import keyboard

from mid import config
from mid.display import Stimuli, draw_cue, draw_feedback, draw_fixation, draw_target
from mid.recorder import ScanPhase, TrialRecord
from mid.quest import quest_sd
from mid.scanner import PulseCounter


def run_cue(
    win: visual.Window,
    stimuli: Stimuli,
    cue_type: str,
    target_accuracy: int,
    kb: keyboard.Keyboard,
) -> None:
    """Display cue for STUDY_TIMES_S['cue'] seconds."""
    timer = core.CountdownTimer(config.STUDY_TIMES_S["cue"])
    while timer.getTime() > 0:
        draw_cue(stimuli, cue_type, target_accuracy)
        win.flip()
        _check_quit(kb)


def run_fixation(
    win: visual.Window,
    stimuli: Stimuli,
    kb: keyboard.Keyboard,
) -> bool:
    """
    Display fixation for STUDY_TIMES_S['delay'] seconds.
    Returns True if a response key was pressed during the fixation (early press).
    """
    psy_event.clearEvents()
    timer = core.CountdownTimer(config.STUDY_TIMES_S["fixation"])
    while timer.getTime() > 0:
        draw_fixation(stimuli)
        win.flip()
        _check_quit(kb)
    # Sample accumulated events at fixation end to detect early press
    keys = psy_event.getKeys(keyList=config.EXP_KEYS)
    return len(keys) > 0


def run_response(
    win: visual.Window,
    stimuli: Stimuli,
    kb: keyboard.Keyboard,
    jitter_s: float,
    intensity_s: float,
    early_press: bool,
) -> tuple[bool, float | None, bool]:
    """
    Display response phase (STUDY_TIMES_S['target'] seconds total).
    Target appears after jitter_s and is shown for MIN_TARGET_DUR_S + intensity_s.
    Returns (hit, rt_s) where rt_s is seconds from target onset, or None if no press.
    """
    target_dur_s = config.MIN_TARGET_DUR_S + intensity_s
    phase_clock = core.Clock()
    target_shown = False
    target_removed = False
    clock_reset_scheduled = False
    hit = False
    rt_s: float | None = None

    psy_event.clearEvents()

    while phase_clock.getTime() < config.STUDY_TIMES_S["response"]:
        t = phase_clock.getTime()

        # Schedule RT clock reset and event clear on the flip that shows the target
        if not clock_reset_scheduled and t >= jitter_s:
            win.callOnFlip(kb.clock.reset)
            win.callOnFlip(psy_event.clearEvents)
            clock_reset_scheduled = True
            target_shown = True

        if target_shown and not target_removed and (t - jitter_s) >= target_dur_s:
            target_removed = True

        if target_shown and not target_removed:
            draw_target(stimuli)
        win.flip()

        # Check for early press during jitter window
        if not target_shown and not early_press:
            if psy_event.getKeys(keyList=config.EXP_KEYS):
                early_press = True

        # Check for response after target is shown
        if target_shown and not hit and rt_s is None and not early_press:
            keys = psy_event.getKeys(keyList=config.EXP_KEYS, timeStamped=kb.clock)
            if keys:
                rt_s = keys[0][-1]  # [key_name, rt] list from event backend
                if not target_removed:
                    hit = True

        _check_quit(kb)

    return hit, rt_s, early_press


def _compute_reward(
    hit: bool, cue_type: str, total_earned: int
) -> tuple[str, int]:
    """Return (reward_outcome_label, new_total_earned)."""
    if cue_type == "gain":
        if hit:
            return "+$5", total_earned + 5
        else:
            return "$0", total_earned
    elif cue_type == "loss":
        if hit:
            return "$0", total_earned
        else:
            return "-$5", total_earned - 5
    else:  # neutral
        return "$0", total_earned


def run_outcome(
    win: visual.Window,
    stimuli: Stimuli,
    kb: keyboard.Keyboard,
    hit: bool,
    cue_type: str,
    total_earned: int,
) -> tuple[str, int]:
    """
    Display outcome for STUDY_TIMES_S['feedback'] seconds.
    Returns (reward_outcome, new_total_earned).
    """
    reward_outcome, new_total_earned = _compute_reward(hit, cue_type, total_earned)
    timer = core.CountdownTimer(config.STUDY_TIMES_S["outcome"])
    while timer.getTime() > 0:
        draw_feedback(stimuli, hit, cue_type, reward_outcome)
        win.flip()
        _check_quit(kb)
    return reward_outcome, new_total_earned


def run_iti(
    win: visual.Window,
    stimuli: Stimuli,
    kb: keyboard.Keyboard,
    fix_dur_s: float,
) -> None:
    """Display fixation for fix_dur_s seconds (drift-corrected by caller)."""
    if fix_dur_s <= 0:
        return
    timer = core.CountdownTimer(fix_dur_s)
    while timer.getTime() > 0:
        draw_fixation(stimuli)
        win.flip()
        _check_quit(kb)


def _check_quit(kb: keyboard.Keyboard) -> None:
    """Quit if escape or end-key is pressed."""
    keys = psy_event.getKeys(keyList=["escape", "l"])
    if keys:
        core.quit()



def run_trial(
    win: visual.Window,
    stimuli: Stimuli,
    kb: keyboard.Keyboard,
    global_clock: core.Clock,
    row: pd.Series,
    trial_n: int,
    quest_name: str,
    handler,                   # data.QuestHandler
    intensity: float,          # seconds above MIN_TARGET_DUR_S
    n_iti_trs: int,
    nominal_time: float,
    total_earned: int,
    subject_id: str,
    run_n: str,
    pulse_ct: int,
    pulse_counter: PulseCounter,
) -> tuple[TrialRecord, list[ScanPhase], float, int]:
    """
    Run one complete trial (cue → fixation → response → outcome → ITI).

    Returns:
        record         – TrialRecord for behavioral.csv
        scan_phases    – list[ScanPhase] for scan_log.csv (5 or 6 entries)
        nominal_time   – updated nominal time after all ITI phases
        total_earned   – updated cumulative earnings
    """
    cue_type = str(row["cue_type"])
    target_accuracy = int(row["target_accuracy"])
    difficulty = config.DIFFICULTY[target_accuracy]
    trial_type = config.TRIAL_TYPE_MAP[(cue_type, target_accuracy)]
    reward = config.REWARD_DOLLARS[cue_type]
    jitter_s = random.uniform(0, config.JITTER_MAX_S)

    target_dur_ms = int(round((config.MIN_TARGET_DUR_S + intensity) * 1000))
    logging.exp(
        f"  -> cue={cue_type}  accuracy={target_accuracy}%  quest={quest_name}  "
        f"target_dur={target_dur_ms} ms  jitter={int(jitter_s * 1000)} ms"
    )

    scan_phases: list[ScanPhase] = []
    tr_within = 0

    # ── CUE ─────────────────────────────────────────────────────────────────
    pulse_ct += pulse_counter.drain()
    time_onset = global_clock.getTime()
    tr_within += 1
    scan_phases.append(ScanPhase(
        trial_n=trial_n, phase="cue", tr_n=tr_within,
        phase_global_time=time_onset,
        phase_trial_time=0.0,
        pulse_ct=pulse_ct,
    ))
    run_cue(win, stimuli, cue_type, target_accuracy, kb)
    nominal_time += config.STUDY_TIMES_S["cue"]

    # ── FIXATION ──────────────────────────────────────────────────────────────
    pulse_ct += pulse_counter.wait_for_tr()
    fixation_start = global_clock.getTime()
    tr_within += 1
    scan_phases.append(ScanPhase(
        trial_n=trial_n, phase="fixation", tr_n=tr_within,
        phase_global_time=fixation_start,
        phase_trial_time=fixation_start - time_onset,
        pulse_ct=pulse_ct,
    ))
    early_press = run_fixation(win, stimuli, kb)
    nominal_time += config.STUDY_TIMES_S["fixation"]

    # ── RESPONSE ─────────────────────────────────────────────────────────────
    pulse_ct += pulse_counter.wait_for_tr()
    response_start = global_clock.getTime()
    tr_within += 1
    scan_phases.append(ScanPhase(
        trial_n=trial_n, phase="response", tr_n=tr_within,
        phase_global_time=response_start,
        phase_trial_time=response_start - time_onset,
        pulse_ct=pulse_ct,
    ))
    hit, rt_s, early_press = run_response(win, stimuli, kb, jitter_s, intensity, early_press)

    # Update QUEST
    handler.addResponse(int(hit))
    quest_n = handler.thisTrialN + 1     # 1-indexed
    step_size = quest_sd(handler)
    target_dur_s = config.MIN_TARGET_DUR_S + intensity
    nominal_time += config.STUDY_TIMES_S["response"]

    # ── OUTCOME ──────────────────────────────────────────────────────────────
    pulse_ct += pulse_counter.wait_for_tr()
    outcome_start = global_clock.getTime()
    tr_within += 1
    scan_phases.append(ScanPhase(
        trial_n=trial_n, phase="outcome", tr_n=tr_within,
        phase_global_time=outcome_start,
        phase_trial_time=outcome_start - time_onset,
        pulse_ct=pulse_ct,
    ))
    reward_outcome, total_earned = run_outcome(
        win, stimuli, kb, hit, cue_type, total_earned
    )
    nominal_time += config.STUDY_TIMES_S["outcome"]

    # ── ITI ──────────────────────────────────────────────────────────────────
    for _ in range(n_iti_trs):
        pulse_ct += pulse_counter.wait_for_tr()
        iti_start = global_clock.getTime()
        tr_within += 1
        scan_phases.append(ScanPhase(
            trial_n=trial_n, phase="post-outcome-fixation", tr_n=tr_within,
            phase_global_time=iti_start,
            phase_trial_time=iti_start - time_onset,
            pulse_ct=pulse_ct,
        ))
        # Drift-correct: adjust ITI so nominal and actual stay aligned
        actual_time = global_clock.getTime()
        iti_dur = config.STUDY_TIMES_S["iti"] - (actual_time - nominal_time)
        nominal_time += config.STUDY_TIMES_S["iti"]
        run_iti(win, stimuli, kb, iti_dur)

    # ── BUILD RECORD ─────────────────────────────────────────────────────────
    time_trial_end = global_clock.getTime()
    time_sched_end = nominal_time

    record = TrialRecord(
        trial_n=trial_n,
        trial_type=trial_type,
        cue_type=cue_type,
        reward=reward,
        difficulty=difficulty,
        target_accuracy=target_accuracy,
        quest=quest_name,
        quest_n=quest_n,
        quest_step=round(step_size, 6),
        quest_intensity=round(intensity, 6),
        time_onset=round(time_onset, 6),
        jitter_ms=int(round(jitter_s * 1000)),
        target_dur_ms=int(round(target_dur_s * 1000)),
        early_press=int(early_press),
        hit=int(hit),
        rt_ms=round(rt_s * 1000, 2) if rt_s is not None else "",
        reward_outcome=reward_outcome,
        total_earned=total_earned,
        time_trial_end=round(time_trial_end, 6),
        trial_dur_ms=int(round((time_trial_end - time_onset) * 1000)),
        time_sched_end=round(time_sched_end, 6),
        timing_drift_ms=round((time_trial_end - time_sched_end) * 1000, 2),
        total_trs=tr_within,
        subject_id=subject_id,
        run_n=run_n,
        pulse_ct=scan_phases[0].pulse_ct,   # pulse_ct at trial ONSET (cue phase)
    )

    return record, scan_phases, nominal_time, total_earned
