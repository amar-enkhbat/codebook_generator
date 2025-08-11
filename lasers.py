import serial
import logging
from typing import List
import time


class LaserController:
    def __init__(self, port: str='COM7'):
        self.port = port
        self.teensy = None
        try:
            self.teensy = serial.Serial(port=port, baudrate=115200, timeout=1)
        except Exception as e:
            logging.warning(f"Teensy not connected: {e}")

    def send_lasers_values(self, values: List[int]) -> None:
        if self.teensy is not None:
            data_str = ",".join(map(str, values)) + "\n"
            self.teensy.write(data_str.encode())  # Send data
        else:
            logging.warning("Teensy not connected, values not sent.")
        
    def lasers_on(self) -> None:
        self.send_lasers_values([1] * 8)

    def lasers_off(self) -> None:
        self.send_lasers_values([0] * 8)
        
    def close(self) -> None:
        if self.teensy is not None:
            self.teensy.close()