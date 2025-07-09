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
from psychopy import sound, visual, prefs, tools
import random

random.seed(42)
np.random.seed(42)


class StimController:
    def __init__(self):
        self.codebooks = []
        self.n_objs = 8
        self.obj_names = ['bottle', 'bandage', 'remote', 'can', 'candle', 'box', 'book', 'cup']
        
        # Mode
        self.mode = 'screen'
        
        # Audio path
        self.cue_audio_path = './tts/queries/psychopy_slowed'

        # Connect to teensy
        self.connect_teensy()
        self.connect_button_box()
        self.init_sequence_lsl_stream()
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

        # Protcol switch
        self.protocol = 'erp'
        self.n_stim_on_frames = self.n_erp_stim_on_frames
        self.n_stim_off_frames = self.n_erp_stim_off_frames
        self.sequence_on_duration = self.erp_sequence_on_duration
        self.sequence_off_duration = self.erp_sequence_off_duration

        # Experiment global settings
        self.run_rest_duration = 10
        self.n_runs = 8
        self.n_blocks = 4
        self.block_rest_duration = 10
        self.obj_order = np.arange(self.n_objs)
        self.obj_orders = {}

        # Number of conditions
        self.conditions = np.arange(self.n_blocks)
        self.n_cond_repeats = 2

        # Screen (condition 4)
        self.win = visual.Window(size=(1920, 1080), fullscr=True, screen=2, units="pix", color='grey', waitBlanking=True, allowGUI=True)
        self.width, self.height = self.win.size
        
        # Create flicker boxes
        # Create a box on top left of screen for vsync sensor
        
        sensor_box_size = 400
        self.sensor_box = visual.Rect(self.win, width=sensor_box_size, height=sensor_box_size, pos=(-self.width / 2, self.height / 2), color='black')
        self.sensor_box.setAutoDraw(False)

        # Boxes behind pictograms
        self.box_size = 150
        self.space = (self.width - self.box_size * 8) // 9
        self.poss = [(self.space + i*(self.box_size + self.space) - self.width // 2 + self.box_size / 2, 0) for i in range(self.n_objs)] # Psychopy decided that positions are determined as the center of the objects
        self.init_boxes()
        self.pictogram_poss = [(self.space + i*(self.box_size + self.space) - self.width // 2 + self.box_size / 2, 0) for i in range(self.n_objs)] # Psychopy decided that positions are determined as the center of the objects
        self.init_pictograms()

        # Init description text on screen
        self.init_text()
        
    def init_boxes(self):
        self.boxes = []
        for i in range(self.n_objs):
            box = visual.Rect(self.win, width=self.box_size, height=self.box_size, pos=self.poss[i], units='pix', color='black')
            box.setAutoDraw(False)
            self.boxes.append(box)

    def init_pictograms(self):
        # Pictograms on top of boxes
        self.pictograms = []
        for i, img_path in enumerate(self.obj_names):
            pictogram = visual.ImageStim(self.win, f'./icons/{img_path}.png', mask=None, units='pix', pos=self.pictogram_poss[i], size=self.box_size)
            pictogram.setAutoDraw(False)
            self.pictograms.append(pictogram)

    def init_text(self):
        self.description_text = visual.TextStim(self.win, text="Hello World", pos=(0, 0), color='white', height=50)
        self.description_text.setAutoDraw(False)

    def fill_text(self, text: str):
        self.description_text.setText(text)
    
    def draw_text(self):
        self.description_text.draw()
    
    def connect_teensy(self) -> None:
        try:
            self.teensy = serial.Serial(port='COM7', baudrate=115200, timeout=1)
            perf_sleep(2)  # Wait for Arduino to initialize
        except Exception as e:
            self.teensy = None
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
            self.button_box = None
            logging.warning(f"Button box not connected: {e}")
    
    def init_sequence_lsl_stream(self) -> None:
        """cf_int8 = 6, cf_string = 3
        """
        try:
            info = StreamInfo(name='SequenceStream', type='Marker', channel_count=8, channel_format=6, nominal_srate=0, source_id='sequence_stream_id')
            self.sequence_outlet = StreamOutlet(info)
        except Exception as e:
            self.sequence_outlet = None
            logging.warning(f"Sequence outlet couldn't be initialized")
            
    
    def init_marker_lsl_stream(self) -> None:
        try:
            info = StreamInfo(name='MarkerStream', type='Marker', channel_count=1, channel_format=3, nominal_srate=0, source_id='marker_stream_id')
            self.marker_outlet = StreamOutlet(info)
        except Exception as e:
            self.marker_outlet = None
            logging.warning(f"Marker outlet couldn't be initialized")
    
    def send_laser_values(self, values) -> None:
        end_time = time.perf_counter() + self.sequence_on_duration
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

    def load_codebooks_block_1(self, path: str='./codebooks/condition_1') -> None:
        """Block 1 aka Henrich's codebook"""
        self.codebooks = []
        fpaths = sorted(glob.glob(f'{path}/codebook_obj_*.npy'))
        for fpath in fpaths:
            codebook = self.load_codebook(fpath)
            self.codebooks.append(codebook)
        self.codebooks = np.array(self.codebooks)
        logging.info(f'Codebooks loaded. shape: {np.array(self.codebooks).shape}')
        
    def load_codebooks_block_2(self, path: str='./codebooks/condition_2') -> None:
        """Block 2 aka custom codebook"""
        self.codebooks = []
        fpaths = sorted(glob.glob(f'{path}/codebook_obj_*.npy'))
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
            
    def switch_protocol(self, protocol: str):
        self.protocol = protocol
        if self.protocol == 'erp':
            self.n_stim_on_frames = self.n_erp_stim_on_frames
            self.n_stim_off_frames = self.n_erp_stim_off_frames
            self.sequence_on_duration = self.erp_sequence_on_duration
            self.sequence_off_duration = self.erp_sequence_off_duration
        elif self.protocol == 'cvep':
            self.n_stim_on_frames = self.n_cvep_stim_on_frames
            self.n_stim_off_frames = self.n_cvep_stim_off_frames
            self.sequence_on_duration = self.cvep_sequence_on_duration
            self.sequence_off_duration = self.cvep_sequence_off_duration
        else:
            raise ValueError('protoc must be erp or cvep')

    def cue_audio(self, ref_obj: str, target_obj: str):
        """Cue audio before a trial"""
        audio = sound.Sound(f'{self.cue_audio_path}/{self.mode}_{ref_obj}2{target_obj}.mp3')

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

            # 3-second pause between playbacks, still checking for input
            end_time = time.perf_counter() + 3
            while time.perf_counter() < end_time:
                try:
                    x = self.button_box.readline().decode()
                    if len(x):
                        self.marker_outlet.push_sample(['button_press'])
                        audio.stop()
                        self.marker_outlet.push_sample(['audio_stop'])
                        perf_sleep(np.random.randint(30, 41, 1) / 10)  # wait 3~4 seconds
                        return x
                except:
                    continue
    
    def cue_audio_single(self, ref_obj: str, target_obj: str):
        """Cue audio before a trial"""
        audio = sound.Sound(f'{self.cue_audio_path}/{self.mode}_{ref_obj}2{target_obj}.mp3')

        audio.play()
        start_time = time.perf_counter()
        duration = audio.getDuration() + 2

        # Monitor button input during audio playback
        while time.perf_counter() - start_time < duration:
            pass
        
    def play_description_audio(self):
        """Cue audio before a trial"""
        audio = sound.Sound(f'{self.cue_audio_path}/description_{self.mode}.mp3')
        audio.play()
        start_time = time.perf_counter()
        duration = audio.getDuration() + 2 # Wait 2 seconds after finished playing audio
        while time.perf_counter() - start_time < duration:
            pass
    
    def fill_boxes(self, sequence: np.ndarray):
        for val, box in zip(sequence, self.boxes):
            box.fillColor = 'white' if val == 1 else 'black'

    def fill_sensor_box(self, color: str):
        self.sensor_box.fillColor = color

    
    def draw_boxes(self):
        for box in self.boxes:
            box.draw()
        self.sensor_box.draw()

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
        self.fill_text("")
        self.draw_boxes()
        self.draw_pictograms()
        self.draw_text()
        self.win.flip()

    def run_sequence(self, sequence: list):
        """Run a single sequence"""
        # Turn on the Lasers
        end_time = time.perf_counter() + self.sequence_on_duration
        self.send_laser_values(sequence)
        self.post_sequence(sequence)
        # Wait until turn on duration is over
        while time.perf_counter() <= end_time:
            pass
        
        # Turn off the lasers
        if self.sequence_off_duration != 0:
            end_time = time.perf_counter() + self.sequence_off_duration
            self.send_laser_values([0] * 8)
            self.post_sequence([0] * 8)
            # Wait until turn off duration is over
            while time.perf_counter() < end_time:
                pass
        
    def run_trial(self, codebook: list):
        """Run a single trial with multiple sequences"""
        perf_sleep(self.trial_screen_warmup_duration)
        self.post_marker('Trial start')
        for sequence in codebook:
            sequence_start_time = time.perf_counter()
            self.run_sequence(sequence)
            dt = time.perf_counter() - sequence_start_time
            logging.info(f'{self.mode} sequence duration: {dt // 60} mins {dt % 60} secs {(dt * 1000) } ms')
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
        
    def run_trial_screen(self, codebook: list, target_obj_idx: int):
        """Run a single trial with multiple sequences on monitor"""
        self.screen_warmup()
        self.post_marker('Trial start')
        for sequence in codebook:
            sequence_start_time = time.perf_counter()
            for i in range(self.n_stim_on_frames):
                self.fill_sensor_box('white' if sequence[target_obj_idx] == 1 else 'black')
                self.fill_boxes(sequence)
                self.draw_boxes()
                self.draw_pictograms()
                self.win.flip()
                if i == 0:
                    self.post_sequence(sequence)
            for i in range(self.n_stim_off_frames):
                self.fill_sensor_box('black')
                self.fill_boxes([0] * 8)
                self.draw_boxes()
                self.draw_pictograms()
                self.win.flip()
                if i == 0:
                    self.post_sequence([0] * 8)
            dt = time.perf_counter() - sequence_start_time
            logging.info(f'{self.mode} sequence duration: {dt // 60} mins {dt % 60} secs {(dt * 1000) } ms')
        self.post_marker('Trial end')

        # Reset boxes
        self.fill_boxes([0] * 8)
        self.draw_boxes()
        self.draw_pictograms()
        self.win.flip()
            
    def run_run(self):
        """Run a single run with multiple trials"""
        # Randomize objects
        obj_order = np.random.permutation(np.arange(self.n_objs))
        codebooks = self.codebooks[obj_order]
        self.post_marker(f"Objects order: {obj_order}") # Save order objects to marker
        self.post_marker('Run start')

        for trial_num in range(len(obj_order)):
        # for trial_num in range(1):
            codebook = codebooks[trial_num]
            target_obj_idx = obj_order[trial_num]
            
            target_obj = self.obj_names[target_obj_idx]
            ref_obj_idx = np.random.choice(obj_order, 1, p=(obj_order != target_obj_idx) / (obj_order != target_obj_idx).sum())[0]
            ref_obj = self.obj_names[ref_obj_idx]

            self.post_marker(f'Target id/obj: {target_obj_idx}_{target_obj}, ref_obj: {ref_obj_idx}_{ref_obj}')
            self.post_marker('Audio start')
            self.cue_audio(ref_obj, target_obj)
            # self.cue_audio_single(ref_obj, target_obj)
            self.post_marker('Audio end')

            trial_start_time = time.perf_counter()
            if self.mode == 'scene':
                self.run_trial(codebook)
            elif self.mode == 'screen':
                self.run_trial_screen(codebook, target_obj_idx)
            dt = time.perf_counter() - trial_start_time
            logging.info(f'{self.mode} trial duration: {dt // 60} mins {dt % 60} secs {dt * 1000} ms')
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
        self.post_marker(f"Conditions order: {conditions}") # Save conditions to marker
        print(conditions)
        
        self.post_marker('Block start')
        for condition in conditions:
            # Load codebooks depending on condition
            self.post_marker(f'Condition: {condition}')
            if condition == 0:
                self.turn_off_screen()
                self.mode = 'scene'
                self.switch_protocol('erp')
                self.load_codebooks_block_1()
            elif condition == 1:
                self.turn_off_screen()
                self.mode = 'scene'
                self.switch_protocol('erp')
                self.load_codebooks_block_2()
            elif condition == 2:
                self.turn_off_screen()
                self.mode = 'scene'
                self.switch_protocol('cvep')
                self.load_codebooks_block_3()
            elif condition == 3:
                self.turn_on_screen()
                self.mode = 'screen'
                self.switch_protocol('erp')
                self.load_codebooks_block_2()
            elif condition == 4:
                self.turn_on_screen()
                self.mode = 'screen'
                self.switch_protocol('cvep')
                self.load_codebooks_block_3()
            else:
                raise ValueError('Condition must be values between 0~4')
            
            self.post_marker('Run Rest')
            perf_sleep(self.run_rest_duration)

            # self.play_description_audio()
            run_start_time = time.perf_counter()
            for _ in range(self.n_cond_repeats):
                self.run_run()
            dt = time.perf_counter() - run_start_time
            logging.info(f'Run duration: {dt // 60} mins {dt % 60} secs {dt * 1000} ms')
        self.post_marker('Block end')
        
    def run_session(self):
        # Start ERP condition 1
        for i in range(self.n_blocks):
        # for i in range(1):
            # Randomize positions of pictograms
            if self.mode == 'screen':
                new_idc = np.random.permutation(np.arange(self.n_objs)).astype(int).tolist()
                self.pictogram_poss = [self.pictogram_poss[i] for i in new_idc]
                self.init_pictograms()
                self.post_marker(f'New pictogram order: {new_idc}')
            
            # Start block
            # _ = input(f'Start block num: {i}. Press any key to continue:\n')
            block_start_time = time.perf_counter()
            self.run_block()
            dt = time.perf_counter() - block_start_time
            logging.info(f'Block duration: {dt // 60} mins {dt % 60} secs {dt * 1000} ms')
            perf_sleep(self.block_rest_duration)
            
            # Return pictograms to original order
            if self.mode == 'screen':
                prev_idc = [0] * len(new_idc)
                for i, o in enumerate(new_idc):
                    prev_idc[o] = i
                self.pictogram_poss = [self.pictogram_poss[i] for i in prev_idc]
                self.init_pictograms()
                self.win.flip()

        self.fill_text('Thank you! You have successfully completed the experiment!')
        self.description_text.setHeight(60)
        self.draw_text()
        self.win.flip()
        if input('End the experiment? y/n\n') == 'y':
            exit()

    def screen_timing_test(self):
        self.mode = 'screen'
        self.win.recordFrameIntervals = True
        self.load_codebooks_block_2()
        self.switch_protocol('erp')

        # Turn screen completely on/off
        for _ in range(60):
            self.turn_on_screen()
            self.turn_off_screen()
        self.turn_on_screen()

        # Flip boxes for 2 seconds
        for _ in range(120):
            self.fill_sensor_box('white')
            self.fill_boxes([1] * 8)
            self.draw_boxes()
            self.win.flip()
            self.fill_sensor_box('black')
            self.fill_boxes([0] * 8)
            self.draw_boxes()
            self.win.flip()

        # Run 1 trial
        self.run_trial_screen(self.codebooks[0], 0)
        
        # Log results
        n_dropped_frames = sum(np.array(self.win.frameIntervals) > 1.5 * (1/controller.refresh_rate))
        logging.info(f"Avg frame interval: {np.mean(self.win.frameIntervals)}")
        logging.info(f"Max frame interval: {np.max(self.win.frameIntervals)}")
        logging.info(f"Dropped frames: {n_dropped_frames}")
        logging.info(f"Actual refresh rate: {self.win.getActualFrameRate()}")
        print(f'# of dropped frames: {n_dropped_frames}')
        
        self.win.recordFrameIntervals = False

    def get_available_audio_devices(self):
        return list(tools.systemtools.getAudioDevices().keys())
        
    
    def select_speakers(self):
        # Set speakers
        prefs.hardware['audioLib'] = ['PTB'] if ['PTB'] in prefs.hardware['audioLib'] else prefs.hardware['audioLib'] # Most time accurate library according to psychopy docs
        # default_audio_devices = [
        #     'OUT 3-4 (BEHRINGER X-AIR)',
        #     'Speakers (Realtek(R) Audio)',
        #     'Speakers (High Definition Audio Device)'
        # ]

        while True:
            print("Available audio devices:\nFOR EXPERIMENT SELECT 'OUT 3-4 (BEHRINGER X-AIR)'\n")
            audio_devices = self.get_available_audio_devices()
            for i, device_name in enumerate(audio_devices):
                print(i, device_name)
            audio_device_id = int(input(f'Select audio device: {list(range(len(audio_devices)))}\n'))
            audio_device = audio_devices[audio_device_id]
            print(audio_device)
            prefs.hardware['audioDevice'] = audio_device
            self.cue_audio_single(self.obj_names[0], self.obj_names[1])
            if input('Do the speakers work? y/n\n') == 'y':
                break

    def familiarization(self):
        while True:
            print('Conditions:')
            print('0: scene/erp')
            print('1: scene/erp')
            print('2: scene/cvep')
            print('3: screen/erp')
            print('4: screen/cvep')
            condition = int(input('Select condition: [0, 1, 2, 3, 4]\n'))
            if condition == 0:
                self.turn_off_screen()
                self.mode = 'scene'
                self.switch_protocol('erp')
                self.load_codebooks_block_1()
            elif condition == 1:
                self.turn_off_screen()
                self.mode = 'scene'
                self.switch_protocol('erp')
                self.load_codebooks_block_2()
            elif condition == 2:
                self.turn_off_screen()
                self.mode = 'scene'
                self.switch_protocol('cvep')
                self.load_codebooks_block_3()
            elif condition == 3:
                self.turn_on_screen()
                self.mode = 'screen'
                self.switch_protocol('erp')
                self.load_codebooks_block_2()
            elif condition == 4:
                self.turn_on_screen()
                self.mode = 'screen'
                self.switch_protocol('cvep')
                self.load_codebooks_block_3()
            else:
                raise ValueError('Condition must be values between 0~4')
            
            self.run_run()

            if input('Continue familiarization? y/n\n') != 'y':
                break
    
    def resting_state_recording(self):
        self.fill_text('.')
        self.description_text.setHeight(200)
        self.draw_text()
        self.win.flip()
        if input('Start eyes open recording? y/n\n') == 'y':
            self.post_marker('Start eyes open')
            perf_sleep(150)
            self.post_marker('End eyes open')

        if input('Start eyes closed recording? y/n\n') == 'y':
            self.post_marker('Start eyes closed')
            perf_sleep(150)
            self.post_marker('End eyes closed')

        self.fill_text('Resting state recording finished')
        self.description_text.setHeight(50)
        self.draw_text()
        self.win.flip()
        

if __name__ == "__main__":
    # Set logging filename to ./logs/log_%Y-%m-%d_%H-%M-%S.log
    filename = datetime.datetime.now().strftime('./logs/log_%Y-%m-%d_%H-%M-%S.log')
    logging.basicConfig(
        filename=filename, 
        filemode='w',
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    controller = StimController()
    # prefs.hardware['audioDevice'] = 'Speakers (Realtek(R) Audio)'
    prefs.hardware['audioDevice'] = 'Speakers (High Definition Audio Device)'
    
    # # Initialize vsync sensor
    # controller.turn_off_screen()
    # controller.fill_text('Initializing VSync Sensor.')
    # controller.draw_text()
    # controller.win.flip()
    # if input('Have you initialized the vsync sensor? y/n?\n') != 'y':
    #     exit()

    # # Start experiment
    # controller.fill_text('Initializing Speakers.')
    # controller.draw_text()
    # controller.win.flip()
    # controller.select_speakers()

    # # Testing phase
    # controller.screen_timing_test()
    # if input('Continue? y/n\n') != 'y':
    #     exit()

    # # Familiarization phase
    # print('#####################')
    # print('Familiarization Phase.')
    # controller.familiarization()

    # # Resting state recording
    # print('#####################')
    # print('Resting state recording Phase.')
    # controller.resting_state_recording()
    
    # Start experiment
    if input('Start experiment? y/n\n') == 'y':
        try:
            session_start_time = time.perf_counter()
            controller.run_session()
            dt = time.perf_counter() - session_start_time
            logging.info(f'Block duration: {dt // 60} mins {dt % 60} secs {dt * 1000} ms')
            
        except KeyboardInterrupt:
            controller.send_laser_values([0] * 8)
            controller.win.close()
            print('Experiment interrupted. Gracefully closed.')
    else:
        exit()
        