from PyQt5.QtWidgets import (
    QPushButton,
    QWidget,
    QGridLayout,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
)
from PyQt5.QtGui import QFont

import pyqtgraph as pg
from pyqtgraph.functions import mkPen

import numpy as np


class PlotLogicGrid(QWidget):
    def __init__(self, parent, timetagger, ui_config=None, num_plot_widgets=6):
        super(QWidget, self).__init__(parent)
        self.timetagger = timetagger
        self.ui_config = ui_config

        layout = QGridLayout()
        self.plots = [
            PlotLogic(self, timetagger, ui_config, default_logic_int=j + 1)
            for j in range(num_plot_widgets)
        ]
        for i, plot in enumerate(self.plots):
            layout.addWidget(plot, i, 1)

        self.setLayout(layout)

    def update_grid(self):
        duration_s = self.ui_config["INTEGRATION_TIME_MS"] / 1000.0
        self.timetagger.read(duration_s)  # read the data from the time tagger once per loop
        for i, plot in enumerate(self.plots):
            plot.onNewData()


class PlotLogic(QWidget):
    def __init__(self, parent, timetagger, ui_config, default_logic_int=0):
        super(QWidget, self).__init__(parent)
        self.timetagger = timetagger
        self.ui_config = ui_config

        layout = QHBoxLayout()

        self.add_plot = True

        # add row of checkboxes to set pattern
        self.count_value = QLabel(f"{round(0)}")
        width = 100
        self.count_value.setMaximumWidth(width)
        self.count_value.setMinimumWidth(width)
        self.count_value.setFont(QFont("Arial", ui_config["NUMERIC_FONT_SIZE"]))
        layout.addWidget(self.count_value)

        self.logic_pattern_buttons = []
        button_layout = QHBoxLayout()
        plot_button_layout = QVBoxLayout()

        default_pattern = list(reversed("{0:016b}".format(default_logic_int)))

        for i in range(
            16
        ):  # loop through the 16 channels on the time tagger and add a button for each
            btn = TimeTaggerPatternButton(self)
            btn.setMinimumWidth(20)
            self.logic_pattern_buttons.append(btn)
            btn.clicked.connect(btn.callback)
            if default_pattern[i] == "1":
                btn.callback()
            button_layout.addWidget(btn)
        plot_button_layout.addLayout(button_layout)

        if self.add_plot:
            # plot initialization
            self.plot = pg.PlotWidget()
            self.plot.setLabel("left", "(Counts)")
            self.plot.time = [0]
            self.plot.data = [0]
            self.plot.getAxis("bottom").setTicks([])

            self.ylim = [0, 1]

            self.data = {
                "x": list(np.linspace(-10, 0, self.ui_config["NUMBER_POINTS_MEM"])),
                "y": list(np.zeros(self.ui_config["NUMBER_POINTS_MEM"])),
            }
            self.line = self.plot.plot(
                self.data["x"],
                self.data["y"],
                pen=mkPen(color=self.ui_config["COLORS"][1]),
            )
            plot_button_layout.addWidget(
                self.plot
            )  # 16 is for the number of channels on the time tagger

        layout.addLayout(plot_button_layout)
        self.setLayout(layout)

    def onNewData(self):
        # create binary pattern for the logic pattern to plot
        channels = []
        for ch, btn in enumerate(self.logic_pattern_buttons, 1):
            if btn.curr_value == 1:
                channels.append(ch)

        dt, counts, rate = self.timetagger.get_count_data(channels)

        # update this value with the one from the logic pattern
        new_count_value = round(counts)

        # set the label text to the current value
        self.count_value.setText(f"{new_count_value}")

        # add the current count value to the plot
        yscaling = "auto"
        if self.add_plot:
            # update with the most recent count value
            self.update_array(
                self.data["y"], new_count_value, self.ui_config["NUMBER_POINTS_MEM"]
            )
            self.line.setData(self.data["x"], self.data["y"])

            # set upper ylim to the largest value seen
            if yscaling == "auto":
                self.ylim[1] = np.max(self.data["y"])

            elif yscaling == "max-mem":
                if new_count_value > self.ylim[1]:
                    self.ylim[1] = new_count_value
            self.plot.setYRange(self.ylim[0], self.ylim[1])

        return

    @staticmethod
    def update_array(array, new_value, size):
        array.append(new_value)
        if len(array) >= size:
            array.pop(0)
        return


class TimeTaggerPatternButton(QPushButton):
    def __init__(self, parent):
        super(QPushButton, self).__init__(parent)
        self.curr_value = 0
        self.labels = (" ", "+")
        self.set_background_and_label()

    def callback(self):
        self.curr_value = (
            self.curr_value + 1
        ) % 2  # cycle through 0 and 1 everytime it is clicked
        self.set_background_and_label()

    def set_background_and_label(self):
        label = self.labels[self.curr_value]
        self.setText(label)
        if self.curr_value == 1:  # AND logic pattern for this channel
            self.setStyleSheet("background-color : #7299ba")
        else:
            self.setStyleSheet("background-color : #cfcfcf")
