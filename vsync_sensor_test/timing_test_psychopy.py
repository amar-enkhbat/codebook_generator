from psychopy import visual, core, event
from pylsl import StreamInfo, StreamOutlet
import numpy as np
import time

# Parameters
refresh_rate = 60  # Hz
frame_duration = 1 / refresh_rate
stim_on_duration = 0.1 # seconds
stim_off_duration = 0.15 # seconds
n_stim_on_frames = int(stim_on_duration // frame_duration)
n_stim_off_frames = int(stim_off_duration // frame_duration)
print('#stim on frames:', n_stim_on_frames)
print('#stim off frames:', n_stim_off_frames)

n_stims = 1000

rest_duration = 0.3  # seconds
n_rest_frames = int(rest_duration // frame_duration)
print('#of rest frames:', n_rest_frames)

# Create LSL outlet
info = StreamInfo(
   name='ScreenSequenceStream', type='Markers', channel_count=1,
   nominal_srate=0, channel_format='string'
)
outlet = StreamOutlet(info)

# Create fullscreen window on main screen (screen=0)
win = visual.Window(size=(1920, 1080), winType='pyglet', fullscr=True, screen=1, units="pix", color='black', waitBlanking=True, allowGUI=True)
#win.recordFrameIntervals = True

# Create a box on top left
width, height = win.size
box_size = 100

boxes = []
boxes.append(visual.Rect(win, width=100, height=100, pos=(-width / 2, height / 2), color='red'))
for i in range(8):
    boxes.append(visual.Rect(win, width=box_size, height=box_size, pos=(150*i - height/2, 0)))

objects = {
    0: 'bottle', 
    1: 'bandage', 
    2: 'remote', 
    3: 'can', 
    4: 'candle', 
    5: 'box', 
    6: 'book', 
    7: 'cup'
}
pictograms = []
for i, img_path in enumerate(objects.values()):
    pictogram = visual.ImageStim(win, f'../icons/{img_path}.png', mask=None, units='pix', pos=(150*i - height/2, 0), size=100)
    pictograms.append(pictogram)

def screen_warmup(warmup_duration: float=1.0):
    """Flip screen at refresh rate for dt seconds to warmup.
    """
    for _ in range(int(warmup_duration * refresh_rate)):  # 1 second of flips at 60Hz
        color = 'black'
        for box in boxes:
            box.fillColor = color
            box.draw()
        for pictogram in pictograms:
            pictogram.draw()
        win.flip()

# Image stims
# Warmup
for i in range(5 * 60):
    color = 'white' if i % 2 == 0 else 'black'
    for box in boxes:
        box.fillColor = color
        box.draw()
    for pictogram in pictograms:
        pictogram.draw()
    win.flip()

# Wait start
for box in boxes:
    box.fillColor = 'black'
    box.draw()
for pictogram in pictograms:
    pictogram.draw()
win.flip()

# Wait for Enter key to start
text = visual.TextStim(win, text='Press Enter to start', color=(1, 1, 1))
text.draw()
win.flip()
event.waitKeys(keyList=['return', 'enter'])
core.wait(1)

# Start stim
outlet.push_sample(['Start'])
core.wait(1)

for stim_num in range(n_stims):
    # Stim on
    screen_warmup()
    for i in range(n_stim_on_frames):
        for box in boxes:
            box.fillColor = 'white'
            box.draw()
        for pictogram in pictograms:
            pictogram.draw()
        win.flip()
        if i == 0: # Send label only after first flip
           outlet.push_sample(['1'])
    # Stim off
    
    for i in range(n_stim_off_frames):
        start = time.perf_counter()
        for box in boxes:
            box.fillColor = 'black'
            box.draw()
        for pictogram in pictograms:
            pictogram.draw()
        win.flip()
        elapsed = (time.perf_counter() - start) * 1000
        print(f"Flip execution time: {elapsed:.3f} ms")
        if i == 0: # Send label only after first flip
           outlet.push_sample(['0'])
    # Pause every 12 stims
    if (stim_num + 1) % 12 == 0:
        for _ in range(n_rest_frames):
            for box in boxes:
                box.fillColor = 'black'
                box.draw()
            for pictogram in pictograms:
                pictogram.draw()
            win.flip()

# End experiment
outlet.push_sample(['end'])

# Cleanup
win.close()
core.quit()
