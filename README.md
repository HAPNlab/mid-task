# MID task

## Usage
- Run MID_ED.py for the MID task with only +$5, -$5, and $0 cues (short version).
- Run MID_long_ED.py for the MID task with +$5, -$5, +$1, -$1, and $0 cues (long version).
- See text/instructions_MID.txt to edit task instructions.
- Experimental output stored in data folder.
- When "practice" task is selected, a shorter version of the MID task will be presented. Otherwise, choose MID1 or MID2. 
- If "fMRI" is selected, the experiment will not begin until the scanner sends TR signal.

## Adding a new MID task:
A new set of trials can be added be creating a csv file with cue type in 1st column and accuracy in 2nd column. Cue types can be any single-digit integer dollar amount. Cue accuracies should come in three types (low, medium, high) indicated by a number between 0 and 100 (also specify in line 52). The csv file should be stored in the main directory and named as MID[task]_trials.csv if short version and MID[task]_long_trials.csv if long version, where [task] is replaced by new task name. 

## Updating visuals and display parameters:
Experimental design parameters (e.g., initial and closing fixation times, minimum target duration, cue shapes) can be updated in lines 43-52. 