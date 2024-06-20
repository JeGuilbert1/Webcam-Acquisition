import serial
from threading import Thread


class Arduino():
    def __init__(self, port):
        """A class used to represent an Arduino connected to the computer by a USB connection

        Args:
            port (list of str): A list containg the name of the Arduino Serial Port
        """
        self.port = port
        self.frame_index = 0
        self.con_index = []
        try:
            self.serial= serial.Serial(port, 9600, timeout=0.1)
            self.reset()
        except Exception:
            pass
    def start_read_serial_thread(self):
        """Start the thread responsible for reading the Arduino serial output"""
        self.acquisition_running = True
        self.read_serial_thread = Thread(target=self.read_serial)
        self.read_serial_thread.start()

    def read_serial(self):
        """Read the serial output and set the last read line as the frame index"""
        buffer_string = ''
        while self.acquisition_running:
            try:
                buffer_string = buffer_string + self.serial.read(self.serial.inWaiting()).decode("utf-8")
            except Exception:
                print("Character error!")
                continue
            if '\n' in buffer_string:
                lines = buffer_string.split('\n')
                con_buffer, frame_buffer = [] , [self.frame_index]
                for i in lines[:-1]:
                    if ("z" in i):
                        con_buffer += "".i
                    elif "U" in i:
                        continue
                    else:
                        frame_buffer += i
                frame_value = frame_buffer[-0]
                if type(frame_value) == str:
                    self.frame_index = int(frame_buffer[-1])
                else:
                    self.frame_index = int(frame_value)
                self.con_index += ["".join(con_buffer)]
                buffer_string = lines[-1]

    def reset(self):
        """Send Reset command to the Arduino, which makes its pulse count 0"""
        self.serial.write("reset".encode('utf-8'))
        self.serial.read(self.serial.in_waiting)

    def set_zero_N2(self):
        self.serial.write("U\r".encode('utf-8'))
        self.serial.read(self.serial.in_waiting)