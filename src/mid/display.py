"""
PsychoPy visual component construction and draw helpers.
No clocks, no response logic, no I/O.
"""
from __future__ import annotations

from dataclasses import dataclass

from psychopy import visual

from mid import config


@dataclass
class Stimuli:
    win: visual.Window
    fix: visual.TextStim
    cue: visual.Polygon
    cue_label: visual.TextStim
    accuracy_label: visual.TextStim
    target: visual.Polygon
    feedback_trial: visual.TextStim
    feedback_exp: visual.TextStim
    instr_prompt: visual.TextStim
    instr_first: visual.TextStim
    instr_move: visual.TextStim
    instr_finish: visual.TextStim
    wait: visual.TextStim
    end: visual.TextStim


def build_stimuli(win: visual.Window) -> Stimuli:
    """Construct all visual stimuli and return a Stimuli dataclass."""
    y_scr = 1.0
    win_res = win.size
    x_scr = float(win_res[0]) / float(win_res[1])
    font_h = y_scr / 25
    wrap_w = x_scr / 1.5
    text_col = "black"

    fix = visual.TextStim(
        win, name="fix", pos=(0, 0), text="+", height=font_h * 2, color=text_col,
        autoLog=False,
    )

    cue = visual.Polygon(win, name="cue", radius=0.2, pos=(0, 0), fillColor="white",
        autoLog=False,
    )

    cue_label = visual.TextStim(
        win, name="cue_label", font="Arial", pos=(0, 0), height=font_h, color=text_col,
        autoLog=False,
    )

    accuracy_label = visual.TextStim(
        win, name="accuracy_label", font="Arial", pos=(0, -y_scr / 4), height=font_h, color=text_col,
        autoLog=False,
    )

    target = visual.Polygon(
        win, name="target", edges=3, radius=0.2, fillColor="white", lineWidth=0, pos=(0, 0),
        autoLog=False,
    )

    feedback_trial = visual.TextStim(
        win, name="feedback_trial", font="Arial", pos=(0, -y_scr / 20),
        height=font_h + y_scr / 30, wrapWidth=None, color=text_col,
        autoLog=False,
    )

    feedback_exp = visual.TextStim(
        win, name="feedback_exp", font="Arial", pos=(0, y_scr / 6),
        height=font_h + y_scr / 30, wrapWidth=None, color="Green",
        autoLog=False,
    )

    instr_prompt = visual.TextStim(
        win, name="instr_prompt", font="Arial", pos=(0, y_scr / 10),
        height=font_h, wrapWidth=wrap_w, color=text_col,
        autoLog=False,
    )

    keys_map = config.KEYS_BEHAVIORAL  # updated per session in display_instructions
    instr_first = visual.TextStim(
        win, name="instr_first", text=f"Press {keys_map['forward']} to continue.",
        height=font_h, color=text_col, pos=(0, -y_scr / 4),
        autoLog=False,
    )
    instr_move = visual.TextStim(
        win, name="instr_move",
        text=f"Press {keys_map['forward']} to continue, or {keys_map['back']} to go back.",
        height=font_h, color=text_col, pos=(0, -y_scr / 4),
        autoLog=False,
    )
    instr_finish = visual.TextStim(
        win, name="instr_finish",
        text=(
            "You have reached the end of the instructions. "
            "When you are ready to begin the task, place your fingers on the "
            "keys and notify the experimenter."
        ),
        height=font_h, color=text_col, pos=(0, 0), wrapWidth=wrap_w,
        autoLog=False,
    )

    wait = visual.TextStim(
        win, name="wait", pos=(0, 0),
        text="The task will begin momentarily. Get ready...",
        height=font_h, color=text_col, wrapWidth=wrap_w,
        autoLog=False,
    )

    end = visual.TextStim(
        win, name="end", pos=(0, 0), text="Thank you!", height=font_h, color=text_col,
        wrapWidth=wrap_w, autoLog=False,
    )

    return Stimuli(
        win=win,
        fix=fix,
        cue=cue,
        cue_label=cue_label,
        accuracy_label=accuracy_label,
        target=target,
        feedback_trial=feedback_trial,
        feedback_exp=feedback_exp,
        instr_prompt=instr_prompt,
        instr_first=instr_first,
        instr_move=instr_move,
        instr_finish=instr_finish,
        wait=wait,
        end=end,
    )


def update_instr_keys(stimuli: Stimuli, fmri: bool) -> None:
    """Update instruction navigation key labels based on run mode."""
    keys_map = config.KEYS_FMRI if fmri else config.KEYS_BEHAVIORAL
    stimuli.instr_first.text = f"Press {keys_map['forward']} to continue."
    stimuli.instr_move.text = (
        f"Press {keys_map['forward']} to continue, or {keys_map['back']} to go back."
    )


def draw_cue(stimuli: Stimuli, cue_type: str, target_accuracy: int) -> None:
    stimuli.cue.edges = config.CUE_SHAPES[cue_type]
    stimuli.cue_label.text = f" {config.CUE_LABELS[cue_type]}"
    stimuli.accuracy_label.text = f"({target_accuracy}% chance of winning)"
    stimuli.cue.draw()
    stimuli.cue_label.draw()
    stimuli.accuracy_label.draw()


def draw_fixation(stimuli: Stimuli) -> None:
    stimuli.fix.draw()


def draw_target(stimuli: Stimuli) -> None:
    stimuli.target.draw()


def draw_feedback(stimuli: Stimuli, hit: bool, cue_type: str, reward_outcome: str) -> None:
    if hit:
        stimuli.feedback_exp.text = "You won!"
        stimuli.feedback_exp.color = "Green"
    else:
        stimuli.feedback_exp.text = "You missed!"
        stimuli.feedback_exp.color = "Red"
    stimuli.feedback_trial.text = f"Trial outcome: {reward_outcome}"
    stimuli.feedback_trial.draw()
    stimuli.feedback_exp.draw()
