from PyQt5.QtWidgets import QVBoxLayout, QWidget, QLabel, QHBoxLayout, QLineEdit, QPushButton, QFileDialog, QApplication, QComboBox, QMessageBox, QSlider
from PyQt5.QtGui import QFont, QIcon, QImage, QPixmap
from PyQt5.QtCore import Qt, QThread, Qt, pyqtSignal, pyqtSlot
import sys
import os
import cv2
import numpy as np
import json
from threading import Thread
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.controls import Arduino

class ImageThread(QThread):
    changePixmap = pyqtSignal(QImage)

    def run(self):
        """Acquire webcam images and emit signal to update video preview"""
        ex.cap = cv2.VideoCapture(0)
        ex.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        ex.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        while not ex.close_signal:
            return_value, frame = ex.cap.read()
            frame = frame[ex.crop[0]:ex.crop[1], ex.crop[2]:ex.crop[3]]
            if return_value is True:
                if ex.saving is True:
                    frame_index = ex.arduino.frame_index
                    print("Frame index: {}".format(frame_index))
                    ex.indices.append(frame_index-1)
                    ex.concentrations += [ex.arduino.con_index + [ex.cap.get(cv2.CAP_PROP_POS_MSEC)]]
                    try:
                        ex.shown_concen = int(ex.concentrations[-1][-2][-8:-2])/1000
                        ex.concentration_cell.setText(f"{ex.shown_concen}" + " % CO2")
                    except Exception:
                        continue
                    ex.arduino.con_index = []
                    ex.time.append(ex.cap.get(cv2.CAP_PROP_POS_MSEC))
                    ex.frames.append(frame)
                rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h,w,ch = rgbImage.shape
                bytesPerLine = ch*w
                convertToQtFormat = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
                p = convertToQtFormat.scaled(960, 540, Qt.KeepAspectRatio)
                self.changePixmap.emit(p)
                if ex.set_zero_val:
                    ex.arduino.set_zero_N2()
                    ex.set_zero_val = False
                if ex.set_con:
                    ex.arduino.set_con(ex.des_con)
                    ex.set_con = False
                if ex.analog_cont:
                    ex.arduino.analog_cont()
                    ex.analog_cont = False
                if ex.mixer_bool:
                    ex.arduino.MixerToggle()
                    ex.mixer_bool = False
                if ex.purgeair:
                    ex.arduino.purgeAir()
                    ex.purgeair = False
                if ex.purgeco2:
                    ex.arduino.purgeCO2()
                    ex.purgeco2 = False
                if ex.flow_off:
                    ex.arduino.Flow_off()
                    ex.flow_off = False

