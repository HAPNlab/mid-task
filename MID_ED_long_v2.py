# -*- coding: utf-8 -*-
"""
MID.py

Monetary incentive delay task. Participants attend a circle (+$), diamond (-$) or hexagon ($0), and are required to respond to a subsequently presented white triangle while it is presented.
Triangle presentation times vary based on a stepwise procedure calibrated to reach low, medium, and high performance. 
Responding in time for a reward cues yields a monetary gain; responding in time to a no-reward cue does nothing.

Current version: two tasks (MID1 or MID2) each with 105 trials total.  
WRITTEN FOR fMRI - affects the beginning and the end of the task.

Originally written for PsychoPy v 1.84.2
(Peirce, JW (2007) PsychoPy - Psychophysics software in Python. J Neurosci Methods, 162(1-2):8-13)
Oct 13 2020 - Updated for compatibility with Python3 (PsychoPy v 2020.2.4)

External dependencies:
    a folder (inst_dir parameter) with a txt file containing the instructions (inst_file parameter)
    a csv file (trials_file parameter) in the root directory (the directory running the code) with N+1 lines, where N is the number of trials. First line in the CSV file should be "CueType", "Accuracy".

User-defined variables: see # setting up some user-defined variables

Adapted from: nivreggev (reggevn@bgu.ac.il)

Last updated: June 28 2023
Revised by: edenzdeng
"""
from __future__ import division
from psychopy import gui, visual, core, data, event, logging, monitors
from psychopy.constants import (NOT_STARTED, STARTED, PLAYING, PAUSED,
                                STOPPED, FINISHED, PRESSED, RELEASED, FOREVER)
from psychopy.hardware.emulator import launchScan
import numpy as np  # whole numpy lib is available, prepend 'np.'
import pandas as pd
from numpy.random import random, shuffle
import random
import pyglet
import csv

import os  # handy system and path functions
import sys  # to get file system encoding
#add the current dir to search path
sys.path.append(os.getcwd())

#import the mcc stuff
from time import sleep
from mcculw import ul
from mcculw.device_info import DaqDeviceInfo

## setting up some user-defined variables

expName = "MID-long"
data_dir = "data" # location of outputs to be generated; includes data for participants as well as trial selection and trial presentation sequence
inst_dir = "text" # location of instructions directory
inst_file = ["instructions_MID.txt"] # name of instructions files (needs to be .txt)
study_times = [2, 2, 2, 2, 2] # duration of different parts of the task trials, in seconds: cue, delay (additional random 0-0.5s duration added within trial), target (actualy display shorter; the value here is the total duration for the trial), feedback, lastfixation
initial_fix_dur = 12 # added time to make sure homogenicity of magnetic field is reached
closing_fix_dur = 8 # added time to make sure haemodynamic responses of the last trials are properly modeled 
min_target_dur = 0.13 # sets the minimum presentation time for target (in seconds)
cue_dict = {"+$5": 128, "+$1": 128, "-$5": 4, "-$1": 4, "$0": 6} # assign cue shapes (circle, square, hexagon) to cue types. Note: the order here is meaningful; trialtypes 1-3 correspond to the first dict item, trialtypes 4-6 correspond to the 2nd dict item, etc.
accuracies = [80, 50, 20] # desired accuracy levels (high, medium, low). Note: the order here is meaningful; e.g., the high accuracy level corresponds to trialtypes 1, 4, 7, etc.
board_num = 0 # desired board number configured with Instacal
scanner_pulse_rate = 46 # number of pulses per TR in epi scan, this value depends on scan type

# settings for fMRI emulation:
MR_settings = {
    'TR': 2.000,     # duration (sec) per whole-brain volume
    'volumes': 587,    # number of whole-brain 3D volumes per scanning run
    'sync': 'equal', # character to use as the sync timing event; assumed to come at start of a volume
    'skip': 0,       # number of volumes lacking a sync pulse at start of scan (for T1 stabilization)
    'sound': False    # in test mode: play a tone as a reminder of scanner noise
    }

## defining some initialization functions

