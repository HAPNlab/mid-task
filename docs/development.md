# Development Guide

This guide covers setting up and developing the mid-task project.

## Prerequisites

- Python 3.11+
- [UV](https://docs.astral.sh/uv/) – Fast Python package installer and resolver
- macOS or Windows (PsychoPy supports both; MCC DAQ hardware is Windows-only)

### macOS

Install system libraries required by PsychoPy's dependencies:

```bash
brew install hdf5 openblas lapack
```

### Windows (fMRI hardware mode)

The MCC DAQ counter board (used to read scanner TR pulses) requires:

- [Instacal](https://www.mccdaq.com/Software-Downloads) – MCC device configuration utility
- `mcculw` Python package (installed via `uv sync`)

Configure your DAQ board number in `src/mid/config.py` (`BOARD_NUM`).

## Quick Start

1. **Create the virtual environment**

   ```bash
   uv venv
   ```

2. **Install all dependencies**

   ```bash
   uv sync --all-extras
   ```

3. **Run the task**

   ```bash
   uv run mid-task
   ```

   Or activate the venv first:

   ```bash
   source .venv/bin/activate
   mid-task
   ```

## Project Structure

```
mid-task/
├── src/
│   └── mid/
│       ├── __init__.py       # Version
│       ├── __main__.py       # Entry point; wires all modules together
│       ├── config.py         # All task constants (no cross-module imports)
│       ├── display.py        # PsychoPy stimuli construction and draw helpers
│       ├── quest.py          # QuestHandler construction and management
│       ├── recorder.py       # TrialRecord, ScanPhase, CSV writers, manifest
│       ├── scanner.py        # HardwareBackend, EmulatedBackend, PulseCounter
│       ├── session.py        # Startup dialog, screen setup, sequence loading
│       └── trial.py          # Per-phase functions and run_trial()
├── sequences/
│   ├── run_1.csv             # 62-trial sequence for run 1
│   ├── run_2.csv             # 62-trial sequence for run 2
│   └── practice.csv          # 8-trial practice sequence
├── text/
│   └── instructions_MID.txt  # Instruction pages (one line per page)
├── data/                     # Output directory (created at runtime)
├── tests/
├── docs/
└── pyproject.toml
```

## Module Overview

| Module | Responsibility |
|--------|---------------|
| `config.py` | Single source of truth for all timing, keyboard, scanner, and QUEST constants |
| `session.py` | Startup GUI dialog, screen/monitor setup, sequence CSV loading, instruction display |
| `display.py` | Build all PsychoPy `Visual` objects; draw helpers for each phase |
| `quest.py` | Build `QuestHandler` instances (one per accuracy level); advance and clip intensities |
| `scanner.py` | Abstract scanner backend; `HardwareBackend` (MCC DAQ) and `EmulatedBackend` (software clock) |
| `trial.py` | `run_trial()` and per-phase functions (`run_cue`, `run_fixation`, `run_response`, `run_outcome`, `run_iti`) |
| `recorder.py` | `TrialRecord` and `ScanPhase` dataclasses; CSV writers; `write_manifest()` |
| `__main__.py` | Orchestration: init → instructions → wait for scan → trial loop → cleanup |

## Key Constants (`config.py`)

All timing values are in seconds. Edit `config.py` to adjust task parameters.

| Constant | Value | Description |
|----------|-------|-------------|
| `STUDY_TIMES_S` | `{cue: 2.0, fixation: 2.0, response: 2.0, outcome: 2.0, iti: 2.0}` | Phase durations |
| `MIN_TARGET_DUR_S` | `0.130` | Minimum target display duration |
| `MAX_TARGET_DUR_S` | `0.500` | Maximum target display duration |
| `INITIAL_TARGET_DUR_S` | `0.265` | Default starting duration for QUEST |
| `INITIAL_QUEST_SD_S` | `0.067` | Initial QUEST posterior SD (≈ 4 frames at 60 Hz) |
| `INITIAL_FIX_DUR_S` | `12.0` | Initial fixation before first trial |
| `CLOSING_FIX_DUR_S` | `8.0` | Closing fixation after last trial |
| `JITTER_MAX_S` | `0.05` | Max uniform jitter before target onset |
| `SCANNER_PULSE_RATE` | `46` | Hardware pulses per TR from MCC counter |

## QUEST Adaptive Staircase

The task uses three independent `QuestHandler` instances, one per accuracy level (80%, 50%, 20%). Each handler tracks target duration (in seconds above `MIN_TARGET_DUR_S`) to converge toward its target hit rate.

- **Intensity** = additional seconds above `MIN_TARGET_DUR_S`
- **Actual target duration** = `MIN_TARGET_DUR_S + intensity`
- QUEST updates after every response via `handler.addResponse(int(hit))`

## Scanner Synchronisation

`PulseCounter` wraps a backend and exposes two methods:

- `wait_for_tr()` – blocks until `SCANNER_PULSE_RATE` more pulses arrive, returns delta
- `drain()` – returns pulses accumulated since last call without blocking

In fMRI mode, `HardwareBackend` reads the MCC DAQ counter register directly.
In behavioral/development mode, `EmulatedBackend` simulates pulses at the correct rate based on wall-clock time, allowing the full trial loop to run without scanner hardware.

## Testing

```bash
uv run pytest
```

## Sequence Files

Sequences live in `sequences/` as CSV files with columns:

| Column | Description |
|--------|-------------|
| `cue_type` | `gain`, `loss`, or `neutral` |
| `target_accuracy` | Target hit rate: `80`, `50`, or `20` |
| `n_iti` | Number of ITI TRs (1 or 2) for pseudorandom spacing |

The task ships with `run_1.csv` (62 trials), `run_2.csv` (62 trials), and `practice.csv` (8 trials). To create custom sequences, follow the same column structure.
