import pyglet
from pyglet import shapes
from pyglet.window import key
from datetime import datetime
import time
import gc
import csv
import psutil
from pylsl import StreamInfo, StreamOutlet

pyglet.options['debug_gl'] = False

class StimuliVisualization(pyglet.window.Window):
    def __init__(self, width=2560, height=1440, fullscreen=False, vsync=True):
        super().__init__(width=width, height=height, caption="Visual Stimuli", fullscreen=fullscreen, vsync=vsync)

        self.batch = pyglet.graphics.Batch()
        self.background_color = (128, 128, 128, 255)
        self.background = shapes.Rectangle(0, 0, width, height, color=self.background_color, batch=self.batch)

        self.rect_height = 200
        self.rect_width = 200
        self.vsync_box_left = shapes.Rectangle(x=0, y=height-self.rect_height, width=self.rect_width, height=self.rect_height, color=(0, 0, 0, 255), batch=self.batch)
        self.vsync_box_right = shapes.Rectangle(x=width-self.rect_width, y=height-self.rect_height, width=self.rect_width, height=self.rect_height, color=(0, 0, 0, 255), batch=self.batch)

        self.description = pyglet.text.Label('Press ENTER to start', font_size=60, x=width//2, y=height//8, anchor_x='center', anchor_y='center', color=(0, 0, 0, 255), batch=self.batch)

        self.flash_state = False
        self.frame_counter = 0
        self.flash_counter = 0

        self.fps = 120
        self.flash_on_frames = int(0.1 * self.fps)  # 100 ms
        self.flash_off_frames = int(0.15 * self.fps)  # 150 ms
        self.flash_cycle_frames = self.flash_on_frames + self.flash_off_frames
        self.rest_frames = self.fps  # 1s wait after every 5 flashes

        self.total_flash_phases = 5
        self.in_rest_period = False

        self.flash_events = []

        info = StreamInfo(name='ScreenSequenceStream', type='Marker', channel_count=1, channel_format='string', source_id='screen_seq')
        self.lsl_outlet = StreamOutlet(info)

        self.ctx = dict(
            pause=True,
            flash_index=0,
            frame_in_cycle=0
        )

    def hide_text(self):
        self.description.text = ''

    def update(self, dt):
        if self.ctx['pause']:
            return

        if self.in_rest_period:
            self.ctx['frame_in_cycle'] += 1
            if self.ctx['frame_in_cycle'] >= self.rest_frames:
                self.ctx['frame_in_cycle'] = 0
                self.flash_counter = 0
                self.in_rest_period = False
            return

        self.ctx['frame_in_cycle'] += 1

        if self.ctx['frame_in_cycle'] < self.flash_on_frames:
            self.flash_state = True
        elif self.ctx['frame_in_cycle'] < self.flash_cycle_frames:
            self.flash_state = False
        else:
            self.ctx['frame_in_cycle'] = 0
            self.flash_counter += 1
            if self.flash_counter >= self.total_flash_phases:
                self.in_rest_period = True

    def on_draw(self):
        self.clear()

        color = (255, 255, 255, 255) if self.flash_state else (0, 0, 0, 255)
        self.vsync_box_left.color = color
        self.vsync_box_right.color = color
        self.batch.draw()

        # Log event if changed
        timestamp = time.perf_counter()
        state_str = 'ON' if self.flash_state else 'OFF'
        self.flash_events.append((state_str, timestamp))
        self.lsl_outlet.push_sample([state_str])

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ENTER:
            self.hide_text()
            self.ctx['pause'] = not self.ctx['pause']
            if not self.ctx['pause']:
                gc.disable()
                self.ctx['frame_in_cycle'] = 0
                self.flash_counter = 0
                self.in_rest_period = False
            else:
                gc.enable()
        if symbol == key.ESCAPE:
            self.quit()

    def quit(self):
        gc.enable()
        print(f"Logged {len(self.flash_events)} flash events.")
        filename = f"flash_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Flash State', 'Timestamp (seconds)'])
            for event, t in self.flash_events:
                writer.writerow([event, f"{t:.9f}"])
        print(f"Events saved to {filename}")
        pyglet.app.exit()


def main():
    p = psutil.Process()
    p.nice(psutil.HIGH_PRIORITY_CLASS)

    demo = StimuliVisualization(fullscreen=True, vsync=True)
    # pyglet.clock.schedule_interval(demo.update, 1/120.0)
    pyglet.clock.schedule(demo.update)
    pyglet.app.run()


if __name__ == "__main__":
    main()
