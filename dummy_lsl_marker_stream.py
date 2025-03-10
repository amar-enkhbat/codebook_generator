from pylsl import StreamInfo, StreamOutlet
import time

info = StreamInfo(name='LaserMarkerStream', type='Markers', channel_count=1, nominal_srate = 0, channel_format='string', source_id='CharacterEvent')
outlet = StreamOutlet(info)

while True:
    outlet.push_sample(['on'])
    time.sleep(0.1)
    outlet.push_sample(['off'])
    time.sleep(0.15)