def initialization(expName):
    """Present initial dialog; initialize some parameters"""
    # Store info about the experiment session
    expInfo = {u'Subject ID': u'XXX000', u'fMRI? (yes/no)': u'no', u'Task number (1/2/practice)': u'practice', u'Show instructions? (yes/no)': u'yes'}
    dlg = gui.DlgFromDict(dictionary=expInfo, title=expName)
    if dlg.OK == False:
        core.quit()  # user pressed cancel
    expInfo['date'] = data.getDateStr()  # add a simple timestamp
    expInfo['expName'] = expName
    sn = str(expInfo['Subject ID'])
    
    # Check for various experimental handles
    if expInfo['fMRI? (yes/no)'].lower() == 'yes':
        fmri = True
    else:
        fmri = False
    task = expInfo['Task number (1/2/practice)']
    expName = expName + '-' + task
    return(expInfo,expName,sn,fmri,task)

def make_screen():
    """Generates screen variables"""
    platform = pyglet.canvas.get_display()
    display = pyglet.canvas.get_display()
    screens = display.get_screens()
    win_res = [screens[-1].width, screens[-1].height]
    exp_mon = monitors.Monitor('exp_mon')
    exp_mon.setSizePix(win_res)
    win = visual.Window(size=win_res, screen=len(screens)-1, allowGUI=True,
                        fullscr=True, monitor=exp_mon, units='height',
                        color=(0.2, 0.2, 0.2))
    return(win_res, win)

def start_datafiles(_thisDir, expName, expInfo, data_dir, sn, fmri):
    """Creates name for datafile (after checking for old one)"""
    fname = expName + '_' + ['behavioral', 'fmri'][fmri] + '_' + sn
    curdirlist = os.listdir(_thisDir + os.sep + data_dir)
    for i in curdirlist:
            if i == fname + '.csv':
                warndlg = gui.Dlg(title='Warning!')
                warndlg.addText('A data file with this number already exists.')
                warndlg.addField('Overwrite?\t\t', initial="no")
                warndlg.addField('If no, new ID:\t', initial='0')
                warndlg.show()
                if gui.OK:
                    over = warndlg.data[0].lower() == 'no'
                else:
                    core.quit()
                if over:
                    sn = str(warndlg.data[1])
                    fname = expName + '_'  + ['behavioral', 'fmri'][fmri] + '_' + sn
    filename = _thisDir + os.sep + data_dir + os.sep + fname
    return(filename)
    
def display_inst(instr_part,task,forwardKey,backKey,startKey,instructFinish):
    """ display instructions for a specific experimental task; input includes: 
    instr_part: instructions extracted from text
    task: task serial number (in actual serial order, starting at 1; convetred to Python's representation, where 1 is 0, in the function"""
    endOfInstructions = False
    instructLine = 0
    inst = instr_part[task-1]
    while not endOfInstructions:
        instructPrompt.setText(inst[instructLine])
        instructPrompt.draw()
        if instructLine == 0:
            instructFirst.draw()
            win.flip()
            instructRep = event.waitKeys(keyList=[forwardKey])
        else:
            instructMove.draw()
            win.flip()
            instructRep = event.waitKeys(keyList=[forwardKey, backKey])
        if event.getKeys(keyList=[endKey]):
            core.quit()       
        if instructRep[0] == backKey:
            instructLine -= 1
        elif instructRep[0] == forwardKey:
            instructLine += 1
        if inst[instructLine] == "end":
            endOfInstructions = True
        # check for quit:
    instructFinish.draw()
    win.flip()
    event.waitKeys(keyList=[startKey])
    
### START SET UP OF STUDY 

# Ensure that relative paths start from the same directory as this script
_thisDir = os.path.dirname(os.path.abspath(__file__))#.decode(sys.getfilesystemencoding())
os.chdir(_thisDir)

# present initialization dialog
[expInfo,expName,sn,fmri,task] = initialization(expName) 

# Data file name creation; later add .psyexp, .csv, .log, etc
filename = start_datafiles(_thisDir, expName, expInfo, data_dir, sn, fmri)

# An ExperimentHandler isn't essential but helps with data saving
thisExp = data.ExperimentHandler(name=expName, version=task, extraInfo=expInfo, runtimeInfo=None,
    originPath=None, savePickle=True, saveWideText=True, dataFileName=filename)

