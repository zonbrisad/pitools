#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
#
# simple gui for handling raspberry pi gpio ports.
#
# File:     pgio
# Author:   Peter Malmberg  <peter.malmberg@gmail.com>
# Org:      
# Date:     2025-04-09
# License:
# Python:   >= 3.0
#
# ----------------------------------------------------------------------------
#
# https://sourceforge.net/p/raspberry-gpio-python/wiki/Examples/
# https://gpiozero.readthedocs.io/en/latest/recipes.html
# https://pypi.org/project/RPi.GPIO/
# https://gpiozero.readthedocs.io/en/latest/migrating_from_rpigpio.html
#

import traceback
import os
import sys
import logging
import argparse
from dataclasses import dataclass, field
from PyQt5.QtCore import Qt, QTimer, QSettings, QIODevice
from PyQt5.QtGui import QIcon, QCloseEvent, QIntValidator
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QMenu,
    QMenuBar,
    QAction,
    QStatusBar,
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QSlider,
    QLineEdit,
)
from infodialog import InfoDialog
from rp_misc import RpGpio, rp_gpio_list

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("RPi.GPIO not available, running in simulation mode.")
    GPIO = None


class App:
    NAME = "pgio"
    VERSION = "0.01"
    DESCRIPTION = "simple gui for handling raspberry pi gpio ports."
    LICENSE = ""
    AUTHOR = "Peter Malmberg"
    EMAIL = "<peter.malmberg@gmail.com>"
    ORG = "__ORGANISATION__"
    HOME = ""
    ICON = ""


# Qt main window settings
win_title = App.NAME
win_x_size = 600
win_y_size = 240

css = """
    body {
        font-family: Courier New, monospace;
        }
"""

class StyleS:
    normal = """
    QLineEdit:enabled {
    color:Black;
    }
    QLineEdit:disabled {
    color:gray;
    }
    """
    error = """
    QLineEdit:enabled {
    color:Red;
    }
    QLineEdit:disabled {
    color:gray;
    }
    """
    win = "border:0"
    
def board_info() -> None:
    board_info=f"""<center><h2>System information</h2></center>
<center>
<table>
<tr>
<td><b>Board:</b></td><td>{GPIO.RPI_INFO['TYPE']}</td>
</tr>
<tr>
<td><b>CPU:</b></td><td>{GPIO.RPI_INFO['PROCESSOR']}</td>
</tr>
<tr>
<td><b>RAM:</b></td><td>{GPIO.RPI_INFO['RAM']}</td>
</tr>
<tr>
<td><b>Revision:</b></td><td>{GPIO.RPI_INFO['REVISION']}</td>
</tr>
<tr>
<td><b>P1 Revision:</b></td><td>{GPIO.RPI_INFO['P1_REVISION']}</td>
</tr>
<tr>
<td><b>GPIO Version:</b></td><td>{GPIO.VERSION}</td>
</tr>
</table>
</center>
"""
    InfoDialog.show(board_info, title="System info", y=200)


def program_info() -> None:
    about_html = f"""
<center><h2>{App.NAME}</h2></center>
<br>

<style>hr {{
  border: 0;
  height: 1px;
  background: #eee;
}}
</style>
<b>Version: </b>{App.VERSION}
<br>
<b>Author: </b>{App.AUTHOR}
<br>
<hr>
<br>
{App.DESCRIPTION}
<br>
"""
    InfoDialog.show(about_html, title="About")
    


