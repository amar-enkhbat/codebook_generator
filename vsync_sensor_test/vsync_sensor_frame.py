import pyglet
from pyglet.window import key
import time
from pylsl import StreamInfo, StreamOutlet
import pylsl

# LSL marker stream setup
info = StreamInfo(name='ScreenMarkers', type='Markers', channel_count=1,
                  nominal_srate=0.0, channel_format='string', source_id='screen123')
outlet = StreamOutlet(info)

# Window and input
window = pyglet.window.Window(fullscreen=True)
keys = key.KeyStateHandler()
window.push_handlers(keys)

white = False  # Start with black background
flipping = False
sent_start = False
fps_display = pyglet.window.FPSDisplay(window, samples=10)

# Background rectangle that covers the whole window
batch = pyglet.graphics.Batch()
background = pyglet.shapes.Rectangle(0, 0, window.width, window.height, color=(0, 0, 0), batch=batch)
background.draw()
window.flip()
screen_refresh_rate = 60
frame_duration = 1 / screen_refresh_rate
duration = 1 # run for 5 seconds
total_n_frames = screen_refresh_rate * duration

# Wait duration
wait_frames = 5
wait_duration = 5 * frame_duration

# --- Wait for Enter key ---
print("Waiting for ENTER key to start...")
while not keys[key.ENTER]:
    window.dispatch_events()
    window.clear()
    batch.draw()
    fps_display.draw()
    window.flip()
    time.sleep(0.01)

outlet.push_sample(["Start"])
for frame_num in range(total_n_frames):
    if (frame_num + 1) % 10 == 0:
        wait_time = time.perf_counter() + wait_duration
        while time.perf_counter() < wait_time:
            pass
    
    now = time.perf_counter()
    next_frame_time = now + frame_duration

    window.dispatch_events()
    background.color = (255, 255, 255) if white else (0, 0, 0)

    window.clear()
    batch.draw()
    fps_display.draw()
    window.flip()
    outlet.push_sample([str(white)])
    
    white = not white
    # Spin wait for next frame
    while time.perf_counter() < next_frame_time:
        pass

outlet.push_sample(["Stop"])
window.close()