# save a log file for detail verbose info
logFile = logging.LogFile(filename+'.log', level=logging.EXP)
logging.console.setLevel(logging.WARNING)  # this outputs to the screen, not a file

endExpNow = False  # flag for 'escape' or other condition => quit the exp

# Setup the window and presentation constants
[win_res, win] = make_screen()
yScr = 1.
xScr = float(win_res[0])/win_res[1]
fontH = yScr/25
wrapW = xScr/1.5
textCol = 'black'
# store frame rate of monitor if we can measure it
expInfo['frameRate'] = win.getActualFrameRate()
if expInfo['frameRate'] != None and expInfo['frameRate'] <200: # inserted a manual byapss here to aviod illogical refresh rates
    frameDur = 1.0 / round(expInfo['frameRate'])
else:
    frameDur = 1.0 / 60.0  # could not measure, so guess

# set random seed - participant dependent
random.seed(sn)

# determine accepted inputs 
if fmri:
    forwardKey = "7"
    backKey = "6"
    startKey = "0"
    expKeys = ["1","2","3","4"] # including all response button keys to catch misaligned fingers/responses
    endKey = "l"
    # Initialize components for Routine "instructions"
    instructFirst = visual.TextStim(win, text="Press 7 to continue.", height=fontH, color=textCol, pos=[0, -yScr/4])
    instructMove = visual.TextStim(win, text="Press 7 to continue, or 6 to go back.", height=fontH, color=textCol, pos=[0, -yScr/4])
else:
    forwardKey = "4"
    backKey = "3"
    startKey = "0"
    expKeys = ["1", "2", "3", "4"] 
    endKey = "l"
    # Initialize components for Routine "instructions"
    instructFirst = visual.TextStim(win, text="Press 4 to continue.", height=fontH, color=textCol, pos=[0, -yScr/4])
    instructMove = visual.TextStim(win, text="Press 4 to continue, or 3 to go back.", height=fontH, color=textCol, pos=[0, -yScr/4])

#import instructions
instr_part = [[],[],[]]
if fmri:
    inst_file = inst_file
else:
    inst_file = inst_file
for inst in range (0,len(inst_file)):
    inname = _thisDir + os.sep + inst_dir + os.sep + inst_file[inst]
    infile = open(inname, 'r')
    for line in infile:
        instr_part[inst].append(line.rstrip())
    instr_part[inst].append("end")
    infile.close()

## START component code to be run before the window creation

#create fixation stimulus
fix = visual.TextStim(win, pos=[0, 0], text='+', height=fontH*2, color=textCol)
FixClock = core.Clock()

# Initialize components for Routine "instructions"
instructPrompt = visual.TextStim(win=win, font='Arial', pos=(0, yScr/10), height=fontH, wrapWidth=wrapW, color=textCol);
instructFinish = visual.TextStim(win, text="You have reached the end of the instructions. When you are ready to begin the task, place your fingers on the keys and notify the experimenter.",
                                     height=fontH, color=textCol, pos=[0, 0], wrapWidth=wrapW)    

# Initialize components for task transitions
wait = visual.TextStim(win, pos=[0, 0], text="The task will begin momentarily. Get ready...", height=fontH, color=textCol, wrapWidth=wrapW)
wait_str = "The task will begin momentarily. Get ready..."
endf = visual.TextStim(win, pos=[0, 0], text="Thank you!",wrapWidth=wrapW, height=fontH, color=textCol)                                     

# Initialize components for Routine "cue" 
Cue = visual.Polygon(win, radius=0.2, pos=(0, 0), fillColor="white")
CueLabel = visual.TextStim(win=win, font='Arial', pos=(0, 0), height=fontH, color=textCol)
AccuracyLabel = visual.TextStim(win=win, font='Arial', pos=(0, -yScr/4), height=fontH, color=textCol)
CueClock = core.Clock()
Cue_trials_template = _thisDir + os.sep + "MID" + task + "_long_trials.csv"

# Initialize components for Routine "Target"
TargetClock = core.Clock()
Target = visual.Polygon(win, edges=3, radius=0.2, fillColor = "white", lineWidth=0, pos=(0,0)) 

