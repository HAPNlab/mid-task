"""
Session initialisation: dialog, screen setup, output directory, sequence loading,
and instruction display.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyglet
from psychopy import core, gui, monitors, visual

from mid import config

# Resolve project root as two levels above src/mid/
_PACKAGE_DIR = Path(__file__).parent          # src/mid/
_PROJECT_ROOT = _PACKAGE_DIR.parent.parent    # project root
_SEQUENCES_DIR = _PROJECT_ROOT / "sequences"
_TEXT_DIR = _PROJECT_ROOT / "text"


@dataclass
class SessionInfo:
    subject_id: str
    fmri: bool
    run_n: str                 # "1" | "2" | "practice"
    show_instructions: bool


def show_dialog() -> SessionInfo:
    """Present the startup dialog and return a SessionInfo."""
    fields = {
        "Subject ID": "XXX000",
        "fMRI? (yes/no)": "no",
        "Task number (1/2/practice)": "practice",
        "Show instructions? (yes/no)": "yes",
    }
    dlg = gui.DlgFromDict(dictionary=fields, title="MID Task")
    if not dlg.OK:
        core.quit()

    return SessionInfo(
        subject_id=str(fields["Subject ID"]),
        fmri=fields["fMRI? (yes/no)"].strip().lower() == "yes",
        run_n=str(fields["Task number (1/2/practice)"]).strip(),
        show_instructions=fields["Show instructions? (yes/no)"].strip().lower() == "yes",
    )


def setup_screen() -> tuple[list[int], visual.Window]:
    """Create and return (win_res, win)."""
    display = pyglet.canvas.get_display()
    screens = display.get_screens()
    win_res = [screens[-1].width, screens[-1].height]
    exp_mon = monitors.Monitor("exp_mon")
    exp_mon.setSizePix(win_res)
    win = visual.Window(
        size=win_res,
        screen=len(screens) - 1,
        allowGUI=True,
        fullscr=True,
        monitor=exp_mon,
        units="height",
        color=(0.2, 0.2, 0.2),
    )
    return win_res, win


def make_run_dir(data_dir: Path, session_info: SessionInfo, session_time: datetime) -> Path:
    """Create and return data/{subject_id}_run{n}_{YYYYMMDDTHHMMSS}/."""
    ts = session_time.strftime("%Y%m%dT%H%M%S")
    run_dir = data_dir / f"{session_info.subject_id}_run{session_info.run_n}_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_sequence(run_n: str) -> pd.DataFrame:
    """Read sequences/{run_n}.csv (or sequences/practice.csv) and return a DataFrame."""
    if run_n == "practice":
        path = _SEQUENCES_DIR / "practice.csv"
    else:
        path = _SEQUENCES_DIR / f"run_{run_n}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Sequence file not found: {path}")
    df = pd.read_csv(path)
    # Validate columns
    required = {"cue_type", "target_accuracy"}
    if not required.issubset(df.columns):
        raise ValueError(f"Sequence file must have columns {required}; got {set(df.columns)}")
    df["target_accuracy"] = df["target_accuracy"].astype(int)
    return df.reset_index(drop=True)


def display_instructions(
    win: visual.Window,
    stimuli,              # Stimuli dataclass from display.py; avoid circular import
    session_info: SessionInfo,
    kb,                   # psychopy.hardware.keyboard.Keyboard passed from caller
) -> None:
    """Display instructions from text/instructions_MID.txt one page at a time."""
    keys_map = config.KEYS_FMRI if session_info.fmri else config.KEYS_BEHAVIORAL
    forward_key = keys_map["forward"]
    back_key = keys_map["back"]
    start_key = keys_map["start"]
    end_key = keys_map["end"]

    inst_path = _TEXT_DIR / "instructions_MID.txt"
    pages: list[str] = []
    with open(inst_path) as f:
        for line in f:
            stripped = line.rstrip()
            if stripped:
                pages.append(stripped)

    if not pages:
        return

    page_idx = 0

    while True:
        stimuli.instr_prompt.text = pages[page_idx]
        stimuli.instr_prompt.draw()
        if page_idx == 0:
            stimuli.instr_first.draw()
        else:
            stimuli.instr_move.draw()
        win.flip()

        keys = kb.waitKeys(keyList=[forward_key, back_key, end_key])
        if keys[0].name == end_key:
            core.quit()
        elif keys[0].name == back_key and page_idx > 0:
            page_idx -= 1
        elif keys[0].name == forward_key:
            page_idx += 1
            if page_idx >= len(pages):
                break

    stimuli.instr_finish.draw()
    win.flip()
    kb.waitKeys(keyList=[start_key])
