import os
import glob
import psutil
import serial
import time
import datetime
import numpy as np
from pylsl import StreamInfo, StreamOutlet, resolve_streams
import logging
from utils import perf_sleep

from typing import List

logger = logging.getLogger(__name__)

class StimController:
    def __init__(self, port: str):
        self.port = port
        self.baud_rate = 115200
        
        # self.optimize_timer_resolution()
        
        self.codebooks = []
        self.n_objs = 8
        
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
        # Start description stream
        self.desc_outlet = None
        self.init_desc_lsl_stream()
        
        # Experimental setup for condition 1
        self.sequence_on_duration = 0.1
        self.sequence_off_duration = 0.15
        self.sequence_duration = self.sequence_on_duration + self.sequence_off_duration
        self.cue_duration = 6
        self.trial_duration = 12 # Except condition 1 where it is 24 seconds
        self.trial_rest_duration = 3
        self.n_trials = self.n_objs

        self.run_rest_duration = 30
        self.n_runs = 8
        self.obj_order = np.arange(self.n_objs)
        self.obj_orders = {}
        
        # Exeriment vars
        self.trial_num = 1
        self.run_num = 1
        self.block_num = 1
    
    def connect_teensy(self) -> None:
        try:
            self.teensy = serial.Serial(self.port, self.baud_rate, timeout=1)
            perf_sleep(2)  # Wait for Arduino to initialize
        except Exception as e:
            logging.warning(f"Teensy not connected: {e}")

    def connect_button_box(self, port='COM6', baud_rate='115200', timeout=1.0) -> None:
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
        
    def init_desc_lsl_stream(self) -> None:
        info = StreamInfo(name='DescriptionStream', type='Marker', channel_count=1, channel_format=3, nominal_srate=0)
        self.desc_outlet = StreamOutlet(info)
    
    def send_laser_values(self, values) -> None:
        if self.teensy is not None:
            data_str = ",".join(map(str, values)) + "\n"
            self.teensy.write(data_str.encode())  # Send data
    
    def load_codebook(self, filepath: str) -> np.ndarray:
        codebook = np.load(filepath).T
        assert codebook.shape[1] == self.n_objs, f'Codebook shape should be (n_sequences, {self.n_objs}). Current shape: {codebook.shape}'
        return codebook

    def load_codebooks_block_1(self, filepath: str='./codebooks/condition_1/codebook_1_henrich.npy') -> None:
        """Block 1 aka Henrich's codebook"""
        self.codebooks = []
        codebook = self.load_codebook(filepath)
        for _ in range(self.n_objs):
            self.codebooks.append(codebook.tolist())
        logging.info(f'Codebooks loaded. shape: {np.array(self.codebooks).shape}')
            
    def load_codebooks_block_2(self, dir: str='./codebooks/condition_2') -> None:
        """Block 2 aka custom codebook"""
        self.codebooks = []
        
        fpaths = sorted(glob.glob(f'{dir}/codebook_obj_*.npy'))
        assert len(fpaths) == self.n_objs, f'there should be {self.n_objs} codebooks for block 2. Current codebooks: {len(fpaths)}'
        
        for fpath in fpaths:
            codebook = self.load_codebook(fpath).tolist()
            self.codebooks.append(codebook)
        logging.info(f'Codebooks loaded. shape: {np.array(self.codebooks).shape}')
        
    def load_codebooks_block_3(self, fpath: str='./codebooks/condition_3/mseq_61_shift_8.npy') -> None:
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
        self.post_marker('Trial start')
        for sequence in codebook:
            sequence_start_time = time.perf_counter()
            self.run_sequence(sequence)
            dt = time.perf_counter() - sequence_start_time
            logging.info(f'Sequence duration: {dt.seconds // 60} mins {dt.seconds % 60} secs {dt.microseconds / 1000} ms')
        self.post_marker('Trial end')
        self.trial_num = self.trial_num + 1
            
    def run_run(self):
        """Run a single run with multiple trials"""
        self.obj_order = np.random.permutation(np.arange(self.n_objs))
        codebooks = self.codebooks(self.obj_order)
        self.post_marker('Run start')
        for idx, codebook in zip(self.obj_order, codebooks):
            trial_start_time = time.perf_counter()
            self.run_trial(codebook)
            dt = time.perf_counter() - trial_start_time
            logging.info(f'Trial duration: {dt.seconds // 60} mins {dt.seconds % 60} secs {dt.microseconds / 1000} ms')
            # Rest for trial_rest_duration seconds
            rest_end_time = time.perf_counter() + self.trial_rest_duration
            self.post_marker('Trial Rest')
            self.send_laser_values([0] * 8)
            self.post_sequence([0] * 8)
            while time.perf_counter() < rest_end_time:
                pass
        self.post_marker('Run end')
        self.trial_num = 1
        self.run_num = self.run_num + 1
                
    def run_block(self):
        """Run a block with multiple runs"""
        self.post_marker('Block start')
        for _ in range(self.n_runs):
            self.post_marker('Run Rest')
            for i in range(30):
                perf_sleep(1)
                
            run_start_time = time.perf_counter()
            self.run_run()
            dt = time.perf_counter() - run_start_time
            logging.info(f'Run duration: {dt.seconds // 60} mins {dt.seconds % 60} secs {dt.microseconds / 1000} ms')
        self.post_marker('Block end')
        self.run_num = 1
        self.block_num = self.block_num + 1
        
    def run_session(self):
        # Start ERP condition 1
        controller.load_codebooks_block_1()
        controller.run_block()
        
        # Start ERP condition 2
        # controller.load_codebooks_block_2()
        # controller.run_block()
        
        # # # Start cVEP
        # controller.load_codebooks_block_3()
        # controller.sequence_on_duration = 1/63
        # controller.sequence_off_duration = 0
        # controller.run_block()
        
    def run_test(self):
        """Run a test sequence"""
        self.post_marker('Test start')
        for i in range(8):
            self.run_sequence([0] * 8)
            self.run_sequence([1] * 8)
        self.post_marker('Test end')
    

if __name__ == "__main__":
    # Set logging filaname to ./logs/log_%Y-%m-%d_%H-%M-%S.log
    filename = datetime.datetime.now().strftime('./logs/log_%Y-%m-%d_%H-%M-%S.log')
    logging.basicConfig(
        filename=filename, 
        filemode='w',
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    port = 'COM7'  # Windows
    # port = '/dev/tty.usbmodem156466901' # Mac
    controller = StimController(port)
    
    # Start experiment
    kw = input('Start run? y/n\n')
    
    test = True
    if kw == 'y':
        if test:
            controller.run_test()
        else:
            controller.run_session()