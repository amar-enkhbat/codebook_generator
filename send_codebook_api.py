import os
import glob
import datetime
import psutil
import serial
import time
import numpy as np
import requests
from pylsl import StreamInfo, StreamOutlet, resolve_streams
import logging
logger = logging.getLogger(__name__)

class StimController:
    def __init__(self, port: str):
        self.port = port
        self.baud_rate = 115200
        
        self.optimize_timer_resolution()
        
        self.codebooks = []
        self.n_objs = 8
        
        # Connect to teensy
        self.teensy = None
        self.connect_teensy()
        
        # Start marker stream
        self.marker_outlet = None
        self.init_marker_lsl_stream()
        
        # Start description stream
        self.desc_outlet = None
        self.init_desc_lsl_stream()
        
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
        
        # Exeriment vars
        self.trial_num = 1
        self.run_num = 1
        self.block_num = 1
    
    def connect_teensy(self):
        try:
            self.teensy = serial.Serial(self.port, self.baud_rate, timeout=1)
            time.sleep(2)  # Wait for Arduino to initialize
        except Exception as e:
            logging.warning(f"Teensy not connected: {e}")
    
    def init_marker_lsl_stream(self):
        info = StreamInfo(name='LaserMarkerStream', type='Markers', channel_count=1, nominal_srate=0, channel_format='string', source_id='CharacterEvent')
        self.marker_outlet = StreamOutlet(info)
        
    def init_desc_lsl_stream(self):
        info = StreamInfo(name='DescriptionStream', type='Markers', channel_count=1, nominal_srate=0, channel_format='string', source_id='CharacterEvent')
        self.desc_outlet = StreamOutlet(info)
    
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
        
    def load_codebooks_block_3(self, fpath: str='./codebooks/condition_3/mseq_61_shift_8.npy'):
        """Block 2 aka custom cVEP"""
        self.codebooks = []
        
        codebook = self.load_codebook(fpath)
        # Select 8 codebooks
        codebook = np.vstack([codebook] * self.trial_duration)
        self.codebooks = np.array([codebook] * 8)
        self.codebooks = self.codebooks.tolist()
        
        logging.info(f'Codebooks loaded. shape: {np.array(self.codebooks).shape}')
            
    def post_sequence(self, sequence: list):
        """send sequence to lsl stream"""
        try:
            self.marker_outlet.push_sample([str(sequence)])
        except Exception as e:
            logging.warning(f"Error posting sequence: {e}")
            
    def post_description(self, description: str):
        """send description to lsl stream"""
        try:
            self.desc_outlet.push_sample([description])
        except Exception as e:
            logging.warning(f"Error posting description: {e}")

    def run_sequence(self, sequence: list):
        """Run a single sequence"""
        # Turn on the Lasers
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=self.sequence_on_duration)
        self.send_laser_values(sequence)
        self.marker_outlet.push_sample([str(sequence)])
        self.post_sequence(sequence)
        # Wait until turn on duration is over
        while datetime.datetime.now() < end_time:
            pass
        # Turn off the lasers
        if self.sequence_off_duration != 0:
            end_time = datetime.datetime.now() + datetime.timedelta(seconds=self.sequence_off_duration)
            self.send_laser_values([0] * 8)
            self.marker_outlet.push_sample(['off'])
            self.post_sequence([0] * 8)
            # Wait until turn off duration is over
            while datetime.datetime.now() < end_time:
                pass
        
    def run_trial(self, codebook: list):
        """Run a single trial with multiple sequences"""
        self.post_description(f'Block:{self.block_num} Run:{self.run_num} Trial:{self.trial_num}')
        self.marker_outlet.push_sample(['Trial start'])
        for sequence in codebook:
            sequence_start_time = datetime.datetime.now()
            self.run_sequence(sequence)
            dt = datetime.datetime.now() - sequence_start_time
            logging.info(f'Sequence duration: {dt.seconds // 60} mins {dt.seconds % 60} secs {dt.microseconds / 1000} ms')
        self.marker_outlet.push_sample(['Trial end'])
        self.trial_num = self.trial_num + 1
            
    def run_run(self):
        self.marker_outlet.push_sample(['Run start'])
        for codebook in self.codebooks:
            trial_start_time = datetime.datetime.now()
            self.run_trial(codebook)
            dt = datetime.datetime.now() - trial_start_time
            logging.info(f'Trial duration: {dt.seconds // 60} mins {dt.seconds % 60} secs {dt.microseconds / 1000} ms')
            # Rest for trial_rest_duration seconds
            rest_end_time = datetime.datetime.now() + datetime.timedelta(seconds=self.trial_rest_duration)
            self.post_description('Rest')
            self.marker_outlet.push_sample(['Trial Rest'])
            self.send_laser_values([0] * 8)
            self.post_sequence([0] * 8)
            while datetime.datetime.now() < rest_end_time:
                pass
        self.marker_outlet.push_sample(['Run end'])
        self.trial_num = 1
        self.run_num = self.run_num + 1
                
    def run_block(self):
        self.marker_outlet.push_sample(['Block start'])
        for _ in range(self.n_runs):
        #     for i in range(30):
        #         self.post_description(f'Rest. Run start in: {30 - i}')
        #         self.lsl_outlet.push_sample(['Run Rest'])
        #         sleep_s(1)
                
            run_start_time = datetime.datetime.now()
            self.run_run()
            dt = datetime.datetime.now() - run_start_time
            logging.info(f'Run duration: {dt.seconds // 60} mins {dt.seconds % 60} secs {dt.microseconds / 1000} ms')
        self.marker_outlet.push_sample(['Block end'])
        self.run_num = 1
        self.block_num = self.block_num + 1
    

if __name__ == "__main__":
    # Set logging filaname to ./logs/log_%Y-%m-%d_%H-%M-%S.log
    fname = datetime.datetime.now().strftime('./logs/log_%Y-%m-%d_%H-%M-%S.log')
    logging.basicConfig(
        filename=fname, 
        filemode='w',
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    port = 'COM5'  # Change as needed
    port = '/dev/tty.usbmodem156466901'  # Change to the correct port (MAC)
    controller = StimController(port)
    
    # Start recording lsl streams
    # Get list of stream from LSL using pylsl
    streams = resolve_streams(wait_time=1.0)
    print('List of streams:')
    for stream in streams:
        print(f'Name: {stream.name()}, Type: {stream.type()}')
        

    
    kw = input('Start run? y/n\n')
    if kw == 'y':
        # Start ERP condition 1
        # controller.load_codebooks_block_1()
        # controller.run_block()
        
        # # Start ERP condition 2
        # controller.load_codebooks_block_2()
        # controller.run_block()
        
        # Start cVEP
        controller.load_codebooks_block_3()
        controller.sequence_on_duration = 1/63
        controller.sequence_off_duration = 0
        controller.run_block()
        
        controller.post_description('Experiment over.')