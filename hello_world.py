#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Demo: show a very basic program: hello world
"""
from __future__ import absolute_import, division, print_function


import os,sys
sys.path.append(os.getcwd())

from mcculw import ul
from mcculw.device_info import DaqDeviceInfo

# Import key parts of the PsychoPy library:
from psychopy import visual, core

board_num = 0
#trigger info
ctr_info = DaqDeviceInfo(board_num).get_ctr_info()
counter_num = ctr_info.chan_info[0].channel_num
curr_val = ul.c_in_32(board_num,counter_num)


# Create a visual window:
win = visual.Window()

# Create (but not yet display) some text:
msg1 = visual.TextStim(win, text=u"Hello world!")  # default position = centered
msg2 = visual.TextStim(win, text=u"\u00A1Hola mundo!", pos=(0, -0.3))
msg3 = visual.TextStim(win, text=u"Current Count %s" % (str(curr_val),), pos=(0, -.8))


# Draw the text to the hidden visual buffer:
msg1.draw()
msg2.draw()
msg3.draw()

# Show the hidden buffer--everything that has been drawn since the last win.flip():
win.flip()

# Wait 3 seconds so people can see the message, then exit gracefully:
core.wait(3)

win.close()
core.quit()

# The contents of this file are in the public domain.
