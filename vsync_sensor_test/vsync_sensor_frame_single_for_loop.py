import pyglet
import time
from pylsl import StreamInfo, StreamOutlet


# Parameters
refresh_rate = 60  # Hz
frame_duration = 1 / refresh_rate
# stim_on_duration = 0.1 # seconds
# stim_off_duration = 0.15 # seconds
# n_stim_on_frames = int(stim_on_duration // frame_duration)
# n_stim_off_frames = int(stim_off_duration // frame_duration)
n_stim_on_frames = 1
n_stim_off_frames = 1
print('#stim on frames:', n_stim_on_frames)
print('#stim off frames:', n_stim_off_frames)

n_stims = 10000

rest_duration = 0.3  # seconds
n_rest_frames = int(rest_duration // frame_duration)
print('#of rest frames:', n_rest_frames)

# Create LSL outlet
info = StreamInfo(name='ScreenSequenceStream', type='Markers', channel_count=1,
                  nominal_srate=0, channel_format='string')
outlet = StreamOutlet(info)

# Create a fullscreen window
display = pyglet.display.get_display()
screens = display.get_screens()
print(screens)

config = pyglet.gl.Config(double_buffer=True)
window = pyglet.window.Window(fullscreen=True, vsync=True, config=config, screen=screens[0])

# Colors for the background
white = (255, 255, 255)
black = (0, 0, 0)

# Background rectangle that covers the whole window
background = pyglet.shapes.Rectangle(0, 0, window.width, window.height, color=black)

def on_flip(color):
    background.color = color
    window.dispatch_events()
    window.clear()
    background.draw()
    window.flip()
    pyglet.gl.glFinish()

def perf_wait(dt):
    # Wait in seconds
    start_time = time.perf_counter()
    while time.perf_counter() < start_time + dt:
        pass
    
# Warmup
for i in range(5 * 60):
    color = white if i % 2 == 0 else black
    on_flip(color)

# Wait start
on_flip(black)

# Wait 5 seconds
perf_wait(1)

# Start stim
if input('Start? Y/n\n') != 'y':
    exit(0)

outlet.push_sample(['Start'])
perf_wait(1)

for stim_num in range(n_stims):
    # print('Stim num:', stim_num)
    # Stim on
    for i in range(n_stim_on_frames):
        on_flip(white)
        if i == 0: # Send label only after first flip
            outlet.push_sample(['1'])
    # Stim off
    for i in range(n_stim_off_frames):
        on_flip(black)
        if i == 0: # Send label only after first flip
            outlet.push_sample(['0'])
    # Pause every 12 stims
    if (stim_num + 1) % 12 == 0:
        on_flip(black)
        for _ in range(n_rest_frames):
            background.draw()
            window.flip()

# End experiment
outlet.push_sample(['end'])

# Cleanup
window.close()