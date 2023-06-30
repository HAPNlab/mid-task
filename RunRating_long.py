# -*- coding: utf-8 -*-
"""
Authored by: edenzdeng
June 28 2023
"""
from __future__ import division
from psychopy import gui, visual, core, data, event, logging, monitors
from psychopy.constants import (NOT_STARTED, STARTED, PLAYING, PAUSED,
                                STOPPED, FINISHED, PRESSED, RELEASED, FOREVER)
import numpy as np
import pandas as pd
from numpy.random import random, shuffle
import random
import pyglet
import csv
import os  # handy system and path functions
import sys  # to get file system encoding

## setting up some user-defined variables

expName = "RunRating-long"
data_dir = "data" # location of outputs to be generated; includes data for participants as well as trial selection and trial presentation sequence
inst_dir = "text" # location of instructions directory
inst_file = ["instr_rating.txt", "instr_valence.txt", "instr_arousal.txt", "instr_description.txt"] # name of instructions files (needs to be .txt)
cue_dict = {"+$5": 128, "-$5": 4, "$0": 6, "+$1": 128, "-$1": 4} # assign cue shapes (circle, square, hexagon) to cue types
accuracies = [80, 50, 20] # desired accuracy levels (high, medium, low)
inter_trial_time = 0.5 # time between cues

## defining some initialization functions

def initialization(expName):
    """Present initial dialog; initialize some parameters"""
    # Store info about the experiment session
    expInfo = {u'Subject ID': u'XXX000', u'Show instructions? (yes/no)': u'yes'}
    dlg = gui.DlgFromDict(dictionary=expInfo, title=expName)
    if dlg.OK == False:
        core.quit()  # user pressed cancel
    expInfo['date'] = data.getDateStr()  # add a simple timestamp
    expInfo['expName'] = expName
    sn = str(expInfo['Subject ID'])
    
    # Check for various experimental handles
    if expInfo['Show instructions? (yes/no)'].lower() == 'yes':
        show_instr = True
    else:
        show_instr = False
    return(expInfo,expName,sn,show_instr)

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

def start_datafiles(_thisDir, expName, expInfo, data_dir, sn):
    """Creates name for datafile (after checking for old one)"""
    fname = expName + '_' + sn
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
                    fname = expName + '_' + sn
    filename = _thisDir + os.sep + data_dir + os.sep + fname
    return(filename)
    
def display_inst(instr_part,task):
    """ display instructions for a specific experimental task; input includes: 
    instr_part: instructions extracted from text
    task: task serial number (in actual serial order, starting at 1; convetred to Python's representation, where 1 is 0, in the function"""
    inst = instr_part[task-1]
    instructPrompt.setText(inst)
    instructPrompt.draw()
    instructMove.draw()
    win.flip()
    event.waitKeys(keyList=None)
    
### START SET UP OF STUDY 

# Ensure that relative paths start from the same directory as this script
_thisDir = os.path.dirname(os.path.abspath(__file__))#.decode(sys.getfilesystemencoding())
os.chdir(_thisDir)

# present initialization dialog
[expInfo,expName,sn,show_instr] = initialization(expName) 

# Data file name creation; later add .psyexp, .csv, .log, etc
filename = start_datafiles(_thisDir, expName, expInfo, data_dir, sn)

# An ExperimentHandler isn't essential but helps with data saving
thisExp = data.ExperimentHandler(name=expName, extraInfo=expInfo, runtimeInfo=None,
    originPath=None, savePickle=True, saveWideText=True, dataFileName=filename)

# save a log file for detail verbose info
logFile = logging.LogFile(filename+'.log', level=logging.EXP)
logging.console.setLevel(logging.WARNING)  # this outputs to the screen, not a file

endExpNow = False  # flag for 'escape' or other condition => quit the exp

# Setup the window and presentation constants
[win_res, win] = make_screen()
yScr = 1.
xScr = float(win_res[0])/win_res[1]
fontH = 0.75*yScr/25
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
expKeys = ['1', '2', '3', '4'] 
endKey = "l"

# Initialize components for Routine "instructions"
instructMove = visual.TextStim(win, text="Press any button to continue.", height=yScr/35, color=textCol, pos=[0, -yScr/3])

#import instructions
instr_part = ["", "", "", ""]
for inst in range (0,len(inst_file)):
    inname = _thisDir + os.sep + inst_dir + os.sep + inst_file[inst]
    infile = open(inname, 'r')
    for line in infile:
        instr_part[inst] = instr_part[inst] + line.rstrip() + "\n"
    infile.close()

## START component code to be run before the window creation

# create fixation stimulus
fix = visual.TextStim(win, pos=[0, 0], text='+', height=fontH*2, color=textCol)
FixClock = core.Clock()

