import serial
import logging
from typing import List
import time
import numpy as np
from rusocsci import buttonbox
from utils import perf_sleep, load_codebooks_block_2, load_codebooks_block_3, load_codebooks_block_1, random_wait

# BrainVision trigger codes (1-255, single byte). Trial start/end encode the
# target object id (0-7); flash markers distinguish target vs non-target flashes.
TRIAL_START_CODE_BASE = 100  # 100-107 -> trial start, target_id = code - 100
TRIAL_END_CODE_BASE = 200    # 200-207 -> trial end, target_id = code - 200
TARGET_FLASH_CODE = 1
NONTARGET_FLASH_CODE = 2


class LaserController:
    """Laser is always on except right before start of a trial"""
    def __init__(self, port: str='COM7'):
        self.port = port
        self.teensy = None
        try:
            self.teensy = serial.Serial(port=port, baudrate=115200, timeout=1)
        except Exception as e:
            logging.warning(f"Teensy not connected: {e}")

        # Init BrainVision hardware trigger box (sends 1-255 codes, recorded
        # sample-accurately by the amplifier's digital trigger input).
        # Port hardcoded because rusocsci's auto-detect (registry scan) is
        # unreliable even when Windows/Device Manager sees the device fine.
        self.bb = buttonbox.Buttonbox(port='COM6')

        # Turn on lasers
        self.on()

    def send_marker(self, code: int) -> None:
        """Send a hardware trigger code (1-255) to BrainVision, then reset to 0."""
        self.bb.sendMarker(val=code)
        self.bb.sendMarker(val=0)

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

    def run_trial_erp(self, codebook: List[int], target_id: int, trial_id: int, run_id: int, on_duration: float=0.1, off_duration: float=0.15):
        """Run a single trial with multiple sequences on objects using lasers"""
        self.send_marker(TRIAL_START_CODE_BASE + target_id) # Trial start marker (encodes target_id)
        for seq_id, sequence in enumerate(codebook):
            is_target = sequence[target_id]
            # Turn on lasers
            end_time = time.perf_counter() + on_duration
            self.send_lasers_values(sequence)
            self.send_marker(TARGET_FLASH_CODE if is_target == 1 else NONTARGET_FLASH_CODE)
            while time.perf_counter() <= end_time:
                pass
            # Turn off lasers
            end_time = time.perf_counter() + off_duration
            self.off()
            while time.perf_counter() <= end_time:
                pass

        self.send_marker(TRIAL_END_CODE_BASE + target_id) # Trial end marker (encodes target_id)

    def run_trial_kolkhorst(self, codebook: List[int], target_id: int, trial_id: int, run_id: int, on_duration: float=0.1, off_duration: float=0.15):
        """Run a single trial with multiple sequences on objects using lasers"""
        self.send_marker(TRIAL_START_CODE_BASE + target_id) # Trial start marker (encodes target_id)
        for seq_id, sequence in enumerate(codebook):
            is_target = sequence[target_id]
            # Turn on lasers
            end_time = time.perf_counter() + on_duration
            self.send_lasers_values(sequence)
            self.send_marker(TARGET_FLASH_CODE if is_target == 1 else NONTARGET_FLASH_CODE)
            while time.perf_counter() <= end_time:
                pass
            # Turn off lasers
            end_time = time.perf_counter() + off_duration
            self.off()
            while time.perf_counter() <= end_time:
                pass

        self.send_marker(TRIAL_END_CODE_BASE + target_id) # Trial end marker (encodes target_id)


    def run_trial_cvep(self, codebook: List[int], target_id: int, trial_id: int, run_id: int, on_duration: float=1 / 60):
        """Run a single trial with multiple sequences on objects using lasers"""
        self.send_marker(TRIAL_START_CODE_BASE + target_id) # Trial start marker (encodes target_id)
        for seq_id, sequence in enumerate(codebook):
            is_target = sequence[target_id]
            # Turn on lasers
            end_time = time.perf_counter() + on_duration
            self.send_lasers_values(sequence)
            self.send_marker(TARGET_FLASH_CODE if is_target == 1 else NONTARGET_FLASH_CODE)
            while time.perf_counter() <= end_time:
                pass

        self.send_marker(TRIAL_END_CODE_BASE + target_id) # Trial end marker (encodes target_id)

        # Turn off everything after end of the trial
        self.off()

    def test_erp(self, n_trials=8):
        """Test Run ERP protocol"""
        codebook = load_codebooks_block_2()[0].astype(int).tolist()
        # codebook = load_codebooks_block_1()[0].astype(int).tolist()

        trial_run_times = []
        for trial_id in range(n_trials):
            start_time = time.perf_counter()
            self.run_trial_erp(codebook, target_id=0, trial_id=trial_id, run_id=999, on_duration=0.1, off_duration=0.15)
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
            self.run_trial_kolkhorst(codebook, target_id=0, trial_id=trial_id, run_id=999, on_duration=0.1, off_duration=0.15)
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
            self.run_trial_cvep(codebook, target_id=0, trial_id=trial_id, run_id=999, on_duration=2)
            elapsed_time = time.perf_counter() - start_time
            trial_run_times.append(elapsed_time)
            perf_sleep(3)

        print('Trial run times:', trial_run_times)
        print('Mean trial run time (should be 12):', np.mean(trial_run_times))

    def close(self) -> None:
        if self.teensy is not None:
            self.off()
            self.teensy.close()

    def test_laser_order(self) -> None:
        for i in range(8):
            seq = [0] * 8
            seq[i] = 1
            self.send_lasers_values(seq)
            perf_sleep(1)

if __name__ == '__main__':
    lasers = LaserController(port="COM14")
    # lasers.on()
    lasers.off()
    _ = input('Press any key to continue.\n')
    # lasers.off()
    # lasers.test_laser_order()
    # lasers.run_quick_flash(n_trials=8)
    # lasers.run_quick_flash(n_trials=16, wait_low=1/60, wait_high=1/60)
    # lasers.run_isolated_flash(1)
    # lasers.run_burst_flash(2)
    # _ = input('Press any key!\n')

    # lasers.test_erp(1)
    # perf_sleep(3)
    perf_sleep(3)
    lasers.test_cvep(1)

    _ = input('Press any key to continue.\n')
    perf_sleep(3)
    # lasers.test_erp_kolkhorst(1)
    # _ = input('Press any key!\n')
    # lasers.test_erp_kolkhorst(10)
    # _ = input('Press any key!\n')