class GPIOWidget(QWidget):
    def __init__(self, gpio: RpGpio, main_win=None, parent=None):
        super().__init__()
        
        self.gpio = gpio
        self.gpio_direction = GPIO.IN
        self.gpio_pwm = None
        
        self.main_win = main_win 
        
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.setSpacing(2)
        self.setLayout(self.layout)

        self.gpio_enable_CB = QCheckBox()
        self.gpio_enable_CB.clicked.connect(self.gpio_enable)
        self.layout.addWidget(self.gpio_enable_CB)
        
        self.gpio_name_LB = QLabel(gpio.label())
        self.gpio_name_LB.setStyleSheet(css)
        self.gpio_name_LB.setMinimumWidth(130)
        self.layout.addWidget(self.gpio_name_LB)

        self.gpio_id_mode_CB = QComboBox()
        self.gpio_id_mode_CB.addItem("In", GPIO.IN)
        self.gpio_id_mode_CB.addItem("Out", GPIO.OUT)
        self.gpio_id_mode_CB.addItem("PWM sw", "PWMSW")
        # self.gpio_mode.addItem("PWM hw", "PWMHW")
        self.gpio_id_mode_CB.activated.connect(self.gpio_change_mode)
        self.layout.addWidget(self.gpio_id_mode_CB)

        self.gpio_pullup_mode_CB = QComboBox()
        self.gpio_pullup_mode_CB.addItem("Pullup", GPIO.PUD_UP)
        self.gpio_pullup_mode_CB.addItem("Pulldown", GPIO.PUD_DOWN)
        self.gpio_pullup_mode_CB.addItem("None", GPIO.PUD_OFF)
        self.gpio_pullup_mode_CB.activated.connect(self.gpio_change_mode)
        self.layout.addWidget(self.gpio_pullup_mode_CB)

        self.gpio_toggle_PB = QPushButton("Toggle")
        self.gpio_toggle_PB.setCheckable(True)
        self.gpio_toggle_PB.setMinimumWidth(146)
        self.gpio_toggle_PB.setMaximumWidth(146)
        self.gpio_toggle_PB.setToolTip("Toggle output high/low")
        self.layout.addWidget(self.gpio_toggle_PB)
        self.gpio_toggle_PB.clicked.connect(self.gpio_toggle)

        self.freq_LE = QLineEdit("1000")
        self.freq_LE.setMinimumWidth(40)
        self.freq_LE.setMaximumWidth(40)
        self.freq_LE.textChanged.connect(self.freq_LE_changed)
        self.freq_LE.setToolTip("PWM frequency in Hz")
        self.freq_LE.setValidator(QIntValidator(0, 1000, self))
        self.layout.addWidget(self.freq_LE)
        
        self.pwm_SL = QSlider(Qt.Horizontal)
        self.pwm_SL.setMinimumWidth(100)
        self.pwm_SL.setMaximumWidth(100)
        self.pwm_SL.setMinimum(0)
        self.pwm_SL.setMaximum(100)
        self.pwm_SL.setValue(25)
        self.pwm_SL.valueChanged.connect(self.pwm_slider_changed)
        self.pwm_SL.setToolTip("PWM duty cycle %")
        self.layout.addWidget(self.pwm_SL)
        
        self.gpio_state_LB = QLabel()
        self.gpio_state_LB.setMinimumWidth(50)
        self.gpio_state_LB.setStyleSheet("font-family: monospace;")
        self.layout.addWidget(self.gpio_state_LB)
        self.layout.addStretch()
        
        self.update_widgets()
        
    def gpio_enable(self) -> None:
        if self.gpio_is_enabled() is not True:
            GPIO.cleanup(self.gpio.id_cpu)
            self.gpio_pwm = None
            logging.debug(f"Releasing pin: {self.gpio.id_cpu}")
        else:
            self.gpio_setup(self.gpio_id_mode_CB.currentData(), self.gpio_pullup_mode_CB.currentData())
            
        self.update_widgets()
        
    def gpio_change_mode(self) -> None:
        self.gpio_setup(self.gpio_id_mode_CB.currentData(), self.gpio_pullup_mode_CB.currentData())
        self.update_widgets()
    
    def gpio_toggle(self) -> None:
        if self.gpio_direction == GPIO.IN:
            return
        
        xin = GPIO.input(self.gpio.id_cpu)
        if xin == 0:
            GPIO.output(self.gpio.id_cpu, GPIO.HIGH)
        else: 
            GPIO.output(self.gpio.id_cpu, GPIO.LOW)
            
    def freq_LE_changed(self) -> None:
        if self.gpio_direction != "PWMSW":
            return
        
        print(f"freq_LE_changed {self.freq_LE.text()}")
        try:
            freq = int(self.freq_LE.text())
            if freq < 1:
                freq = 1
            self.gpio_pwm.ChangeFrequency(freq)
        except ValueError:
            pass
        
        self.update_widgets()
        
    def pwm_slider_changed(self) -> None:       
        if self.gpio_direction != "PWMSW":
            return
        
        duty_cycle = self.pwm_SL.value()
        self.gpio_pwm.ChangeDutyCycle(duty_cycle)
        
        self.update_widgets()     
         
    def gpio_setup(self, direction, pull_upp) -> None:
        if self.gpio_is_enabled() is False:
            return
        
        if self.gpio_pwm is not None:
            self.gpio_pwm.stop()
            self.gpio_pwm = None
                
        try:
            GPIO.cleanup(self.gpio.id_cpu)
            if direction == GPIO.IN:
                self.pin = GPIO.setup(self.gpio.id_cpu, GPIO.IN, pull_up_down=pull_upp)
            elif direction == GPIO.OUT:
                self.pin = GPIO.setup(self.gpio.id_cpu, GPIO.OUT)
            elif direction == "PWMSW":
                self.pin = GPIO.setup(self.gpio.id_cpu, GPIO.OUT)
                self.gpio_pwm = GPIO.PWM(self.gpio.id_cpu, 1000)  # 0.1 kHz
                self.gpio_pwm.start(self.pwm_SL.value())
        except: 
            logging.error(f"Pin: {self.gpio.id_cpu} busy")
            self.main_win.message_error(f"Pin: {self.gpio.id_cpu} busy")
            self.gpio_enable_CB.setChecked(False)
            return
        
        self.gpio_direction = direction
    
    def gpio_is_enabled(self) -> bool:
        return self.gpio_enable_CB.isChecked()
    
    def update_gpio(self) -> None:        
        if self.gpio_is_enabled() is False:
            self.gpio_state_LB.setText("<center>N/A</center>")
            # self.gpio_state.setText("N/A")
            return

        if self.gpio_direction == "PWMSW":
            self.gpio_state_LB.setText(f"{self.freq_LE.text():>4} Hz {self.pwm_SL.value():>3} %")
            # self.gpio_state_LB.setText(f"<center>{self.freq_LE.text():>4} Hz    {self.pwm_SL.value():<3} %</center>")
            return

        xin = GPIO.input(self.gpio.id_cpu)
        self.gpio_state_LB.setText(f"<center>{xin}</center>")
        
    def update_widgets(self) -> None:
        if self.gpio_is_enabled() is False:
            self.gpio_id_mode_CB.setEnabled(False)
            self.gpio_pullup_mode_CB.setEnabled(False)
            self.gpio_toggle_PB.setEnabled(False)
            self.gpio_toggle_PB.setVisible(True)
            self.pwm_SL.setEnabled(False)
            self.pwm_SL.setVisible(False)
            self.freq_LE.setVisible(False)
            return
        
        if self.gpio_direction == GPIO.IN:
            self.gpio_pullup_mode_CB.setEnabled(True)
            self.gpio_toggle_PB.setEnabled(False)
            self.gpio_toggle_PB.setVisible(True)
            self.pwm_SL.setEnabled(False)
            self.pwm_SL.setVisible(False)
            self.freq_LE.setVisible(False)
        elif self.gpio_direction == GPIO.OUT:
            self.gpio_pullup_mode_CB.setEnabled(False)
            self.gpio_toggle_PB.setEnabled(True)
            self.gpio_toggle_PB.setVisible(True)
            self.pwm_SL.setEnabled(False)
            self.pwm_SL.setVisible(False)
            self.freq_LE.setVisible(False)
        elif self.gpio_direction == "PWMSW":
            self.gpio_pullup_mode_CB.setEnabled(False)
            self.gpio_toggle_PB.setEnabled(False)
            self.gpio_toggle_PB.setVisible(False)
            self.pwm_SL.setEnabled(True)
            self.pwm_SL.setVisible(True)
            self.freq_LE.setVisible(True)
            
        self.gpio_id_mode_CB.setEnabled(True)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.resize(win_x_size, win_y_size)
        self.setWindowTitle(win_title)
        # self.setWindowIcon(QIcon(App.ICON))

        # Create central widget
        self.centralwidget = QWidget(self)
        self.setCentralWidget(self.centralwidget)
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setContentsMargins(2, 2, 2, 2)
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        self.gpiowidgets: list[GPIOWidget] = []
        for gpio in rp_gpio_list:
            gw = GPIOWidget(gpio, 
                            main_win=self, 
                            parent=self.centralwidget)
            self.gpiowidgets.append(gw)
            self.verticalLayout.addWidget(gw)
            
        self.verticalLayout.addStretch()

        # Menubar
        self.menubar = QMenuBar(self)
        self.setMenuBar(self.menubar)

        # Menus
        self.menuFile = QMenu("File", self.menubar)
        self.menubar.addAction(self.menuFile.menuAction())

        self.menuHelp = QMenu("Help", self.menubar)
        self.menubar.addAction(self.menuHelp.menuAction())

        self.actionQuit = QAction("Quit", self)
        self.actionQuit.setStatusTip("Quit application")
        self.actionQuit.setShortcut("Ctrl+Q")
        self.actionQuit.triggered.connect(self.exit)
        self.menuFile.addAction(self.actionQuit)

        self.actionAbout = QAction("About", self)
        self.actionAbout.setStatusTip("About")
        self.actionAbout.triggered.connect(lambda: program_info())
        self.menuHelp.addAction(self.actionAbout)
        
        self.actionSysInfo = QAction("Sys info")
        self.actionSysInfo.setStatusTip("System information")
        self.actionSysInfo.triggered.connect(lambda: board_info())
        self.menuHelp.addAction(self.actionSysInfo)

        # Statusbar
        self.statusbar = QStatusBar(self)
        self.statusbar.setLayoutDirection(Qt.LeftToRight)
        self.statusbar.setStyleSheet(StyleS.normal)
        self.setStatusBar(self.statusbar)
        self.message_error("Error messages shown here")

        # self.statusbar.showMessage(
        #     f"Board: {GPIO.RPI_INFO['TYPE']}  CPU: {GPIO.RPI_INFO['PROCESSOR']} {GPIO.RPI_INFO['RAM']} P1:{GPIO.RPI_INFO['P1_REVISION']}"
        # )
        
        self.pi_type_label = QLabel(f"{GPIO.RPI_INFO['TYPE']}")
        self.pi_type_label.setStyleSheet("color:Black;")
        
        self.statusbar.addPermanentWidget(
            self.pi_type_label,
            stretch=0,
        )
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(100)
        
    def update(self) -> None:
        for gw in self.gpiowidgets:
            gw.update_gpio()
        
    def message_error(self, msg: str) -> None:
        self.statusbar.setStyleSheet("color:Red;")
        self.statusbar.showMessage(msg, 5000)
        logging.debug(msg)
        

    def exit(self):
        for gw in self.gpiowidgets:
            try:
                GPIO.cleanup(self.gpio.id_cpu)
            except:            
                pass

        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.exit()
        return super().closeEvent(event)


def main() -> None:
    logging_format = "[%(levelname)s] %(lineno)-4d %(funcName)-14s : %(message)s"
    logging.basicConfig(format=logging_format)

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
    parser = argparse.ArgumentParser(
        prog=App.NAME, description=App.DESCRIPTION, epilog="", add_help=True
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{App.NAME} {App.VERSION}",
        help="Print version information",
    )

    parser.add_argument(
        "--debug", action="store_true", default=False, help="Print debug messages"
    )

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(format=logging_format, level=logging.DEBUG)


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except KeyboardInterrupt as e:  # Ctrl-C
        raise e
    except SystemExit as e:  # sys.exit()
        raise e
    except Exception as e:
        print("ERROR, UNEXPECTED EXCEPTION")
        print(str(e))
        traceback.print_exc()
        os._exit(1)
