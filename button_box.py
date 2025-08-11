import serial
import logging


class ButtonBoxController:
    def __init__(self, port='COM6', baud_rate=115200, timeout=1.0):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.button_box = None

    def connect(self) -> None:
        try:
            self.button_box = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)
            self.button_box.write('A1'.encode())
            self.button_box.reset_input_buffer()
            self.button_box.flush()
            text = ""
            for _ in range(100):
                text = text + self.button_box.read().decode()
                if "BITSI mode, Ready!\r\n" in text:
                    logging.info("Button box ready!")
                    break
        except Exception as e:
            self.button_box = None
            logging.warning(f"Button box not connected: {e}")

    def read(self) -> str:
        return self.button_box.readline().decode() if self.button_box else ""
    
    def close(self) -> None:
        if self.button_box is not None:
            self.button_box.close()