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
win = visual.Window(size=(2560, 1440), fullscr=True, screen=1, units="pix", color=(0, 0, 0), waitBlanking=True, allowGUI=False)

# Create a box on top left
width, height = win.size
box_size = 400
box = visual.Rect(win, width=box_size, height=box_size, pos=((-width / 2 + box_size / 2, height / 2 - box_size / 2)))

# Wait for Enter key to start
text = visual.TextStim(win, text='Press Enter to start', color=(1, 1, 1))
text.draw()
win.flip()
event.waitKeys(keyList=['return', 'enter'])


def log(marker: str, on_flip: bool = False) -> None:
        """
        Log a marker to the marker stream.

        Parameters
        ----------
        marker: str
            The marker to log.
        on_flip: bool (default: False)
            Whether to log on the next frame flip.
        """
        if on_flip:
            win.callOnFlip(outlet.push_sample, [marker])
        else:
            outlet.push_sample([marker])

start_marker = 'Start'
stop_marker = 'Stop'

if start_marker is not None:
    log(start_marker, on_flip=True)
# Flicker loop
for i in range(n_frames):
    # stime = time.time()
    stime = time.perf_counter() # for more accurate timing on Windows OS

    # Set box color for current frame
    color = [1, 1, 1] if sequence[i] else [-1, -1, -1]
    box.fillColor = color
    box.draw()
    win.flip()

    # Send LSL marker
    outlet.push_sample([str(sequence[i])])

    # Check for dropped frames
    # etime = time.time() - stime
    etime = time.perf_counter() - stime # for more accurate timing on Windows OS
    if etime >= 1 / refresh_rate:
        print(f"Frame flip took too long ({etime:.6f}), dropping frames!")

    if event.getKeys(keyList=["escape", "q"]):
        break
if stop_marker is not None:
    log(stop_marker)

# Cleanup
win.close()
core.quit()
