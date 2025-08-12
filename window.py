import time
import numpy as np
from psychopy import visual, event
from typing import Dict, List
from pylsl import StreamInfo, StreamOutlet
from utils import load_codebooks_block_2, load_codebooks_block_3


class ScreenStimWindow:
    def __init__(self, objects: Dict[int, str]):
        self.objects = objects
        self.n_objs = len(objects)
        self.screen_warmup_duration = 1 # seconds
        self.refresh_rate = 60 # Hz
        
        # Screen (condition 4)
        self.win = visual.Window(size=(1920, 1080), winType='pyglet', fullscr=True, screen=1, units="pix", color='grey', waitBlanking=True, allowGUI=False)
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

        # Init marker stream
        info = StreamInfo(name='MarkerStream', type='Marker', channel_count=1, channel_format=4, nominal_srate=0, source_id='marker_stream_id')
        self.marker_outlet = StreamOutlet(info)

    def init_sensor(self):
        # Create a box on top left of screen for vsync sensor
        self.sensor_box = visual.Rect(self.win, width=self.sensor_box_size, height=self.sensor_box_size, pos=(-self.width / 2 + self.sensor_box_size / 2, self.height / 2 - self.sensor_box_size / 2), color='black', autoLog=False)
        self.sensor_box.setAutoDraw(False)
        
    def init_boxes(self):
        # Boxes behind pictograms
        self.boxes = []
        for i in range(self.n_objs):
            box = visual.Rect(self.win, width=self.stim_box_size, height=self.stim_box_size, pos=self.stim_box_poss[i], units='pix', color='black', autoLog=False)
            box.setAutoDraw(False)
            self.boxes.append(box)

    def init_pictograms(self):
        # Pictograms on top of boxes
        self.pictograms = []
        for i, img_path in enumerate(self.objects.values()):
            pictogram = visual.ImageStim(self.win, f'./icons/{img_path}.png', mask=None, units='pix', pos=self.pictogram_poss[i], size=self.stim_box_size, autoLog=False)
            pictogram.setAutoDraw(False)
            self.pictograms.append(pictogram)

    def init_text(self):
        self.description_text = visual.TextStim(self.win, text="Hello World", pos=(0, 0), color='white', height=50, autoLog=False)
        self.description_text.setAutoDraw(False)

    def draw_text(self, text: str):
        self.description_text.setText(text)
        self.description_text.draw()
        
        
    def draw_boxes(self, sequence: List[int]):
        # for val, box in zip(sequence, self.boxes):
        for i in range(len(sequence)):
            if sequence[i] == 1:
                self.boxes[i].fillColor = 'white'
            elif sequence[i] == 0:
                self.boxes[i].fillColor = 'black'
            else:
                self.boxes[i].fillColor = 'grey'
            self.boxes[i].draw()
            self.pictograms[i].draw()

    def draw_sensor_box(self, color: str):
        self.sensor_box.fillColor = color
        self.sensor_box.draw()
    
    def disable_stims(self):
        self.draw_sensor_box('grey')
        self.draw_boxes([2] * 8)
        self.win.flip()
    
    def hide_stims(self, hide_duration: float=1.0):
        for _ in range(int(hide_duration * self.refresh_rate)):  # 1 second of flips at 60Hz
            self.draw_sensor_box('grey')
            self.draw_boxes([2] * 8)
            self.win.flip()
            
    def screen_warmup(self, duration: float=1.0):
        """Flip screen at refresh rate for dt seconds to warmup.

        Args:
            dt (float): warmup duration (seconds)
        """
        for _ in range(int(duration * self.refresh_rate)):  # 1 second of flips at 60Hz
            self.draw_sensor_box('black')
            self.draw_boxes([0] * 8)
            self.win.flip()
            
    def reorder_pictograms(self, new_idc: List[int]):
        self.pictogram_poss = [self.pictogram_poss[i] for i in new_idc]  # NOTE: Could be indexing twice.
        self.init_pictograms()
    
    def default_order_pictograms(self):
        self.pictogram_poss = [(self.stim_box_space + i*(self.stim_box_size + self.stim_box_space) - self.width // 2 + self.stim_box_size / 2, 0) for i in range(self.n_objs)]
        self.init_pictograms()

    def run_trial_erp(self, codebook: list, target_obj_idx: int, trial_id: int, n_stim_on_frames: int=6, n_stim_off_frames: int=9):
        """Run a single trial with multiple sequences on monitor"""
        self.screen_warmup(duration=1)
        print(trial_id, target_obj_idx)
        self.marker_outlet.push_sample([200 + trial_id]) # Push trial start marker
        for sequence in codebook:
            for i in range(n_stim_on_frames):
                is_target = sequence[target_obj_idx]
                self.draw_sensor_box('white' if is_target == 1 else 'black')
                self.draw_boxes(sequence)
                self.win.flip()
                # If first sequence and is_target is equal to 1 push to target outlet
                if i == 0:
                    if is_target == 1:
                        self.marker_outlet.push_sample([111 + target_obj_idx]) # Push target marker
                    elif is_target == 0:
                        self.marker_outlet.push_sample([101 + target_obj_idx]) # Push non-target marker
                    else:
                        ValueError(f'Unknown target value: {is_target}')
            for i in range(n_stim_off_frames):
                self.draw_sensor_box('black')
                self.draw_boxes([0] * 8)
                self.win.flip()
                
    def run_trial_cvep(self, codebook: list, target_obj_idx: int):
        """Run a single trial with multiple sequences on monitor"""
        self.screen_warmup()
        for sequence in codebook:
            self.draw_sensor_box('white' if sequence[target_obj_idx] == 1 else 'black')
            self.draw_boxes(sequence)
            self.win.flip()
            self.sequence_outlet.push_sample(sequence)
        self.draw_sensor_box('black')
        self.draw_boxes([0] * 8)
        self.win.flip()

    def test_erp(self):
        """Test Run ERP protocol"""
        self.win.recordFrameIntervals = True
        # run 10 trials with 1 warmup in-between
        codebook = load_codebooks_block_2()[0]
        n_on_frames = 6 # 0.1 seconds
        n_off_frames = 9 # 0.15 seconds
        for trial_id in range(10):
            self.run_trial_erp(codebook, target_obj_idx=0, trial_id=trial_id, n_stim_on_frames=n_on_frames, n_stim_off_frames=n_off_frames)
            time.sleep(1)
    
    def test_cvep(self):
        """Test Run CVEP protocol"""
        self.win.recordFrameIntervals = True
        # run 10 trials with 1 warmup in-between
        codebook = load_codebooks_block_3()[0]
        codebook = list(codebook)
        for _ in range(10):
            self.run_trial_cvep(codebook, target_obj_idx=0)
            time.sleep(1)

    def screen_timing_test(self):
        """Do some test to measure screen timing."""
        self.win.recordFrameIntervals = True
        # Turn on/off only boxes and sensor box
        for _ in range(5):
            end_time = time.perf_counter() + self.screen_warmup_duration
            self.draw_boxes([1] * 8)
            self.draw_sensor_box('white')
            self.win.flip()
            while time.perf_counter() < end_time:
                pass
            
            end_time = time.perf_counter() + self.screen_warmup_duration
            self.draw_boxes([0] * 8)
            self.draw_sensor_box('black')
            self.win.flip()
            while time.perf_counter() < end_time:
                pass
            
        # Reorder pictograms 5 times
        for _ in range(5):
            new_idc = list(np.random.permutation(np.arange(self.n_objs)).astype(int))
            self.reorder_pictograms(new_idc)
            self.init_pictograms()
            end_time = time.perf_counter() + self.screen_warmup_duration
            self.draw_boxes([1] * 8)
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
                self.draw_sensor_box('white')
                self.draw_boxes([1] * 8)
                self.win.flip()
                while time.perf_counter() < end_time:
                    pass
                end_time = time.perf_counter() + 1 / self.refresh_rate
                self.draw_sensor_box('black')
                self.draw_boxes([0] * 8)
                self.win.flip()
                while time.perf_counter() < end_time:
                    pass
        
        # Flip boxes for 5 seconds every frame
        for _ in range(5):
            for _ in range(60):
                end_time = time.perf_counter() + 1 / self.refresh_rate
                self.draw_sensor_box('white')
                self.draw_boxes([1] * 8)
                self.win.flip()
                while time.perf_counter() < end_time:
                    pass
            for _ in range(60):
                end_time = time.perf_counter() + 1 / self.refresh_rate
                self.draw_sensor_box('black')
                self.draw_boxes([0] * 8)
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
        self.draw_text("Screen timing test completed. Press any key to close.")
        self.win.flip()

        event.waitKeys()
        self.win.close()

if __name__ == '__main__':
    from window import ScreenStimWindow

    objects = {
        0: 'bottle', 
        1: 'bandage', 
        2: 'remote', 
        3: 'can', 
        4: 'candle', 
        5: 'box', 
        6: 'book', 
        7: 'cup'
    }
    screen = ScreenStimWindow(objects)
    _ = input('Press any key to start test\n')
    screen.test_erp()
    # screen.test_cvep()
    # screen.screen_timing_test()