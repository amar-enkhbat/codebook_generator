import numpy as np
import os, psutil, time, datetime
import serial


def optimize_timer_resolution():
    """Optimize the timer resolution to improve precision."""
    import ctypes
    try:
        print("Optimizing timer resolution...")
        ctypes.windll.winmm.timeBeginPeriod(1)
        print("Timer resolution set to 1ms.")
    except Exception as e:
        print(f"Error optimizing timer resolution: {e}")
    
    p = psutil.Process(os.getpid())
    p.nice(psutil.HIGH_PRIORITY_CLASS if os.name == 'nt' else 10) # If HIGH_PRIORITY_CLASS not found in unix, equivalent is integer 10
    print("Priority set. Running script...")
    
def connect_teensy(port, baud_rate):
    teensy = serial.Serial(port, baud_rate, timeout=1)
    time.sleep(2)  # Wait for Arduino to initialize
    return teensy
    
def send_laser_values(teensy, values):
    data_str = ",".join(map(str, values)) + "\n"
    teensy.write(data_str.encode())  # Send data    

def run_sequence(sequence: list, on_duration=0.1, off_duration=0.15):
    """Run a single sequence"""
    # Turn on the Lasers
    end_time = datetime.datetime.now() + datetime.timedelta(seconds=on_duration)
    send_laser_values(teensy, sequence)
    # Wait until turn on duration is over
    while datetime.datetime.now() < end_time:
        pass
    # Turn off the lasers
    if off_duration != 0:
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=off_duration)
        send_laser_values(teensy, [0] * 8)
        # Wait until turn off duration is over
        while datetime.datetime.now() < end_time:
            pass


codebook = [
    [0, 0, 0, 1, 1, 0, 0, 0],
    [1, 0, 0, 0, 0, 0, 1, 0],
    [0, 1, 0, 1, 1, 1, 1, 1],
    [1, 1, 0, 0, 1, 1, 0, 1],
    [0, 1, 1, 0, 1, 1, 1, 0],
    [1, 1, 0, 0, 1, 0, 0, 1],
    [1, 1, 0, 1, 0, 0, 0, 1],
    [0, 1, 0, 1, 0, 0, 1, 1],
    [0, 0, 0, 0, 1, 1, 0, 0],
    [1, 1, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 0, 1, 1, 1, 1],
    [0, 1, 1, 0, 0, 1, 1, 0],
    [1, 0, 1, 1, 0, 1, 1, 1],
    [1, 1, 1, 0, 0, 1, 0, 0],
    [1, 1, 1, 0, 1, 0, 0, 0],
    [0, 0, 1, 0, 1, 0, 0, 1],
    [1, 0, 0, 0, 0, 1, 1, 0],
    [1, 1, 1, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 1, 1],
    [1, 0, 1, 1, 0, 0, 1, 1],
    [0, 1, 0, 1, 1, 0, 1, 1],
    [0, 1, 1, 1, 0, 0, 1, 0],
    [1, 1, 1, 1, 0, 1, 0, 0],
    [0, 0, 0, 1, 0, 1, 0, 0],
    [0, 1, 0, 0, 0, 0, 1, 1],
    [1, 1, 1, 1, 0, 0, 0, 0],
    [1, 0, 1, 0, 1, 0, 1, 1],
    [1, 1, 0, 1, 1, 0, 0, 1],
    [0, 0, 1, 0, 1, 1, 0, 1],
    [0, 0, 1, 1, 1, 0, 0, 1],
    [0, 1, 1, 1, 1, 0, 1, 0],
    [1, 0, 0, 0, 1, 0, 1, 0],
    [0, 0, 1, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 0, 0, 0],
    [1, 1, 0, 1, 0, 1, 0, 1],
    [1, 1, 1, 0, 1, 1, 0, 0],
    [1, 0, 0, 1, 0, 1, 1, 0],
    [0, 0, 0, 1, 1, 1, 0, 0],
    [0, 0, 1, 1, 1, 1, 0, 1],
    [1, 1, 0, 0, 0, 1, 0, 1],
    [0, 0, 0, 1, 0, 0, 0, 0],
    [1, 1, 1, 1, 1, 1, 0, 0],
    [0, 1, 1, 0, 1, 0, 1, 0],
    [0, 1, 1, 1, 0, 1, 1, 0],
    [0, 1, 0, 0, 1, 0, 1, 1],
    [1, 0, 0, 0, 1, 1, 1, 0],
    [1, 0, 0, 1, 1, 1, 1, 0],
    [0, 1, 1, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 1, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 1, 0, 1, 0, 1],
    [1, 0, 1, 1, 1, 0, 1, 1],
    [0, 0, 1, 0, 0, 1, 0, 1],
    [0, 1, 0, 0, 0, 1, 1, 1],
    [0, 1, 0, 0, 1, 1, 1, 1],
    [0, 0, 1, 1, 0, 0, 0, 1],
    [0, 0, 0, 0, 0, 1, 0, 0],
    [1, 0, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 1, 1, 0, 1, 0],
    [1, 1, 0, 1, 1, 1, 0, 1],
    [1, 0, 0, 1, 0, 0, 1, 0],
    [1, 0, 1, 0, 0, 0, 1, 1],
    [1, 0, 1, 0, 0, 1, 1, 1]
]

if __name__ == '__main__':
    optimize_timer_resolution()
    port = 'COM5' # Windows
    port = '/dev/tty.usbmodem156466901'  # MAC
    baud_rate = 115200
    teensy = connect_teensy(port, baud_rate)
    
    
    protocol = input('Method: erp/cvep?\n')
    
    if protocol == 'erp':
        while True:
            for sequence in codebook:
                run_sequence(sequence)
            
    elif protocol == 'cvep':
        while True:
            for sequence in codebook:
                run_sequence(sequence, on_duration=1/60, off_duration=0)
        