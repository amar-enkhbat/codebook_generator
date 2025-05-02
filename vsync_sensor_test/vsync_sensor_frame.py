import pyglet
from pyglet.window import key
import time
from pylsl import StreamInfo, StreamOutlet

# LSL marker stream setup
info = StreamInfo(name='ScreenMarkers', type='Markers', channel_count=1,
                  nominal_srate=0.0, channel_format='string', source_id='screen123')
outlet = StreamOutlet(info)

# Window and input
window = pyglet.window.Window(800, 600)
keys = key.KeyStateHandler()
window.push_handlers(keys)

white = False  # Start with black background
flipping = False
sent_start = False
fps_display = pyglet.window.FPSDisplay(window)

# Background rectangle that covers the whole window
batch = pyglet.graphics.Batch()
background = pyglet.shapes.Rectangle(0, 0, window.width, window.height, color=(0, 0, 0), batch=batch)
background.draw()
window.flip()
frame_duration = 1 / 60

while not window.has_exit:
    now = time.perf_counter()
    next_frame_time = now + frame_duration

    window.dispatch_events()

    if not flipping and keys[key.ENTER]:
        flipping = True
        if not sent_start:
            outlet.push_sample(["Start"])
            sent_start = True

    if flipping:
        background.color = (255, 255, 255) if white else (0, 0, 0)
        white = not white

        window.clear()
        batch.draw()
        fps_display.draw()
        window.flip()

        # Spin wait for next frame
        while time.perf_counter() < next_frame_time:
            pass

# Send "Stop" marker when exiting
if sent_start:
    outlet.push_sample(["Stop"])
