from datetime import datetime
import pyglet
from pyglet import shapes
from pyglet.window import key
import requests


class StimuliVisualization(pyglet.window.Window):
    def __init__(self, width=1920, height=1080, interval=120, fullscreen=False, vsync=False):
        """Initialize the window and properties."""
        # Adjust window size based on fullscreen
        if fullscreen:
            pyglet.options.dpi_scaling = 'scaled'
            display = pyglet.display.get_display()
            screen = display.get_default_screen()
            fs_width, fs_height = screen.width, screen.height
            width, height = fs_width * 2, fs_height * 2
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
        
        # Sequence fetch URL
        self.url = "http://127.0.0.1:8000/get_sequence"
        
        # Background properties
        self.background_color = (128, 128, 128, 255)
        self.background = shapes.Rectangle(0, 0, width, height, color=self.background_color, batch=self.batch)
        
        # Circle properties
        self.circles = []
        if fullscreen:
            self.circle_spacing = 160
        else:
            self.circle_spacing = 80
        self.circle_radius = 75
        self.circle_init_coors = (width // 2 // 4, height // 2)
        self.circle_background_color = (0, 255, 0, 255) # "RG" elicited the strongest response
        self.circle_highlight_color = (255, 0, 0, 255) # # "RG" elicited the strongest response
        # self.circle_background_color = (0, 0, 0, 255) # "WB" elicited the strongest response
        # self.circle_highlight_color = (255, 255, 255, 255) # "WB" elicited the strongest response
        for i in range(self.n_lasers):
            self.circles.append(shapes.Circle(self.circle_init_coors[0] + (self.circle_spacing + self.circle_radius * 2) * i, self.circle_init_coors[1], radius=self.circle_radius, color=self.circle_background_color, batch=self.batch))
        
        # Add description text on screen
        self.description = pyglet.text.Label('Press ENTER to start', font_size=60, x=width//2, y=height//8, anchor_x='center', anchor_y='center', color=(0, 0, 0, 255), batch=self.batch)
        self.description_url = 'http://127.0.0.1:8000/get_description'
        
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
    
    def lasers_off(self):
        """Turn off all lasers."""
        for i in range(self.n_lasers):
            self.circles[i].color = self.circle_background_color
            
    def hide_text(self):
        """Hide the description text."""
        self.description.text = ''
        
    def fetch_sequence(self):
        """Fetch the sequence from the API."""
        try:
            response = requests.get(self.url)
            # if response is invalid or empty, do nothing
            if response.status_code == 200 and response.json():
                self.sequence = response.json()['sequence']
        except requests.exceptions.RequestException as e:
            # print(f"Error fetching sequence: {e}")
            return
    
    def fetch_description(self):
        """Fetch the description from the API."""
        try:
            response = requests.get(self.description_url)
            # if response is invalid or empty, do nothing
            if response.status_code == 200 and response.json():
                self.description.text = response.json()['description']
        except requests.exceptions.RequestException as e:
            # print(f"Error fetching description: {e}")
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
            # print(f'Update time: {(end_time - start_time).microseconds / 1000} ms')
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