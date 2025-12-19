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
            0: 'can', 
            1: 'bandage', 
            2: 'remote', 
            3: 'bottle', 
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

        self.n_blocks = 3
        self.n_runs = 4
        self.n_trials = 10
        self.trial_duration = 12
        self.trial_duration_kolkhorst = 24
        self.trial_rest_duration = 3
        self.run_rest_duration = 20
        self.block_rest_duration = 60
        self.resting_state_duration = 90
        
        # Screen settings
        self.refresh_rate = 60 # Hz

        # ERP settings
        self.erp_on_duration = 0.1
        self.erp_off_duration = 0.15

        # c-VEP settings
        self.cvep_on_duration = 1 / self.refresh_rate
        self.cvep_off_duration = 0
        
        # Filepath for audio cues
        self.cue_audio_path = './tts/queries/psychopy_slowed'
        self.random_wait_duration = (3, 5)
        

        # Screen settings
        self.erp_on_frames = int(self.erp_on_duration * self.refresh_rate) # Should be 6 frames for 60hz monitor
        self.erp_off_frames = int(self.erp_off_duration * self.refresh_rate) # Should be 6 frames for 60hz monitor
        self.cvep_on_frames = 1
        self.screen_warmup_duration = self.trial_rest_duration  # seconds
        
        # Init laser controller
        self.laser_controller = LaserController()

        # Init button box controller
        self.button_box_controller = ButtonBoxController()

        # Stim verify duration for familiarization
        self.verify_duration = (1, 1)

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
        self.screen.draw_sensor_box('black')
        self.screen.draw_text('Start resting state eye open? y/n\n')
        self.screen.win.flip()
        print("###########################################")
        print('Follow instructions on screen.')
        print("###########################################")
        key = event.waitKeys()
        if key == ['y']:
            self.resting_state_eyes_open()

        self.screen.draw_text('Start resting state eye closed? y/n\n')
        self.screen.win.flip()
        print("###########################################")
        print('Follow instructions on screen.')
        print("###########################################")
        key = event.waitKeys()
        if key == ['y']:
            self.resting_state_eyes_closed()

        self.screen.draw_text('Start Familiarization? y/n\n')
        self.screen.win.flip()
        print("###########################################")
        print('Follow instructions on screen.')
        print("###########################################")
        key = event.waitKeys()
        if key == ['y']:
            self.familiarization()
        
        self.screen.draw_text('Start experiment? y/n\n')
        self.screen.win.flip()
        print("###########################################")
        print('Follow instructions on screen.')
        print("###########################################")
        key = event.waitKeys()
        if key != ['y']:
            self.exit()
        self.laser_controller.off()

        # Start experiment
        for block_id in range(self.n_blocks):
            # Start block
            self.misc_marker_outlet.push_sample([f'block_{block_id}-start'])
            self.run_block(block_id)
            self.misc_marker_outlet.push_sample([f'block_{block_id}-end'])
            
            self.misc_marker_outlet.push_sample([f'block_{block_id}_rest-start'])
            self.screen.draw_text(f'Block: {block_id + 1} complete. Press any key to start next block.')
            self.screen.win.flip()
            print("###########################################")
            print(f'Block: {block_id + 1} complete. Follow instructions on screen.')
            print("###########################################")
            event.waitKeys()
            self.misc_marker_outlet.push_sample([f'block_{block_id}_rest-end'])
            
        self.screen.draw_sensor_box('black')
        self.screen.draw_text('Start resting state eye open? y/n\n')
        self.screen.win.flip()
        print("###########################################")
        print('Follow instructions on screen.')
        print("###########################################")
        key = event.waitKeys()
        if key == ['y']:
            self.resting_state_eyes_open()

        self.screen.draw_text('Start resting state eye closed? y/n\n')
        self.screen.win.flip()
        print("###########################################")
        print('Follow instructions on screen.')
        print("###########################################")
        key = event.waitKeys()
        if key == ['y']:
            self.resting_state_eyes_closed()

        self.screen.draw_text('Start Refamiliarization? y/n\n')
        self.screen.win.flip()
        print("###########################################")
        print('Follow instructions on screen.')
        print("###########################################")
        key = event.waitKeys()
        if key == ['y']:
            self.familiarization()

        self.screen.draw_text('Thank you! You have successfully completed the experiment!\nWait for the researcher for further instructions...')
        self.screen.win.flip()
        print("###########################################")
        print('Experiment complete!')
        print("###########################################")
        event.waitKeys()

    def run_block(self, block_id: int) -> None:
        """Run a block with multiple runs"""
        # Get randomize pictograms
        self.new_pictograms_order = self.df_pictogram_orders[f'block_{block_id}'].tolist()
        print('New pictograms order:', self.new_pictograms_order)
        # Initialize screen
        self.screen.init_boxes(n_boxes=self.n_objs)
        self.screen.reorder_pictograms(self.new_pictograms_order)
        self.misc_marker_outlet.push_sample([f'pictograms order: {self.new_pictograms_order}'])
        self.screen.screen_warmup(3)

        # Start block
        for run_id in range(self.n_runs):
            
            run_id = run_id + block_id * self.n_runs
            if run_id != 1:
                continue
            print("rUND iD:", run_id)
            # Start run
            self.misc_marker_outlet.push_sample([f'run_{run_id}-start'])
            self.run_run(run_id)
            self.misc_marker_outlet.push_sample([f'run_{run_id}-end'])

            # Run rest
            self.misc_marker_outlet.push_sample([f'run_{run_id}_rest-start'])
            self.screen.draw_text(f'Run: {run_id + 1} complete. Press any key to start next run.')
            self.screen.win.flip()
            print("###########################################")
            print(f'Run: {run_id + 1} complete. Follow instructions on screen.')
            print("###########################################")
            event.waitKeys()
            self.misc_marker_outlet.push_sample([f'run_{run_id}_rest-end'])

        # Return to original pictogram positions to prevent double indexing
        self.screen.default_order_pictograms()
            
    def run_run(self, run_id: int) -> None:
        """Run a single run with multiple trials"""
        # Get conditions order
        conditions_order = self.df_trial_orders[f'run_{run_id}'].tolist()
        self.misc_marker_outlet.push_sample([f'run:{run_id}; conditions order: {conditions_order}'])

        # Start run
        for trial_id, condition in enumerate(conditions_order):
            # Start trial
            self.misc_marker_outlet.push_sample([f'trial_{trial_id}-start;{condition}'])
            self.run_trial(condition=condition, trial_id=trial_id, run_id=run_id, play_audio_once=False, verify_target=False)
            self.misc_marker_outlet.push_sample([f'trial_{trial_id}-end;{condition}'])
            perf_sleep(1) # wait 1 second before saying done to keep response from last stimulus
            self.audio_controller.play_done()

            # Start trial rest
            self.misc_marker_outlet.push_sample([f'trial_{trial_id}_rest-start;{condition}'])
            perf_sleep(self.trial_rest_duration) # 3 second rest after trials
            self.misc_marker_outlet.push_sample([f'trial_{trial_id}_rest-end;{condition}'])

    def run_trial(self, condition: str, trial_id: int, run_id: int, play_audio_once: bool=False, verify_target: bool=False) -> None:
        # Display stimuli
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

        # Get ref object and play audio cue
        ref_id = np.random.choice([i for i in range(self.n_objs) if i!=target_id])
        ref_obj = self.objects[ref_id]
        print(f'target obj: {target_obj}, ref obj: {ref_obj}')
        self.misc_marker_outlet.push_sample([f'target obj: {target_obj}, ref obj: {ref_obj}'])
        # Run trial based on mode
        if condition == 0:
            # Load codebook
            codebook = self.codebook_kolkhorst[target_id]
            # Play audio cue
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode, play_audio_once=play_audio_once)
            self.laser_controller.off()
            # For familiarization purposes. Turn target stimulus on for 1s and off for 1s before starting trial for target verification.
            if verify_target:
                self.laser_controller.send_lasers_values([0 if i!= target_id else 1 for i in range(self.n_objs)])
                perf_sleep(self.verify_duration[0])
                self.laser_controller.send_lasers_values([0] * self.n_objs)
                perf_sleep(self.verify_duration[1])
            # wait for 3~5 seconds after audio cue
            random_wait(self.random_wait_duration[0], self.random_wait_duration[1])
            # Start trial
            self.laser_controller.run_trial_kolkhorst(codebook, target_id, trial_id=trial_id, run_id=run_id, on_duration=self.erp_on_duration, off_duration=self.erp_off_duration)
        elif condition == 1:
            # Load codebook
            codebook = self.codebook_fast_erp[target_id]
            # Play audio cue
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode, play_audio_once=play_audio_once)
            self.laser_controller.off()
            # For familiarization purposes. Turn target stimulus on for 1s and off for 1s before starting trial for target verification.
            if verify_target:
                self.laser_controller.send_lasers_values([0 if i!= target_id else 1 for i in range(self.n_objs)])
                perf_sleep(self.verify_duration[0])
                self.laser_controller.send_lasers_values([0] * self.n_objs)
                perf_sleep(self.verify_duration[0])
            # wait for 3~5 seconds after audio cue
            random_wait(self.random_wait_duration[0], self.random_wait_duration[1])
            # Start trial
            self.laser_controller.run_trial_erp(codebook, target_id, trial_id=trial_id, run_id=run_id, on_duration=self.erp_on_duration, off_duration=self.erp_off_duration)
        elif condition == 2:
            # Load codebook
            codebook = self.codebook_cvep[target_id]
            # Play audio cue
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode, play_audio_once=play_audio_once)
            self.laser_controller.off()
            # For familiarization purposes. Turn target stimulus on for 1s and off for 1s before starting trial for target verification.
            if verify_target:
                self.laser_controller.send_lasers_values([0 if i!= target_id else 1 for i in range(self.n_objs)])
                perf_sleep(self.verify_duration[0])
                self.laser_controller.send_lasers_values([0] * self.n_objs)
                perf_sleep(self.verify_duration[1])
            # wait for 3~5 seconds after audio cue
            random_wait(self.random_wait_duration[0], self.random_wait_duration[1])
            # Start trial
            self.laser_controller.run_trial_cvep(codebook=codebook, target_id=target_id, trial_id=trial_id, run_id=run_id, on_duration=1/self.refresh_rate)
        elif condition == 3:
            # Load codebook
            codebook = self.codebook_fast_erp[target_id]
            # Get new target id from rearranged pictograms
            new_target_id = self.new_pictograms_order.index(target_id)
            # Play audio cue
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode, play_audio_once=play_audio_once)
            self.laser_controller.off()
            # For familiarization purposes. Turn target stimulus on for 1s and off for 1s before starting trial for target verification.
            if verify_target:
                # 1 second on
                tmp_codebook = np.zeros((self.refresh_rate * self.verify_duration[0], self.n_objs)) # 1s codebook
                tmp_codebook[:, new_target_id] = 1
                self.screen.run_trial_cvep(tmp_codebook, new_target_id, trial_id=999, run_id=999)
                # 1 second off
                self.screen.screen_warmup(self.verify_duration[1])
            # wait 3 to 5 seconds
            random_wait(self.random_wait_duration[0] - self.verify_duration[0] - self.verify_duration[1], self.random_wait_duration[1] - self.verify_duration[0] - self.verify_duration[1])
            self.screen.screen_warmup(self.verify_duration[0] + self.verify_duration[1])
            # Start trial
            self.screen.run_trial_erp(codebook, target_id=new_target_id, trial_id=trial_id, run_id=run_id, n_stim_on_frames=self.erp_on_frames, n_stim_off_frames=self.erp_off_frames)
        elif condition == 4:
            # Load codebook
            codebook = self.codebook_cvep[target_id]
            # Get new target id after rearranged pictograms
            new_target_id = self.new_pictograms_order.index(target_id)
            # Play audio cue
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode, play_audio_once=play_audio_once)
            self.laser_controller.off()
            # For familiarization purposes. Turn target stimulus on for 1s and off for 1s before starting trial for target verification.
            if verify_target:
                # 1 second on
                tmp_codebook = np.zeros((self.refresh_rate * self.verify_duration[0], self.n_objs))
                tmp_codebook[:, new_target_id] = 1
                self.screen.run_trial_cvep(tmp_codebook, new_target_id, trial_id=999, run_id=999)
                # 1 second off
                self.screen.screen_warmup(self.verify_duration[1])
            # wait 3 to 5 seconds
            random_wait(self.random_wait_duration[0] - self.verify_duration[0] - self.verify_duration[1], self.random_wait_duration[1] - self.verify_duration[0] - self.verify_duration[1])
            self.screen.screen_warmup(self.verify_duration[0] + self.verify_duration[1])
            # Start trial
            self.screen.run_trial_cvep(codebook, target_id=new_target_id, trial_id=trial_id, run_id=run_id)
        else:
            raise ValueError(f'Condition doesnt exist: {condition}')

    def resting_state_eyes_open(self) -> None:
        """Resting state eyes open recording session."""
        # Start countdown
        self.text_countdown(duration=10, text='Resting state. Eyes open.')
        # Display a dot on screen
        self.screen.description_text.setHeight(200)
        self.screen.draw_text('.')
        self.screen.win.flip()

        # Wait 2s before starting
        perf_sleep(2)
        self.marker_outlet.push_sample(['Start eyes open'])
        perf_sleep(self.resting_state_duration)
        self.marker_outlet.push_sample(['End eyes open'])
        print('Resting state eyes open finished.\n')
        # Display text.
        self.screen.description_text.setHeight(100)
        self.screen.draw_text('Resting state recording finished')
        self.screen.win.flip()

    def resting_state_eyes_closed(self):
        """Resting state eyes closed recording session."""
        # Start countdown
        self.text_countdown(duration=10, text='Resting state. Eyes closed.')
        # Wait 2s before starting
        perf_sleep(2)
        self.marker_outlet.push_sample(['Start eyes closed'])
        perf_sleep(self.resting_state_duration)
        self.marker_outlet.push_sample(['End eyes closed'])
        print('Resting state eyes closed finished.\n')
        # Display text
        self.screen.description_text.setHeight(100)
        self.screen.draw_text('Resting state recording finished')
        self.screen.win.flip()
        
    def familiarization(self):
        # Audio cue, button box familiarization
        while True:
            target_obj_id = int(input('Target obj id: 0, 1, 2, 3, 4, 5, 6, 7\n'))
            if target_obj_id not in [0, 1, 2, 3, 4, 5, 6, 7]:
                break
            mode = int(input('Mode: 0, 1\n'))
            mode = 'scene' if mode == 0 else 'screen'
            ref_obj = np.random.choice(list(self.objects.values()))
            target_obj = self.objects[target_obj_id]
            self.audio_controller.cue_audio(ref_obj=ref_obj, target_obj=target_obj, mode=mode)

        while True:
            condition = int(input('Select condition:\n 0, 1, 2, 3, 4\n'))
            if condition not in [0, 1, 2, 3, 4]:
                break
            play_audio_once = int(input('Play once? 0, 1\n'))
            verify_target = int(input('Verify target? 0, 1\n'))
            run_id = np.random.choice(np.arange(self.n_runs * self.n_blocks))
            trial_id = np.random.choice(np.arange(self.n_trials))
            self.run_trial(condition, trial_id=trial_id, run_id=run_id, play_audio_once=play_audio_once, verify_target=verify_target)

    def exit(self):
        self.laser_controller.close()
        self.button_box_controller.close()
        self.screen.win.close()
        exit(0)

if __name__ == "__main__":
    controller = StimController()
    try:
        controller.run_session()
    except KeyboardInterrupt:
        print('Graceful quit.')
        controller.exit()
    


