import time
import datetime
import logging
import random
import numpy as np
import pandas as pd

from utils import perf_sleep
from utils import load_codebooks_block_1, load_codebooks_block_2, load_codebooks_block_3

from lasers import LaserController
from button_box import ButtonBoxController
from audio import AudioController
from window import ScreenStimWindow

from pylsl import StreamInfo, StreamOutlet, cf_string


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

        self.df_trial_orders = pd.read_csv('./config/trial_orders.csv')
        self.df_obj_orders = pd.read_csv('./config/obj_orders.csv')
        self.df_pictogram_orders = pd.read_csv('./config/pictogram_orders.csv')

        self.n_blocks = 3
        self.n_runs = 8
        self.n_trials = 10
        self.trial_duration = 12
        self.trial_duration_kolkhorst = 24
        self.trial_rest_duration = 3 # NOTE: check if 3 seconds is enough
        self.run_rest_duration = 60
        self.block_rest_duration = 60
        
        # Screen settings
        self.refresh_rate = 60 # Hz

        # ERP settings
        self.erp_on_duration = 0.1
        self.erp_off_duration = 0.15
        self.erp_duration = self.erp_on_duration + self.erp_off_duration

        # c-VEP settings
        self.cvep_on_duration = 1 / self.refresh_rate
        self.cvep_off_duration = 0
        self.cvep_duration = self.cvep_on_duration + self.cvep_off_duration
        
        # Filepath for audio cues
        self.cue_audio_path = './tts/queries/psychopy_slowed'

        # Screen settings
        self.erp_on_frames = int(self.erp_on_duration * self.refresh_rate) # Should be 6 frames for 60hz monitor
        self.erp_off_frames = int(self.erp_off_duration * self.refresh_rate) # Should be 6 frames for 60hz monitor
        self.cvep_on_frames = 1
        self.screen_warmup_duration = self.trial_rest_duration  # seconds
        
        # Init laser controller
        self.laser_controller = LaserController()

        # Init button box controller
        self.button_box_controller = ButtonBoxController()

        # Init audio controller
        self.audio_controller = AudioController(audio_path='./tts/queries/psychopy_slowed', button_box=self.button_box_controller)

        # Init screen stimulus window
        self.screen = ScreenStimWindow(self.objects)
        
        # Init markers for resting state
        info = StreamInfo(name='RestingStateMarkerStream', type='Marker', channel_count=1, channel_format=cf_string, nominal_srate=0, source_id='resting_state_marker_stream_id')
        self.marker_outlet = StreamOutlet(info)
        

    def rest(self, duration: int, text: str='Rest'):
        for t in range(duration):
            start_time = time.perf_counter()
            self.screen.draw_text(text + f'\n Experiment will start in\n{duration - t} seconds.')
            # self.screen.description_text.setHeight(60)
            self.screen.win.flip()
            perf_sleep(1 - 1/self.refresh_rate)
            print(time.perf_counter() - start_time)


    def run_session(self):
        for block_id in range(self.n_blocks):
            # Start block
            _ = input(f'Press any key to start block: {block_id}')
            logging.info(f'block_{block_id}-start')
            self.run_block(block_id)
            self.rest(self.block_rest_duration, text=f'Block: {block_id} complete.')
            logging.info(f'block_{block_id}-end')

        self.screen.draw_text('Thank you! You have successfully completed the experiment!')
        self.screen.win.flip()
        if input('End the experiment? y/n\n') == 'y':
            exit()

    def run_block(self, block_id: int):
        """Run a block with multiple runs"""

        # Get prerandomized pictogram order
        new_pictograms_order = self.df_pictogram_orders[f'block_{block_id}'].tolist()
        print('New pictograms order:', new_pictograms_order)
        self.screen.reorder_pictograms(new_pictograms_order)
        logging.info(f'block:{block_id}; pictograms order: {new_pictograms_order}')

        for run_id in range(self.n_runs):
            _ = input(f'Start block: {block_id}; run: {run_id}. Press any key to continue:\n')
            logging.info(f'run_{run_id}-start')
            self.run_run(run_id)
            self.rest(self.run_rest_duration, text=f'Run: {run_id} complete.')
            logging.info(f'run_{run_id}-end')

        # Return to original pictogram positions to prevent double indexing
        self.screen.default_order_pictograms()

        # Finish block
        self.screen.draw_text(f'Block {block_id} complete!\nPlease wait for instructions.')
        self.screen.description_text.setHeight(60)
        self.screen.win.flip()
            
    def run_run(self, run_id: int):
        """Run a single run with multiple trials"""
        # Get prerandomized conditions order
        conditions_order = self.df_trial_orders[f'run_{run_id}'].tolist()
        logging.info(f'run:{run_id}; conditions order: {conditions_order}')

        for trial_id, condition in enumerate(conditions_order):
            logging.info(f'trial_{trial_id}-start;{condition}')
            self.run_trial(condition=condition, trial_id=trial_id, run_id=run_id)
            logging.info(f'trial_{trial_id}-end;{condition}')
        # return pictograms to their original order
        self.screen.default_order_pictograms()
        
    def run_trial(self, condition: str, trial_id: int, run_id: int):
        # Select mode
        mode = condition.split('_')[0]
        target_id = self.df_obj_orders[f'run_{run_id}'][f'trial_{trial_id}']
        target_obj = self.objects[target_id]
        # Get ref and play audio cue
        ref_id = np.random.choice(np.arange(8), 1)[0]
        ref_obj = self.objects[ref_id]
        
        # Run trial based on mode
        self.screen.screen_warmup(duration=self.trial_rest_duration) # Initial warmup before start of trial
        
        if condition == 0:
            codebook = list(self.codebook_kolkhorst[run_id, :, target_id])
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode)
            self.laser_controller.run_trial_erp(codebook, target_id, trial_id=trial_id, on_duration=self.erp_on_duration, off_duration=self.erp_off_duration)
        elif condition == 1:
            codebook = list(self.codebook_fast_erp[run_id, :, target_id])
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode)
            self.laser_controller.run_trial_erp(codebook, target_id, trial_id=trial_id, on_duration=self.erp_on_duration, off_duration=self.erp_off_duration)
        elif condition == 2:
            codebook = list(self.codebook_cvep[run_id, :, target_id])
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode)
            self.laser_controller.run_trial_cvep(codebook=codebook, target_id=target_id, trial_id=trial_id, on_duration=1/self.refresh_rate)
        elif condition == 3:
            codebook = list(self.codebook_fast_erp[run_id, :, target_id])
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode)
            self.screen.run_trial_erp(codebook, target_id=target_id, trial_id=trial_id, n_stim_on_frames=self.erp_on_frames, n_stim_off_frames=self.erp_off_frames)
        elif condition == 4:
            codebook = list(self.codebook_cvep[run_id, :, target_id])
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode)
            self.screen.run_trial_cvep(codebook, target_id=target_id, trial_id=trial_id)
        else:
            raise ValueError(f'Condition doesnt exist: {condition}')
        
        
        perf_sleep(self.trial_rest_duration) # 3 second rest after trials
    
    def resting_state_recording(self):
        self.screen.draw_text('.')
        self.screen.description_text.setHeight(200)
        self.screen.win.flip()
        if input('Start eyes open recording? y/n\n') == 'y':
            self.marker_outlet.push_sample(['Start eyes open'])
            perf_sleep(150)
            self.marker_outlet.push_sample(['End eyes open'])

        if input('Start eyes closed recording? y/n\n') == 'y':
            self.marker_outlet.push_sample(['Start eyes closed'])
            perf_sleep(150)
            self.marker_outlet.push_sample(['End eyes closed'])

        self.screen.draw_text('Resting state recording finished')
        self.screen.description_text.setHeight(50)
        self.screen.win.flip()
        

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
    controller.run_session()
