from datetime import datetime
import pyglet
from pyglet import shapes
from pyglet.window import key
import pylsl
import serial


class StimuliVisualization(pyglet.window.Window):
    def __init__(self, width=1920, height=1080, interval=120, fullscreen=False, vsync=False):
        """Initialize the window and properties."""
        # Adjust window size based on fullscreen
        if fullscreen:
            pyglet.options.dpi_scaling = 'scaled'
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
        
        # Sequence properties
        self.n_lasers = 8
        self.sequence = [0] * self.n_lasers
        
        # Background properties
        self.background_color = (128, 128, 128, 255)
        self.background = shapes.Rectangle(0, 0, width, height, color=self.background_color, batch=self.batch)
        
        # Circle properties
        self.circles = []
        if fullscreen:
            self.circle_spacing = width // 9 // 2
        else:
            self.circle_spacing = 80
        self.circle_radius = 50
        self.circle_init_coors = (width // 2 // 4, height // 2)
        self.circle_background_color = (0, 255, 0, 255) # "RG" elicited the strongest response
        self.circle_highlight_color = (255, 0, 0, 255) # # "RG" elicited the strongest response
        # self.circle_background_color = (0, 0, 0, 255) # "WB" elicited the strongest response
        # self.circle_highlight_color = (255, 255, 255, 255) # "WB" elicited the strongest response
        for i in range(self.n_lasers):
            self.circles.append(shapes.Circle(self.circle_init_coors[0] + (self.circle_spacing + self.circle_radius * 2) * i, self.circle_init_coors[1], radius=self.circle_radius, color=self.circle_background_color, batch=self.batch))
        
        # Add description text on screen
        self.description = pyglet.text.Label('Press ENTER to start', font_size=60, x=width//2, y=height//8, anchor_x='center', anchor_y='center', color=(0, 0, 0, 255), batch=self.batch)
        
        # Init LSL streams
        self.marker_stream = None
        self.description_stream = None
        self.init_lsl_streams()
        
        # Init vsync sensors
        self.vsync_sensor = serial.Serial('COM6', 115200, timeout=1.0)
        # Draw boxes for vsync sensors on top left and top right
        self.vsync_box_left = shapes.Rectangle(0, height, width // 4, height // 4, color=(255, 255, 255, 255), batch=self.batch)
        self.vsync_box_right = shapes.Rectangle(width - width // 4, height, width // 4, height // 4, color=(255, 255, 255, 255), batch=self.batch)
        
        # Load sequences
        self.ctx = dict(
            pause = True,
        )
        
    def lasers_on(self):
        """Turn on the lasers based on the sequence."""
        for i, value in enumerate(self.sequence):
            if value == 1:
                self.circles[i].color = self.circle_highlight_color
            elif value == 0:
                self.circles[i].color = self.circle_background_color
    
    def init_lsl_streams(self):
        """Init marker and description lsl streams"""
        streams = pylsl.resolve_streams(wait_time=1.0)
        self.marker_stream = pylsl.resolve_byprop('name', 'LaserMarkerStream', timeout=1.0)[0]
        self.marker_stream = pylsl.StreamInlet(self.marker_stream)
        self.description_stream = pylsl.resolve_byprop('name', 'DescriptionStream', timeout=1.0)[0]
        self.description_stream = pylsl.StreamInlet(self.description_stream)
        
        
        
    
    def lasers_off(self):
        """Turn off all lasers."""
        for i in range(self.n_lasers):
            self.circles[i].color = self.circle_background_color
            
    def hide_text(self):
        """Hide the description text."""
        self.description.text = ''
        
    def fetch_sequence(self):
        """Fetch sequence from marker stream."""
        try:
            sample, _ = self.marker_stream.pull_sample(timeout=0.0)
            if sample:
                sample = sample[0]
                sample = eval(sample)
                self.sequence = sample
        except Exception as e:
            print(f"Error fetching sequence: {e}")
            return
    
    def fetch_description(self):
        """Fetch the description from description stream"""
        try:
            sample, _ = self.description_stream.pull_sample(timeout=0.0)
            if sample:
                self.description.text = sample[0]
        except Exception as e:
            print(f"Error fetching description: {e}")
            return
        
            
    def update(self, dt):
        """Update the window every dt seconds."""
        if not self.ctx['pause']:
            # self.hide_text()
            start_time = datetime.now()
            
            # Fetch sequence
            self.fetch_sequence()
            # Turn on lasers
            self.lasers_on()
            # Fetch description
            self.fetch_description()
            
            # Print update time in milliseconds
            end_time = datetime.now()
            print(f'Update time: {(end_time - start_time).microseconds / 1000} ms')
        else:
            # Display text
            self.lasers_off()
            self.description.text = 'Press ENTER to start'
    
    def on_draw(self):
        demo.clear()
        demo.batch.draw()
        self.fps_display.draw()

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ENTER:
            print('Enter key was pressed. Pause:', self.ctx['pause'])
            self.ctx['pause'] = not self.ctx['pause']
        
        if symbol == key.ESCAPE:
            pyglet.app.exit()
        

if __name__ == "__main__":
    FPS = 240 # fps shoud be double the 
    interval = 1 / FPS
    
    width, height = 1920, 1080
    demo = StimuliVisualization(width, height, interval, fullscreen=False, vsync=False)
    pyglet.clock.schedule_interval(demo.update, interval=interval) # NOTE: MD: Schedule is fast enough. Using the standard system clock. -/+5~15ms due to clock.
    # fps_display.draw()
    pyglet.app.run(interval=interval)