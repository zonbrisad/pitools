#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
#
# simple gui for handling raspberry pi gpio ports.
#
# File:     pgio
# Author:   Peter Malmberg  <peter.malmberg@gmail.com>
# Org:      __ORGANISTATION__
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

import traceback
import os
import sys
import logging
import argparse
from dataclasses import dataclass, field
from PyQt5.QtCore import Qt, QTimer, QSettings, QIODevice
from PyQt5.QtGui import QIcon, QCloseEvent
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
)
from infodialog import InfoDialog

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
win_x_size = 420
win_y_size = 240

css = """
    body {
        font-family: Courier New, monospace;
        }
"""
    
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
    

@dataclass
class GPIOX:
    id_p1: int = 0
    id_cpu: int = 0
    alternative: str = ""

    def __str__(self):
        if self.alternative == "":
            return f"{self.id_p1:02d} GPIO{self.id_cpu:2d}"
        return f"{self.id_p1:02d} GPIO{self.id_cpu:12d} ({self.alternative})"

    def label(self) -> str:
        return f'<pre><span style="color:Blue">{self.id_p1:02d}</span> <span style="color:Green">GPIO{self.id_cpu:2d}</span> <span style="color:Purple">{self.alternative}</span></pre>'

    def __post_init__(self):
        pass


gpio_list = [
    GPIOX(3, 2, "SDA"),
    GPIOX(5, 3, "SCL"),
    GPIOX(7, 3, "GPCLK"),
    GPIOX(8, 14, "TXD"),
    GPIOX(10, 15, "RXD"),
    GPIOX(11, 17, ""),
    GPIOX(12, 18, "PCM_CLK"),
    GPIOX(13, 27, ""),
    GPIOX(15, 22, ""),
    GPIOX(16, 23, ""),
    GPIOX(18, 24, ""),
    GPIOX(19, 10, "SPI_MOSI"),
    GPIOX(21, 9, "SPI_MISO"),
    GPIOX(22, 25, ""),
    GPIOX(23, 11, "SPI_SCLK"),
    GPIOX(24, 8, "SPI_CE0"),
    GPIOX(26, 7, "SPI_CE1"),
    GPIOX(29, 5, ""),
    GPIOX(31, 6, ""),
    GPIOX(32, 12, ""),
    GPIOX(33, 13, ""),
    GPIOX(35, 19, ""),
    GPIOX(36, 16, ""),
    GPIOX(37, 26, ""),
    GPIOX(38, 20, ""),
    GPIOX(40, 21, ""),
]


