from psychopy import visual, core, event
from pylsl import StreamInfo, StreamOutlet
import numpy as np
import time

# Parameters
refresh_rate = 60  # Hz
frame_duration = 1 / refresh_rate
duration = 5       # seconds
n_frames = int(duration * refresh_rate)

# Generate flicker sequence
sequence = [0, 1] * 5 # flash 5 times
sequence = sequence + [0] * 10 # flash 5 times, wait 10 frames
sequence = np.array(sequence * 50) # Repeat 50 times

# Create LSL outlet
info = StreamInfo(name='ScreenSequenceStream', type='Markers', channel_count=1,
                  nominal_srate=0, channel_format='string')
outlet = StreamOutlet(info)

# Create fullscreen window on main screen (screen=0)
win = visual.Window(size=(1920, 1080), fullscr=True, screen=0, units="pix", color=(-1, -1, -1), waitBlanking=True, allowGUI=False)

# Create a box on top left
width, height = win.size
box_size = 400
box = visual.Rect(win, width=box_size, height=box_size, pos=((-width / 2 + box_size / 2, height / 2 - box_size / 2)))

# Wait for Enter key to start
text = visual.TextStim(win, text='Press Enter to start', color=(1, 1, 1))
text.draw()
win.flip()
event.waitKeys(keyList=['return', 'enter'])

outlet.push_sample(['Start'])
for i in range(10000):
    print(i)
    # event.waitKeys(keyList=['return', 'enter'])

    stime = time.perf_counter() # for more accurate timing on Windows OS
    # Set box color for current frame
    color = [1, 1, 1] if i % 2 == 0 else [-1, -1, -1]
    box.fillColor = color
    box.draw()
    win.flip()

    # Send LSL marker
    outlet.push_sample(['1'])

    # Check for dropped frames
    # etime = time.time() - stime
    etime = time.perf_counter() - stime # for more accurate timing on Windows OS
    if etime >= 1 / refresh_rate:
        print(f"Frame flip took too long ({etime:.6f}), dropping frames!")
    if i % 10 == 0:
        core.wait(0.3)

outlet.push_sample(['end'])


# Cleanup
win.close()
core.quit()
