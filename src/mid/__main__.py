"""
Entry point: `python -m mid` or `mid-task` script.
Wires all modules together.
"""
from __future__ import annotations


def _patch_emulator() -> None:
    """Apply psychopy-mri-emulator patch before any other PsychoPy imports."""
    try:
        import psychopy_mri_emulator.emulator
        import psychopy.hardware.emulator as _hw_emu
        _hw_emu.launchScan = psychopy_mri_emulator.emulator.launchScan
        _hw_emu.SyncGenerator = psychopy_mri_emulator.emulator.SyncGenerator
        _hw_emu.ResponseEmulator = psychopy_mri_emulator.emulator.ResponseEmulator
    except ImportError:
        pass


def run() -> None:
    _patch_emulator()

    # Disable pyglet event checking in background threads (prevents macOS crash)
    from psychopy import core
    core.checkPygletDuringWait = False

    from datetime import datetime
    from pathlib import Path

    import numpy as np
    from psychopy import logging
    from psychopy.hardware import keyboard

    from mid import config, display, recorder, session, staircase, trial

    # ── INITIALISE SESSION ───────────────────────────────────────────────────
    session_info = session.show_dialog()
    session_time = datetime.now()

    win_res, win = session.setup_screen()

    # Measure frame rate
    measured_fps = win.getActualFrameRate()
    frame_rate = measured_fps if (measured_fps is not None and measured_fps < 200) else 60.0

    # ── LOGGING ──────────────────────────────────────────────────────────────
    data_dir = Path("data")
    run_dir = session.make_run_dir(data_dir, session_info, session_time)
    logging.LogFile(str(run_dir / "experiment.log"), level=logging.EXP)
    logging.console.setLevel(logging.WARNING)

    # ── BUILD STIMULI ────────────────────────────────────────────────────────
    stimuli_obj = display.build_stimuli(win)
    display.update_instr_keys(stimuli_obj, session_info.fmri)

    # ── LOAD SEQUENCE ────────────────────────────────────────────────────────
    sequence = session.load_sequence(session_info.run_n)
    n_trials = len(sequence)

    # ── BUILD STAIRCASES ─────────────────────────────────────────────────────
    staircases = staircase.build_staircases(sequence)

    # ── SETUP OUTPUT FILES ───────────────────────────────────────────────────
    behavioral_writer = recorder.BehavioralCsvWriter(run_dir / "behavioral.csv")
    scan_log_writer = recorder.ScanLogWriter(run_dir / "scan_log.csv")

    # ── KEYBOARD ─────────────────────────────────────────────────────────────
    kb = keyboard.Keyboard()

    # ── ITI TR VECTOR ────────────────────────────────────────────────────────
    # Half the trials get 2 ITI TRs, half get 1
    tr_vec = np.ones(n_trials, dtype=int)
    tr_vec[: n_trials // 2] = 2
    np.random.shuffle(tr_vec)

    # ── HIDE MOUSE ───────────────────────────────────────────────────────────
    win.mouseVisible = False

    # ── INSTRUCTIONS ─────────────────────────────────────────────────────────
    if session_info.show_instructions:
        session.display_instructions(win, stimuli_obj, session_info, kb)

    # ── WAIT FOR SCAN START ───────────────────────────────────────────────────
    stimuli_obj.wait.draw()
    win.flip()

    if session_info.fmri:
        from psychopy.hardware.emulator import launchScan
        launchScan(win, config.MR_SETTINGS, globalClock=None)
        kb.waitKeys(keyList=["equal"])   # wait for first TR pulse
    else:
        keys_map = config.KEYS_BEHAVIORAL
        kb.waitKeys(keyList=[keys_map["start"]])

    # ── GLOBAL CLOCK & INITIAL FIXATION ──────────────────────────────────────
    global_clock = core.Clock()
    global_clock.reset()

    t_fix_end = config.INITIAL_FIX_DUR_S
    while global_clock.getTime() < t_fix_end:
        stimuli_obj.fix.draw()
        win.flip()

    # Seed nominal time from actual clock reading when initial fixation ends
    nominal_time = global_clock.getTime()

    # ── TRIAL LOOP ───────────────────────────────────────────────────────────
    pulse_ct = 0
    total_earned = 0

    for trial_idx, row in sequence.iterrows():
        trial_n = int(trial_idx) + 1
        stair_name, handler = staircase.get_active_staircase(row, staircases)
        intensity = staircase.next_intensity(handler)
        n_iti = int(tr_vec[trial_n - 1])

        rec, scan_phases, nominal_time, total_earned = trial.run_trial(
            win=win,
            stimuli=stimuli_obj,
            kb=kb,
            global_clock=global_clock,
            row=row,
            trial_n=trial_n,
            stair_name=stair_name,
            handler=handler,
            intensity=intensity,
            n_iti_trs=n_iti,
            nominal_time=nominal_time,
            total_earned=total_earned,
            subject_id=session_info.subject_id,
            run_n=session_info.run_n,
            pulse_ct=pulse_ct,
            fmri=session_info.fmri,
        )

        # Update cumulative pulse count from the last scan phase recorded
        if scan_phases:
            pulse_ct = scan_phases[-1].pulse_ct

        behavioral_writer.append(rec)
        for sp in scan_phases:
            scan_log_writer.append(sp)

    # ── CLOSING FIXATION ─────────────────────────────────────────────────────
    t_close_start = global_clock.getTime()
    while global_clock.getTime() < t_close_start + config.CLOSING_FIX_DUR_S:
        stimuli_obj.fix.draw()
        win.flip()

    # ── END SCREEN ───────────────────────────────────────────────────────────
    stimuli_obj.end.draw()
    win.flip()
    kb.waitKeys(keyList=["0"])

    # ── WRITE MANIFEST ───────────────────────────────────────────────────────
    recorder.write_manifest(
        run_dir=run_dir,
        session_info=session_info,
        session_time=session_time,
        frame_rate=frame_rate,
        n_trials=n_trials,
    )

    # ── CLEANUP ──────────────────────────────────────────────────────────────
    behavioral_writer.close()
    scan_log_writer.close()
    logging.flush()
    win.close()
    core.quit()


if __name__ == "__main__":
    run()