# Initialize components for instructions
instructPrompt = visual.TextStim(win=win, font='Arial', pos=(0, yScr/10), height=fontH, wrapWidth=wrapW, color=textCol);
instructFinish = visual.TextStim(win, text="Please make ratings individually for each particular cue.\nPlease make your ratings as accurately as possible.\n\nYou have reached the end of the instructions.",
                                     height=fontH, color=textCol, pos=[0, 0], wrapWidth=wrapW)    

# Initialize components for task transitions
endf = visual.TextStim(win, pos=[0, 0], text="Thank you. This part of the experiment is now complete. Please call the experimenter.",wrapWidth=wrapW, height=fontH, color=textCol)                                     

# Initialize cue components 
Cue = visual.Polygon(win, radius=0.2, pos=(0, yScr/6), fillColor="white")
CueLabel = visual.TextStim(win=win, font='Arial', pos=(0, yScr/6), height=yScr/25, color=textCol)

# Initialize Likert scale components 
ArousalScale = visual.RatingScale(win, low=1, high=7, markerStart=1, leftKeys='1', rightKeys = '2', acceptKeys='3', marker='circle', markerColor='DarkGreen', pos=(0,-yScr/3.5), showAccept=False,
                                  textColor=textCol, textFont='Arial', noMouse=True, showValue=False, scale='AROUSAL', labels=["Very low", "Moderate", "Very high"])
ValenceScale = visual.RatingScale(win, low=1, high=7, markerStart=4, leftKeys='1', rightKeys = '2', acceptKeys='3', marker='circle', markerColor='DarkRed', pos=(0,-yScr/3.5), showAccept=False,
                                  textColor=textCol, textFont='Arial', noMouse=True, showValue=False, scale='VALENCE', labels=["Very Negative", "Neutral", "Very positive"])
RatingInstr = visual.TextStim(win=win, font='Arial', pos=(0, -yScr/3), height=fontH, color=textCol, text="Move < > with FIRST and MIDDLE fingers, then press with RING finger to select")
globalClock = core.Clock()

## Displaying Instructions

# keyboard checking is just starting
event.clearEvents(eventType='keyboard')    
event.Mouse(visible=False)  # hide mouse cursor
if show_instr:
    display_inst(instr_part,1)
    display_inst(instr_part,2)
    while ValenceScale.noResponse:
        ValenceScale.draw()
        RatingInstr.draw()
        win.flip()
    display_inst(instr_part,3)
    while ArousalScale.noResponse:
        ArousalScale.draw()
        RatingInstr.draw()
        win.flip()
    display_inst(instr_part,4)
    instructFinish.draw()
    instructMove.draw()
    win.flip()
    event.waitKeys(keyList=None)
 
### START EXPERIMENTAL LOOP

for cue in list(cue_dict.keys()):
    for accuracy in accuracies:
        # reset all rating scales
        ArousalScale.reset()
        ValenceScale.reset()

        # add trial onset time to the data file
        thisExp.addData('start.time', globalClock.getTime())
        
        # update component parameters for each repeat
        Choice_Resp = event.BuilderKeyResponse()

        # add cue info to the data file
        trialtype = list(cue_dict.keys()).index(cue)*len(accuracies) + accuracies.index(accuracy)+1
        thisExp.addData('trialtype', trialtype)
        thisExp.addData('cue', "{} ({}% accuracy)".format(cue, accuracy))

        Cue.edges = cue_dict[cue]
        CueLabel.text = "{}\n({}% accuracy)".format(cue, accuracy)
        
        # -------Start Routine "ArousalRating"-------
        while ArousalScale.noResponse:
            Cue.draw()
            CueLabel.draw()
            ArousalScale.draw()
            RatingInstr.draw()
            win.flip()
            # check for quit (the Esc key)
            if endExpNow or event.getKeys(keyList=[endKey]):
                core.quit()

        # Add rating to experiment data
        thisExp.addData('ArousalRating', ArousalScale.getRating())
        
        # -------Start Routine "ValenceRating"-------
        while ValenceScale.noResponse:
            Cue.draw()
            CueLabel.draw()
            ValenceScale.draw()
            RatingInstr.draw()
            win.flip()
            # check for quit (the Esc key)
            if endExpNow or event.getKeys(keyList=[endKey]):
                core.quit()

        # Add rating to experiment data
        thisExp.addData('ValenceRating', ValenceScale.getRating())
    
        # -------Start Routine "fix"-------
        FixClock.reset()
        while FixClock.getTime() < inter_trial_time:
            fix.draw()
            # check for quit (the Esc key)
            if endExpNow or event.getKeys(keyList=[endKey]):
                core.quit()
            win.flip()
                    
        # advance to next trial/line in logFile
        thisExp.nextEntry()

# completed experiment
# end of study message
endf.draw()
win.flip()

# these shouldn't be strictly necessary (should auto-save)
thisExp.saveAsWideText(filename+'.csv',fileCollisionMethod = 'overwrite')
thisExp.saveAsPickle(filename, fileCollisionMethod = 'rename')
logging.flush()

# make sure everything is closed down
thisExp.abort()  # or data files will save again on exit
win.close()
core.quit()
