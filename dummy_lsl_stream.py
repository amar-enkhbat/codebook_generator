import time
import numpy as np
from pylsl import StreamInfo, StreamOutlet

# Create a dummy LSL stream with 32 channels and 1000 Hz sampling rate
info = StreamInfo(name='DummyStream', type='Dummy', channel_count=32, nominal_srate=1000, channel_format='float32', source_id='DummySource')
outlet = StreamOutlet(info)
\
# Send random data
while True:
    data = np.random.randn(32) / 10
    outlet.push_sample(data)
    time.sleep(0.001)