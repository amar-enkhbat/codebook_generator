import serial
import logging
from pylsl import StreamInfo, StreamOutlet


class ButtonBoxController:
    def __init__(self, port='COM6', baud_rate=115200, timeout=0.01):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.connect()

        # Init marker stream
        info = StreamInfo(name='ButtonBoxMarkerStream', type='Marker', channel_count=1, channel_format=6, nominal_srate=0, source_id='button_box_marker_stream_id')
        self.marker_outlet = StreamOutlet(info)

    def connect(self) -> None:
        self.button_box = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)
        self.button_box.write('A1'.encode())
        self.button_box.reset_input_buffer()
        self.button_box.flush()
        text = ""
        for _ in range(200):
            text = text + self.button_box.read().decode()
            if "BITSI mode, Ready!\r\n" in text:
                print("Button box ready!")
                break

    def read(self) -> str:
        val = self.button_box.readline().decode()
        return val

    
    def close(self) -> None:
        if self.button_box is not None:
            self.button_box.close()


if __name__ == '__main__':
    button_box = ButtonBoxController()
    while True:
        print(button_box.read())