from datetime import datetime
import pyglet
from pyglet import shapes
from pyglet.window import key
import pylsl
import time

pyglet.options['debug_gl'] = True

class StimuliVisualization(pyglet.window.Window):
    def __init__(self, width=1920, height=1080, interval=120, fullscreen=False, vsync=False):
        """Initialize the window and properties."""
        # Adjust window size based on fullscreen
        if fullscreen:
            pyglet.options.dpi_scaling = 'scaled'
            pyglet.options.dpi_scaling = 'real'
            display = pyglet.display.get_display()
            screen = display.get_default_screen()
            fs_width, fs_height = screen.width, screen.height
            width, height = fs_width, fs_height
        else:
            pyglet.options.dpi_scaling = 'real'
        # Init window
        super().__init__(width=width, height=height, caption="Visual Stimuli", fullscreen=fullscreen, vsync=vsync)
        
        # Window properties
        self.fps_display = pyglet.window.FPSDisplay(window=self, color=(0, 255, 0, 255))
        self.batch = pyglet.graphics.Batch()
        self.interval = interval
        
        # Background properties
        self.background_color = (128, 128, 128, 255)
        self.background = shapes.Rectangle(0, 0, width, height, color=self.background_color, batch=self.batch)

        # Draw boxes for vsync sensors on top left and top right
        self.vsync_box_left = shapes.Rectangle(x=0, y=height-100, width=100, height=100, color=(0, 0, 0, 255), batch=self.batch)
        self.vsync_box_right = shapes.Rectangle(x=width-100, y=height-100, width=100, height=100, color=(0, 0, 0, 255), batch=self.batch)
        
        # Add description text on screen
        self.description = pyglet.text.Label('Press ENTER to start', font_size=60, x=width//2, y=height//8, anchor_x='center', anchor_y='center', color=(0, 0, 0, 255), batch=self.batch)
        
        # Sequence properties
        self.sequence = [0] * 8 # Initialize sequence with zeros
        self.timestamp = 0.0 # Initialize timestamp
        self.offset = 0.0 # Initialize offset
        # Log sensor results as csv file
        
        # Init LSL streams
        self.sequence_inlet = pylsl.resolve_byprop('name', 'SequenceStream', timeout=0.0)[0]
        self.sequence_inlet = pylsl.StreamInlet(self.sequence_inlet)
        
        info = pylsl.StreamInfo(name='ScreenSequenceStream', type='Marker', channel_count=8, channel_format=6)
        self.screen_sequence_outlet = pylsl.StreamOutlet(info)
        
        # Load sequences
        self.ctx = dict(
            pause = True,
            ctr = 0
        )

    def rect_off(self):
        """Flip the vsync sensor boxes."""
        if self.vsync_box_left.color == (255, 255, 255, 255):
            self.vsync_box_left.color = (0, 0, 0, 255)
            self.vsync_box_right.color = (0, 0, 0, 255)
            
    def rect_on(self):
        if self.vsync_box_left.color == (0, 0, 0, 255):
            self.vsync_box_left.color = (255, 255, 255, 255)
            self.vsync_box_right.color = (255, 255, 255, 255)
            
    def hide_text(self):
        """Hide the description text."""
        self.description.text = ''
        
    def fetch_sequence(self):
        """Fetch sequence from marker stream."""
        try:
            sample, timestamp = self.sequence_inlet.pull_sample(timeout=0.0)
            if sample is not None:
                offset = self.sequence_inlet.time_correction()
                self.sequence = sample
                self.timestamp = timestamp + offset
                self.offset = offset

        except Exception as e:
            print(f"Error fetching sequence: {e}")
            
    def update(self, dt):
        """Update the window every dt seconds."""
        if not self.ctx['pause']:
            start_time = time.perf_counter()
            # Fetch sequence
            self.fetch_sequence()
            if self.ctx['ctr'] == 1000:
                self.quit()
            
            
            # Turn on rectangle
            if sum(self.sequence) == 0:
                self.rect_off()
            else:
                self.rect_on()
                
            # Flip buffer
            self.flip()
            self.screen_sequence_outlet.push_sample(self.sequence)
            
            # Check if process can happen within a frame flip
            end_time = time.perf_counter()
            elapsed_time = end_time - start_time
            if elapsed_time > self.interval:
                print(f"Warning: Processing time exceeded frame interval: {elapsed_time:.4f} seconds")
                
            self.ctx['ctr'] += 1
                
        else:
            # Display text
            self.description.text = 'Press ENTER to start'
    
    def on_draw(self):
        self.clear()
        self.batch.draw()
        self.fps_display.draw()

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ENTER:
            print('Enter key was pressed. Pause:', self.ctx['pause'])
            self.hide_text()
            self.ctx['pause'] = not self.ctx['pause']
            
        if symbol == key.ESCAPE:
            self.quit()
            
    def quit(self):
        """Exit the application."""
        pyglet.app.exit()
        

def main():
    fps = 240
    interval = 1 / fps
    
    width, height = 1920, 1080
    fullscreen = True
    vsync = True
    demo = StimuliVisualization(width, height, interval, fullscreen=fullscreen, vsync=vsync)
    pyglet.clock.schedule_interval(demo.update, interval=interval) # NOTE: MD: Schedule is fast enough. Using the standard system clock. -/+5~15ms due to clock.
    # fps_display.draw()
    pyglet.app.run(interval=interval)
    
if __name__ == "__main__":
    main()