# Initialize components for Routine "Feedback"
FeedbackClock = core.Clock()
Trial_FB = visual.TextStim(win=win, name='Trial_FB',text='Trial outcome:',font='Arial',pos=(0, -yScr/20), height=fontH+yScr/30, wrapWidth=None, ori=0, 
    color=textCol, colorSpace='rgb', opacity=1)
Exp_FB = visual.TextStim(win=win, name='Exp_FB',text='You won!',font='Arial',pos=(0, yScr/6), height=fontH+yScr/30, wrapWidth=None, ori=0, 
    color='Green', colorSpace='rgb', opacity=1)
Blank_FB_Rectangle = visual.ImageStim(win=win, name='Blank_FB', mask=None,ori=0, pos=(0, 0), size=(xScr/8, xScr/8),texRes=128, interpolate=True)

# Create some handy timers
globalClock = core.Clock()  # to track the time since experiment started
routineTimer = core.CountdownTimer()  # to track time remaining of each (non-slip) routine 

# create content to be displayed
stimuli = pd.read_csv(Cue_trials_template) # read template stimuli

# generate vector to determine which trials have extra TR
tr_vec = np.ones(len(stimuli)) # 31 trials
tr_vec[:len(stimuli)//2] = 2 # 32 trials
np.random.shuffle(tr_vec)

## Displaying Instructions

# keyboard checking is just starting
event.clearEvents(eventType='keyboard')    
event.Mouse(visible=False)  # hide mouse cursor
if expInfo['Show instructions? (yes/no)'].lower() == 'yes':
    display_inst(instr_part,1,forwardKey,backKey,startKey,instructFinish)

# reset the non-slip timer for next routine
routineTimer.reset()
event.clearEvents(eventType='keyboard')    
 
### START EXPERIMENTAL LOOP

# wait for TR signal if in scanner
if fmri:
    wait.draw()
    win.flip()
    #event.waitKeys(keyList=['equal'])
    # get the current counter value
    ctr_info = DaqDeviceInfo(board_num).get_ctr_info()
    counter_num = ctr_info.chan_info[0].channel_num
    curr_val = ul.c_in_32(board_num, counter_num)
    # poll the counter and sleep while its the same as the previous poll
    while curr_val == ul.c_in_32(board_num, counter_num):
        sleep(0.001)
else:
    # launch: operator selects Scan or Test (emulate); see API docuwmentation
    vol = launchScan(win, MR_settings, globalClock=globalClock, wait_msg=wait_str)
    #wait.draw()
    win.flip()
    event.waitKeys(keyList=['equal'])
    
# set up counters for trials (to determine cue color and for total earnings
trial_counter = 0
Tot_Earn = 0

# set up function to add TR info to csv
def addTR(trials, time_start, trial_counter, curr_TR, TR_start, trialtype, CueType, CueAccuracy):
    trials.addOtherData('time.onset', time_start)
    trials.addOtherData('time.trial', globalClock.getTime()-time_start)
    trials.addOtherData('true_trialN', trial_counter)
    trials.addOtherData('TR', (curr_TR-TR_start)//scanner_pulse_rate + 1)
    trials.addOtherData('pulse.ct', curr_TR-TR_start)
    trials.addOtherData('trialtype', trialtype)
    trials.addOtherData('cue', "{} ({}% accuracy)".format(CueType, CueAccuracy))

# create the staircase handler to adjust for individual threshold (stairs defined in units of screen frames; actual minimum presentation duration is determined by the min_target_dur parameter, the staircase procedure can only add frame rates to that minimum value)
high = data.QuestHandler(startVal=8.1, startValSd=4, pThreshold=accuracies[0]/100, name='high', gamma=0.01,
                         nTrials=len(stimuli[stimuli["Accuracy"]==accuracies[0]]), minVal=0, maxVal=22.2)
thisExp.addLoop(high)
medium = data.QuestHandler(startVal=8.1, startValSd=4, pThreshold=accuracies[1]/100, name='medium', gamma=0.01,
                         nTrials=len(stimuli[stimuli["Accuracy"]==accuracies[1]]), minVal=0, maxVal=22.2)
thisExp.addLoop(medium)
low = data.QuestHandler(startVal=8.1, startValSd=4, pThreshold=accuracies[2]/100, name='low', gamma=0.01, 
                         nTrials=len(stimuli[stimuli["Accuracy"]==accuracies[2]]), minVal=0, maxVal=22.2)
thisExp.addLoop(low)

nominalTime = 0 # set up virtual time keeper to align actual with a-priori time allocation
globalClock.reset() # to align actual time with virtual time keeper
    
# present initial fixation
t_start = globalClock.getTime()
t = t_start
while t < t_start + initial_fix_dur:
    t = globalClock.getTime()
    fix.draw()
    win.flip()              
nominalTime = t # set up virtual time keeper to align actual with a-priori time allocation

while trial_counter < len(stimuli):
    # Choose the correct staircase handler based on desired accuracy level
    CueType = stimuli.iloc[trial_counter][0] # get cue type from the externally imported stimuli list, based on trial_counter
    CueAccuracy = stimuli.iloc[trial_counter][1]
    trialtype = list(cue_dict.keys()).index(CueType)*len(accuracies) + accuracies.index(CueAccuracy)+1
    if CueAccuracy == accuracies[0]:
        trials = high
    elif CueAccuracy == accuracies[1]:
        trials = medium
    elif CueAccuracy == accuracies[2]:
        trials = low
    currentLoop = trials
    intensity = next(trials)

    # update component parameters for each repeat
    Choice_Resp = event.BuilderKeyResponse()

    Cue.edges = cue_dict[CueType]
    CueLabel.text = f"         {CueType}"
    AccuracyLabel.text = f"         ({CueAccuracy}% chance of winning)"
    trial_counter += 1
    
    # ------Prepare to start Routine "Cue"-------
    t = 0
    CueClock.reset()  # clock
    # reset the non-slip timer for next routine
    routineTimer.reset()                
    continueRoutine = True
    routineTimer.add(study_times[0]) # set time limit for current phase
    nominalTime += study_times[0] # update nominal time keeper
    time_start = globalClock.getTime()
    
    # keep track of which components have finished
    CueComponents = [Cue, CueLabel, AccuracyLabel]
    for thisComponent in CueComponents:
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    
    # -------Start Routine "Cue"-------
    # add new TR to data file
    if fmri:
        curr_TR = ul.c_in_32(board_num, counter_num)
    else:
        curr_TR = 0
        scanner_pulse_rate = 1
    TR_start = curr_TR
    addTR(trials, time_start, trial_counter, curr_TR, TR_start, trialtype, CueType, CueAccuracy)

    while continueRoutine and routineTimer.getTime() > 0:
        # get current time
        t = CueClock.getTime()
        
        # first screen updates
        if t >= 0.0 and Cue.status == NOT_STARTED:
            # keep track of start time/frame for later
            Cue.tStart = t; CueLabel.tStart = t
            Cue.setAutoDraw(True)
            CueLabel.setAutoDraw(True)
            AccuracyLabel.setAutoDraw(True)
        frameRemains = 0.0 + study_times[0] - win.monitorFramePeriod * 0.75  # most of one frame period left
        if Cue.status == STARTED and t >= frameRemains:
            Cue.setAutoDraw(False)
            CueLabel.setAutoDraw(False)
            AccuracyLabel.setAutoDraw(False)

        # check if all components have finished
        if not continueRoutine:  # a component has requested a forced-end of Routine
            break
        continueRoutine = False  # will revert to True if at least one component still running
        for thisComponent in CueComponents:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # check for quit (the Esc key)
        if endExpNow or event.getKeys(keyList=[endKey]):
            core.quit()
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # -------Ending Routine "Choice"-------
    for thisComponent in CueComponents:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)

    # ------Prepare to start Routine "fix"-------
    t = 0
    FixClock.reset()  # clock    
    # reset the non-slip timer for next routine
    routineTimer.reset()   
    continueRoutine = True
    
    # set fixation time duration 
    nominalTime += study_times[1]
    routineTimer.add(study_times[1])
    
    # keep track of which components have finished
    fixComponents = [fix]
    for thisComponent in fixComponents:
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    
    # -------Start Routine "fix"-------
    # add new TR to data file
    if fmri:
        if ul.c_in_32(board_num, counter_num) < curr_TR + scanner_pulse_rate:
            while ul.c_in_32(board_num, counter_num) < curr_TR + scanner_pulse_rate: # wait for scanner to catch up
                sleep(0.001); routineTimer.add(0.001)
        curr_TR = ul.c_in_32(board_num, counter_num)
    else:
        if event.getKeys(keyList=['equal']):
            curr_TR += 1
    thisExp.nextEntry()
    addTR(trials, time_start, trial_counter, curr_TR, TR_start, trialtype, CueType, CueAccuracy)

    while continueRoutine and routineTimer.getTime() > 0:
        
        # get current time
        t = FixClock.getTime()
                
        # fix updates
        if t >= 0 and fix.status == NOT_STARTED:
            # keep track of start time/frame for later
            fix.tStart = t
            fix.setAutoDraw(True)
            # start keyboard checking
            event.clearEvents(eventType='keyboard')  
            theseKeys = []
        frameRemains = 0.0 + study_times[1] - win.monitorFramePeriod * 0.75  # most of one frame period left
        if fix.status == STARTED and t >= frameRemains:
            fix.setAutoDraw(False)
            # check for early response
            theseKeys = event.getKeys(keyList=expKeys)
            EarlyResp = 0
            if len(theseKeys) > 0:  # at least one key was pressed
                EarlyResp = 1
        
        # check if all components have finished
        if not continueRoutine:  # a component has requested a forced-end of Routine
            break
        continueRoutine = False  # will revert to True if at least one component still running
        for thisComponent in fixComponents:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # check for quit (the Esc key)
        if endExpNow or event.getKeys(keyList=[endKey]):
            core.quit()
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # -------Ending Routine "fix"-------
    for thisComponent in fixComponents:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)    
    
    # ------Prepare to start Routine "Target"-------
    t = 0
    TargetClock.reset()  # clock
    
    # reset the non-slip timer for next routine
    routineTimer.reset()                   
    continueRoutine = True
    routineTimer.add(study_times[2])
    nominalTime += study_times[2]

    # update component parameters for each repeat
    Target_Resp = event.BuilderKeyResponse()
    
    # keep track of which components have finished
    TargetComponents = [Target, Target_Resp]
    for thisComponent in TargetComponents:
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    
    # set a random delay before target appears
    jitter = random.uniform(0, 0.05)
    trials.addOtherData('jitter', jitter)

    # -------Start Routine "Target"-------
    # add new TR to data file
    if fmri:
        if ul.c_in_32(board_num, counter_num) < curr_TR + scanner_pulse_rate:
            while ul.c_in_32(board_num, counter_num) < curr_TR + scanner_pulse_rate: # wait for scanner to catch up
                sleep(0.001); routineTimer.add(0.001)
        curr_TR = ul.c_in_32(board_num, counter_num)
    else:
        if event.getKeys(keyList=['equal']):
            curr_TR += 1
    thisExp.nextEntry()
    addTR(trials, time_start, trial_counter, curr_TR, TR_start, trialtype, CueType, CueAccuracy)

    while continueRoutine and routineTimer.getTime() > 0:
        # get current time
        t = TargetClock.getTime()
        
        # selection screen updates
        if t >= jitter and Target.status == NOT_STARTED:
            # keep track of start time/frame for later
            Target.tStart = t
            # display target 
            Target.setAutoDraw(True)
            # open response options
            Target_Resp.tStart = t
            Target_Resp.status = STARTED
            # keyboard checking is just starting
            win.callOnFlip(Target_Resp.clock.reset)  # t=0 on next screen flip
            event.clearEvents(eventType='keyboard')  
            theseKeys = []

        frameRemainsResp = min_target_dur + frameDur*intensity # range: min_target_dur (130ms) + one frame (~17ms, depends on refresh rate) * 22.2
        if Target.status == STARTED and t >= frameRemainsResp:
            print('thisTrial:',intensity) # print for QA purpose
            print('frameDur:',frameDur) # print for QA purpose
            print('frameRemainsResp:',frameRemainsResp) # print for QA purpose
            
            Target.setAutoDraw(False)
            theseKeys = event.getKeys(keyList=expKeys)
            ThisResp = 0 # set response to no response - change only if response was given in the allowed time frame
            
            if len(theseKeys) > 0 and EarlyResp == 0:  # at least one key was pressed
                ThisResp = 1
                Target_Resp.rt = Target_Resp.clock.getTime()
           
        # check if all components have finished
        if not continueRoutine:  # a component has requested a forced-end of Routine
            break
        continueRoutine = False  # will revert to True if at least one component still running
        for thisComponent in TargetComponents:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # check for quit (the Esc key)
        if endExpNow or event.getKeys(keyList=[endKey]):
            core.quit()
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # -------Ending Routine "Target"-------
    for thisComponent in TargetComponents:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    
    # add the data to the staircase so it can be used to calculate the next level
    trials.addResponse(ThisResp)
    trials.addOtherData('early', EarlyResp)
    trials.addOtherData('hit', ThisResp)
    trials.addOtherData('target_ms', frameRemainsResp)

    # check responses to add RT
    if ThisResp:  # we had a response
        trials.addOtherData('rt', Target_Resp.rt)
    
    # ------Prepare to start Routine "Feedback"-------
    t = 0
    FeedbackClock.reset()  # clock
    # reset the non-slip timer for next routine
    routineTimer.reset()                   
    continueRoutine = True
    routineTimer.add(study_times[3])
    nominalTime += study_times[3]
    
    # וupdate trial components
    if ThisResp:
        Exp_FB.setText('You won!')
        Exp_FB.setColor('Green')
        if CueType=="$0": # if it was a neutral trial with hit response
            newText = 'Trial outcome: +' + CueType
            trials.addOtherData('rewardType', '$0')
        elif CueType[0]=='+': # if it was a reward trial with hit response
            Tot_Earn += int(CueType[-1])
            newText = 'Trial outcome: ' + CueType
            trials.addOtherData('rewardType', CueType)
        else: # if it was a miss trial with hit response
            newText = 'Trial outcome: $0'
            trials.addOtherData('rewardType', '$0')
    elif not ThisResp:
        Exp_FB.setText('You missed!')
        Exp_FB.setColor('Red')
        if CueType=="$0": # if it was a neutral trial with miss response
            newText = 'Trial outcome: -' + CueType
            trials.addOtherData('rewardType', '$0')
        elif CueType[0]=='-': # if it was a loss trial with miss response
            Tot_Earn -= int(CueType[-1])
            newText = 'Trial outcome: ' + CueType
            trials.addOtherData('rewardType', CueType)
        else: # if it was a reward trial with miss response
            newText = 'Trial outcome: $0'
            trials.addOtherData('rewardType', '$0')
    Trial_FB.setText(newText)
        
    # add to be presented stimuli to output
    trials.addOtherData('total_earned', Tot_Earn) 
             
    # keep track of which components have finished
    FeedbackComponents = [Trial_FB, Exp_FB]
    for thisComponent in FeedbackComponents:
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED

    # -------Start Routine "Feedback"-------
    # add new TR to data file
    if fmri:
        if ul.c_in_32(board_num, counter_num) < curr_TR + scanner_pulse_rate:
            while ul.c_in_32(board_num, counter_num) < curr_TR + scanner_pulse_rate: # wait for scanner to catch up
                sleep(0.001); routineTimer.add(0.001)
        curr_TR = ul.c_in_32(board_num, counter_num)
    else:
        if event.getKeys(keyList=['equal']):
            curr_TR += 1
    thisExp.nextEntry()
    addTR(trials, time_start, trial_counter, curr_TR, TR_start, trialtype, CueType, CueAccuracy)

    while continueRoutine and routineTimer.getTime() > 0:
        # get current time
        t = FeedbackClock.getTime()
        
        # feedback screen updates
        if t >= 0.0 and Trial_FB.status == NOT_STARTED:
            # keep track of start time/frame for later
            Trial_FB.tStart = t
            Trial_FB.setAutoDraw(True)
            Exp_FB.setAutoDraw(True)
        frameRemains = 0.0 + study_times[3] - win.monitorFramePeriod * 0.75  # most of one frame period left
        if Trial_FB.status == STARTED and t >= frameRemains:
            Trial_FB.setAutoDraw(False)
            Exp_FB.setAutoDraw(False)

        # check if all components have finished
        if not continueRoutine:  # a component has requested a forced-end of Routine
            break
        continueRoutine = False  # will revert to True if at least one component still running
        for thisComponent in FeedbackComponents:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # check for quit (the Esc key)
        if endExpNow or event.getKeys(keyList=[endKey]):
            core.quit()
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # -------Ending Routine "Feedback"-------
    for thisComponent in FeedbackComponents:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)

    # ------Prepare to start Routine "fix"-------
    for i in range(0, int(tr_vec[trial_counter-1])):
        t = 0
        FixClock.reset()  # clock    
        # reset the non-slip timer for next routine
        routineTimer.reset()   
        continueRoutine = True
        
        # set fixation time duration 
        tend = globalClock.getTime() #CueClock.getTime() # actual ending time for trial presentation
        tcor = tend-nominalTime # difference between actual elapsed time and pre-allocated time
        fix_add = study_times[4]
        fix_time = fix_add - tcor # calculate fix time to correct for time drifts
        nominalTime += study_times[4]
        routineTimer.add(fix_time)
        
        # keep track of which components have finished
        fixComponents = [fix]
        for thisComponent in fixComponents:
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        
        # -------Start Routine "fix"-------
        # add new TR to data file
        if fmri:
            if ul.c_in_32(board_num, counter_num) < curr_TR + scanner_pulse_rate:
                while ul.c_in_32(board_num, counter_num) < curr_TR + scanner_pulse_rate: # wait for scanner to catch up
                    sleep(0.001); routineTimer.add(0.001)
            curr_TR = ul.c_in_32(board_num, counter_num)
        else:
            if event.getKeys(keyList=['equal']):
                curr_TR += 1
        thisExp.nextEntry()
        addTR(trials, time_start, trial_counter, curr_TR, TR_start, trialtype, CueType, CueAccuracy)

        while continueRoutine and routineTimer.getTime() > 0:
            
            # get current time
            t = FixClock.getTime()
                
            # fix updates
            if t >= 0.0 and fix.status == NOT_STARTED:
                # keep track of start time/frame for later
                fix.tStart = t
                fix.setAutoDraw(True)
            frameRemains = 0.0 + fix_time - win.monitorFramePeriod * 0.75  # most of one frame period left
            if fix.status == STARTED and t >= frameRemains:
                fix.setAutoDraw(False)
            
            # check if all components have finished
            if not continueRoutine:  # a component has requested a forced-end of Routine
                break
            continueRoutine = False  # will revert to True if at least one component still running
            for thisComponent in fixComponents:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # check for quit (the Esc key)
            if endExpNow or event.getKeys(keyList=[endKey]):
                core.quit()
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # -------Ending Routine "fix"-------
        for thisComponent in fixComponents:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)    
    
    # add data to log file
    trials.addOtherData('time.end.global', globalClock.getTime())      
    trials.addOtherData('time.end.nominal', nominalTime)      
    trials.addOtherData('time.trial.total', CueClock.getTime())
                
    # advance to next trial/line in logFile
    thisExp.nextEntry()

# completed experiment
# present ending fixation (to allow for better evaluation of the last experimental TRs)
t_end = globalClock.getTime()
t = t_end
while t < t_end + closing_fix_dur:
    t = globalClock.getTime()
    fix.draw()
    win.flip()      

# completed experimental phase

# end of study message
endf.draw()
win.flip()
event.waitKeys(keyList=['0'])

# these shouldn't be strictly necessary (should auto-save)
thisExp.saveAsWideText(filename+'.csv',fileCollisionMethod = 'overwrite')
thisExp.saveAsPickle(filename, fileCollisionMethod = 'rename')
logging.flush()

# make sure everything is closed down
thisExp.abort()  # or data files will save again on exit
win.close()
core.quit()
