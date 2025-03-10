import os
import glob
import datetime
import psutil
import serial
import time
import numpy as np
import requests
from pylsl import StreamInfo, StreamOutlet
from dareplane_utils.general.time import sleep_s
import logging
logger = logging.getLogger(__name__)

class StimController:
    def __init__(self, port: str):
        self.port = port
        self.baud_rate = 115200
        self.url = "http://127.0.0.1:8000/update_sequence"
        self.description_url = "http://127.0.0.1:8000/update_description"
        
        self.optimize_timer_resolution()
        
        self.codebooks = []
        self.n_objs = 8
        
        # Connect to teensy
        self.teensy = None
        self.connect_teensy()
        
        # Start LSL stream
        self.lsl_outlet = None
        self.init_lsl_stream()
        
        # Check if API is running
        try:
            requests.get(self.url)
        except Exception:
            logging.warning("API not running. Not sending data to visual stimulation.")
        
        # Experimental setup for codebooks 1 and 2
        self.sequence_on_duration = 0.1
        self.sequence_off_duration = 0.15
        self.sequence_duration = self.sequence_on_duration + self.sequence_off_duration
        self.trial_duration = 12
        self.trial_rest_duration = 3
        self.n_trials = self.n_objs
        
        self.run_duration = self.trial_duration * self.n_trials + self.trial_rest_duration * (self.n_trials - 1)
        self.run_rest_duration = 30
        self.n_runs = 3
        
        self.trial_num = 1
        self.run_num = 1
        self.block_num = 1
    
    def connect_teensy(self):
        try:
            self.teensy = serial.Serial(self.port, self.baud_rate, timeout=1)
            time.sleep(2)  # Wait for Arduino to initialize
        except Exception as e:
            logging.warning(f"Teensy not connected: {e}")
    
    def init_lsl_stream(self):
        info = StreamInfo(name='LaserMarkerStream', type='Markers', channel_count=1, nominal_srate=0, channel_format='string', source_id='CharacterEvent')
        self.lsl_outlet = StreamOutlet(info)
    
    def optimize_timer_resolution(self):
        """Optimize the timer resolution to improve precision."""
        import ctypes
        try:
            logging.info("Optimizing timer resolution...")
            ctypes.windll.winmm.timeBeginPeriod(1)
            logging.info("Timer resolution set to 1ms.")
        except Exception as e:
            logging.warning(f"Error optimizing timer resolution: {e}")
        
        p = psutil.Process(os.getpid())
        p.nice(psutil.HIGH_PRIORITY_CLASS if os.name == 'nt' else 10)
        logging.info("Priority set. Running script...")
    
    def send_laser_values(self, values):
        if self.teensy is not None:
            data_str = ",".join(map(str, values)) + "\n"
            self.teensy.write(data_str.encode())  # Send data
    
    def load_codebook(self, filepath):
        codebook = np.load(filepath).T
        assert codebook.shape[1] == self.n_objs, f'Codebook shape should be (n_sequences, {self.n_objs}). Current shape: {codebook.shape}'
        return codebook

    def load_codebooks_block_1(self, filepath: str='./codebooks/condition_1/codebook_1_henrich.npy'):
        """Block 1 aka Henrich's codebook"""
        self.codebooks = []
        codebook = self.load_codebook(filepath)
        for _ in range(self.n_objs):
            self.codebooks.append(codebook.tolist())
        logging.info(f'Codebooks loaded. shape: {np.array(self.codebooks).shape}')
            
    def load_codebooks_block_2(self, path: str='./codebooks/condition_2'):
        """Block 2 aka custom codebook"""
        self.codebooks = []
        
        fpaths = sorted(glob.glob(f'{path}/codebook_obj_*.npy'))
        assert len(fpaths) == self.n_objs, f'there should be {self.n_objs} codebooks for block 2. Current codebooks: {len(fpaths)}'
        
        for fpath in fpaths:
            codebook = self.load_codebook(fpath).tolist()
            self.codebooks.append(codebook)
        logging.info(f'Codebooks loaded. shape: {np.array(self.codebooks).shape}')
            
    def post_sequence(self, sequence: list):
        """Post a single sequence to the API"""
        try:
            _ = requests.post(self.url, json={'values': sequence})
        except Exception as e:
            logging.warning(f"Error posting sequence: {e}")
            
    def post_description(self, description: str):
        """Post a description to the API"""
        try:
            _ = requests.post(self.description_url, json={'value': description})
        except Exception as e:
            logging.warning(f"Error posting sequence: {e}")

    def run_sequence(self, sequence: list):
        """Run a single sequence"""
        # Turn on the Lasers
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=self.sequence_on_duration)
        self.send_laser_values(sequence)
        self.post_sequence(sequence)
        self.lsl_outlet.push_sample(['on'])
        # Wait until turn on duration is over
        while datetime.datetime.now() < end_time:
            pass
        
        # Turn off the lasers
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(seconds=self.sequence_off_duration)
        self.send_laser_values([0] * 8)
        self.post_sequence([0] * 8)
        self.lsl_outlet.push_sample(['off'])
        # Wait until turn off duration is over
        while datetime.datetime.now() < end_time:
            pass
    
    def run_trial(self, codebook: list):        
        for sequence in codebook:
            sequence_start_time = datetime.datetime.now()
            self.run_sequence(sequence)
            sequence_end_time = datetime.datetime.now()
            dt = sequence_end_time - sequence_start_time
            logging.info(f'Sequence duration: {dt.seconds // 60} mins {dt.seconds % 60} secs {dt.microseconds / 1000} ms')
            
    def run_run(self):
        # Send a countdown of 5 seconds
        for i in range(5):
            self.post_description(f'Run start in: {5 - i}')
            sleep_s(1)
        
        run_start_time = datetime.datetime.now()
        
        for i, codebook in enumerate(self.codebooks):
            trial_start_time = datetime.datetime.now()
            
            self.post_description(f'Block: {self.block_num}\nRun: {self.run_num}\nTrial: {self.trial_num}')
            self.run_trial(codebook)
            self.trial_num = self.trial_num + 1
            
            self.post_description('Rest')
            sleep_s(3) # Rest time between trials
            
            trial_end_time = datetime.datetime.now()
            dt = trial_end_time - trial_start_time
            logging.info(f'Trial duration: {dt.seconds // 60} mins {dt.seconds % 60} secs {dt.microseconds / 1000} ms')
        
        # Reset lasers
        self.trial_num = 1
        self.send_laser_values([0] * 8)
        self.post_sequence([0] * 8)
        
        run_end_time = datetime.datetime.now()
        dt = run_end_time - run_start_time
        # Print run duration in mins, seconds and milliseconds
        logging.info(f'Run duration: {dt.seconds // 60} mins {dt.seconds % 60} secs {dt.microseconds / 1000} ms')
        
    def run_block(self):
        block_start_time = datetime.datetime.now()
        for _ in range(self.n_runs):
            self.run_run()
            self.run_num = self.run_num + 1
            sleep_s(30) # rest time between runs
            
                
        block_end_time = datetime.datetime.now()
        dt = block_end_time - block_start_time
        # Print run duration in mins, seconds and milliseconds
        logging.info(f'Block duration: {dt.seconds // 60} mins {dt.seconds % 60} secs {dt.microseconds / 1000} ms')

if __name__ == "__main__":
    logging.basicConfig(
        filename='log.log', 
        filemode='w',
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    port = 'COM5'  # Change as needed
    controller = StimController(port)
    
    
    
    kw = input('Start run? y/n\n')
    if kw == 'y':
        controller.load_codebooks_block_1()
        controller.run_block()
        
        controller.load_codebooks_block_2()
        
    controller.post_description('Experiment over.')