import serial
import pylsl

def main():
    vsync_sensor = serial.Serial('COM4', 115200, timeout=0.0)
    vsync_sensor.reset_input_buffer()
    vsync_sensor.write(b'1') # Start sensor
    for _ in range(13):
        print(vsync_sensor.read())
        
    info = pylsl.StreamInfo(name='ScreenSensorStream', type='Marker', channel_count=1, channel_format=6)
    sensor_outlet = pylsl.StreamOutlet(info)

    while True:
        try:
            data = vsync_sensor.read()
            if data == b'A':
                sensor_outlet.push_sample([1])
            elif data == b'a':
                sensor_outlet.push_sample([0])
        except KeyboardInterrupt:
            print("Stopping the vsync sensor stream.")
            break
        
if __name__ == "__main__":
    main()