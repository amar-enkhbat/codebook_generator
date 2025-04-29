from datetime import datetime
import pyglet
from pyglet import shapes
from pyglet.window import key
import pylsl
import time
import psutil, os
import gc
import csv

pyglet.options['debug_gl'] = False

class StimuliVisualization(pyglet.window.Window):
    def __init__(self, width=1920, height=1080, interval=1/120, fullscreen=False, vsync=True, *args, **kwargs):
        """Initialize the window and properties."""
        if fullscreen:
            display = pyglet.display.get_display()
            screen = display.get_default_screen()
            width, height = screen.width, screen.height
        super().__init__(width=width, height=height, caption="Visual Stimuli", fullscreen=fullscreen, vsync=vsync, *args, **kwargs)

        self.fps_display = pyglet.window.FPSDisplay(window=self, color=(0, 255, 0, 255))
        self.batch = pyglet.graphics.Batch()
        self.interval = interval

        self.background_color = (128, 128, 128, 255)
        self.background = shapes.Rectangle(0, 0, width, height, color=self.background_color, batch=self.batch)

        self.rect_height = 200
        self.rect_width = 200
        self.vsync_box_left = shapes.Rectangle(x=0, y=height-self.rect_height, width=self.rect_width, height=self.rect_height, color=(0, 0, 0, 255), batch=self.batch)
        self.vsync_box_right = shapes.Rectangle(x=width-self.rect_width, y=height-self.rect_height, width=self.rect_width, height=self.rect_height, color=(0, 0, 0, 255), batch=self.batch)

        self.description = pyglet.text.Label('Press ENTER to start', font_size=60, x=width//2, y=height//8, anchor_x='center', anchor_y='center', color=(0, 0, 0, 255), batch=self.batch)
        self.warmup_text = pyglet.text.Label('', font_size=40, x=width//2, y=height//2, anchor_x='center', anchor_y='center', color=(255, 0, 0, 255), batch=self.batch)

        self.sequence = [0] * 8
        self.timestamp = 0.0
        self.offset = 0.0
        self.should_flash = False

        self.dropped_frames = 0

        self.flash_events = []  # List to store (state, timestamp) tuples
        self.last_flash_state = False

        self.sequence_inlet = pylsl.resolve_byprop('name', 'SequenceStream', timeout=0.0)[0]
        self.sequence_inlet = pylsl.StreamInlet(self.sequence_inlet)

        info = pylsl.StreamInfo(name='ScreenSequenceStream', type='Marker', channel_count=8, channel_format=6)
        self.screen_sequence_outlet = pylsl.StreamOutlet(info)

        marker_info = pylsl.StreamInfo(name='PhaseMarkers', type='Markers', channel_count=1, channel_format=pylsl.cf_string)
        self.phase_marker_outlet = pylsl.StreamOutlet(marker_info)

        self.ctx = dict(
            pause=True,
            ctr=0,
            warmup=True,
            warmup_start=time.perf_counter(),
            warmup_frames=0,
            start_marker_sent=False
        )

    def hide_text(self):
        self.description.text = ''

    def fetch_sequence(self):
        try:
            sample, timestamp = self.sequence_inlet.pull_sample(timeout=0.0)
            if sample is not None:
                offset = self.sequence_inlet.time_correction()
                self.sequence = sample
                self.timestamp = timestamp + offset
                self.offset = offset
        except Exception as e:
            print(f"Error fetching sequence: {e}")

    def warmup_phase(self):
        elapsed = time.perf_counter() - self.ctx['warmup_start']
        if elapsed >= 5.0:
            self.ctx['warmup'] = False
            self.warmup_text.text = ''
            self.phase_marker_outlet.push_sample(['WarmupEnd'])
            if not self.ctx['start_marker_sent']:
                self.phase_marker_outlet.push_sample(['StartExperiment'])
                self.ctx['start_marker_sent'] = True
            print(f"Warmup phase ended. Total warmup frames: {self.ctx['warmup_frames']}")
        else:
            self.warmup_text.text = f"Warmup: {5 - int(elapsed)}s"

    def update(self, dt=0):
        start_time = time.perf_counter()

        if not self.ctx['pause']:
            if self.ctx['warmup']:
                self.warmup_phase()
            else:
                # if self.ctx['ctr'] == 2000:
                #     self.quit()

                self.fetch_sequence()
                self.should_flash = (sum(self.sequence) != 0)
                self.screen_sequence_outlet.push_sample(self.sequence)

                self.ctx['ctr'] += 1

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        if elapsed_time > (1/120):
            print(f"[Warning] Update frame took {elapsed_time*1000:.2f} ms (should be < 8 ms)")
            self.dropped_frames += 1

    def on_draw(self):
        self.clear()

        if self.ctx['warmup']:
            self.should_flash = not self.should_flash
            self.ctx['warmup_frames'] += 1

        color = (255, 255, 255, 255) if self.should_flash else (0, 0, 0, 255)
        self.vsync_box_left.color = color
        self.vsync_box_right.color = color

        self.batch.draw()
        self.fps_display.draw()

        if self.should_flash != self.last_flash_state:
            event = 'ON' if self.should_flash else 'OFF'
            self.flash_events.append((event, time.perf_counter()))
        self.last_flash_state = self.should_flash

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ENTER:
            print('Enter key was pressed. Pause:', self.ctx['pause'])
            self.hide_text()
            self.ctx['pause'] = not self.ctx['pause']
            if not self.ctx['pause']:
                gc.disable()
                self.ctx['warmup'] = True
                self.ctx['warmup_start'] = time.perf_counter()
                self.ctx['warmup_frames'] = 0
                self.ctx['start_marker_sent'] = False
                self.phase_marker_outlet.push_sample(['WarmupStart'])
            else:
                gc.enable()
        if symbol == key.ESCAPE:
            self.phase_marker_outlet.push_sample(['EndExperiment'])
            self.quit()

    def quit(self):
        gc.enable()
        print(f"Total dropped frames detected: {self.dropped_frames}")
        if self.flash_events:
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
    fps = 120
    interval = 1 / fps

    width, height = 1920, 1080
    fullscreen = True
    vsync = True

    config = pyglet.gl.Config(double_buffer=True, sample_buffers=1, samples=64)

    p = psutil.Process(os.getpid())
    p.nice(psutil.HIGH_PRIORITY_CLASS)

    demo = StimuliVisualization(width, height, interval, fullscreen=fullscreen, vsync=vsync, config=config)
    pyglet.clock.schedule(demo.update)
    pyglet.app.run()


if __name__ == "__main__":
    main()
