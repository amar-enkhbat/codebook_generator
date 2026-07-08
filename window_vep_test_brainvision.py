import time
import numpy as np
from psychopy import visual, event
from typing import Dict, List
from rusocsci import buttonbox
from utils import load_codebooks_block_2, load_codebooks_block_3, random_wait

# BrainVision trigger codes (1-255, single byte). Trial start/end encode the
# target object id (0-7); flash markers distinguish target vs non-target flashes.
TRIAL_START_CODE_BASE = 100  # 100-107 -> trial start, target_id = code - 100
TRIAL_END_CODE_BASE = 200    # 200-207 -> trial end, target_id = code - 200
TARGET_FLASH_CODE = 1
NONTARGET_FLASH_CODE = 2


class ScreenStimWindow:
    def __init__(self, objects: Dict[int, str]):
        self.objects = objects
        self.quick_flash_wait_duration = (0.75, 1) # 0.75 to 1 seconds


        self.n_objs = len(objects)
        self.screen_warmup_duration = 1 # seconds
        self.refresh_rate = 60 # Hz

        # Screen (condition 4)
        self.win = visual.Window(size=(1920, 1080), winType='pyglet', fullscr=True, screen=1, units="pix", color='grey', waitBlanking=True, allowGUI=False)
        # self.win = visual.Window(size=(2560, 1440), winType='pyglet', fullscr=True, screen=1, units="pix", color='grey', waitBlanking=True, allowGUI=False)
        self.width, self.height = self.win.size
        self.actual_refresh_rate = int(round(self.win.getActualFrameRate(nMaxFrames=300, nWarmUpFrames=60)))
        print(f'Calculated screen refresh rate (should be {self.refresh_rate}):', self.actual_refresh_rate)


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

        # Init BrainVision hardware trigger box (sends 1-255 codes, recorded
        # sample-accurately by the amplifier's digital trigger input).
        # Port hardcoded because rusocsci's auto-detect (registry scan) is
        # unreliable here even though Windows/Device Manager sees the device fine.
        self.bb = buttonbox.Buttonbox(port='COM6')

    def send_marker(self, code: int):
        """Send a hardware trigger code (1-255) to BrainVision, then reset to 0."""
        self.bb.sendMarker(val=code)
        self.bb.sendMarker(val=0)

    def init_sensor(self):
        # Create a box on top left of screen for vsync sensor
        self.sensor_box = visual.Rect(self.win, width=self.sensor_box_size, height=self.sensor_box_size, pos=(-self.width / 2 + self.sensor_box_size / 2, self.height / 2 - self.sensor_box_size / 2), color='black', autoLog=False)
        self.sensor_box.setAutoDraw(False)

    def init_boxes(self, n_boxes: int):
        # Boxes behind pictograms
        if n_boxes == 1:
            self.stim_box_poss = [(0, 0)]
        else:
            self.stim_box_poss = [(self.stim_box_space + i*(self.stim_box_size + self.stim_box_space) - self.width // 2 + self.stim_box_size / 2, 0) for i in range(self.n_objs)]
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
        new_idc = [new_idc.index(i) for i in range(len(new_idc))]
        new_poss = [self.pictogram_poss[i] for i in new_idc]
        for i in range(len(new_poss)):
            self.pictograms[i].pos = new_poss[i]

    def default_order_pictograms(self):
        new_poss = [(self.stim_box_space + i*(self.stim_box_size + self.stim_box_space) - self.width // 2 + self.stim_box_size / 2, 0) for i in range(self.n_objs)]
        for i in range(len(new_poss)):
            self.pictograms[i].pos = new_poss[i]

    def run_trial_erp(self, codebook: list, target_id: int, trial_id: int, run_id: int, n_stim_on_frames: int, n_stim_off_frames: int):
        """Run a single trial with multiple sequences on monitor"""

        self.send_marker(TRIAL_START_CODE_BASE + target_id) # Trial start marker (encodes target_id)
        for seq_id, sequence in enumerate(codebook):
            is_target = sequence[target_id]
            for i in range(n_stim_on_frames):
                self.draw_sensor_box('white' if is_target == 1 else 'black')
                self.draw_boxes(sequence)
                self.draw_pictograms()
                self.win.flip()
                # If first frame of the on-burst, send a target/non-target flash marker
                if i == 0:
                    self.send_marker(TARGET_FLASH_CODE if is_target == 1 else NONTARGET_FLASH_CODE)
            for i in range(n_stim_off_frames):
                self.draw_sensor_box('black')
                self.draw_boxes([0] * 8)
                self.draw_pictograms()
                self.win.flip()
        self.send_marker(TRIAL_END_CODE_BASE + target_id) # Trial end marker (encodes target_id)

    def run_trial_cvep(self, codebook: list, target_id: int, trial_id: int, run_id: int):
        """Run a single trial with multiple sequences on monitor"""
        self.send_marker(TRIAL_START_CODE_BASE + target_id) # Trial start marker (encodes target_id)
        for seq_id, sequence in enumerate(codebook):
            is_target = sequence[target_id]
            self.draw_sensor_box('white' if is_target == 1 else 'black')
            self.draw_boxes(sequence)
            self.draw_pictograms()
            self.win.flip()
            self.send_marker(TARGET_FLASH_CODE if is_target == 1 else NONTARGET_FLASH_CODE)

        self.send_marker(TRIAL_END_CODE_BASE + target_id) # Trial end marker (encodes target_id)

        # Rest stims after trial
        self.draw_sensor_box('black')
        self.draw_boxes([0] * 8)
        self.draw_pictograms()
        self.win.flip()

    def test_erp(self, n_trials: int=8):
        """Test Run ERP protocol"""
        # Load codebook
        codebooks = load_codebooks_block_2().astype(int).tolist()

        n_on_frames = 6 # 0.1 seconds
        n_off_frames = 9 # 0.15 seconds
        trial_run_times = []
        self.screen_warmup(duration=3)
        self.win.recordFrameIntervals = True
        for trial_id in range(n_trials):
            target_id = np.random.randint(0, self.n_objs) # Get a random target
            start_time = time.perf_counter()
            self.run_trial_erp(codebooks[target_id], target_id=target_id, trial_id=trial_id, run_id=999, n_stim_on_frames=n_on_frames, n_stim_off_frames=n_off_frames)
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
        print(f"Dropped frames: {n_dropped_frames} out of {len(frame_intervals)}")
        print(f'Specified refresh rate: {self.refresh_rate}')
        print(f'# of dropped frames: {n_dropped_frames}')
        self.win.recordFrameIntervals = False

        print('Trial run times:', trial_run_times)
        print('Mean trial run time (should be 12):', np.mean(trial_run_times))

    def test_vep(self, n_trials: int=8):
        """Test Run ERP protocol"""
        # Create new codebook with only one target
        sequence_length = 600 # roughly 60 seconds
        print(sequence_length)
        sequence = []
        while len(sequence) < sequence_length:
            run_length = np.random.randint(5, 11)
            zero_run = np.zeros(run_length, dtype=np.uint8).tolist()
            sequence.extend(zero_run)
            sequence.append(1)
        sequence = np.array(sequence)[:sequence_length]

        codebooks = np.zeros((8, sequence_length, 8), dtype=np.int8)
        codebooks[0, :, 0] = sequence
        print(codebooks.shape)
        codebooks = codebooks.tolist()
        target_id = 0

        n_on_frames = 1 # 0.01666 seconds
        n_off_frames = 6 # 0.1 seconds

        print('duration:', sequence.sum() * n_on_frames/60 - (sequence - 1).sum() * n_off_frames/60)
        trial_run_times = []
        self.screen_warmup(duration=3)
        self.win.recordFrameIntervals = True
        for trial_id in range(n_trials):
            start_time = time.perf_counter()
            self.run_trial_erp(codebooks[target_id], target_id=target_id, trial_id=trial_id, run_id=999, n_stim_on_frames=n_on_frames, n_stim_off_frames=n_off_frames)
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
        print(f"Dropped frames: {n_dropped_frames} out of {len(frame_intervals)}")
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
            self.run_trial_cvep(codebook, target_id=0, trial_id=trial_id, run_id=999)
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
        print(f"Dropped frames: {n_dropped_frames} out of {len(frame_intervals)}")
        print(f'Specified refresh rate: {self.refresh_rate}')
        print(f'# of dropped frames: {n_dropped_frames}')
        self.win.recordFrameIntervals = False

        print('Trial run times:', trial_run_times)
        print('Mean trial run time (should be 12.016):', np.mean(trial_run_times))

    def test_cvep_vep(self, n_trials: int=8):
        """Test Run CVEP protocol"""
        self.screen_warmup(duration=3)
        self.win.recordFrameIntervals = True
        # run 10 trials with 1 warmup in-between
        codebook = load_codebooks_block_3()[0]
        print(codebook.shape)
        codebook[:, 1:] = 0

        trial_run_times = []
        for trial_id in range(n_trials):
            start_time = time.perf_counter()
            self.run_trial_cvep(codebook, target_id=0, trial_id=trial_id, run_id=999)
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
        print(f"Dropped frames: {n_dropped_frames} out of {len(frame_intervals)}")
        print(f'Specified refresh rate: {self.refresh_rate}')
        print(f'# of dropped frames: {n_dropped_frames}')
        self.win.recordFrameIntervals = False

        print('Trial run times:', trial_run_times)
        print('Mean trial run time (should be 12.016):', np.mean(trial_run_times))


def main():
    objects = {
        0: 'can',
        1: 'bandage',
        2: 'remote',
        3: 'bottle',
        4: 'candle',
        5: 'box',
        6: 'book',
        7: 'cup'
    }
    screen = ScreenStimWindow(objects)
    # Set sensor box to black
    screen.screen_warmup(3)
    screen.draw_sensor_box('black')
    screen.draw_text('Press any key to continue\nVEP')
    screen.init_boxes(1)
    screen.win.flip()
    event.waitKeys()
    for _ in range(5):
        screen.screen_warmup(3)
        screen.test_vep(1)
        screen.screen_warmup(10)

    screen.screen_warmup(3)
    screen.draw_sensor_box('black')
    screen.draw_text('Press any key to continue\ncVEP')
    screen.init_boxes(1)
    screen.win.flip()
    event.waitKeys()
    for _ in range(10):
        screen.screen_warmup(3)
        screen.test_cvep_vep(1)



if __name__ == '__main__':
    main()
