import time
import datetime
import logging
import random
import numpy as np
import pandas as pd
from psychopy import event

from utils import perf_sleep, random_wait
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
        self.codebook_kolkhorst = load_codebooks_block_1().astype(int).tolist()
        self.codebook_fast_erp = load_codebooks_block_2().astype(int).tolist()
        self.codebook_cvep = load_codebooks_block_3().astype(int).tolist()
        
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

        self.df_trial_orders = pd.read_csv('./config/trial_orders.csv', index_col=0)
        self.df_obj_orders = pd.read_csv('./config/obj_orders.csv', index_col=0)
        self.df_pictogram_orders = pd.read_csv('./config/pictogram_orders.csv', index_col=0)
        self.new_pictograms_order = np.arange(8).tolist()

        self.n_blocks = 4
        self.n_runs = 8
        self.n_trials = 10
        self.trial_duration = 12
        self.trial_duration_kolkhorst = 24
        self.trial_rest_duration = 3
        self.run_rest_duration = 20
        self.block_rest_duration = 60
        self.resting_state_duration = 150
        
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
        self.verify_lasers = False
        self.verify_screen = False

        # Init button box controller
        self.button_box_controller = ButtonBoxController()

        # Init audio controller
        self.audio_controller = AudioController(audio_path='./tts/queries/psychopy_slowed', button_box=self.button_box_controller)

        # Init screen stimulus window
        self.screen = ScreenStimWindow(self.objects)
        
        # Init markers for resting state
        info = StreamInfo(name='RestingStateMarkerStream', type='Marker', channel_count=1, channel_format=cf_string, nominal_srate=0, source_id='resting_state_marker_stream_id')
        self.marker_outlet = StreamOutlet(info)

        info = StreamInfo(name='MiscMarkerStream', type='Marker', channel_count=1, channel_format=cf_string, nominal_srate=0, source_id='misc_marker_stream_id')
        self.misc_marker_outlet = StreamOutlet(info)
        

    def text_countdown(self, duration: int, text: str='Rest'):
        for t in range(duration):
            start_time = time.perf_counter()
            self.screen.draw_text(text + f'\n Experiment will start in\n{duration - t} seconds.')
            # self.screen.description_text.setHeight(60)
            self.screen.win.flip()
            perf_sleep(1 - 1/self.refresh_rate)
        self.screen.draw_text('')
        self.screen.description_text.setHeight(50)
        self.screen.win.flip()

    def run_session(self):
        self.laser_controller.on()
        _ = input('Finished setting up the lasers? y/n\n')
        
        self.laser_controller.off()
        self.screen.draw_sensor_box('black')
        self.screen.draw_text('Press any key to start!')
        self.screen.win.flip()
        event.waitKeys()

        # self.misc_marker_outlet.push_sample(['start_resting_state'])
        # self.resting_state_recording()
        # self.misc_marker_outlet.push_sample(['end_resting_state'])

        # self.text_countdown(duration=10, text='Laser Quick Flash.')

        # _ = input('Start laser isolated flash?')
        # self.misc_marker_outlet.push_sample(['start_laser_isolated_flash'])
        # self.laser_controller.run_isolated_flash(8)
        # self.misc_marker_outlet.push_sample(['end_laser_isolated_flash'])

        # _ = input('Start laser burst flash?')
        # self.misc_marker_outlet.push_sample(['start_laser_burst_flash'])
        # self.laser_controller.run_burst_flash(80)
        # self.misc_marker_outlet.push_sample(['end_laser_burst_flash'])

        self.laser_controller.off()
        self.text_countdown(duration=10, text='Screen Quick Flash.')

        # _ = input('Start screen isolated flash?')
        # self.misc_marker_outlet.push_sample(['start_screen_isolated_flash'])
        # self.screen.test_isolated_flash(8)
        # self.misc_marker_outlet.push_sample(['end_screen_isolated_flash'])

        
        # _ = input('Start screen burst flash?')
        # self.misc_marker_outlet.push_sample(['start_screen_burst_flash'])
        # self.screen.test_burst_flash(40)
        # self.misc_marker_outlet.push_sample(['end_screen_burst_flash'])

        # Start experiment
        self.n_blocks = 1
        for block_id in range(self.n_blocks):
            # Start block
            self.misc_marker_outlet.push_sample([f'block_{block_id}-start'])
            self.run_block(block_id)
            self.text_countdown(self.block_rest_duration, text=f'Block: {block_id} complete.')
            self.misc_marker_outlet.push_sample([f'block_{block_id}-end'])

        self.screen.draw_text('Thank you! You have successfully completed the experiment!')
        self.screen.win.flip()

    def run_block(self, block_id: int):
        """Run a block with multiple runs"""
        # Get prerandomized pictogram order
        self.new_pictograms_order = self.df_pictogram_orders[f'block_{block_id}'].tolist()
        print('New pictograms order:', self.new_pictograms_order)
        # Initialize screen
        self.screen.init_boxes(n_boxes=8)
        self.screen.reorder_pictograms(self.new_pictograms_order)
        self.misc_marker_outlet.push_sample([f'pictograms order: {self.new_pictograms_order}'])
        self.screen.screen_warmup(3)

        for run_id in range(self.n_runs):
            self.misc_marker_outlet.push_sample([f'run_{run_id}-start'])
            self.run_run(run_id)
            self.misc_marker_outlet.push_sample([f'run_{run_id}-end'])

            self.misc_marker_outlet.push_sample([f'run_{run_id}_rest-start'])
            self.text_countdown(self.run_rest_duration, text=f'Run: {run_id + 1} complete.')
            self.misc_marker_outlet.push_sample([f'run_{run_id}_rest-end'])
            



        # Return to original pictogram positions to prevent double indexing
        self.screen.default_order_pictograms()
        self.misc_marker_outlet.push_sample([f'pictograms order: {[i for i in range(8)]}'])

        # Finish block
        self.screen.draw_text(f'Block {block_id} complete!\nPlease wait for instructions.')
        self.screen.description_text.setHeight(60)
        self.screen.win.flip()
            
    def run_run(self, run_id: int):
        """Run a single run with multiple trials"""
        # Get prerandomized conditions order
        conditions_order = self.df_trial_orders[f'run_{run_id}'].tolist()
        self.misc_marker_outlet.push_sample([f'run:{run_id}; conditions order: {conditions_order}'])

        for trial_id, condition in enumerate(conditions_order):
            self.misc_marker_outlet.push_sample([f'trial_{trial_id}-start;{condition}'])
            self.run_trial(condition=condition, trial_id=trial_id, run_id=run_id)
            self.misc_marker_outlet.push_sample([f'trial_{trial_id}-end;{condition}'])

            self.misc_marker_outlet.push_sample([f'trial_{trial_id}_rest-start;{condition}'])
            perf_sleep(self.trial_rest_duration) # 3 second rest after trials
            self.misc_marker_outlet.push_sample([f'trial_{trial_id}_rest-end;{condition}'])
        # return pictograms to their original order

    def run_trial(self, condition: str, trial_id: int, run_id: int):
        # Show stims
        self.laser_controller.on()
        self.screen.screen_warmup(0.1)
        
        # Select condition
        if condition in [0, 1, 2]:
            mode = 'scene'
        elif condition in [3, 4]:
            mode = 'screen'
        else:
            ValueError(f'Condition not found: {condition}')

        # Get target id and obj
        target_id = self.df_obj_orders[f'run_{run_id}'][f'trial_{trial_id}']
        target_obj = self.objects[target_id]

        # Get ref and play audio cue
        ref_id = np.random.choice([i for i in range(self.n_objs) if i!=target_id])
        ref_obj = self.objects[ref_id]
        print(f'target obj: {target_obj}, ref obj: {ref_obj}')
        self.misc_marker_outlet.push_sample([f'target obj: {target_obj}, ref obj: {ref_obj}'])
        # Run trial based on mode
        if condition == 0:
            # Load codebook
            codebook = self.codebook_kolkhorst[run_id]
            # Cue audio
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode)
            self.laser_controller.off()
            # Verify target
            if self.verify_lasers:
                self.laser_controller.send_lasers_values([0 if i!= target_id else 1 for i in range(8)])
                perf_sleep(1)
                self.laser_controller.send_lasers_values([0] * 8)
                perf_sleep(1)
            # wait for 3~5 seconds
            random_wait(3, 5)
            self.laser_controller.run_trial_kolkhorst(codebook, target_id, trial_id=trial_id, run_id=run_id, on_duration=self.erp_on_duration, off_duration=self.erp_off_duration)
        elif condition == 1:
            # Load codebook
            codebook = self.codebook_fast_erp[run_id]
            # Play audio
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode)
            # Turn off lasers after key press
            self.laser_controller.off()
            # Verify target
            if self.verify_lasers:
                self.laser_controller.send_lasers_values([0 if i!= target_id else 1 for i in range(8)])
                perf_sleep(1)
                self.laser_controller.send_lasers_values([0] * 8)
                perf_sleep(1)
            # wait for 3~5 seconds
            random_wait(3, 5)
            self.laser_controller.run_trial_erp(codebook, target_id, trial_id=trial_id, run_id=run_id, on_duration=self.erp_on_duration, off_duration=self.erp_off_duration)
        elif condition == 2:
            # Load codebook
            codebook = self.codebook_cvep[run_id]
            # Play audio cue
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode)
            # Turn lasers off after key press
            self.laser_controller.off()
            # Verify target
            if self.verify_lasers:
                self.laser_controller.send_lasers_values([0 if i!= target_id else 1 for i in range(8)])
                perf_sleep(1)
                self.laser_controller.send_lasers_values([0] * 8)
                perf_sleep(1)
            # wait for 3~5 seconds
            random_wait(3, 5)
            self.laser_controller.run_trial_cvep(codebook=codebook, target_id=target_id, trial_id=trial_id, run_id=run_id, on_duration=1/self.refresh_rate)
        elif condition == 3:
            # Load codebook
            codebook = self.codebook_fast_erp[run_id]
            # Get new target id after rearranged pictograms
            new_target_id = self.new_pictograms_order.index(target_id)
            # Play audio cue
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode)
            # Turn lasers off after key press
            self.laser_controller.off()
            # Verify target
            if self.verify_screen:
                tmp_codebook = np.zeros((60, self.n_objs))
                tmp_codebook[:, new_target_id] = 1
                # 1 second on
                self.screen.run_trial_cvep(tmp_codebook, new_target_id, trial_id=999, run_id=999)
                # 1 second off
                self.screen.screen_warmup(1)
            # wait 3 to 5 seconds
            random_wait(1, 3)
            self.screen.screen_warmup(2)
            self.screen.run_trial_erp(codebook, target_id=new_target_id, trial_id=trial_id, run_id=run_id, n_stim_on_frames=self.erp_on_frames, n_stim_off_frames=self.erp_off_frames)
        elif condition == 4:
            # Load codebook
            codebook = self.codebook_cvep[run_id]
            # Get new target id after rearranged pictograms
            new_target_id = self.new_pictograms_order.index(target_id)
            # Play audio cue
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode)
            # Turn lasers off after key press
            self.laser_controller.off()
            # Verify target
            if self.verify_screen:
                # 1 second on then off
                tmp_codebook = np.zeros((60, self.n_objs))
                tmp_codebook[:, new_target_id] = 1
                self.screen.run_trial_cvep(tmp_codebook, new_target_id, trial_id=999, run_id=999)
                # 1 second off
                self.screen.screen_warmup(1)
            # wait 3 to 5 seconds
            random_wait(1, 3)
            self.screen.screen_warmup(2)
            self.screen.run_trial_cvep(codebook, target_id=new_target_id, trial_id=trial_id, run_id=run_id)
        else:
            raise ValueError(f'Condition doesnt exist: {condition}')

    def resting_state_recording(self):
        self.text_countdown(duration=10, text='Resting state. Eyes open.')
        self.screen.description_text.setHeight(200)
        self.screen.draw_text('.')
        self.screen.win.flip()
        self.marker_outlet.push_sample(['Start eyes open'])
        perf_sleep(self.resting_state_duration)
        self.marker_outlet.push_sample(['End eyes open'])

        self.screen.description_text.setHeight(100)
        self.screen.win.flip()


        self.text_countdown(duration=10, text='Resting state. Eyes closed.')
        self.marker_outlet.push_sample(['Start eyes closed'])
        perf_sleep(self.resting_state_duration)
        self.marker_outlet.push_sample(['End eyes closed'])

        self.screen.description_text.setHeight(100)
        self.screen.draw_text('Resting state recording finished')
        self.screen.win.flip()

        

if __name__ == "__main__":
    # # Set logging filename to ./logs/log_%Y-%m-%d_%H-%M-%S.log
    # filename = datetime.datetime.now().strftime('./logs/log_%Y-%m-%d_%H-%M-%S.log')
    # logging.basicConfig(
    #     filename=filename, 
    #     filemode='w',
    #     level=logging.INFO, 
    #     format='%(asctime)s - %(levelname)s - %(message)s'
    # )
    controller = StimController()
    # controller.verify_lasers = True
    # controller.verify_screen = True
    # controller.resting_state_duration = 5
    print('Press any button on the experiment window!\n')
    controller.run_session()
    


