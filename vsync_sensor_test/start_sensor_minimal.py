import serial
import time
import pandas as pd

def main():
    vsync_sensor = serial.Serial('COM4', 115200, timeout=0.0)
    vsync_sensor.reset_input_buffer()
    vsync_sensor.write(b'1') # Start sensor
    for i in range(100):
        data = vsync_sensor.read()
        print(data)

    results = []

    while True:
        try:
            data = vsync_sensor.read()
            timestamp = time.perf_counter()
            if data == b'A':
                value = 1
                results.append({'timestamp': timestamp, 'value': value})
                time.sleep(1 / 240)
            elif data == b'a':
                value = 0
                results.append({'timestamp': timestamp, 'value': value})
                time.sleep(1 / 240)
            else:
                time.sleep(1 / 240)
            
        except KeyboardInterrupt:
            print("Stopping the vsync sensor stream.")
            # Save results to a CSV file
            df = pd.DataFrame(results)
            df.to_csv('sensor_results.csv', index=False)
            break
        
if __name__ == "__main__":
    main()