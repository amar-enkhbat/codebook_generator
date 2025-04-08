# Start marker stream

import glob
import numpy as np
import datetime
from pylsl import StreamInfo, StreamOutlet, resolve_streams

def main():
    info = StreamInfo(name='SequenceStream', type='Marker', channel_count=8, channel_format=6)
    sequence_outlet = StreamOutlet(info)
    
    sequence_on = [1] * 8
    sequence_off = [0] * 8
    
    while True:
        try:
            # Send on sequence
            end_time = datetime.datetime.now() + datetime.timedelta(seconds=0.1)
            sequence_outlet.push_sample(sequence_on)
            while datetime.datetime.now() < end_time:
                pass
            
            # Send off sequence
            end_time = datetime.datetime.now() + datetime.timedelta(seconds=0.15)
            sequence_outlet.push_sample(sequence_off)
            while datetime.datetime.now() < end_time:
                pass
        except KeyboardInterrupt:
            print("Stopping the sequence stream.")
            break
    
if __name__ == "__main__":
    main()