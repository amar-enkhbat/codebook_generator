import serial
import logging
from typing import List
import time
import numpy as np
from pylsl import StreamOutlet, StreamInfo
from utils import perf_sleep, load_codebooks_block_2, load_codebooks_block_3

class LaserController:
    def __init__(self, port: str='COM7'):
        self.marker_ids = {
            'non_target': 100,
            'target': 110,
            'trial_start': 200,
            'trial_end': 210
        }
        self.port = port
        self.teensy = None
        try:
            self.teensy = serial.Serial(port=port, baudrate=115200, timeout=1)
        except Exception as e:
            logging.warning(f"Teensy not connected: {e}")

        # Init marker stream
        info = StreamInfo(name='LaserMarkerStream', type='Marker', channel_count=1, channel_format=5, nominal_srate=0, source_id='laser_marker_stream_id')
        self.marker_outlet = StreamOutlet(info)

    def send_lasers_values(self, values: List[int]) -> None:
        if self.teensy is not None:
            data_str = ",".join(map(str, values)) + "\n"
            self.teensy.write(data_str.encode())  # Send data
        else:
            logging.warning("Teensy not connected, values not sent.")
        
    def on(self) -> None:
        self.send_lasers_values([1] * 8)

    def off(self) -> None:
        self.send_lasers_values([0] * 8)
        
    def on_for(self, duration: float) -> None:
        end_time = time.perf_counter() + duration
        self.on()
        while time.perf_counter() <= end_time:
            pass
        
    def off_for(self, duration: float) -> None:
        end_time = time.perf_counter() + duration
        self.off()
        while time.perf_counter() <= end_time:
            pass

    def run_trial_erp(self, codebook: List[int], target_id: int, trial_id: int, on_duration: float=0.1, off_duration: float=0.15):
        """Run a single trial with multiple sequences on objects using lasers"""
        self.marker_outlet.push_sample([self.marker_ids['trial_start'] + trial_id]) # Push trial start marker
        for sequence in codebook:
            is_target = sequence[target_id]
            # Turn on lasers
            end_time = time.perf_counter() + on_duration
            self.send_lasers_values(sequence)
            if is_target == 1:
                self.marker_outlet.push_sample([self.marker_ids['target'] + target_id]) # Push target marker
            elif is_target == 0:
                self.marker_outlet.push_sample([self.marker_ids['non_target'] + target_id]) # Push non-target marker
            else:
                ValueError(f'Unknown target value: {is_target}')
            while time.perf_counter() <= end_time:
                pass
            # Turn off lasers
            end_time = time.perf_counter() + off_duration
            self.off()
            while time.perf_counter() <= end_time:
                pass

        self.marker_outlet.push_sample([self.marker_ids['trial_end'] + trial_id])

    
    def run_trial_cvep(self, codebook: List[int], target_id: int, trial_id: int, on_duration: float=1 / 60):
        """Run a single trial with multiple sequences on objects using lasers"""
        self.marker_outlet.push_sample([self.marker_ids['trial_start'] + trial_id]) # Push trial start marker
        for sequence in codebook:
            is_target = sequence[target_id]
            # Turn on lasers
            end_time = time.perf_counter() + on_duration
            self.send_lasers_values(sequence)
            if is_target == 1:
                self.marker_outlet.push_sample([self.marker_ids['target'] + target_id]) # Push target marker
            elif is_target == 0:
                self.marker_outlet.push_sample([self.marker_ids['non_target'] + target_id]) # Push non-target marker
            else:
                ValueError(f'Unknown target value: {is_target}')
            while time.perf_counter() <= end_time:
                pass

        self.marker_outlet.push_sample([self.marker_ids['trial_end'] + trial_id])
        self.off()
    
    def test_erp(self, n_trials=8):
        """Test Run ERP protocol"""
        codebook = load_codebooks_block_2()[0].astype(int).tolist()

        trial_run_times = []
        for trial_id in range(n_trials):
            start_time = time.perf_counter()
            self.run_trial_erp(codebook, target_id=0, trial_id=trial_id, on_duration=0.1, off_duration=0.15)
            elapsed_time = time.perf_counter() - start_time
            trial_run_times.append(elapsed_time)
            perf_sleep(3)

        print('Trial run times:', trial_run_times)
        print('Mean trial run time (should be 12):', np.mean(trial_run_times))

    def test_cvep(self, n_trials=8):
        """Test Run ERP protocol"""
        codebook = load_codebooks_block_3()[0].astype(int).tolist()
        codebook = codebook[:720]

        trial_run_times = []
        for trial_id in range(n_trials):
            start_time = time.perf_counter()
            self.run_trial_cvep(codebook, target_id=0, trial_id=trial_id, on_duration=1/60)
            elapsed_time = time.perf_counter() - start_time
            trial_run_times.append(elapsed_time)
            perf_sleep(3)

        print('Trial run times:', trial_run_times)
        print('Mean trial run time (should be 12):', np.mean(trial_run_times))

    def close(self) -> None:
        if self.teensy is not None:
            self.teensy.close()


if __name__ == '__main__':
    lasers = LaserController()
    _ = input('Press any key to continue.\n')
    # lasers.test_erp(8)
    lasers.test_cvep(8)