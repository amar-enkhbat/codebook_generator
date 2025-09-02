import serial
import logging
from typing import List
import time
import numpy as np
from pylsl import StreamOutlet, StreamInfo, cf_string
from utils import perf_sleep, load_codebooks_block_2, load_codebooks_block_3, load_codebooks_block_1, random_wait

class LaserController:
    """Laser is always on except right before start of a trial"""
    def __init__(self, port: str='COM7'):
        self.port = port
        self.teensy = None
        try:
            self.teensy = serial.Serial(port=port, baudrate=115200, timeout=1)
        except Exception as e:
            logging.warning(f"Teensy not connected: {e}")

        # Init marker stream
        info = StreamInfo(name='LaserMarkerStream', type='Marker', channel_count=1, channel_format=cf_string, nominal_srate=0, source_id='laser_marker_stream_id')
        self.marker_outlet = StreamOutlet(info)

        # Turn on lasers
        self.on()

    def send_lasers_values(self, values: List[int]) -> None:
        if self.teensy is not None:
            new_order = [0, 1, 2, 4, 5, 3, 6, 7] # For fixing laser orders being not accurate in the Teensy board
            values = [values[i] for i in new_order]
            values = values[::-1] # Mirror the sequences so that the stimuli are correctly presented
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
        self.marker_outlet.push_sample([f'erp;start;{trial_id};null;{target_id};null']) # Push trial start marker
        for seq_id, sequence in enumerate(codebook):
            is_target = sequence[target_id]
            # Turn on lasers
            end_time = time.perf_counter() + on_duration
            self.send_lasers_values(sequence)
            self.marker_outlet.push_sample([f'erp;null;{trial_id};{is_target};{target_id};{seq_id}']) # Push target marker
            while time.perf_counter() <= end_time:
                pass
            # Turn off lasers
            end_time = time.perf_counter() + off_duration
            self.off()
            while time.perf_counter() <= end_time:
                pass

        self.marker_outlet.push_sample([f'erp;end;{trial_id};null;{target_id};null']) # Push target marker

    def run_trial_kolkhorst(self, codebook: List[int], target_id: int, trial_id: int, on_duration: float=0.1, off_duration: float=0.15):
        """Run a single trial with multiple sequences on objects using lasers"""
        self.marker_outlet.push_sample([f'kolkhorst;start;{trial_id};null;{target_id};null']) # Push target marker
        for seq_id, sequence in enumerate(codebook):
            is_target = sequence[target_id]
            # Turn on lasers
            end_time = time.perf_counter() + on_duration
            self.send_lasers_values(sequence)
            self.marker_outlet.push_sample([f'kolkhorst;null;{trial_id};{is_target};{target_id};{seq_id}']) # Push target marker
            while time.perf_counter() <= end_time:
                pass
            # Turn off lasers
            end_time = time.perf_counter() + off_duration
            self.off()
            while time.perf_counter() <= end_time:
                pass

        self.marker_outlet.push_sample([f'kolkhorst;end;{trial_id};null;{target_id};null']) # Push target marker

    
    def run_trial_cvep(self, codebook: List[int], target_id: int, trial_id: int, on_duration: float=1 / 60):
        """Run a single trial with multiple sequences on objects using lasers"""
        self.marker_outlet.push_sample([f'cvep;start;{trial_id};null;{target_id};null']) # Push target marker
        for seq_id, sequence in enumerate(codebook):
            is_target = sequence[target_id]
            # Turn on lasers
            end_time = time.perf_counter() + on_duration
            self.send_lasers_values(sequence)
            self.marker_outlet.push_sample([f'cvep;null;{trial_id};{is_target};{target_id};{seq_id}']) # Push target marker
            while time.perf_counter() <= end_time:
                pass

        self.marker_outlet.push_sample([f'cvep;end;{trial_id};null;{target_id};null']) # Push target marker

        # Turn off everything after end of the trial
        self.off()
    
    def test_erp(self, n_trials=8):
        """Test Run ERP protocol"""
        codebook = load_codebooks_block_2()[0].astype(int).tolist()
        # codebook = load_codebooks_block_1()[0].astype(int).tolist()

        trial_run_times = []
        for trial_id in range(n_trials):
            start_time = time.perf_counter()
            self.run_trial_erp(codebook, target_id=0, trial_id=trial_id, on_duration=0.1, off_duration=0.15)
            elapsed_time = time.perf_counter() - start_time
            trial_run_times.append(elapsed_time)
            perf_sleep(3)

        print('Trial run times:', trial_run_times)
        print('Mean trial run time (should be 12):', np.mean(trial_run_times))

    def test_erp_kolkhorst(self, n_trials=8):
        """Test Run ERP protocol"""
        codebook = load_codebooks_block_1()[0].astype(int).tolist()

        trial_run_times = []
        for trial_id in range(n_trials):
            start_time = time.perf_counter()
            print(len(codebook))
            self.run_trial_kolkhorst(codebook, target_id=0, trial_id=trial_id, on_duration=0.1, off_duration=0.15)
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

    def run_trial_isolated_flash(self, n_flashes: int, trial_id: int, duration: float=1/60, seq: List[int]=[0, 0, 0, 0, 1, 0, 0, 0], wait_low=0.75, wait_high=1):
        self.marker_outlet.push_sample([f'isolated;start;{trial_id};null;0;null']) # Push target marker
        for flash_id in range(n_flashes):
            end_time = time.perf_counter() + duration
            self.send_lasers_values(seq)
            self.marker_outlet.push_sample([f'isolated;null;{trial_id};1;0;null']) # Push target marker
            while time.perf_counter() <= end_time:
                pass
            self.off()
            random_wait(wait_low, wait_high)
        self.marker_outlet.push_sample([f'isolated;end;{trial_id};null;0;null']) # Push target marker

    def run_trial_burst_flash(self, n_flashes: int, trial_id: int, duration: float=1/60, seq: List[int]=[0, 0, 0, 0, 1, 0, 0, 0], wait=1/60):
        self.marker_outlet.push_sample([f'burst;start;{trial_id};null;0;null']) # Push target marker
        for flash_id in range(n_flashes):
            end_time = time.perf_counter() + duration
            self.send_lasers_values(seq)
            self.marker_outlet.push_sample([f'burst;null;{trial_id};1;0;null']) # Push target marker
            while time.perf_counter() <= end_time:
                pass
            self.off()
            perf_sleep(wait)
        self.marker_outlet.push_sample([f'burst;end;{trial_id};null;0;null']) # Push target marker


    def run_quick_flash(self, n_trials: int=8, seq: List[int]=[0, 0, 0, 0, 1, 0, 0, 0], n_flashes: int=12, flash_duration: float=1/60, wait_low=0.75, wait_high=1.0):
        # show initial position
        self.send_lasers_values(seq)
        perf_sleep(1)
        self.off()
        perf_sleep(2)

        # Run, N flashes and 3 second pause in between
        for trial_id in range(n_trials):
            self.run_trial_isolated_flash(n_flashes=n_flashes, trial_id=trial_id, duration=flash_duration, wait_low=wait_low, wait_high=wait_high)
            perf_sleep(3)

    def run_isolated_flash(self, n_trials: int=8, seq: List[int]=[0, 0, 0, 0, 1, 0, 0, 0], n_flashes: int=12, flash_duration: float=1/60, wait=1/60):
        # show initial position
        self.send_lasers_values(seq)
        perf_sleep(1)
        self.off()
        perf_sleep(2)

        # Run, N flashes and 3 second pause in between
        for trial_id in range(n_trials):
            self.run_trial_burst_flash(n_flashes=n_flashes, trial_id=trial_id, duration=flash_duration, wait=wait)
            perf_sleep(3)

    def close(self) -> None:
        if self.teensy is not None:
            self.teensy.close()

    def test_laser_order(self) -> None:
        while True:
            try:
                for i in range(8):
                    seq = [0] * 8
                    seq[i] = 1
                    print(seq)
                    self.send_lasers_values(seq)
                    perf_sleep(1)
            except KeyboardInterrupt:
                break

if __name__ == '__main__':
    lasers = LaserController()
    lasers.on()
    _ = input('Press any key to continue.\n')
    lasers.off()
    # lasers.test_laser_order()
    # lasers.run_quick_flash(n_trials=8)
    # lasers.run_quick_flash(n_trials=16, wait_low=1/60, wait_high=1/60)
    lasers.test_erp(1)
    lasers.test_erp_kolkhorst(1)
    lasers.test_cvep(1)