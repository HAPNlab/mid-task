# Usage Guide

This guide covers how to run the MID (Monetary Incentive Delay) task.

## Overview

The MID task is a PsychoPy-based fMRI task. On each trial, participants see a cue indicating potential gain, loss, or neutral outcome, then must press a button while a brief target is on screen to earn or avoid losing money. Target duration is adapted trial-by-trial using a QUEST staircase to maintain a target hit rate.

## Launching the Task

From the project directory:

```bash
mid-task
```

Or without installation:

```bash
uv run mid-task
```

A startup dialog will appear.

## Startup Dialog

| Field | Description | Example |
|-------|-------------|---------|
| **Subject ID** | Participant identifier; used in output filenames | `ABC123` |
| **fMRI? (yes/no)** | Enable hardware TR pulse sync and fMRI keyboard layout | `yes` |
| **Task number (1/2/practice)** | Which sequence to run | `1` |
| **Show instructions? (yes/no)** | Display instruction slides before the task begins | `yes` |
| **Initial target duration (s)** | Starting target duration for QUEST (default: 0.265) | `0.265` |

Click **OK** to start or cancel to quit.

## Modes

### fMRI Mode (`fmri = yes`)

- Waits for the first hardware TR pulse from the MCC DAQ counter board before starting
- Uses the scanner keyboard layout (numpad keys)
- Requires the MCC DAQ board to be connected and configured with Instacal

### Behavioral Mode (`fmri = no`)

- Press **0** to start the task when the "waiting" screen appears
- Uses the standard keyboard layout
- No scanner hardware required; TR timing is emulated in software

## Keyboard Controls

### Behavioral Mode

| Key | Action |
|-----|--------|
| `4` | Navigate instructions backward |
| `3` | Navigate instructions forward |
| `0` | Start task / advance past instructions finish screen |
| `1`–`9` | Response button during target |
| `Escape` or `l` | Quit at any time |

### fMRI Mode

| Key | Action |
|-----|--------|
| `6` | Navigate instructions backward |
| `7` | Navigate instructions forward |
| `0` | Advance past instructions finish screen |
| `1`–`9` | Response button during target |
| `Escape` or `l` | Quit at any time |

## Trial Structure

Each trial proceeds through five phases:

```
Cue (2 s) → Fixation (2 s) → Response (2 s) → Outcome (2 s) → ITI (2–4 s)
```

| Phase | Duration | Description |
|-------|----------|-------------|
| **Cue** | 2.0 s | Shape indicates trial type (circle = gain, triangle = loss, hexagon = neutral) |
| **Fixation** | 2.0 s | Crosshair; early button press here is flagged and prevents scoring |
| **Response** | 2.0 s | Target appears briefly; press any response key while it's visible to score a hit |
| **Outcome** | 2.0 s | Feedback showing result (+$5, $0, or -$5) |
| **ITI** | 2–4 s | Inter-trial fixation; duration varies (1–2 TRs) for jitter |

### Cue Types

| Cue | Shape | Hit outcome | Miss outcome |
|-----|-------|-------------|--------------|
| **Gain** | Circle (many sides) | +$5 | $0 |
| **Loss** | Triangle | $0 | -$5 |
| **Neutral** | Hexagon | $0 | $0 |

### Adaptive Target Duration (QUEST)

The target duration is adjusted automatically each trial to maintain a target hit rate. There are three independent staircases:

| Difficulty | Target hit rate |
|------------|----------------|
| High | 80% |
| Medium | 50% |
| Low | 20% |

The task starts with the initial target duration set in the dialog (default: 265 ms). The valid range is 130–500 ms.

## Run Structure

1. **Initial fixation** – 12 s crosshair before the first trial
2. **Trial loop** – 62 trials (practice: 8 trials)
3. **Closing fixation** – 8 s crosshair after the last trial
4. **End screen** – Press `0` to exit

The terminal shows a live trial-by-trial summary with cue type, accuracy level, target duration, result, RT, outcome, cumulative earnings, and hit rate.

## Output Files

Each run creates a timestamped directory under `data/`:

```
data/
└── ABC123_run1_20260226T143000/
    ├── manifest.json
    ├── behavioral_ABC123_run1.csv
    ├── scan_log_ABC123_run1.csv
    └── experiment.log
```

### manifest.json

Session metadata snapshot: software version, subject ID, run number, frame rate, MR settings, and QUEST parameters.

### behavioral_ABC123_run1.csv

One row per trial. Key columns:

| Column | Description |
|--------|-------------|
| `trial_n` | Trial number (1-indexed) |
| `trial_type` | Integer 1–9 encoding cue×difficulty combination |
| `cue_type` | `gain`, `loss`, or `neutral` |
| `target_accuracy` | Target hit rate for this trial (80, 50, or 20) |
| `target_dur_ms` | Actual target duration shown (ms) |
| `jitter_ms` | Random onset jitter within response phase (ms) |
| `early_press` | 1 if a button was pressed during fixation |
| `hit` | 1 if target was pressed while visible |
| `rt_ms` | Reaction time from target onset (ms); blank if no response |
| `reward_outcome` | Outcome label: `+$5`, `$0`, or `-$5` |
| `total_earned` | Cumulative earnings after this trial ($) |
| `time_onset` | Trial onset time relative to scan start (s) |
| `timing_drift_ms` | Deviation from scheduled trial end time (ms) |
| `quest_intensity` | QUEST intensity (s above minimum target duration) |
| `pulse_ct` | Scanner pulse count at trial onset |

### scan_log_ABC123_run1.csv

One row per trial phase, suitable for aligning behavioral events to TRs. Columns: `trial_n`, `phase`, `tr_n`, `phase_global_time`, `phase_trial_time`, `pulse_ct`.

### experiment.log

PsychoPy experiment log at `EXP` level. Contains trial-by-trial summaries, QUEST parameters, and session metadata.

## Quitting Early

Press **Escape** or **l** at any point to quit. Output files written up to that point are saved.