class GPIOWidget(QWidget):
    def __init__(self, gpio: GPIOX, parent=None):
        super().__init__()
        
        self.gpio = gpio
        self.gpio_direction = GPIO.IN
        
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(2, 2, 2, 2)
        # self.layout.setSpacing(2)
        self.setLayout(self.layout)

        self.gpio_enable = QCheckBox()
        self.gpio_enable.clicked.connect(self.set_enable)
        self.layout.addWidget(self.gpio_enable)
        
        self.pin_name = QLabel(gpio.label())
        self.pin_name.setStyleSheet(css)
        self.layout.addWidget(self.pin_name)
        self.layout.addStretch()

        self.pin_direction = QComboBox()
        self.pin_direction.addItem("Input", GPIO.IN)
        self.pin_direction.addItem("Output", GPIO.OUT)
        self.layout.addWidget(self.pin_direction)
        self.pin_direction.activated.connect(self.change_dir)

        self.pin_pullup_mode = QComboBox()
        self.pin_pullup_mode.addItem("Pullup", GPIO.PUD_UP)
        self.pin_pullup_mode.addItem("Pulldown", GPIO.PUD_DOWN)
        self.pin_pullup_mode.addItem("None", GPIO.PUD_OFF)
        self.pin_pullup_mode.activated.connect(self.change_dir)
        self.layout.addWidget(self.pin_pullup_mode)

        self.pin_toggle = QPushButton("Toggle")
        self.pin_toggle.setCheckable(True)
        self.layout.addWidget(self.pin_toggle)
        self.pin_toggle.clicked.connect(self.set_output)

        self.pin_state = QLabel()
        self.pin_state.setStyleSheet("font-family: monospace;")
        self.layout.addWidget(self.pin_state)
        
        self.update_state()
        
    def update_gpio(self) -> None:
        if self.pin_is_enabled() is True:
            xin = GPIO.input(self.gpio.id_cpu)
            self.pin_state.setText(f" {xin} ")
        else:
            self.pin_state.setText("N/A")
        
    def update_state(self) -> None:
        if self.pin_is_enabled() is False:
            self.pin_direction.setEnabled(False)
            self.pin_pullup_mode.setEnabled(False)
            self.pin_toggle.setEnabled(False)
            return
        
        if self.gpio_direction == GPIO.IN:
            self.pin_direction.setEnabled(True)
            self.pin_pullup_mode.setEnabled(True)
            self.pin_toggle.setEnabled(False)
            return
        
        self.pin_direction.setEnabled(True)
        self.pin_pullup_mode.setEnabled(True)
        self.pin_toggle.setEnabled(True)
        
    def set_output(self) -> None:
        if self.gpio_direction == GPIO.IN:
            return
        
        xin = GPIO.input(self.gpio.id_cpu)
        if xin == 0:
            GPIO.output(self.gpio.id_cpu, GPIO.HIGH)
        else: 
            GPIO.output(self.gpio.id_cpu, GPIO.LOW)
         
    def gpio_setup(self, direction, pull_upp) -> None:
        if self.pin_is_enabled() is False:
            return
            
        try:
            if direction == GPIO.IN:
                self.pin = GPIO.setup(self.gpio.id_cpu, direction, pull_up_down=pull_upp)
            else:
                self.pin = GPIO.setup(self.gpio.id_cpu, direction)
        except: 
            logging.error(f"Pin: {self.gpio.id_cpu} busy")
            self.gpio_enable.setChecked(False)
            return
        
        self.gpio_direction = direction
    
    def pin_is_enabled(self) -> bool:
        return self.gpio_enable.isChecked()
            
    def change_dir(self) -> None:
        self.gpio_setup(self.pin_direction.currentData(), self.pin_pullup_mode.currentData())
        self.update_state()
    
    def set_enable(self) -> None:
        if self.pin_is_enabled() is not True:
            GPIO.cleanup(self.gpio.id_cpu)
            logging.debug(f"Releasing pin: {self.gpio.id_cpu}")
        else:
            self.gpio_setup(self.pin_direction.currentData(), self.pin_pullup_mode.currentData())
            
        self.update_state()


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
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setContentsMargins(2, 2, 2, 2)

        # TextEdit
        # self.textEdit = QTextEdit(self.centralwidget)
        # self.verticalLayout.addWidget(self.textEdit)
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        self.gpiowidgets: list[GPIOWidget] = []
        for gpio in gpio_list:
            gw = GPIOWidget(gpio, self.centralwidget)
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
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)

        # self.statusbar.showMessage(
        #     f"Board: {GPIO.RPI_INFO['TYPE']}  CPU: {GPIO.RPI_INFO['PROCESSOR']} {GPIO.RPI_INFO['RAM']} P1:{GPIO.RPI_INFO['P1_REVISION']}"
        # )
        
        self.statusbar.addPermanentWidget(
            QLabel(f"{GPIO.RPI_INFO['TYPE']}"),
            stretch=0
        )
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(100)
        
    def update(self) -> None:
        for gw in self.gpiowidgets:
            gw.update_gpio()
            pass

    def exit(self):
        self.close()
        # msgBox = QMessageBox()
        # msgBox.setIcon(QMessageBox.Information)
        # msgBox.setWindowTitle("Quit")
        # msgBox.setText("Are you sure you want to quit?")
        # msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        # if msgBox.exec() == QMessageBox.Ok:
        #     self.close()

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
