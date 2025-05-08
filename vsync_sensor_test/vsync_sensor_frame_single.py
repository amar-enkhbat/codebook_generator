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
key_up_pressed = False
key_down_pressed = False

try:
    while True:
        window.dispatch_events()
        
        # Check for UP key press (only once when pressed)
        if keys[key.UP] and not key_up_pressed:
            background.color = black  # Black background
            window.clear()
            background.draw()
            window.flip()
            outlet.push_sample(['up'])
            key_up_pressed = True
            
        # Check for DOWN key press (only once when pressed)
        elif keys[key.DOWN] and not key_down_pressed:
            background.color = white  # White background
            window.clear()
            background.draw()
            window.flip()
            outlet.push_sample(['down'])
            key_down_pressed = True

        # Reset key states when keys are released
        if not keys[key.UP]:
            key_up_pressed = False
        if not keys[key.DOWN]:
            key_down_pressed = False

        time.sleep(0.01)  # Small delay to prevent CPU overload

except KeyboardInterrupt:
    window.close()
