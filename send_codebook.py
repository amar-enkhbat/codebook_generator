import os
import psutil
import serial
import time

import numpy as np
from pylsl import StreamInfo, StreamOutlet

from dareplane_utils.general.time import sleep_s

# Adjust to your Arduino's port (check Device Manager on Windows or `ls /dev/tty*` on Linux/Mac)
PORT = '/dev/tty.usbmodem156466901'  # Change to the correct port
BAUD_RATE = 115200
arduino = serial.Serial(PORT, BAUD_RATE, timeout=1)
time.sleep(2)  # Wait for Arduino to initialize

def optimize_timer_resolution_unix():
    """Optimize the timer resolution to improve precision."""
    import ctypes
    try:
        print("Optimizing timer resolution...")
        ctypes.windll.winmm.timeBeginPeriod(1)  # Set the timer resolution to 1ms
        print("Timer resolution set to 1ms.")
    except Exception as e:
        print(f"Error optimizing timer resolution: {e}")

    p = psutil.Process(os.getpid())
    # High priority, suitable for time-critical processes.
    p.nice(10)
    print("Priority set to 10. Running script...")




def send_led_values(values):
    if len(values) != 8:
        print("Error: Must send exactly 8 values")
        return

    data_str = ",".join(map(str, values)) + "\n"
    arduino.write(data_str.encode())  # Send data

def main():
    # Init params
    brightness = 255
    
    # Init LSL stream
    info = StreamInfo(name='LaserMarkerStream', type='Markers', channel_count=1, nominal_srate = 0, channel_format='string', source_id='CharacterEvent')
    outlet = StreamOutlet(info)
    
    codebooks = np.load('./codebooks/condition_1/codebook_1_henrich.npy').T # Codebook 1
    codebooks = np.load('./codebooks/condition_2/codebook_obj_2.npy').T # Codebook 2
    codebooks = np.ones((1, 8)) # Dummy
    
    # Codebook 3
    # codebooks = np.load('./codebooks/codebook_3_mseq_61_shift.npy')
    # codebooks = codebooks[:8].T
    
    
    codebooks = codebooks * brightness
    codebooks = codebooks.tolist()
    
    try:
        while True:
            for codebook in codebooks:
                if len(codebook) == 8 and all(0 <= v <= 255 for v in codebook):
                    send_led_values(codebook)  # Turn LEDs on
                    outlet.push_sample(['on'])
                    sleep_s(0.1)  # Keep LEDs on for 100ms

                    send_led_values([0] * 8)  # Turn LEDs off
                    outlet.push_sample(['off'])
                    sleep_s(0.15)  # Keep LEDs off for 150ms
                else:
                    print("Invalid input! Please enter exactly 8 numbers between 0 and 255.")

    except KeyboardInterrupt:
        print("Exiting...")
        send_led_values([0] * 8)  # Turn LEDs off
        arduino.close()
    
    
if __name__ == '__main__':
    optimize_timer_resolution_unix()
    main()