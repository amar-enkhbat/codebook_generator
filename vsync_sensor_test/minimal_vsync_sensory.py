from datetime import datetime
import pyglet
from pyglet import shapes
from pyglet.window import key
import time
import pandas as pd

pyglet.options['debug_gl'] = True

class StimuliVisualization(pyglet.window.Window):
    def __init__(self, width=1920, height=1080, interval=120, fullscreen=False, vsync=False):
        """Initialize the window and properties."""
        # Adjust window size based on fullscreen
        if fullscreen:
            display = pyglet.display.get_display()
            screen = display.get_default_screen()
            fs_width, fs_height = screen.width, screen.height
            width, height = fs_width, fs_height
            
        # Init window
        # config = pyglet.gl.Config(double_buffer=True)
        # super().__init__(width=width, height=height, caption="Visual Stimuli", fullscreen=fullscreen, vsync=vsync, config=config)
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
        self.results = []
        # Log sensor results as csv file
        
        # Load sequences
        self.ctx = dict(
            pause = True,
            on_ctr = 0,
        )

    def rect_off(self):
        """Flip the vsync sensor boxes."""
        self.vsync_box_left.color = (0, 0, 0, 255)
        self.vsync_box_right.color = (0, 0, 0, 255)
            
    def rect_on(self):
        self.vsync_box_left.color = (255, 255, 255, 255)
        self.vsync_box_right.color = (255, 255, 255, 255)
            
    def hide_text(self):
        """Hide the description text."""
        self.description.text = ''
            
    def update(self, dt):
        """Update the window every dt seconds."""
        if len(self.results) == 500:
            df = pd.DataFrame(self.results)
            df.to_csv('pyglet_results.csv', index=False)
            self.quit()
        if not self.ctx['pause']:
            # Wait every 10 results
            if len(self.results) % 10 == 0:
                self.description.text = 'Pause...'
                start_time = time.perf_counter()
                while time.perf_counter() <= start_time + 1:
                    self.description.text = 'Pause...'
            else:
                self.description.text = ''
            # Turn on rectangle
            if sum(self.sequence) == 0:
                self.rect_on()
                start_time = time.perf_counter()
                self.sequence = [1] * 8
                self.results.append({'timestamp': time.perf_counter(), 'value': 1})
                while time.perf_counter() < start_time + 0.1:
                    pass
            else:
                self.rect_off()
                start_time = time.perf_counter()
                self.sequence = [0] * 8
                self.results.append({'timestamp': time.perf_counter(), 'value': 0})
                while time.perf_counter() < start_time + 0.1:
                    pass
            self.flip()

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
            df = pd.DataFrame(self.results)
            df.to_csv('pyglet_results.csv', index=False)
            self.quit()
            
    def quit(self):
        """Exit the application."""
        pyglet.app.exit()
        

def main():
    fps = 60
    interval = 1 / (fps * 2)
    
    width, height = 1920, 1080
    fullscreen = True
    vsync = True
    demo = StimuliVisualization(width, height, interval, fullscreen=fullscreen, vsync=vsync)
    pyglet.clock.schedule_interval(demo.update, interval=interval) # NOTE: MD: Schedule is fast enough. Using the standard system clock. -/+5~15ms due to clock.
    pyglet.app.run()
    
if __name__ == "__main__":
    main()