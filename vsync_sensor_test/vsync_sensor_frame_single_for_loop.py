import pyglet
from pyglet.window import key
import time
from pylsl import StreamInfo, StreamOutlet

# Stream setup for LSL
info = StreamInfo(name='ScreenMarkers', type='Markers', channel_count=1,
                  nominal_srate=0.0, channel_format='string', source_id='screen123')
outlet = StreamOutlet(info)

# Create a fullscreen window
window = pyglet.window.Window(fullscreen=True, vsync=True)
keys = key.KeyStateHandler()
window.push_handlers(keys)

# Colors for the background
white = (255, 255, 255)
black = (0, 0, 0)

# Background rectangle that covers the whole window
background = pyglet.shapes.Rectangle(0, 0, window.width, window.height, color=black)
background.draw()
window.flip()

# Tracking state of key presses
on_off_flag = False


for i in range(1000):
    window.dispatch_events()
    if i % 2 == 0:
        background.color = white
    else:
        background.color = black
    window.clear()
    background.draw()
    window.flip()
    if on_off_flag:
        outlet.push_sample(['1'])
    else:
        outlet.push_sample(['0'])
