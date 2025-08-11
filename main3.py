import time
import datetime
import logging
import random
import numpy as np
import pandas as pd

from utils import perf_sleep
from pylsl import StreamInfo, StreamOutlet

from utils import load_codebooks_block_1, load_codebooks_block_2, load_codebooks_block_3

from lasers import LaserController
from button_box import ButtonBoxController
from audio import AudioController
from window import ScreenStimWindow

class StimController:
    def __init__(self, random_seed: int=42):
        # Set random seeds for reproducibility
        random.seed(random_seed)
        np.random.seed(random_seed)
        
        # Experiment global settings
        self.codebook_kolkhorst = load_codebooks_block_1()
        self.codebook_fast_erp = load_codebooks_block_2()
        self.codebook_cvep = load_codebooks_block_3()
        
        self.objects = {
            0: 'bottle', 
            1: 'bandage', 
            2: 'remote', 
            3: 'can', 
            4: 'candle', 
            5: 'box', 
            6: 'book', 
            7: 'cup'
        }
        self.n_objs = len(self.objects)
        self.conditions = {
            0: 'scene_Kolkhorst',
            1: 'scene_fastERP',
            2: 'scene_cVEP',
            3: 'screen_fastERP',
            4: 'screen_cVEP'
        }
        
        self.df_order_table = pd.read_csv('./config/trial_orders.csv')
        
        self.n_blocks = 3
        self.n_runs = 8
        self.n_trials = 10
        self.trial_duration = 12
        self.trial_duration_kolkhorst = 24
        self.trial_rest_duration = 3 # NOTE: check if 3 seconds is enough
        
        # ERP settings
        self.erp_sequence_on_duration = 0.1
        self.erp_sequence_off_duration = 0.15
        self.erp_sequence_duration = self.erp_sequence_on_duration + self.erp_sequence_off_duration

        # c-VEP settings
        self.cvep_sequence_on_duration = 1 / 60
        self.cvep_sequence_off_duration = 0
        self.cvep_sequence_duration = self.cvep_sequence_on_duration + self.cvep_sequence_off_duration
        
        # Filepath for audio cues
        self.cue_audio_path = './tts/queries/psychopy_slowed'


        self.refresh_rate = 60 # Hz
        self.screen_warmup_duration = 1  # seconds
        
        # Init LSL streams
        self.init_streams()
        
        # Init laser controller
        self.laser_controller = LaserController()

        # Init button box controller
        self.button_box_controller = ButtonBoxController()

        # Init audio controller
        self.audio_controller = AudioController(audio_path='./tts/queries/psychopy_slowed', button_box=self.button_box_controller, marker_outlet=self.marker_outlet)

        # Init screen stimulus window
        self.screen = ScreenStimWindow(self.objects)

    def init_streams(self):
        # Initialize LSL stream for stim sequences/codebook
        info = StreamInfo(name='SequenceStream', type='Marker', channel_count=8, channel_format=6, nominal_srate=0, source_id='sequence_stream_id')
        self.sequence_outlet = StreamOutlet(info)

        # Initialize LSL stream for markers such as trial start/end, button press, audio start/stop etc
        info = StreamInfo(name='MarkerStream', type='Marker', channel_count=1, channel_format=3, nominal_srate=0, source_id='marker_stream_id')
        self.marker_outlet = StreamOutlet(info)
        
        # Initialize LSL stream for target/non-targets
        info = StreamInfo(name='TargetStream', type='Marker', channel_count=1, channel_format=6, nominal_srate=0, source_id='target_stream_id')
        self.target_outlet = StreamOutlet(info)

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
        perf_sleep(self.screen_warmup_duration)
        self.post_marker('Trial start')
        for sequence in codebook:
            sequence_start_time = time.perf_counter()
            self.run_sequence(sequence)
            dt = time.perf_counter() - sequence_start_time
            logging.info(f'{self.mode} sequence duration: {dt // 60} mins {dt % 60} secs {(dt * 1000) } ms')
        self.post_marker('Trial end')

        # Reset
        self.send_laser_values([0] * 8)
        
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
                self.screen.flip()
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
            
    def run_run(self, run_id: int):
        """Run a single run with multiple trials"""
        # Randomize objects
        conditions_order = self.df_order_table[run_id]
        obj_order = list(np.random.permutation(np.arange(self.n_objs)).astype(int))
        pictograms_order = list(np.random.permutation(np.arange(self.n_objs)).astype(int))
        self.screen.reorder_pictograms(pictograms_order)
        logging.info(f'run_{run_id} object order: {obj_order}, pictograms order: {pictograms_order}')
        for trial_id, condition in enumerate(conditions_order):
            logging.info(f'trial_{trial_id}-start;{condition}')
            # TODO: Implement trial logic for each condition
            logging.info(f'trial_{trial_id}-end;{condition}')
        # return pictograms to their original order
        self.screen.default_order_pictograms()
        
        
    def run_block(self, block_id: int):
        """Run a block with multiple runs"""
        for run_id in range(self.n_runs):
            _ = input(f'Start block: {block_id}, run: {run_id}. Press any key to continue:\n')
            logging.info(f'run_{run_id}-start')
            self.run_run(run_id)
            logging.info(f'run_{run_id}-end')

        self.screen.fill_text(f'Block {block_id} complete!\nWait for the researcher to continue.')
        self.screen.description_text.setHeight(60)
        self.screen.draw_text()
        self.screen.win.flip()
        
        
    def run_session(self):
        for block_id in range(self.n_blocks):                
            # Start block
            logging.info(f'block_{block_id}-start')
            self.run_block(block_id)
            logging.info(f'block_{block_id}-end')

        self.screen.fill_text('Thank you! You have successfully completed the experiment!')
        self.screen.description_text.setHeight(60)
        self.screen.draw_text()
        self.screen.win.flip()
        if input('End the experiment? y/n\n') == 'y':
            exit()

    

    

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
                self.mode = 'scene'
                self.switch_protocol('erp')
                self.load_codebooks_block_1()
            elif condition == 1:
                self.mode = 'scene'
                self.switch_protocol('erp')
                self.load_codebooks_block_2()
            elif condition == 2:
                self.mode = 'scene'
                self.switch_protocol('cvep')
                self.load_codebooks_block_3()
            elif condition == 3:
                self.mode = 'screen'
                self.switch_protocol('erp')
                self.load_codebooks_block_2()
            elif condition == 4:
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
    
    # Setup
    ## Turn on lasers to until key press to setup lasers and objects
    controller.send_laser_values([1] * 8)
    if input('Finished setting up the lasers? y/n\n') != 'y':
        exit()
    controller.send_laser_values([0] * 8)

    ## Initialize vsync sensor
    controller.fill_text('Initializing VSync Sensor.')
    controller.draw_text()
    controller.fill_sensor_box('white')
    controller.sensor_box.draw()
    controller.win.flip()
    if input('Finished setting up the vsync sensor? y/n?\n') != 'y':
        exit()

    # Start experiment
    controller.fill_text('Initializing Speakers...')
    controller.draw_text()
    controller.win.flip()
    controller.select_speakers()

    # Testing phase
    controller.screen_timing_test()
    if input('Does the screen timing test pass? y/n\n') != 'y':
        exit()

    # Familiarization phase
    print('#####################')
    print('Familiarization Phase.')
    controller.familiarization()

    # Start experiment
    if input('Start experiment? y/n\n') == 'y':
        ## Resting state recording
        print('#####################')
        print('Resting state recording Phase.')
        controller.resting_state_recording()

        ## Session
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
        