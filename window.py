import time
import numpy as np
from psychopy import visual, event
from typing import Dict, List
from pylsl import StreamInfo, StreamOutlet
from utils import load_codebooks_block_2, load_codebooks_block_3, random_wait


class ScreenStimWindow:
    def __init__(self, objects: Dict[int, str]):
        self.objects = objects
        self.marker_ids = {
            'non_target': 100,
            'target': 110,
            'trial_start': 200,
            'trial_end': 210
        }
        self.quick_flash_wait_duration = (0.75, 1) # 0.75 to 1 seconds
        

        self.n_objs = len(objects)
        self.screen_warmup_duration = 1 # seconds
        self.refresh_rate = 60 # Hz
        
        # Screen (condition 4)
        self.win = visual.Window(size=(1920, 1080), winType='pyglet', fullscr=True, screen=1, units="pix", color='grey', waitBlanking=True, allowGUI=False)
        self.width, self.height = self.win.size
        self.refresh_rate = int(round(self.win.getActualFrameRate(nMaxFrames=300, nWarmUpFrames=60)))
        print('Calculated screen refresh rate:', self.refresh_rate)
        
        self.sensor_box_size = 80
        self.stim_box_size = 150
        self.stim_box_space = (self.width - self.stim_box_size * 8) // 9
        self.stim_box_poss = [(self.stim_box_space + i*(self.stim_box_size + self.stim_box_space) - self.width // 2 + self.stim_box_size / 2, 0) for i in range(self.n_objs)]
        self.pictogram_poss = [(self.stim_box_space + i*(self.stim_box_size + self.stim_box_space) - self.width // 2 + self.stim_box_size / 2, 0) for i in range(self.n_objs)] # Psychopy decided that positions are determined as the center of the objects
        # Init stimulus window
        self.init_sensor()
        self.init_boxes(n_boxes=self.n_objs)
        self.init_pictograms()
        # Init description text on screen
        self.init_text()

        # Init marker stream
        info = StreamInfo(name='ScreenMarkerStream', type='Marker', channel_count=1, channel_format=5, nominal_srate=0, source_id='screen_marker_stream_id')
        self.marker_outlet = StreamOutlet(info)

    def init_sensor(self):
        # Create a box on top left of screen for vsync sensor
        self.sensor_box = visual.Rect(self.win, width=self.sensor_box_size, height=self.sensor_box_size, pos=(-self.width / 2 + self.sensor_box_size / 2, self.height / 2 - self.sensor_box_size / 2), color='black', autoLog=False)
        self.sensor_box.setAutoDraw(False)
        
    def init_boxes(self, n_boxes: int):
        # Boxes behind pictograms
        if n_boxes == 1:
            self.stim_box_poss = [(0, 0)]
        self.boxes = []
        for i in range(n_boxes):
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
        for i in range(len(self.boxes)):
            if sequence[i] == 1:
                self.boxes[i].fillColor = 'white'
            elif sequence[i] == 0:
                self.boxes[i].fillColor = 'black'
            else:
                self.boxes[i].fillColor = 'grey'
            self.boxes[i].draw()
            
    def draw_pictograms(self):
        for pictogram in self.pictograms:
            pictogram.draw()

    def draw_sensor_box(self, color: str):
        self.sensor_box.fillColor = color
        self.sensor_box.draw()
    
    def disable_stims(self):
        self.draw_sensor_box('grey')
        self.draw_boxes([2] * 8)
        self.win.flip()
    
    def hide_stims(self, hide_duration: float=1.0):
        for _ in range(int(hide_duration * self.refresh_rate)):  # 1 second of flips at 60Hz
            self.disable_stims()
            
    def screen_warmup(self, duration: float=1.0, draw_pictograms=True):
        """Flip screen at refresh rate for dt seconds to warmup.

        Args:
            dt (float): warmup duration (seconds)
        """
        for _ in range(int(duration * self.refresh_rate)):  # 1 second of flips at 60Hz
            self.draw_sensor_box('black')
            self.draw_boxes([0] * 8)
            if draw_pictograms:
                self.draw_pictograms()
            self.win.flip()
            
    def reorder_pictograms(self, new_idc: List[int]):
        # self.pictogram_poss = [self.pictogram_poss[i] for i in new_idc]  # NOTE: Could be indexing twice.
        # self.init_pictograms()
        # new_idc = [new_idc.index(i) for i in range(len(new_idc))]
        new_poss = [self.pictogram_poss[i] for i in new_idc]
        for i in range(len(new_poss)):
            self.pictograms[i].pos = new_poss[i]
    
    def default_order_pictograms(self):
        new_poss = [(self.stim_box_space + i*(self.stim_box_size + self.stim_box_space) - self.width // 2 + self.stim_box_size / 2, 0) for i in range(self.n_objs)]
        for i in range(len(new_poss)):
            self.pictograms[i].pos = new_poss[i]

    def run_trial_erp(self, codebook: list, target_id: int, trial_id: int, n_stim_on_frames: int, n_stim_off_frames: int):
        """Run a single trial with multiple sequences on monitor"""
        self.marker_outlet.push_sample([self.marker_ids['trial_start'] + trial_id]) # Push trial start marker
        for sequence in codebook:
            is_target = sequence[target_id]
            for i in range(n_stim_on_frames):
                self.draw_sensor_box('white' if is_target == 1 else 'black')
                self.draw_boxes(sequence)
                self.draw_pictograms()
                self.win.flip()
                # If first sequence and is_target is equal to 1 push to target outlet
                if i == 0:
                    if is_target == 1:
                        self.marker_outlet.push_sample([self.marker_ids['target'] + target_id]) # Push target marker
                    elif is_target == 0:
                        self.marker_outlet.push_sample([self.marker_ids['non_target'] + target_id]) # Push non-target marker
                    else:
                        ValueError(f'Unknown target value: {is_target}')
            for i in range(n_stim_off_frames):
                self.draw_sensor_box('black')
                self.draw_boxes([0] * 8)
                self.draw_pictograms()
                self.win.flip()
        self.marker_outlet.push_sample([self.marker_ids['trial_end'] + trial_id]) # Push trial start marker

    def run_trial_cvep(self, codebook: list, target_id: int, trial_id: int):
        """Run a single trial with multiple sequences on monitor"""
        self.marker_outlet.push_sample([self.marker_ids['trial_start'] + trial_id]) # Push trial start marker
        for sequence in codebook:
            is_target = sequence[target_id]
            self.draw_sensor_box('white' if is_target == 1 else 'black')
            self.draw_boxes(sequence)
            self.draw_pictograms()
            self.win.flip()
            # If first sequence and is_target is equal to 1 push to target outlet
            if is_target == 1:
                self.marker_outlet.push_sample([self.marker_ids['target'] + target_id]) # Push target marker
            elif is_target == 0:
                self.marker_outlet.push_sample([self.marker_ids['non_target'] + target_id]) # Push non-target marker
            else:
                ValueError(f'Unknown target value: {is_target}')
                    
        self.marker_outlet.push_sample([self.marker_ids['trial_end'] + trial_id]) # Push trial start marker

        # Rest stims after trial
        self.draw_sensor_box('black')
        self.draw_boxes([0] * 8)
        self.draw_pictograms()
        self.win.flip()
        
    def run_trial_quick_flash(self, n_flashes: int, trial_id: int, n_stim_on_frames: int=1, ):
        """Run a quick flashing on a monitor"""
        # NOTE: n_stim_stim_on_frames is equal 1 to reflect the speed of cVEP
        # Start trial
        self.marker_outlet.push_sample([self.marker_ids['trial_start'] + trial_id]) # Push trial start marker
        for flash_id in range(n_flashes):
            self.draw_sensor_box('black')
            self.draw_boxes([0] * 8)
            self.win.flip()
            # Random wait between flashes (0.75~1s) == (45~60 frames)
            self.screen_warmup(duration=round(np.random.uniform(self.quick_flash_wait_duration[0], self.quick_flash_wait_duration[1]), 2))
            for i in range(n_stim_on_frames):
                self.draw_sensor_box('white')
                self.draw_boxes([1])
                self.win.flip()
                # If first sequence and is_target is equal to 1 push to target outlet
                if i == 0:
                    self.marker_outlet.push_sample([self.marker_ids['target'] + 0]) # Push target marker
            
        self.marker_outlet.push_sample([self.marker_ids['trial_end'] + trial_id]) # Push trial start marker

    def test_erp(self, n_trials: int=8):
        """Test Run ERP protocol"""
        new_idc = [1, 5, 0, 7, 2, 4, 3, 6]
        self.reorder_pictograms(new_idc)
        
        # run 10 trials with 1 warmup in-between
        codebook = load_codebooks_block_2()[0].astype(int).tolist()
        n_on_frames = 6 # 0.1 seconds
        n_off_frames = 9 # 0.15 seconds
        target_id = 0
        trial_run_times = []
        self.screen_warmup(duration=3)
        self.win.recordFrameIntervals = True
        for trial_id in range(n_trials):
            start_time = time.perf_counter()
            self.run_trial_erp(codebook, target_id=new_idc[target_id], trial_id=trial_id, n_stim_on_frames=n_on_frames, n_stim_off_frames=n_off_frames)
            elapsed_time = time.perf_counter() - start_time
            trial_run_times.append(elapsed_time)
            self.screen_warmup(duration=3)

        # Log results
        frame_intervals = np.array(self.win.frameIntervals)
        n_dropped_frames = sum(frame_intervals > 1.5 * (1/self.refresh_rate))
        print(f"Avg frame interval: {frame_intervals.mean()}")
        print(f"Min frame interval: {frame_intervals.min()}")
        print(f"Max frame interval: {frame_intervals.max()}")
        print(f"Dropped frames: {n_dropped_frames}")
        print(f'Specified refresh rate: {self.refresh_rate}')
        print(f'# of dropped frames: {n_dropped_frames}')
        self.win.recordFrameIntervals = False

        print('Trial run times:', trial_run_times)
        print('Mean trial run time (should be 12):', np.mean(trial_run_times))
    
    def test_cvep(self, n_trials: int=8):
        """Test Run CVEP protocol"""
        self.screen_warmup(duration=3)
        self.win.recordFrameIntervals = True
        # run 10 trials with 1 warmup in-between
        codebook = load_codebooks_block_3()[0].tolist()
        codebook = codebook[:720]

        trial_run_times = []
        for trial_id in range(n_trials):
            start_time = time.perf_counter()
            self.run_trial_cvep(codebook, target_id=0, trial_id=trial_id)
            elapsed_time = time.perf_counter() - start_time
            trial_run_times.append(elapsed_time)
            self.screen_warmup(duration=3)

        # Log results
        frame_intervals = np.array(self.win.frameIntervals)
        n_dropped_frames = sum(frame_intervals > 1.5 * (1/self.refresh_rate))
        print(f"Avg frame interval: {frame_intervals.mean()}")
        print(f"Min frame interval: {frame_intervals.min()}")
        print(f"Max frame interval: {frame_intervals.max()}")
        print(f'5 highest frame interval frame #:', np.argsort(frame_intervals)[-5:])
        print(f"Dropped frames: {n_dropped_frames}")
        print(f'Specified refresh rate: {self.refresh_rate}')
        print(f'# of dropped frames: {n_dropped_frames}')
        self.win.recordFrameIntervals = False

        print('Trial run times:', trial_run_times)
        print('Mean trial run time (should be 12):', np.mean(trial_run_times))
        
    def test_quick_flash(self, n_trials: int=8):
        """Test Run CVEP protocol"""
        # Init flash box with no pictograms
        del self.boxes
        self.init_boxes(n_boxes=1)
        
        self.screen_warmup(duration=3, draw_pictograms=False)
        self.win.recordFrameIntervals = True
        # run 10 trials with 1 warmup in-between

        trial_run_times = []
        for trial_id in range(n_trials):
            start_time = time.perf_counter()
            self.run_trial_quick_flash(n_flashes=12, trial_id=trial_id, n_stim_on_frames=1)
            elapsed_time = time.perf_counter() - start_time
            self.screen_warmup(3, draw_pictograms=False)
            trial_run_times.append(elapsed_time)

        # Log results
        frame_intervals = np.array(self.win.frameIntervals)
        n_dropped_frames = sum(frame_intervals > 1.5 * (1/self.refresh_rate))
        print(f"Avg frame interval: {frame_intervals.mean()}")
        print(f"Min frame interval: {frame_intervals.min()}")
        print(f"Max frame interval: {frame_intervals.max()}")
        print(f'5 highest frame interval frame #:', np.argsort(frame_intervals)[-5:])
        print(f"Dropped frames: {n_dropped_frames}")
        print(f'Specified refresh rate: {self.refresh_rate}')
        print(f'# of dropped frames: {n_dropped_frames}')
        self.win.recordFrameIntervals = False

        print('Trial run times:', trial_run_times)
        print('Mean trial run time (should be 12):', np.mean(trial_run_times))

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

def main():
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
    # Set sensor box to black
    for _ in range(300):
        screen.draw_sensor_box('black')
        screen.draw_text('Press any key to continue')
        screen.win.flip()
    event.waitKeys()
    screen.test_erp()
    # screen.test_cvep()
    # screen.test_quick_flash(n_trials=8)

    # new_idc = np.random.permutation(np.arange(8)).tolist()
    # print(new_idc)
    # print([screen.objects[i] for i in new_idc])
    # screen.reorder_pictograms(new_idc)
    # screen.test_erp(n_trials=1)

    # screen.default_order_pictograms()
    # print(list(objects.values()))
    # screen.test_erp(n_trials=1)

    # screen.test_erp()
    # screen.screen_timing_test()


if __name__ == '__main__':
    main()