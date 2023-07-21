# MID task

## Usage notes
- Run MID_ED_v2.py for the MID task with only +$5, -$5, and $0 cues (short version).
- Run MID_ED_long_v2.py for the MID task with +$5, -$5, +$1, -$1, and $0 cues (long version).
- See text folder to edit task instructions.
- Experimental output is stored in data folder.
- When "practice" task is selected, a shorter version of the MID task will be presented. Otherwise, choose MID1 or MID2. 
- If "fMRI" is selected, the experiment will not begin until the a pulse signal is received from the scanner, and each phase of the trial will be synced with the scanner pulses. Otherwise, in "test" mode the scanner emulator will run in the background to simulate TR pulses through key presses.

## Editing an existing MID task:
- The trial order or contents can be edited by updating the contents of the trials csv.
- If stimuli amounts ($) need to be changed, the script will correctly handle any amounts as long as they are integers less than $10. 
- If trial accuracies need to be changed, line 60 must also be updated to match the new percentages. Note that there must be three (low, medium, high) accuracy levels specified.

## Updating visuals and display parameters:
- Experimental design parameters (e.g., lead-in and closing times, minimum target duration, cue shapes) can be updated in lines 55-59. For cue shapes, the dictionary should specify the desired number of edges (see [Psychopy docs](https://psychopy.org/api/visual/polygon.html)).
- Window display size should be automatically detected. If the display is still not sized to the subject's monitor, try setting fullscr=False in line 98 or hard-coding the desired monitor resolution in line 95.

## Adding a new MID task:
A new set of trials can be added be creating a csv file with cue type in 1st column and accuracy in 2nd column. The csv file should be stored in the main directory and named as MID[task]_trials.csv if short version and MID[task]_long_trials.csv if long version, where [task] is replaced by new task name. Then, enter this task name in the opening prompts.

## Updating the adaptive psychometric function & parameters:
- The target presentation time is iteratively calculated using the Quest algorithm, implemented in lines 328-335. See [PsychoPy docs](https://psychopy.org/_modules/psychopy/data/staircase.html#QuestHandler) for parameter details.
- Note: target presentation times are given in number of frames (~16.67ms) added to the minimum target duration.
  - E.g., for an initial presentation time of 250ms and min target dur of 130ms, set minVal = (250-130)/16.677 = 8.1
  - E.g., for a maximum presentation time of 500ms, set maxVal = (500-130)/16.6667 = 22.2
