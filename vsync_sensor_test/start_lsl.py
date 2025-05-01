# Start marker stream

import glob
import numpy as np
import datetime
import time
from pylsl import StreamInfo, StreamOutlet, resolve_streams

def main():
    info = StreamInfo(name='SequenceStream', type='Marker', channel_count=8, channel_format=6, nominal_srate=0)
    sequence_outlet = StreamOutlet(info)
    
    sequence_on = [1] * 8
    sequence_off = [0] * 8
    
    ctr = 0
    while True:
        try:
            if ctr % 5 == 0:
                end_time = time.perf_counter() + 1
                while time.perf_counter() < end_time:
                    pass
            # Send on sequence
            end_time = time.perf_counter() + 0.1
            sequence_outlet.push_sample(sequence_on)
            ctr += 1
            while time.perf_counter() < end_time:
                pass
            
            # Send off sequence
            end_time = time.perf_counter() + 0.15
            sequence_outlet.push_sample(sequence_off)
            while time.perf_counter() < end_time:
                pass
        except KeyboardInterrupt:
            print("Stopping the sequence stream.")
            break
    
if __name__ == "__main__":
    main()