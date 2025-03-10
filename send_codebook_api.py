import os
import glob
import datetime
import psutil
import serial
import time
import numpy as np
import requests
import pycurl
import json
from pylsl import StreamInfo, StreamOutlet
from dareplane_utils.general.time import sleep_s


class StimController:
    def __init__(self, port, baud_rate=115200, url="http://127.0.0.1:8000/update_sequence"):
        self.port = port
        self.baud_rate = baud_rate
        self.url = url
        
        self.optimize_timer_resolution()
        
        self.trial_duration = 12
        self.trial_rest_duration = 3
        self.n_trials = 8
        
        self.run_duration = self.trial_duration * self.n_trials + self.trial_rest_duration * (self.n_trials - 1)
        self.run_rest_duration = 30
        self.n_runs = 3
        
        self.arduino = None
        self.outlet = None
        self.init_lsl_stream()
        self.connect_teensy()
        
        self.codebooks = []
        self.n_objs = 8
        
        # Check if API is running
        try:
            requests.get(self.url)
        except Exception:
            print("API not running. Not pushing data to GUI.")
    
    def connect_teensy(self):
        try:
            self.arduino = serial.Serial(self.port, self.baud_rate, timeout=1)
            time.sleep(2)  # Wait for Arduino to initialize
        except Exception as e:
            print(f"Teensy not connected: {e}")
    
    def init_lsl_stream(self):
        info = StreamInfo(name='LaserMarkerStream', type='Markers', channel_count=1, nominal_srate=0, channel_format='string', source_id='CharacterEvent')
        self.outlet = StreamOutlet(info)
    
    def optimize_timer_resolution(self):
        """Optimize the timer resolution to improve precision."""
        import ctypes
        try:
            print("Optimizing timer resolution...")
            ctypes.windll.winmm.timeBeginPeriod(1)
            print("Timer resolution set to 1ms.")
        except Exception as e:
            print(f"Error optimizing timer resolution: {e}")
        
        p = psutil.Process(os.getpid())
        p.nice(psutil.HIGH_PRIORITY_CLASS if os.name == 'nt' else 10)
        print("Priority set. Running script...")
    
    def send_led_values(self, values):
        if self.arduino is not None:
            data_str = ",".join(map(str, values)) + "\n"
            self.arduino.write(data_str.encode())  # Send data
    
    def load_codebook(self, filepath):
        codebook = np.load(filepath).T
        assert codebook.shape[1] == self.n_objs, f'Codebook shape should be (n_sequences, {self.n_objs}). Current shape: {codebook.shape}'
        return codebook

    def load_codebooks_block_1(self, filepath: str='./codebooks/condition_1/codebook_1_henrich.npy'):
        """Block 1 aka Henrich's codebook"""
        self.codebooks = []
        codebook = self.load_codebook(filepath)
        for _ in range(self.n_objs):
            self.codebooks.append(codebook)
        print(f'Codebooks loaded. shape: {np.array(self.codebooks).shape}')
            
    def load_codebooks_block_2(self, path: str='./codebooks/condition_2'):
        """Block 2 aka custom codebook"""
        self.codebooks = []
        
        fpaths = sorted(glob.glob(f'{path}/codebook_obj_*.npy'))
        assert len(fpaths) == self.n_objs, f'there should be {self.n_objs} codebooks for block 2. Current codebooks: {len(fpaths)}'
        
        for fpath in fpaths:
            codebook = self.load_codebook(fpath).tolist()
            self.codebooks.append(codebook)
        print(f'Codebooks loaded. shape: {np.array(self.codebooks).shape}')
            
    def post_sequence(self, sequence: list):
        """Post a single sequence to the API"""
        try:
            _ = requests.post(self.url, json={'sequence': sequence})
        except Exception as e:
            print(f"Error posting sequence: {e}")
        
    def run_sequence(self, sequence: list):
        """Run a single sequence"""
        self.send_led_values(sequence)
        self.post_sequence(sequence)
        self.outlet.push_sample(['on'])
        sleep_s(0.1)
        
        self.send_led_values([0] * 8)
        self.post_sequence([0] * 8)
        self.outlet.push_sample(['off'])
        sleep_s(0.15)
    
    def run_trial(self, codebook: list):        
        for sequence in codebook:
            self.run_sequence(sequence)
            
    def run_run(self):
        kw = input('Start run? y/n\n')
        if kw == 'y':
            run_start_time = datetime.datetime.now()
            
            for codebook in self.codebooks:
                trial_start_time = datetime.datetime.now()
                
                self.run_trial(codebook)
                sleep_s(3) # Rest time between trials
                
                trial_end_time = datetime.datetime.now()
                dt = trial_end_time - trial_start_time
                print(f'Trial duration: {dt.seconds // 60} mins {dt.seconds % 60} secs {dt.microseconds / 1000} ms')
            self.outlet.push_sample(['off'])
            self.send_led_values([0] * 8)
            self.post_sequence([0] * 8)
            
            run_end_time = datetime.datetime.now()
            dt = run_end_time - run_start_time
            # Print run duration in mins, seconds and milliseconds
            print(f'Run duration: {dt.seconds // 60} mins {dt.seconds % 60} secs {dt.microseconds / 1000} ms')

if __name__ == "__main__":
    port = 'COM5'  # Change as needed
    controller = StimController(port)
    # controller.load_codebooks_block_1()
    controller.load_codebooks_block_2()
    
    controller.run_run()