class App(QWidget):

    def __init__(self):
        """Initialize the application"""
        super().__init__()
        self.title = 'Webcam Acquisition'
        self.cwd = os.path.dirname(os.path.dirname(__file__))
        self.left = 10
        self.top = 10
        self.width = 600
        self.height = 800
        self.frames = []
        self.indices = []
        self.concentrations = []
        self.shown_concen = "NaN"
        self.time = []
        with open(os.path.join(self.cwd, "config.json"), "r") as file:
            self.config = json.load(file)
        self.arduino = Arduino(self.config["arduino_port"])
        self.start_acquisition_thread()
        self.stop_acquisition_signal = False
        self.close_signal = False
        self.saving = False
        self.saving_threads_started = False
        self.set_zero_val = False
        self.set_con = False
        self.des_con = ""
        self.mixer_bool = False
        self.purgeair = False
        self.purgeco2 = False
        self.flow_off = False
        self.analog_cont = False
        self.initUI()

    @pyqtSlot(QImage)
    def set_preview(self, image):
        """Update the video preview in the GUI"""
        self.label.setPixmap(QPixmap.fromImage(image))

    def closeEvent(self, *args, **kwargs):
        """Close the application"""
        try:
            self.video_feed.release()
        except Exception:
            pass
        self.arduino.acquisition_running = False
        self.close_signal = True

    def initUI(self):
        """Initialize the GUI"""
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.main_layout.setAlignment(Qt.AlignTop)

        self.settings_window = QVBoxLayout()
        self.settings_window.setAlignment(Qt.AlignTop)

        self.experiment_name_window = QHBoxLayout()
        self.experiment_name = QLabel('Experiment Name')
        self.experiment_name_window.addWidget(self.experiment_name)
        self.experiment_name_cell = QLineEdit()
        self.experiment_name_cell.textChanged.connect(self.verify_name)
        self.experiment_name_window.addWidget(self.experiment_name_cell)
        self.resolution_combo = QComboBox()
        self.resolution_combo.currentIndexChanged.connect(self.change_resolution)
        self.resolution_combo.addItem("1080p")
        self.resolution_combo.addItem("720p")
        self.resolution_combo.addItem("480p")
        self.experiment_name_window.addWidget(self.resolution_combo)
        self.settings_window.addLayout(self.experiment_name_window)

        self.save_window = QHBoxLayout()
        self.directory_label = QLabel("Directory")
        self.save_window.addWidget(self.directory_label)
        self.directory_cell = QLineEdit()
        self.directory_cell.setMinimumWidth(150)
        self.directory_cell.setReadOnly(True)
        self.save_window.addWidget(self.directory_cell)
        self.browse_button = QPushButton("Select directory")
        self.browse_button.clicked.connect(self.browse)
        self.save_window.addWidget(self.browse_button)
        self.start_button = QPushButton("Start Acquisition")
        self.start_button.setIcon(QIcon(os.path.join("gui","icons","player-play.png")))
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_saving)
        self.save_window.addWidget(self.start_button)
        self.stop_button = QPushButton("Stop Acquisition")
        self.stop_button.setIcon(QIcon(os.path.join("gui","icons","player-stop.png")))
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_saving)
        self.save_window.addWidget(self.stop_button)
        self.settings_window.addLayout(self.save_window)

        self.con_window = QHBoxLayout()
        self.concentration_label = QLabel("CO2 concentration:")
        self.con_window.addWidget(self.concentration_label)
        self.concentration_cell = QLabel(self.shown_concen + " % CO2")
        self.con_window.addWidget(self.concentration_cell)
        self.zero_button = QPushButton("Set nitrogen zero")
        self.zero_button.setEnabled(True)
        self.zero_button.clicked.connect(self.set_zero)
        self.con_window.addWidget(self.zero_button)
        self.settings_window.addLayout(self.con_window)

        self.con_control_window = QHBoxLayout()
        self.con_control_purgeair = QPushButton("Purge Air")
        self.con_control_purgeair.setEnabled(True)
        self.con_control_purgeair.clicked.connect(self.purge_Air)
        self.con_control_window.addWidget(self.con_control_purgeair)

        self.con_control_purgeCO2 = QPushButton("Purge CO2")
        self.con_control_purgeCO2.setEnabled(True)
        self.con_control_purgeCO2.clicked.connect(self.purge_CO2)
        self.con_control_window.addWidget(self.con_control_purgeCO2)

        self.con_control_off = QPushButton("Flow Off")
        self.con_control_off.setEnabled(True)
        self.con_control_off.clicked.connect(self.Flow_Off)
        self.con_control_window.addWidget(self.con_control_off)

        self.con_control_toggle = QPushButton("Auto Mixer", self)
        self.con_control_toggle.setCheckable(True)
        self.con_control_toggle.clicked.connect(self.changeColor)
        self.con_control_toggle.clicked.connect(self.MixerToggle)
        self.con_control_toggle.setStyleSheet("background-color : red")
        self.con_control_window.addWidget(self.con_control_toggle)

        self.settings_window.addLayout(self.con_control_window)
        self.con_control = QLabel('Concentration demandée:')
        self.con_control_window.addWidget(self.con_control)
        self.con_control_cell = QLineEdit()
        self.con_control_cell.setMaximumWidth(100)
        self.con_control_window.addWidget(self.con_control_cell)
        self.con_control_cell_ind = QLabel('%')
        self.con_control_window.addWidget(self.con_control_cell_ind)
        self.con_control_button = QPushButton("Apply")
        self.con_control_button.setEnabled(True)
        self.con_control_button.clicked.connect(self.send_con)
        self.con_control_window.addWidget(self.con_control_button)

        self.con_control_analog = QPushButton("Analog Control", self)
        self.con_control_analog.setCheckable(True)
        self.con_control_analog.clicked.connect(self.changeColor2)
        self.con_control_analog.clicked.connect(self.Analog_control)
        self.con_control_analog.setStyleSheet("background-color : red")
        self.con_control_window.addWidget(self.con_control_analog)

        self.main_layout.addLayout(self.settings_window)


        self.exposure_window = QHBoxLayout()
        self.exposure_label = QLabel("Exposure")
        self.exposure_window.addWidget(self.exposure_label)
        self.exposure_slider = QSlider(Qt.Horizontal, self)
        self.exposure_slider.setRange(-75, 75)
        self.exposure_slider.setValue(0)
        self.exposure_slider.valueChanged.connect(self.change_brightness)
        self.exposure_window.addWidget(self.exposure_slider)
        self.main_layout.addLayout(self.exposure_window)
        self.preview_window = QVBoxLayout()
        self.preview_label = QLabel("Webcam Preview")
        self.preview_window.addWidget(self.preview_label)
        self.label = QLabel(self)
        self.preview_window.addWidget(self.label)
        self.main_layout.addLayout(self.preview_window)

        self.show()

    def changeColor(self):
        if self.con_control_toggle.isChecked():
            self.con_control_toggle.setStyleSheet("background-color : green")
        else:
            self.con_control_toggle.setStyleSheet("background-color : red")
    def changeColor2(self):
        if self.con_control_analog.isChecked():
            self.con_control_analog.setStyleSheet("background-color : green")
        else:
            self.con_control_analog.setStyleSheet("background-color : red")

    def change_resolution(self):
        center_x, center_y = 1920 // 2, 1080 //2
        try:
            if self.resolution_combo.currentText() == "1080p":
                self.crop = [0, 1080, 0, 1920]
                self.res = [1920, 1080]
            if self.resolution_combo.currentText() == "720p":
                new_width, new_height = 1280, 720
                self.crop = [center_y-new_height//2, center_y+new_height//2, center_x-new_width//2, center_x+new_width//2]
                self.res = [1280, 720]
            if self.resolution_combo.currentText() == "480p":
                new_width, new_height = 640, 480
                self.crop = [center_y-new_height//2, center_y+new_height//2, center_x-new_width//2, center_x+new_width//2]
                self.res = [640, 480]
        except Exception:
            pass

    def change_brightness(self, value):
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, value)
        
    def start_acquisition_thread(self):
        """Start the thread responsible for acquiring webcam frames"""
        self.acquisition_thread = ImageThread(self)
        self.acquisition_thread.changePixmap.connect(self.set_preview)
        self.acquisition_thread.start()

    def start_read_serial_thread(self):
        """Start the thread responsible for reading the Arduino serial output"""
        self.arduino.start_read_serial_thread()

    def start_save_images_thread(self):
        """Start the thread responsible for image saving"""
        self.save_images_thread = Thread(target=self.save_images)
        self.save_images_thread.start()

    def save_images(self):
        """Add buffered frames to the video and release when done. Save indices and time arrays."""
        while not self.close_signal:
            while self.saving is True:
                if len(self.frames) > 0:
                    self.video_feed.write(self.frames.pop(0))
            if (self.request_save is True) and (self.stop_acquisition_signal is True):
                self.video_feed.release()
                if len(set(self.indices)) not in [0, 1]:
                    print("Indices success, saved {} different values".format(len(set(self.indices))))
                else:
                    print("Indices failure")
                np.save(os.path.join(self.directory,self.experiment_name_cell.text(),"indices.npy"), self.indices)
                with open(os.path.join(self.directory,self.experiment_name_cell.text(),"concentrations.json"), "w") as fp:
                    json.dump(self.concentrations, fp)
                np.save(os.path.join(self.directory,self.experiment_name_cell.text(),"time.npy"), self.time)
                self.time = np.array(self.time)
                self.time = (self.time-self.time[0])/1000 #time from 1rst saved frame in s
                np.save(os.path.join(self.directory,self.experiment_name_cell.text(),"time.npy"), self.time)
                self.indices = []
                self.time = []
                self.request_save = False

    def verify_name(self):
        """Verify that experiment name is not empty"""
        self.start_button.setEnabled(self.experiment_name_cell.text() != "")
        
    def browse(self):
        """Choose the directory in which to save the video"""
        self.directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.directory_cell.setText(self.directory)
        self.start_button.setEnabled(True)
    
    def start_saving(self):
        """Start the serial read and image saving threads."""
        if self.check_overwrite():
            self.indices =  []
            self.saving = True
            self.request_save = True
            self.stop_acquisition_signal = False
            self.start_button.setEnabled(False)
            self.resolution_combo.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.video_feed = cv2.VideoWriter(os.path.join(self.directory, self.experiment_name_cell.text(), f"{self.experiment_name_cell.text()}.mp4"), cv2.VideoWriter_fourcc(*'mp4v'), 30, (self.res[0],self.res[1]))
            if self.saving_threads_started is False:
                self.start_read_serial_thread()
                self.start_save_images_thread()
                self.saving_threads_started = True

    def check_overwrite(self):
        """ Check if experiment with the same name already exists"""
        if os.path.isdir(
            os.path.join(
                self.directory,
                self.experiment_name_cell.text()
            )
        ):
            button = QMessageBox.question(
                self,
                "File name already exists",
                "File name already exists. \n Do you want to overwrite?",
            )
            if button == QMessageBox.Yes:
                return True
            else:
                return False
        else:
            os.mkdir(os.path.join(
                self.directory,
                self.experiment_name_cell.text()
            ))
            return True

    def stop_saving(self):
        """Send a signal to stop saving new frames"""
        self.stop_acquisition_signal = True
        self.saving = False
        # self.arduino.acquisition_running = False # Ceci rend impossible de prendre 2 acquisitons d'affilé
        self.stop_button.setEnabled(False)
        self.start_button.setEnabled(True)
        self.resolution_combo.setEnabled(True)

    def set_zero(self):
        self.set_zero_val = True
    def send_con(self):
        self.des_con = self.con_control_cell.text()
        self.set_con = True
    def Analog_control(self):
        self.analog_cont = True
    def MixerToggle(self):
        self.mixer_bool = True
    def purge_CO2(self):
        self.purgeco2 = True
    def purge_Air(self):
        self.purgeair = True
    def Flow_Off(self):
        self.flow_off = True

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    font = QFont()
    font.setFamily("IBM Plex Sans")
    app.setFont(font)
    sys.exit(app.exec_())
