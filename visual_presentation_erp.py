from datetime import datetime
import numpy as np
import pyglet
from pyglet import shapes
from pyglet.window import key

from dareplane_utils.general.time import sleep_s


class StimuliVisualization(pyglet.window.Window):
    def __init__(self, width, height, interval, fullscreen=False, vsync=False):
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
        self.sequence_rate = 1 / self.interval
        self.n_lasers = 8
        
        # Background properties
        self.background_color = (128, 128, 128, 255)
        self.background = shapes.Rectangle(0, 0, width, height, color=self.background_color, batch=self.batch)
        
        # Circle properties
        self.circles = []
        self.circle_spacing = 160
        self.circle_radius = 75
        self.circle_init_coors = (width // 2 // 4, height//2)
        self.circle_background_color = (0, 255, 0, 255) # "RG" elicited the strongest response
        self.circle_highlight_color = (255, 0, 0, 255) # # "RG" elicited the strongest response
        # self.circle_background_color = (0, 0, 0, 255) # "WB" elicited the strongest response
        # self.circle_highlight_color = (255, 255, 255, 255) # "WB" elicited the strongest response
        
        for i in range(self.n_lasers):
            self.circles.append(shapes.Circle(self.circle_init_coors[0] + (self.circle_spacing + self.circle_radius * 2) * i, self.circle_init_coors[1], radius=self.circle_radius, color=self.circle_background_color, batch=self.batch))
        
        # Load sequences
        
        # sequences = np.random.choice([0, 1], size=self.n_lasers * 30).reshape(self.n_lasers, -1)
        # sequences = np.load('./codebook_1_henrich.npy')
        sequences = np.load('./codebooks/condition_2/codebook_obj_2.npy')
        # sequences = np.load('./codebook_3_cvep.npy')
        # sequences = np.load('./mseq_61_shift.npy')
        # sequences = np.load('./mgold_61_6521.npy')
        sequences = sequences[:self.n_lasers, :]
        self.ctx = dict(
            sequences = sequences,
            idx = 0,
            pause = True,
            highlight = True
        )
        
    def turn_on_lasers(self, sequence):
        for i, value in enumerate(sequence):
            if value == 1:
                self.circles[i].color = self.circle_highlight_color
            elif value == 0:
                self.circles[i].color = self.circle_background_color
    
    def turn_off_lasers(self):
        for i in range(self.n_lasers):
            self.circles[i].color = self.circle_background_color
            
    def update(self, dt):
        if not self.ctx['pause']:
            start_time = datetime.now()
            
            # "Turn on" lasers
            if self.ctx['highlight']:
                sequence = self.ctx['sequences'][:, self.ctx['idx']]
                self.turn_on_lasers(sequence)
                sleep_s(0.150) # nsteps 
                self.ctx['highlight'] = False
                self.ctx['idx'] = (self.ctx['idx'] + 1)
                # Reset counter
                if self.ctx['idx'] == self.ctx['sequences'].shape[1]:
                    self.ctx['pause'] = True
                    self.ctx['idx'] = 0

            # "Turn off" lasers
            elif not self.ctx['highlight']:
                self.turn_off_lasers()
                sleep_s(0.100, nsteps=10) # nsteps
                self.ctx['highlight'] = True
                
            stop_time = datetime.now()
            delta = stop_time - start_time
            print(f'Highlight: {self.ctx["highlight"]}, Duration (ms): {delta.microseconds / 1e3}')
    
    def on_draw(self):
        # if not self.ctx['pause']:
        demo.clear()
        demo.batch.draw()
        self.fps_display.draw()

    def on_key_press(self, symbol, modifiers):
        print(self.ctx['pause'])
        if symbol == key.ENTER:
            print('Enter key was pressed.')
            self.ctx['pause'] = not self.ctx['pause']
        
        if symbol == key.ESCAPE:
            pyglet.app.exit()
        

if __name__ == "__main__":
    FPS = 480 # fps shoud be double the 
    interval = 1 / FPS
    
    width, height = 1920, 1080
    demo = StimuliVisualization(width, height, interval, fullscreen=True, vsync=False)
    pyglet.clock.schedule_interval(demo.update, interval=interval) # NOTE: MD: Schedule is fast enough. Using the standard system clock. -/+5~15ms due to clock.
    # fps_display.draw()
    pyglet.app.run(interval=interval)