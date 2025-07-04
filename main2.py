import glob
import serial
import time
import datetime
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pylsl import StreamInfo, StreamOutlet
import logging
from utils import perf_sleep
from psychopy import sound, visual, prefs
prefs.hardware['audioLib'] = ['PTB']
# prefs.hardware['audioDevice'] = 'OUT 3-4 (BEHRINGER X-AIR)'
prefs.hardware['audioDevice'] = 'Speakers (Realtek(R) Audio)'
prefs.hardware['audioDevice'] = 'Speakers (High Definition Audio Device)'

logger = logging.getLogger(__name__)

class StimController:
    def __init__(self):
        self.codebooks = []
        self.n_objs = 8
        self.obj_names = ['bottle', 'bandage', 'remote', 'can', 'candle', 'box', 'book', 'cup']
        
        # Mode
        self.mode = 'screen'

        # Connect to teensy
        self.teensy = None
        self.connect_teensy()

        # Connect button box
        self.button_box = None
        self.connect_button_box()
        
        # Start marker stream
        self.sequence_outlet = None
        self.init_sequence_lsl_stream()
        # Start marker stream
        self.marker_outlet = None
        self.init_marker_lsl_stream()

        self.trial_duration = 12 # Except condition 1 where it is 24 seconds
        self.trial_rest_duration = 2
        self.trial_screen_warmup_duration = 1
        self.n_trials = self.n_objs

        # Experimental setup for ERP
        self.erp_sequence_on_duration = 0.1
        self.erp_sequence_off_duration = 0.15
        self.erp_sequence_duration = self.erp_sequence_on_duration + self.erp_sequence_off_duration
        self.cue_duration = 6

        # Experimental setup for c-VEP
        self.cvep_sequence_on_duration = 1 / 60
        self.cvep_sequence_off_duration = 0
        self.cvep_sequence_duration = self.cvep_sequence_on_duration + self.cvep_sequence_off_duration
        
        # Screen settings
        self.refresh_rate = 60
        self.n_erp_stim_on_frames = int(self.erp_sequence_on_duration * self.refresh_rate)
        self.n_erp_stim_off_frames = int(self.erp_sequence_off_duration * self.refresh_rate)

        self.n_cvep_stim_on_frames = int(self.cvep_sequence_on_duration * self.refresh_rate)
        self.n_cvep_stim_off_frames = int(self.cvep_sequence_off_duration * self.refresh_rate)

        n_trial_rest_frames = int(self.trial_rest_duration // self.refresh_rate)

        # Experiment global settings
        self.run_rest_duration = 1
        self.n_runs = 8
        self.n_blocks = 4
        self.block_rest_duration = 1
        self.obj_order = np.arange(self.n_objs)
        self.obj_orders = {}

        # Number of conditions
        self.conditions = np.arange(self.n_blocks)
        self.n_cond_repeats = 2

        # Screen condition (condition 4)
        self.win = visual.Window(size=(1920, 1080), fullscr=True, screen=0, units="pix", color='grey', waitBlanking=True, allowGUI=True)
        self.width, self.height = self.win.size
        

        # Create flicker boxes
        self.boxes = []
        # Create a box on top left of screen for vsync sensor
        sensor_box_size = 400
        sensor_box = visual.Rect(self.win, width=sensor_box_size, height=sensor_box_size, pos=(-self.width / 2, self.height / 2), color='black')
        sensor_box.setAutoDraw(False)
        self.boxes.append(sensor_box) # For the vsync sensor

        # Boxes behind pictograms
        box_size = 200
        space = (self.width - box_size * 8) // 9
        poss = [(space + i*(box_size + space) - self.width // 2 + box_size / 2, 0) for i in range(self.n_objs)] # Psychopy decided that positions are determined as the center of the objects
        for i in range(self.n_objs):
            box = visual.Rect(self.win, width=box_size, height=box_size, pos=poss[i], units='pix', color='black')
            box.setAutoDraw(False)
            self.boxes.append(box)

        # Pictograms on top of boxes
        self.pictograms = []
        self.img_paths = ['bottle', 'bandage', 'remote', 'can', 'candle', 'box', 'book', 'cup']
        for i, img_path in enumerate(self.img_paths):
            pictogram = visual.ImageStim(self.win, f'./icons/{img_path}.png', mask=None, units='pix', pos=poss[i], size=box_size / 1.5)
            pictogram.setAutoDraw(False)
            self.pictograms.append(pictogram)
    
    def connect_teensy(self) -> None:
        try:
            self.teensy = serial.Serial(port='COM7', baudrate=115200, timeout=1)
            perf_sleep(2)  # Wait for Arduino to initialize
        except Exception as e:
            logging.warning(f"Teensy not connected: {e}")

    def connect_button_box(self, port='COM6', baud_rate=115200, timeout=1.0) -> None:
        try:
            self.button_box = serial.Serial(port, baud_rate, timeout=timeout)
            self.button_box.write('A1'.encode())
            self.button_box.reset_input_buffer()
            self.button_box.flush()
            text = ""
            for _ in range(100):
                text = text + self.button_box.read().decode()
                if "BITSI mode, Ready!\r\n" in text:
                    logging.info("Button box ready!")
                    break
        except Exception as e:
            logging.warning(f"Button box not connected: {e}")
    
    def init_sequence_lsl_stream(self) -> None:
        """cf_int8 = 6, cf_string = 3
        """
        info = StreamInfo(name='SequenceStream', type='Marker', channel_count=8, channel_format=6, nominal_srate=0)
        self.sequence_outlet = StreamOutlet(info)
    
    def init_marker_lsl_stream(self) -> None:
        info = StreamInfo(name='MarkerStream', type='Marker', channel_count=1, channel_format=3, nominal_srate=0)
        self.marker_outlet = StreamOutlet(info)
    
    def send_laser_values(self, values) -> None:
        end_time = time.perf_counter() + self.erp_sequence_on_duration
        if self.teensy is not None:
            data_str = ",".join(map(str, values)) + "\n"
            self.teensy.write(data_str.encode())  # Send data
        # Wait until turn on duration is over
        while time.perf_counter() <= end_time:
            pass
    
    def load_codebook(self, filepath: str) -> np.ndarray:
        codebook = np.load(filepath).T
        assert codebook.shape[1] == self.n_objs, f'Codebook shape should be (n_sequences, {self.n_objs}). Current shape: {codebook.shape}'
        return codebook

    def load_codebooks_block_1(self, filepath: str='./codebooks/condition_1/codebook_1_henrich.npy') -> None:
        """Block 1 aka Henrich's codebook"""
        self.codebooks = []
        codebook = self.load_codebook(filepath)
        for _ in range(self.n_objs):
            self.codebooks.append(codebook)
        self.codebooks = np.array(self.codebooks)
        logging.info(f'Codebooks loaded. shape: {np.array(self.codebooks).shape}')
            
    def load_codebooks_block_2(self, dir: str='./codebooks/condition_2') -> None:
        """Block 2 aka custom codebook"""
        self.codebooks = []
        
        fpaths = sorted(glob.glob(f'{dir}/codebook_obj_*.npy'))
        assert len(fpaths) == self.n_objs, f'there should be {self.n_objs} codebooks for block 2. Current codebooks: {len(fpaths)}'
        
        for fpath in fpaths:
            codebook = self.load_codebook(fpath)
            self.codebooks.append(codebook)
        self.codebooks = np.array(self.codebooks)
        logging.info(f'Codebooks loaded. shape: {np.array(self.codebooks).shape}')
        
    def load_codebooks_block_3(self, fpath: str='./codebooks/condition_3/mseq_61_shift_8.npy') -> None:
        """Block 2 aka custom cVEP"""
        self.codebooks = []
        
        codebook = self.load_codebook(fpath)
        # Select 8 codebooks
        codebook = np.vstack([codebook] * self.trial_duration)
        self.codebooks = np.array([codebook] * 8)
        
        logging.info(f'Codebooks loaded. shape: {np.array(self.codebooks).shape}')
            
    def post_sequence(self, sequence: list):
        """send sequence to lsl stream"""
        try:
            sequence = [int(i) for i in sequence]
            self.sequence_outlet.push_sample(sequence)
        except Exception as e:
            logging.warning(f"Error posting sequence: {e}")
            
    def post_marker(self, marker: str):
        """send marker to lsl stream"""
        try:
            self.marker_outlet.push_sample([marker])
        except Exception as e:
            logging.warning(f"Error posting marker: {e}")

    def cue_audio(self, ref_obj: str, target_obj: str):
        """Cue audio before a trial"""
        audio = sound.Sound(f'./tts/queries/psychopy/output_{ref_obj}2{target_obj}.mp3')

        while True:
            # Play the audio
            audio.play()
            start_time = time.perf_counter()
            duration = audio.getDuration()

            # Monitor button input during audio playback
            while time.perf_counter() - start_time < duration:
                try:
                    x = self.button_box.readline().decode()
                    if len(x):
                        self.marker_outlet.push_sample(['button_press'])
                        audio.stop()
                        perf_sleep(np.random.randint(30, 41, 1) / 10)  # wait 3 to 4 seconds
                        return x
                except:
                    continue

            # 5-second pause between playbacks, still checking for input
            end_time = time.perf_counter() + 3
            while time.perf_counter() < end_time:
                try:
                    x = self.button_box.readline().decode()
                    if len(x):
                        self.marker_outlet.push_sample(['button_press'])
                        audio.stop()
                        self.marker_outlet.push_sample(['audio_stop'])
                        perf_sleep(np.random.randint(30, 41, 1) / 10)  # wait 3 to 4 seconds
                        return x
                except:
                    continue
    
    def cue_audio_single(self, ref_obj: str, target_obj: str):
        """Cue audio before a trial"""
        audio = sound.Sound(f'./tts/queries/psychopy/output_{ref_obj}2{target_obj}.mp3')

        audio.play()
        start_time = time.perf_counter()
        duration = audio.getDuration() + 2

        # Monitor button input during audio playback
        while time.perf_counter() - start_time < duration:
            pass
        
    def play_decription_audio(self):
        """Cue audio before a trial"""
        audio = sound.Sound(f'./tts/queries/psychopy/description_{self.mode}.mp3')

        audio.play()
        start_time = time.perf_counter()
        duration = audio.getDuration() + 1

        # Monitor button input during audio playback
        while time.perf_counter() - start_time < duration:
            pass
    
    def fill_boxes(self, sequence: np.ndarray):
        for val, box in zip(sequence, self.boxes[1:]):
            box.fillColor = 'white' if val == 1 else 'black'

    def fill_sensor_box(self, color: str):
        self.boxes[0].fillColor = color

    def draw_boxes(self):
        for box in self.boxes:
            box.draw()

    def draw_pictograms(self):
        for pictogram in self.pictograms:
            pictogram.draw()

    def turn_off_screen(self):
        self.win.color = 'black'
        self.win.flip()
        self.win.clearBuffer()
        self.win.flip()

    def turn_on_screen(self):
        self.win.color = 'gray'
        self.win.flip()
        self.fill_boxes([0] * 8)
        self.fill_sensor_box('black')
        self.draw_boxes()
        self.draw_pictograms()
        self.win.flip()

    def run_sequence(self, sequence: list):
        """Run a single sequence"""
        # Turn on the Lasers
        end_time = time.perf_counter() + self.erp_sequence_on_duration
        self.send_laser_values(sequence)
        self.post_sequence(sequence)
        # Wait until turn on duration is over
        while time.perf_counter() <= end_time:
            pass
        
        # Turn off the lasers
        if self.erp_sequence_off_duration != 0:
            end_time = time.perf_counter() + self.erp_sequence_off_duration
            self.send_laser_values([0] * 8)
            self.post_sequence([0] * 8)
            # Wait until turn off duration is over
            while time.perf_counter() < end_time:
                pass
        
    def run_trial(self, codebook: list):
        """Run a single trial with multiple sequences"""
        self.post_marker('Trial start')
        for sequence in codebook:
            sequence_start_time = time.perf_counter()
            self.run_sequence(sequence)
            dt = time.perf_counter() - sequence_start_time
            logging.info(f'Sequence duration: {dt // 60} mins {dt % 60} secs {(dt * 1000) } ms')
        self.post_marker('Trial end')

        # Reset
        self.send_laser_values([0] * 8)

    def screen_warmup(self):
        """Flip screen at refresh rate for dt seconds to warmup.

        Args:
            dt (float): warmup duration (seconds)
        """
        for _ in range(int(self.trial_screen_warmup_duration * self.refresh_rate)):  # 1 second of flips at 60Hz
            self.fill_sensor_box('black')
            self.fill_boxes([0] * 8)
            self.draw_boxes()
            self.draw_pictograms()
            self.win.flip()
        
    def run_trial_screen(self, codebook: list):
        """Run a single trial with multiple sequences on monitor"""
        self.screen_warmup(1)
        self.post_marker('Trial start')
        for sequence in codebook:
            for i in range(self.n_erp_stim_on_frames):
                self.fill_sensor_box('white')
                self.fill_boxes(sequence)
                self.draw_boxes()
                self.draw_pictograms()
                self.win.flip()
                if i == 0:
                    self.post_sequence(sequence)
            for i in range(self.n_erp_stim_off_frames):
                self.fill_sensor_box('black')
                self.fill_boxes([0] * 8)
                self.draw_boxes()
                self.draw_pictograms()
                self.win.flip()
                if i == 0:
                    self.post_sequence([0] * 8)
        self.post_marker('Trial end')
            
    def run_run(self):
        """Run a single run with multiple trials"""
        # Randomize objects
        obj_order = np.random.permutation(np.arange(self.n_objs))
        codebooks = self.codebooks[obj_order]
        self.post_marker(f"Objects order: {obj_order}") # Save order objects to marker
        self.post_marker('Run start')

        # for trial_num in range(len(obj_order)):
        for trial_num in range(1):
            codebook = codebooks[trial_num]
            target_obj_idx = obj_order[trial_num]
            
            target_obj = self.obj_names[target_obj_idx]
            ref_obj_idx = np.random.choice(obj_order, 1, p=(obj_order != target_obj_idx) / (obj_order != target_obj_idx).sum())[0]
            ref_obj = self.obj_names[ref_obj_idx]

            self.post_marker(f'Target obj: {target_obj}, ref_obj: {ref_obj}')
            self.post_marker('Audio start')
            # self.cue_audio(ref_obj, target_obj)
            self.cue_audio_single(ref_obj, target_obj)
            self.post_marker('Audio end')

            trial_start_time = time.perf_counter()
            if self.mode == 'scene':
                self.run_trial(codebook)
            elif self.mode == 'screen':
                self.run_trial_screen(codebook)
            dt = time.perf_counter() - trial_start_time
            logging.info(f'Trial duration: {dt // 60} mins {dt % 60} secs {dt * 1000} ms')
            # Rest for trial_rest_duration seconds
            rest_end_time = time.perf_counter() + self.trial_rest_duration
            self.post_marker('Trial Rest')
            while time.perf_counter() <= rest_end_time:
                pass
        self.post_marker('Run end')
                
    def run_block(self):
        """Run a block with multiple runs"""
        # Randomize conditions
        conditions = np.random.permutation(self.conditions)
        conditions = np.array([0, 1, 2, 3])
        self.post_marker(f"Conditions order: {conditions}") # Save conditions to marker
        print(conditions)
        
        self.post_marker('Block start')
        for condition in conditions:
            # Load codebooks depending on condition
            if condition == 0:
                self.turn_off_screen()
                self.mode = 'scene'
                self.load_codebooks_block_1()
                self.erp_sequence_on_duration = 0.1
                self.erp_sequence_off_duration = 0.15
            elif condition == 1:
                self.turn_off_screen()
                self.mode = 'scene'
                self.load_codebooks_block_2()
                self.erp_sequence_on_duration = 0.1
                self.erp_sequence_off_duration = 0.15
            elif condition == 2:
                self.turn_off_screen()
                self.mode = 'scene'
                self.load_codebooks_block_3()
                self.erp_sequence_on_duration = 1/60
                self.erp_sequence_off_duration = 0
            else:
                self.turn_on_screen()
                self.mode = 'screen'
                self.load_codebooks_block_2()
                self.erp_sequence_on_duration = 0.1
                self.erp_sequence_off_duration = 0.15
                # self.load_codebooks_block_3()
                # self.erp_sequence_on_duration = 1 / 60
                # self.erp_sequence_off_duration = 0
            
            self.post_marker('Run Rest')
            perf_sleep(self.run_rest_duration)

            self.play_decription_audio()
            run_start_time = time.perf_counter()
            for i in range(self.n_cond_repeats):
                self.run_run()
            dt = time.perf_counter() - run_start_time
            logging.info(f'Run duration: {dt // 60} mins {dt % 60} secs {dt * 1000} ms')
        self.post_marker('Block end')
        
    def run_session(self):
        # Init sensor
        self.fill_sensor_box('black')
        self.fill_boxes([0] * 8)
        self.draw_boxes()
        self.win.flip()
        if input('Have you initialized the vsync sensor? y/n?\n') != 'y':
            exit()
        # Start ERP condition 1
        for i in range(self.n_blocks):
            self.run_block()
            perf_sleep(self.block_rest_duration)
        
    def run_test(self):
        """Run a test sequence"""
        self.load_codebooks_block_3()
        self.erp_sequence_on_duration = 1 / 60
        self.erp_sequence_off_duration = 0
        self.post_marker('Test start')
        for i in range(1000):
            try:
                # self.run_trial(self.codebooks[0])
                self.run_sequence([1] * 8)
            except KeyboardInterrupt:
                self.run_sequence([0] * 8)
                break
        self.post_marker('Test end')

    

    def test_audio(self):
        while True:
            ref_objs = np.random.choice(self.obj_names, 2)

            target_objs = np.random.choice([i for i in self.obj_names if i not in ref_objs], 2)
            for ref_obj in ref_objs:
                for target_obj in target_objs:
                    self.cue_audio(ref_obj, target_obj)

    def screen_timing_test(self):
        self.mode = 'screen'
        self.load_codebooks_block_1()
        self.erp_sequence_on_duration = 0.1
        self.erp_sequence_off_duration = 0.15

        for _ in range(60):
            self.turn_on_screen()
            self.turn_off_screen()

        self.turn_on_screen()

        for i in range(100):
            self.fill_sensor_box('white')
            self.fill_boxes([1] * 8)
            self.draw_boxes()
            self.win.flip()
            self.fill_sensor_box('black')
            self.fill_boxes([0] * 8)
            self.draw_boxes()
            self.win.flip()
        # perf_sleep(1)
        for _ in range(60):  # 1 second of flips at 60Hz
            self.fill_sensor_box('black')
            self.fill_boxes([0] * 8)
            self.draw_boxes()
            self.draw_pictograms()
            self.win.flip()
        self.run_trial_screen(self.codebooks[0])


if __name__ == "__main__":
    # Set logging filename to ./logs/log_%Y-%m-%d_%H-%M-%S.log
    filename = datetime.datetime.now().strftime('./logs/log_%Y-%m-%d_%H-%M-%S.log')
    logging.basicConfig(
        filename=filename, 
        filemode='w',
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    # port = 'COM7'  # Windows
    # port = '/dev/tty.usbmodem156466901' # Mac
    controller = StimController()
    controller.mode = 'screen'
    
    test = False
    print('TEST:', test)
    # Start experiment
    kw = input('Start run? y/n?\n')
    
    if kw == 'y':
        try:
            if test:
                controller.win.recordFrameIntervals = True
                controller.screen_timing_test()
                print("Avg frame interval:", np.mean(controller.win.frameIntervals))
                print("Max frame interval:", np.max(controller.win.frameIntervals))
                print("Dropped frames:", sum(np.array(controller.win.frameIntervals) > 1.5 * (1/controller.refresh_rate)))
                sns.boxplot(controller.win.frameIntervals)
                plt.show()
                print("Actual refresh rate:", controller.win.getActualFrameRate())
                
            else:
                controller.run_session()
        except KeyboardInterrupt:
            controller.send_laser_values([0] * 8)
            controller.win.close()
            print('Experiment interrupted. Gracefully closed.')