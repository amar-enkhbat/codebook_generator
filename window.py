import time
import numpy as np
from psychopy import visual, event
from typing import Dict, List


class ScreenStimWindow:
    def __init__(self, objects: Dict[int, str]):
        self.objects = objects
        self.n_objs = len(objects)
        self.screen_warmup_duration = 1 # seconds
        self.refresh_rate = 60 # Hz
        
        # Screen (condition 4)
        self.win = visual.Window(size=(1920, 1080), fullscr=True, screen=1, units="pix", color='grey', waitBlanking=True, allowGUI=False)
        self.width, self.height = self.win.size
        
        self.sensor_box_size = 150
        self.stim_box_size = 150
        self.stim_box_space = (self.width - self.stim_box_size * 8) // 9
        self.stim_box_poss = [(self.stim_box_space + i*(self.stim_box_size + self.stim_box_space) - self.width // 2 + self.stim_box_size / 2, 0) for i in range(self.n_objs)]
        self.pictogram_poss = [(self.stim_box_space + i*(self.stim_box_size + self.stim_box_space) - self.width // 2 + self.stim_box_size / 2, 0) for i in range(self.n_objs)] # Psychopy decided that positions are determined as the center of the objects
        # Init stimulus window
        self.init_sensor()
        self.init_boxes()
        self.init_pictograms()
        # Init description text on screen
        self.init_text()
        
    def init_sensor(self):
        # Create a box on top left of screen for vsync sensor
        self.sensor_box = visual.Rect(self.win, width=self.sensor_box_size, height=self.sensor_box_size, pos=(-self.width / 2 + self.sensor_box_size / 2, self.height / 2 - self.sensor_box_size / 2), color='black')
        self.sensor_box.setAutoDraw(False)
        
    def init_boxes(self):
        # Boxes behind pictograms
        self.boxes = []
        for i in range(self.n_objs):
            box = visual.Rect(self.win, width=self.stim_box_size, height=self.stim_box_size, pos=self.stim_box_poss[i], units='pix', color='black')
            box.setAutoDraw(False)
            self.boxes.append(box)

    def init_pictograms(self):
        # Pictograms on top of boxes
        self.pictograms = []
        for i, img_path in enumerate(self.objects.values()):
            pictogram = visual.ImageStim(self.win, f'./icons/{img_path}.png', mask=None, units='pix', pos=self.pictogram_poss[i], size=self.stim_box_size)
            pictogram.setAutoDraw(False)
            self.pictograms.append(pictogram)

    def init_text(self):
        self.description_text = visual.TextStim(self.win, text="Hello World", pos=(0, 0), color='white', height=50)
        self.description_text.setAutoDraw(False)

    def fill_text(self, text: str):
        self.description_text.setText(text)
    
    def draw_text(self):
        self.description_text.draw()
        
    def fill_boxes(self, sequence: List[int]):
        for val, box in zip(sequence, self.boxes):
            if val == 1:
                box.fillColor = 'white'
            elif val == 0:
                box.fillColor = 'black'
            else:
                box.fillColor = 'grey'

    def fill_sensor_box(self, color: str):
        self.sensor_box.fillColor = color

    def draw_boxes(self):
        for box in self.boxes:
            box.draw()

    def draw_sensor_box(self):
        self.sensor_box.draw()

    def draw_pictograms(self):
        for pictogram in self.pictograms:
            pictogram.draw()
    
    def disable_stims(self):
        self.fill_sensor_box('grey')
        self.fill_boxes([2] * 8)
        self.draw_boxes()
        self.draw_sensor_box()
        self.win.flip()
    
    def hide_stims(self, hide_duration: float=1.0):
        for _ in range(int(hide_duration * self.refresh_rate)):  # 1 second of flips at 60Hz
            self.fill_sensor_box('grey')
            self.fill_boxes([2] * 8)
            self.draw_boxes()
            self.draw_sensor_box()
            self.win.flip()
            
    def screen_warmup(self, warmup_duration: float=1.0):
        """Flip screen at refresh rate for dt seconds to warmup.

        Args:
            dt (float): warmup duration (seconds)
        """
        for _ in range(int(warmup_duration * self.refresh_rate)):  # 1 second of flips at 60Hz
            self.fill_sensor_box('black')
            self.fill_boxes([0] * 8)
            self.draw_boxes()
            self.draw_sensor_box()
            self.draw_pictograms()
            self.win.flip()
            
    def reorder_pictograms(self, new_idc: List[int]):
        self.pictogram_poss = [self.pictogram_poss[i] for i in new_idc]  # NOTE: Could be indexing twice.
        self.init_pictograms()
    
    def default_order_pictograms(self):
        self.pictogram_poss = [(self.stim_box_space + i*(self.stim_box_size + self.stim_box_space) - self.width // 2 + self.stim_box_size / 2, 0) for i in range(self.n_objs)]
        self.init_pictograms()

    def screen_timing_test(self):
        """Do some test to measure screen timing."""
        self.win.recordFrameIntervals = True
        Turn on/off only boxes and sensor box
        for _ in range(5):
            end_time = time.perf_counter() + self.screen_warmup_duration
            self.fill_boxes([1] * 8)
            self.fill_sensor_box('white')
            self.draw_boxes()
            self.draw_sensor_box()
            self.win.flip()
            while time.perf_counter() < end_time:
                pass
            
            end_time = time.perf_counter() + self.screen_warmup_duration
            self.fill_boxes([0] * 8)
            self.fill_sensor_box('black')
            self.draw_boxes()
            self.draw_sensor_box()
            self.win.flip()
            while time.perf_counter() < end_time:
                pass

        # Turn on/off only pictograms
        for _ in range(5):
            end_time = time.perf_counter() + self.screen_warmup_duration
            self.fill_boxes([1] * 8)
            self.draw_boxes()
            self.draw_pictograms()
            self.win.flip()
            while time.perf_counter() < end_time:
                pass
            end_time = time.perf_counter() + self.screen_warmup_duration
            self.fill_boxes([1] * 8)
            self.draw_boxes()
            self.win.flip()
            while time.perf_counter() < end_time:
                pass
            
        # Reorder pictograms 5 times
        for _ in range(5):
            new_idc = list(np.random.permutation(np.arange(self.n_objs)).astype(int))
            self.reorder_pictograms(new_idc)
            self.init_pictograms()
            end_time = time.perf_counter() + self.screen_warmup_duration
            self.fill_boxes([1] * 8)
            self.draw_boxes()
            self.draw_pictograms()
            self.win.flip()
            while time.perf_counter() < end_time:
                pass

        # Test turn screen on/off
        for _ in range(5):
            self.hide_stims()
            self.screen_warmup()

        # Flip boxes for 5 times
        # 1 second on and 1 second off
        for _ in range(5):
            for _ in range(120):
                end_time = time.perf_counter() + 1 / self.refresh_rate
                self.fill_sensor_box('white')
                self.fill_boxes([1] * 8)
                self.draw_boxes()
                self.draw_sensor_box()
                self.draw_pictograms()
                self.win.flip()
                while time.perf_counter() < end_time:
                    pass
                end_time = time.perf_counter() + 1 / self.refresh_rate
                self.fill_sensor_box('black')
                self.fill_boxes([0] * 8)
                self.draw_boxes()
                self.draw_sensor_box()
                self.draw_pictograms()
                self.win.flip()
                while time.perf_counter() < end_time:
                    pass
        
        # Flip boxes for 5 seconds every frame
        for _ in range(5):
            for _ in range(60):
                end_time = time.perf_counter() + 1 / self.refresh_rate
                self.fill_sensor_box('white')
                self.fill_boxes([1] * 8)
                self.draw_boxes()
                self.draw_sensor_box()
                self.draw_pictograms()
                self.win.flip()
                while time.perf_counter() < end_time:
                    pass
            for _ in range(60):
                end_time = time.perf_counter() + 1 / self.refresh_rate
                self.fill_sensor_box('black')
                self.fill_boxes([0] * 8)
                self.draw_boxes()
                self.draw_sensor_box()
                self.draw_pictograms()
                self.win.flip()
                while time.perf_counter() < end_time:
                    pass

        # Log results
        n_dropped_frames = sum(np.array(self.win.frameIntervals) > 1.5 * (1/self.refresh_rate))
        print(f"Avg frame interval: {np.mean(self.win.frameIntervals)}")
        print(f"Max frame interval: {np.max(self.win.frameIntervals)}")
        print(f"Dropped frames: {n_dropped_frames}")
        print(f'Specified refresh rate: {self.refresh_rate}')
        print(f"Actual refresh rate: {self.win.getActualFrameRate()}")
        print(f'# of dropped frames: {n_dropped_frames}')
        self.win.recordFrameIntervals = False
        
        self.disable_stims()
        self.fill_text("Screen timing test completed. Press any key to close.")
        self.draw_text()
        self.win.flip()

        event.waitKeys()
        self.win.close()