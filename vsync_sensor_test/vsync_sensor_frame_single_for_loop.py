import pyglet
import time
from pylsl import StreamInfo, StreamOutlet

# Stream setup for LSL
info = StreamInfo(name='ScreenMarkers', type='Markers', channel_count=1,
                  nominal_srate=0, channel_format='string', source_id='screen123')
outlet = StreamOutlet(info)

# Create a fullscreen window
config = pyglet.gl.Config(double_buffer=True)
window = pyglet.window.Window(fullscreen=True, vsync=True, config=config)

# Colors for the background
white = (255, 255, 255)
black = (0, 0, 0)

# Background rectangle that covers the whole window
background = pyglet.shapes.Rectangle(0, 0, window.width, window.height, color=black)
frame_rate = 30
frame_duration = 1 / frame_rate
total_duration = 5 # seconds
total_frames = total_duration * frame_rate

def on_flip(color):
    background.color = color
    window.dispatch_events()
    window.clear()
    background.draw()
    window.flip()
    pyglet.gl.glFinish()
    if color == white:
        outlet.push_sample(['1'])
    elif color == black:
        outlet.push_sample(['0'])
    else:
        raise ValueError('color not white or black')

def perf_wait(dt):
    start_time = time.perf_counter()
    while time.perf_counter() < start_time + dt:
        pass
    

for i in range(total_frames):
    if i%2 == 0:
        color = black
    else:
        color = white
    
    start_time = time.perf_counter()
    on_flip(color)
    duration = time.perf_counter() - start_time
    if duration < frame_duration:
        perf_wait(frame_duration - duration)
    else:
        ValueError('duration > frame duration')
    end_time = time.perf_counter()

    print(start_time, end_time, end_time - start_time)
    