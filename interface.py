from time import sleep
import sys
import numpy as np
import pathlib
import matplotlib.pyplot as plt
import os
import pyqtgraph as pg
from pyqtgraph.functions import mkPen

from PyQt5 import Qt, QtCore, QtGui
from PyQt5.QtWidgets import (
    QMainWindow,
    QApplication,
    QWidget,
    QTabWidget,
    QVBoxLayout,
    QGridLayout,
    QHBoxLayout,
)
from PyQt5.QtWidgets import QLineEdit, QLabel, QDoubleSpinBox, QSpinBox, QCheckBox, QRadioButton, QAction, QButtonGroup, QSizePolicy
from PyQt5.QtWidgets import QPushButton, QFrame, QDockWidget, QScrollArea
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from tqt.utils.io import IO
from tqt.analysis.histogram import cross_correlation_histogram

from tqt.widgets.slider_edit import SliderWithEdit
from tqt.widgets.plot_counts import PlotLogicGrid

from experiment import QuantumOpticalExperiment


system = QuantumOpticalExperiment(simulation=True)

# settings for the interface (color scheme, sizes, refresh rate, font size, etc.)
ui_config = dict(
    # settings for the main window(s)
    WIDTH=1200,  # [pt]
    HEIGHT=900,  # [pt]
    COLORS=["#9b59b6", "#3498db", "#95a5a6", "#e74c3c", "#34495e", "#2ecc71"],
    PLOT_BACKGROUND="#E6E6EA",
    PLOT_FOREGROUND="#434A42",
    LOGO_PATH=str(pathlib.Path(__file__).parent.joinpath("tqt/widgets/iqc.png")),
    # interactivity settings
    #REFRESH_TIME=200,  # [ms] #Obsolete?
    NUMBER_POINTS_MEM=100,  # [-]
    # font size to use for the photon count and power value number strings
    NUMERIC_FONT_SIZE=16,  # [pt]
    # number of single photon plots to create on the interface window
    NUM_COUNT_PLOTS=4,  # [-]
    INTEGRATION_TIME_MS=1000,  # in ms, timetagger integration time and UI refresh rate
    POWER_REFRESH=200  # in ms, power meter refresh rate
)


class LabInterfaceApp(QMainWindow):
    singleton: 'LabInterfaceApp' = None
    def __init__(self):
        super().__init__()

        self.title = "TQT Photonic Quantum Technologies"
        self.left = 100
        self.top = 100
        self.width = ui_config["WIDTH"]
        self.height = ui_config["HEIGHT"]
        self.setWindowIcon(QtGui.QIcon(ui_config["LOGO_PATH"]))

        # For light switch
        self.is_dark_mode = True # Track current state
        
        self.toolbar = self.addToolBar("Main Toolbar")
        self.toolbar.setMovable(False) # Lock it in place
        self.toolbar.setFloatable(False)

        empty = QWidget()
        empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(empty)
        # --
        self.theme_switch = None
        if system.simulation:
            self.theme_switch = QAction("Turn on lights", self)
            self.theme_switch.setToolTip("Toggle Switch")
            self.theme_switch.triggered.connect(self.toggle_theme)
            self.toolbar.addAction(self.theme_switch)

        layout = QVBoxLayout()

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.realtime_data = QDockWidget("", self)
        self.realtime_data.setWidget(RealTimeDataDock(self))
        self.realtime_data.setFloating(False)
        self.addDockWidget(Qt.Qt.RightDockWidgetArea, self.realtime_data)

        self.tab_widget = TabManager(self)
        self.setCentralWidget(self.tab_widget)

        self.setLayout(layout)

        self.showMaximized()

    def toggle_theme(self):
        app = QApplication.instance()
        has_sim_control = hasattr(system.timetagger, "set_ambient_light")
        if self.is_dark_mode:
            # Switch to Light Mode (Standard Fusion Palette)
            app.setPalette(app.style().standardPalette())
            self.is_dark_mode = False
            self.theme_switch.setText("Turn off lights")
            if has_sim_control:
                system.timetagger.set_ambient_light(True)
        else:
            # Switch to Dark Mode (Your Custom Palette)
            app.setPalette(palette)
            self.is_dark_mode = True
            self.theme_switch.setText("Turn on lights")
            if has_sim_control:
                system.timetagger.set_ambient_light(False)
        
        

    def closeEvent(self,event):
        system.close()
        return


class TabManager(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        layout = QVBoxLayout(self)

        self.file_input_output_panel = FileInputOuputPanel(self)
        layout.addWidget(self.file_input_output_panel)

        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.on_tab_change)

        self.tab1 = FullEquipmentControlTab(self)
        self.tabs.addTab(self.tab1, "Full System Control")

        self.tab2 = RunMeasurementsTab(self)
        self.tabs.addTab(self.tab2, "Histogram")

        self.tabs.setCurrentIndex(0)

        # Add tabs to widget
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def on_tab_change(self):
        return


class RealTimeDataDock(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        layout = QVBoxLayout(self)

        # --- Centralized Logic ---
        self.is_measuring = False
        self.worker = None
        self.current_mode_continuous = True # Default state

        # Single Timer for the whole dock
        self.timer = QTimer(self)
        self.timer.setInterval(ui_config["INTEGRATION_TIME_MS"])
        self.timer.timeout.connect(self.trigger_acquisition)
        self.timer.start() # Start because default is Continuous

        # --- Tabs ---
        self.tabs = QTabWidget()
        
        self.tab1 = PhotonStatisticsMonitor(self)
        self.tabs.addTab(self.tab1, "Photon Statistics")

        self.tab2 = PlotOpticalPower(
            self, powermeter=system.powermeter, ui_config=ui_config
        )
        self.tabs.addTab(self.tab2, "Power Meter")

        self.tab3 = CountView(self)
        self.tabs.addTab(self.tab3, "Counts View")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # --- Connections ---
        # 1. Connect Mode Changes (Sync Tabs + Control Timer)
        self.tab1.mode_changed_signal.connect(self.handle_mode_change)
        self.tab3.mode_changed_signal.connect(self.handle_mode_change)

        # 2. Connect Refresh Requests (Both buttons trigger the same function)
        self.tab1.refresh_requested_signal.connect(self.trigger_acquisition)
        self.tab3.refresh_requested_signal.connect(self.trigger_acquisition)

    def handle_mode_change(self, is_continuous):
        self.current_mode_continuous = is_continuous
        
        # 1. Sync the Timer
        if is_continuous:
            self.timer.start()
        else:
            self.timer.stop()

        # 2. Sync the Tabs Visuals
        self.tab1.set_mode_external(is_continuous)
        self.tab3.set_mode_external(is_continuous)

    def trigger_acquisition(self):
        """Runs the measurement ONCE, then updates EVERYONE."""
        # Update Timer Interval if config changed
        if self.timer.interval() != ui_config["INTEGRATION_TIME_MS"]:
            self.timer.setInterval(ui_config["INTEGRATION_TIME_MS"])

        if self.is_measuring:
            return
            
        self.is_measuring = True
        
        # Disable buttons on all tabs during read
        self.tab1.update_ui_state(self.current_mode_continuous, is_measuring=True)
        self.tab3.update_ui_state(self.current_mode_continuous, is_measuring=True)

        duration_s = ui_config["INTEGRATION_TIME_MS"] / 1000.0
        
        # Use the existing MeasurementWorker class
        self.worker = MeasurementWorker(system.timetagger, duration_s)
        self.worker.finished.connect(self.on_acquisition_finished)
        self.worker.start()

    def on_acquisition_finished(self):
        """Data is ready in system.timetagger. Update all views."""
        
        # 1. Update Views
        # The hardware state is now fresh, so both tabs will see the EXACT same data
        self.tab1.update_view()
        self.tab3.update_view()

        # 2. Reset State
        self.is_measuring = False
        self.tab1.update_ui_state(self.current_mode_continuous, is_measuring=False)
        self.tab3.update_ui_state(self.current_mode_continuous, is_measuring=False)

# To prevent clunkiness, new class
class MeasurementWorker(QThread):
    finished = pyqtSignal()

    def __init__(self, timetagger, duration):
        super().__init__()
        self.timetagger = timetagger
        self.duration = duration

    def run(self):
        # This executes the "sleep" in the background
        self.timetagger.read(self.duration)
        self.finished.emit()

class MeasurementBase(QWidget):
    # Signals to talk to the parent (RealTimeDataDock)
    mode_changed_signal = pyqtSignal(bool)  # True=Cont, False=Manual
    refresh_requested_signal = pyqtSignal() # User clicked Refresh

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        
        self.layout_controls = QVBoxLayout()
        self.layout_controls.setContentsMargins(5, 10, 5, 0)
        
        # --- UI Controls ---
        self.mode_group = QButtonGroup(self)
        
        self.radio_cont = QRadioButton("Continuous")
        self.radio_cont.setChecked(True)
        self.radio_cont.toggled.connect(self._handle_local_mode_toggle)
        self.layout_controls.addWidget(self.radio_cont)
        self.mode_group.addButton(self.radio_cont)

        self.radio_manual = QRadioButton("Manual")
        self.layout_controls.addWidget(self.radio_manual)
        self.mode_group.addButton(self.radio_manual)

        self.layout_controls.addSpacing(10)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.clicked.connect(self.refresh_requested_signal.emit)
        self.layout_controls.addWidget(self.refresh_btn)
        
        self.layout_controls.addStretch()

    def _handle_local_mode_toggle(self):
        """User clicked a radio button locally."""
        is_continuous = self.radio_cont.isChecked()
        self.mode_changed_signal.emit(is_continuous)
        self.update_ui_state(is_continuous)

    def set_mode_external(self, is_continuous):
        """Called by parent to force UI update without triggering loops."""
        self.mode_group.blockSignals(True)
        if is_continuous:
            self.radio_cont.setChecked(True)
        else:
            self.radio_manual.setChecked(True)
        self.mode_group.blockSignals(False)
        self.update_ui_state(is_continuous)

    def update_ui_state(self, is_continuous, is_measuring=False):
        """Enables/Disables buttons based on state."""
        if is_measuring:
            self.refresh_btn.setEnabled(False)
            self.radio_cont.setEnabled(False)
            self.radio_manual.setEnabled(False)
        else:
            self.radio_cont.setEnabled(True)
            self.radio_manual.setEnabled(True)
            # Only enable refresh if we are in Manual mode
            self.refresh_btn.setEnabled(not is_continuous)

    def update_view(self):
        """Child classes must implement this to update their specific plots/tables."""
        pass
    
class PhotonStatisticsMonitor(MeasurementBase):
    def __init__(self, parent):
        super().__init__(parent) # Init the base (Timer + Controls)

        # Main Layout: Horizontal
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Add the inherited controls layout
        layout.addLayout(self.layout_controls)

        # Plots
        self.plot = PlotLogicGrid(
            self,
            timetagger=system.timetagger,
            ui_config=ui_config,
            num_plot_widgets=ui_config["NUM_COUNT_PLOTS"],
        )
        layout.addWidget(self.plot)
        self.setLayout(layout)

    def update_view(self):
        # Specific logic for updating plots
        if hasattr(self.plot, 'plots'):
            for plot_widget in self.plot.plots:
                plot_widget.onNewData()


class CountView(MeasurementBase):
    def __init__(self, parent):
        super().__init__(parent) # Init the base (Timer + Controls)

        # Main Layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 20, 10, 20)

        # Add the inherited controls layout
        main_layout.addLayout(self.layout_controls)

        # Visual Separator
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # --- Table Logic (Singles) ---
        singles_layout = QGridLayout()
        singles_layout.setSpacing(10)
        h1 = QLabel("Singles")
        h1.setStyleSheet("font-weight: bold; text-decoration: underline; font-size: 14pt;")
        singles_layout.addWidget(h1, 0, 0, 1, 2, QtCore.Qt.AlignCenter)

        self.singles_map = {
            "Alice 0 (Ch1)": [1], "Alice 1 (Ch3)": [3],
            "Bob 0   (Ch2)": [2], "Bob 1   (Ch4)": [4]
        }
        self.single_value_labels = {}
        val_font = QFont()
        val_font.setPointSize(ui_config["NUMERIC_FONT_SIZE"])

        row = 1
        for name, channels in self.singles_map.items():
            lbl_name = QLabel(name)
            lbl_val = QLabel("0")
            lbl_val.setFont(val_font)
            lbl_val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            singles_layout.addWidget(lbl_name, row, 0)
            singles_layout.addWidget(lbl_val, row, 1)
            self.single_value_labels[tuple(channels)] = lbl_val
            row += 1
        singles_layout.setRowStretch(row, 1)
        main_layout.addLayout(singles_layout)

        # Separator 2
        line2 = QFrame()
        line2.setFrameShape(QFrame.VLine)
        line2.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line2)

        # --- Table Logic (Coincidences) ---
        coinc_layout = QGridLayout()
        coinc_layout.setSpacing(10)
        h2 = QLabel("Coincidences")
        h2.setStyleSheet("font-weight: bold; text-decoration: underline; font-size: 14pt;")
        coinc_layout.addWidget(h2, 0, 0, 1, 2, QtCore.Qt.AlignCenter)

        self.coinc_map = {
            "A0 & B0": [1, 2], "A0 & B1": [1, 4], 
            "A1 & B0": [3, 2], "A1 & B1": [3, 4]  
        }
        self.coinc_value_labels = {}
        row = 1
        for name, channels in self.coinc_map.items():
            lbl_name = QLabel(name)
            lbl_val = QLabel("0")
            lbl_val.setFont(val_font)
            lbl_val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            coinc_layout.addWidget(lbl_name, row, 0)
            coinc_layout.addWidget(lbl_val, row, 1)
            self.coinc_value_labels[tuple(channels)] = lbl_val
            row += 1
        coinc_layout.setRowStretch(row, 1)
        main_layout.addLayout(coinc_layout)

        self.setLayout(main_layout)

    def update_view(self):
        # Update Singles
        for channels, label_widget in self.single_value_labels.items():
            _, count, _ = system.timetagger.get_count_data(list(channels))
            label_widget.setText(f"{count:,}")

        # Update Coincidences
        for channels, label_widget in self.coinc_value_labels.items():
            _, count, _ = system.timetagger.get_count_data(list(channels))
            label_widget.setText(f"{count:,}")

class ControlPanelTimeTag(QFrame):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.timer = QTimer(self)
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Time Tagger Control:"))
        self.update_button = QPushButton("Update instrument")
        self.update_button.clicked.connect(self.update_instrument)
        layout.addWidget(self.update_button)

        # spinbox for setting the measurement time of the time tagger/refresh rate of the UI
        self.meas_time_sb = QSpinBox()
        self.meas_time_sb.setMaximum(600000) #10min max
        self.meas_time_sb.setMinimum(100)
        self.meas_time_sb.setValue(ui_config["INTEGRATION_TIME_MS"])  # set to current default from config
        self.meas_time_sb.setPrefix("Meas. Time: ")
        self.meas_time_sb.setSuffix(" ms")
        layout.addWidget(self.meas_time_sb)

        # spinbox for setting the coincidence window of the time tagger
        self.coinc_window_sb = QDoubleSpinBox()
        self.coinc_window_sb.setValue(
            system.config["COINCIDENCE_WINDOW_NS"]
        )  # set to current default from config
        self.coinc_window_sb.setPrefix("Coinc. Window: ")
        self.coinc_window_sb.setSuffix(" ns")
        self.coinc_window_sb.setMaximum(10.0)
        self.coinc_window_sb.setMinimum(0.25)
        layout.addWidget(self.coinc_window_sb)

        scroll = QScrollArea(self)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scroll.setWidgetResizable(True)

        container = QWidget()
        scroll.setWidget(container)
        scroll.layout = QGridLayout(container)

        scroll.layout.addWidget(QLabel(""), 0, 0)
        scroll.layout.addWidget(QLabel("Delay (ns)"), 0, 1)
        scroll.layout.addWidget(QLabel("Threshold (V)"), 0, 2)
        self.delay_spinboxes = []
        self.threshold_spinboxes = []
        for i in range(16):
            scroll.layout.addWidget(QLabel(f"Ch{i+1}"), i + 1, 0)

            sb = QDoubleSpinBox(self)
            sb.setValue(
                system.config["TIMETAGGER_CHANNEL_DELAYS"][i]
            )  # set to current default from config
            self.delay_spinboxes.append(sb)
            scroll.layout.addWidget(sb, i + 1, 1)

            sb = QDoubleSpinBox(self)
            sb.setValue(
                system.config["TIMETAGGER_CHANNEL_THRESHOLDS"][i]
            )  # set to current default from config
            sb.setMaximum(4.0)
            sb.setMinimum(-4.0)
            self.threshold_spinboxes.append(sb)
            scroll.layout.addWidget(sb, i + 1, 2)

        # set layout after adding scroll bar
        layout.addWidget(scroll)
        self.setLayout(layout)

    def update_instrument(self):
        delays = [delay_spinbox.value() for delay_spinbox in self.delay_spinboxes]
        thresholds = [
            threshold_spinbox.value() for threshold_spinbox in self.threshold_spinboxes
        ]
        meas_time = self.meas_time_sb.value()
        window = self.coinc_window_sb.value()
        ui_config["INTEGRATION_TIME_MS"] = meas_time

        system.set_timetagger_window(window)
        system.set_timetagger_delays(delays)
        system.set_timetagger_thresholds(thresholds)
        message = "Update time tagger | "
        #self.parent().parent().parent().parent().parent().update_message(message)
        print(message)
        #PhotonStatisticsMonitor.reset_timer(self)




class ControlPanelPolarization(QFrame):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)

        self.setFixedWidth(650)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Main Layout for the Frame
        main_layout.addWidget(QLabel("Polarization Control (Sim)"))

        self.update_button = QPushButton("Update Waveplates")
        self.update_button.setMinimumHeight(30)
        self.update_button.clicked.connect(self.update_instrument)
        main_layout.addWidget(self.update_button)
        main_layout.addWidget(QLabel("")) # Spacer

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)

        # --- SECTION 1: SOURCE CONTROL (New Row) ---
        source_group = QFrame()
        source_group.setFrameShape(QFrame.StyledPanel)
        source_layout = QVBoxLayout()
        
        source_label = QLabel("<b>Source Generation</b>")
        source_label.setAlignment(QtCore.Qt.AlignCenter)
        source_layout.addWidget(source_label)

        # Source HWP Slider
        source_row = QHBoxLayout()
        source_row.addWidget(QLabel("Source HWP:"))
        
        self.source_hwp_slider = SliderWithEdit(self, min=0, max=180, step=1, unit="°")
        self.source_hwp_slider.setValue(0) 
        source_row.addWidget(self.source_hwp_slider, 1) 
        
        source_layout.addLayout(source_row)
        source_group.setLayout(source_layout)
        
        layout.addWidget(source_group)

        # --- SECTION 2: DETECTION CONTROL (Alice/Bob) ---
        self.controls = {}

        if hasattr(system.timetagger, 'parties'):
            
            parties_layout = QHBoxLayout()
            
            for party in system.timetagger.parties:
                # Group for each party
                party_group = QFrame()
                party_group.setFrameShape(QFrame.StyledPanel)
                party_layout = QVBoxLayout()
                
                # Title
                title = QLabel(f"<b>{party.name}</b>")
                title.setAlignment(QtCore.Qt.AlignCenter)
                party_layout.addWidget(title)

                # Buttons row
                presets_main_layout = QVBoxLayout()
                
                # Row 1: Standard Bases
                row1_layout = QHBoxLayout()
                buttons_row1 = [("Z", "Z"), ("X", "X"), ("Y", "Y")]

                for label, basis_key in buttons_row1:
                    btn = QPushButton(label)
                    btn.clicked.connect(lambda checked, p=party.name, b=basis_key: self.set_preset_basis(p, b))
                    row1_layout.addWidget(btn)
                
                # Row 2: Diagonal Bases
                row2_layout = QHBoxLayout()
                buttons_row2 = [("(-Z-X)/√2", "-Z-X"), ("(-Z+X)/√2", "-Z+X")]

                for label, basis_key in buttons_row2:
                    btn = QPushButton(label)
                    btn.clicked.connect(lambda checked, p=party.name, b=basis_key: self.set_preset_basis(p, b))
                    row2_layout.addWidget(btn)

                presets_main_layout.addLayout(row1_layout)
                presets_main_layout.addLayout(row2_layout)
                
                party_layout.addLayout(presets_main_layout)

                # HWP Slider
                party_layout.addWidget(QLabel("HWP:"))
                hwp_slider = SliderWithEdit(self, min=0, max=180, step=1, unit="°")
                hwp_slider.setValue(np.degrees(party.hwp_angle))
                party_layout.addWidget(hwp_slider)

                # QWP Slider
                party_layout.addWidget(QLabel("QWP:"))
                qwp_slider = SliderWithEdit(self, min=0, max=180, step=1, unit="°")
                qwp_slider.setValue(np.degrees(party.qwp_angle))
                party_layout.addWidget(qwp_slider)

                # Save references
                self.controls[party.name] = {'hwp': hwp_slider, 'qwp': qwp_slider}
                
                party_group.setLayout(party_layout)
                parties_layout.addWidget(party_group, 1)

            layout.addLayout(parties_layout)

        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def set_preset_basis(self, party_name, basis):
        if party_name not in self.controls: return

        presets = {
            "Z":   (0.0,  0.0), 
            "X":   (22.5, 45.0),   
            "Y":   (22.5, 0),  
            "-Z-X": (56.25, 112.5),  
            "-Z+X": (33.75, 67.5)   
        }

        if basis in presets:
            h, q = presets[basis]
            
            self.controls[party_name]['hwp'].setValue(h)
            self.controls[party_name]['qwp'].setValue(q)
            
            self.update_instrument()
            print(f"Set {party_name} to {basis} (HWP={h}, QWP={q})")

    def update_instrument(self):
        message = "Update Polarization | "
        
        # 1. Update Source (if method exists in backend)
        source_val = self.source_hwp_slider.value()
        if hasattr(system.timetagger, 'set_source_hwp'):
            system.timetagger.set_source_hwp(np.deg2rad(source_val))
            message += f"[Source: {source_val}°] "

        # 2. Update Parties (Alice/Bob)
        for name, widgets in self.controls.items():
            hwp_deg = widgets['hwp'].value()
            qwp_deg = widgets['qwp'].value()

            hwp_rad = np.deg2rad(hwp_deg)
            qwp_rad = np.deg2rad(qwp_deg)

            system.timetagger.set_waveplates(name, hwp_rad, qwp_rad)
            message += f"[{name} H:{hwp_deg:.0f} Q:{qwp_deg:.0f}] "

        print(message)


class RunMeasurementsTab(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        layout = QHBoxLayout()

        layout.addWidget(RunMeasurementCrossCorrelationHistogram(self))

        # layout.addStretch()
        self.setLayout(layout)


class RunMeasurementCrossCorrelationHistogram(QFrame):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Cross Correlation Histogram:"))

        run_pushbutton = QPushButton("Run cross-correlation")
        run_pushbutton.clicked.connect(self.run_measurement)
        layout.addWidget(run_pushbutton)

        # add spinbox for setting the integration time
        self.meas_time = QDoubleSpinBox()
        self.meas_time.setPrefix("Measurement Time: ")
        self.meas_time.setSuffix(" s")
        self.meas_time.setValue(1.0)
        self.meas_time.setMinimum(0.2)
        layout.addWidget(self.meas_time)

        # add spinbox for which channel to use as Channel A
        self.ch_a = QSpinBox()
        self.ch_a.setPrefix("Channel A:")
        self.ch_a.setValue(1)
        self.ch_a.setMinimum(1)
        self.ch_a.setMaximum(16)
        layout.addWidget(self.ch_a)

        # add spinbox for which channel to use as Channel B
        self.ch_b = QSpinBox()
        self.ch_b.setPrefix("Channel B: ")
        self.ch_b.setValue(2)
        self.ch_b.setMinimum(1)
        self.ch_b.setMaximum(16)
        layout.addWidget(self.ch_b)

        # add spinbox for bin width
        self.bin_width = QDoubleSpinBox()
        self.bin_width.setPrefix("Bin Width: ")
        self.bin_width.setSuffix(" ns")
        self.bin_width.setValue(1)
        self.bin_width.setMinimum(0.01)
        layout.addWidget(self.bin_width)

        # add spinbox for total histogram width
        self.hist_width = QDoubleSpinBox()
        self.hist_width.setPrefix("Hist. Width: ")
        self.hist_width.setSuffix(" ns")
        self.hist_width.setValue(50)
        self.hist_width.setMinimum(0.1)
        layout.addWidget(self.hist_width)

        # layout.addStretch()
        self.setLayout(layout)

    def run_measurement(self):
        system.timetagger.switch_logic()
        filename = "time-tags"
        system.timetagger.save_tags(
            io=system.io, filename=filename, time=self.meas_time.value(), convert=True
        )
        system.timetagger.switch_logic()
        tags = system.io.load_timetags(filename=filename + ".txt")

        hist, hist_x, hist_norm = cross_correlation_histogram(
            tags=tags,
            ch_a=self.ch_a.value(),
            ch_b=self.ch_b.value(),
            bin_width=self.bin_width.value(),
            hist_width=self.hist_width.value(),
        )

        fig, ax = plt.subplots(1, 1)
        ax.plot(hist_x, hist)
        ax.set(xlabel="Time (ns)", ylabel="Counts")
        # system.io.save_figure(fig=fig, filename=f"cross_correlation_ch{self.ch_a.value()}_ch{self.ch_b.value()}.png")
        plt.show()

        return


class ControlPanelLaser(QFrame):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Laser Control:"))
        self.update_button = QPushButton("Update instrument")
        self.update_button.clicked.connect(self.update_instrument)
        layout.addWidget(self.update_button)

        self.emission_checkbox = QCheckBox("Emission")
        layout.addWidget(self.emission_checkbox)
        self.power_edit = SliderWithEdit(self, min=0, max=30, step=0.5, unit="mW", vertical=True)
        self.power_edit.setValue(system.config["LASER_POWER"])

        layout.addWidget(self.power_edit)

        layout.addStretch()
        self.setLayout(layout)

    def update_instrument(self):
        message = "Update laser | "
        if self.emission_checkbox.isChecked():
            message += "Turn emission on"
            system.laser.on()
            system.laser.set_power(self.power_edit.value())
        else:
            message += "Turn emission off"
            system.laser.off()

        print(message)



        
class PlotOpticalPower(QWidget):
    def __init__(self, parent, powermeter=None, ui_config=None):
        super(QWidget, self).__init__(parent)
        self.powermeter = powermeter
        self.ui_config = ui_config

        self.timer = QTimer(self)
        self.timer.setInterval(ui_config["POWER_REFRESH"])  # in milliseconds
        self.timer.start()
        self.timer.timeout.connect(self.onNewData)

        layout = QVBoxLayout()
        # layout.setColumnStretch(1, 1)
        # layout.setRowStretch(1, 1)

        # add row of checkboxes to set pattern
        self.count_value = QLabel(str(0))
        self.count_value.setFont(QFont("Arial", ui_config["NUMERIC_FONT_SIZE"]))
        layout.addWidget(self.count_value)

        # plot initialization
        self.plot = pg.PlotWidget()
        self.plot.setLabel("left", "Optical Power (mW)")
        self.plot.time = [0]
        self.plot.data = [0]
        self.plot.getAxis("bottom").setTicks([])

        YLIM = [0, 0.1]
        self.ylim = YLIM

        self.data = {
            "x": list(np.linspace(-10, 0, self.ui_config["NUMBER_POINTS_MEM"])),
            "y": list(np.zeros(self.ui_config["NUMBER_POINTS_MEM"])),
        }
        self.line = self.plot.plot(
            self.data["x"], self.data["y"], pen=mkPen(color=self.ui_config["COLORS"][1])
        )
        layout.addWidget(self.plot)

        self.setLayout(layout)

    def onNewData(self):

        new_count_value = self.powermeter.get_power() * 1000  # W -> mW

        # set the label text to the current value
        self.count_value.setText("Current power: {:.5f} mW".format(new_count_value))

        # add the current count value to the plot
        if new_count_value > self.ylim[1]:
            self.ylim[1] = new_count_value
        # self.plot.setYRange(self.ylim[0], self.ylim[1])

        # update with the most recent count value
        self.update_array(
            self.data["y"], new_count_value, self.ui_config["NUMBER_POINTS_MEM"]
        )
        self.line.setData(self.data["x"], self.data["y"])
        return

    @staticmethod
    def update_array(array, new_value, size):
        array.append(new_value)
        if len(array) >= size:
            array.pop(0)
        return


class FileInputOuputPanel(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        layout = QVBoxLayout()
        options = QHBoxLayout()
        paths = QHBoxLayout()
        layout.addWidget(QLabel("Save path:"))

        self.default_top_path = QLineEdit(f"{IO.default_path}")
        paths.addWidget(self.default_top_path)

        self.parent_path = QLineEdit("data")
        paths.addWidget(self.parent_path)

        layout.addLayout(paths)

        self.disable_paths = QCheckBox("Edit folder path")
        self.disable_paths.toggled.connect(self.disable_path_edits)
        options.addWidget(self.disable_paths)

        self.include_date = QCheckBox("Include date?")
        self.include_date.toggled.connect(self.update_io)
        options.addWidget(self.include_date)

        self.include_uuid = QCheckBox("Include unique ID?")
        self.include_uuid.toggled.connect(self.update_io)

        options.addWidget(self.include_uuid)
        options.addStretch()

        self.path = QLabel("")
        layout.addWidget(self.path)

        layout.addLayout(options)
        layout.addStretch()
        self.setLayout(layout)

        # set the defaults of whether to include the date and/or unique ID string
        # self.include_uuid.toggle()
        self.include_date.toggle()

    def update_io(self):
        io = IO.directory(
            path=self.default_top_path.text(),
            folder=self.parent_path.text(),
            include_date=self.include_date.isChecked(),
            include_uuid=self.include_uuid.isChecked(),
        )
        self.path.setText(str(io.path))
        print(str(io.path))
        system.io = io
        return

    def disable_path_edits(self):
        self.default_top_path.setEnabled(self.disable_paths.isChecked())
        self.parent_path.setEnabled(self.disable_paths.isChecked())

class FullEquipmentControlTab(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        # Main Layout is Vertical (Top Row + Bottom Row)
        main_layout = QVBoxLayout()


        top_row_layout = QHBoxLayout()
        # Col 1 Laser
        self.laser_control_panel = ControlPanelLaser(self)
        top_row_layout.addWidget(self.laser_control_panel)

        # Col 2 Time Tagger
        self.timetag_control_panel = ControlPanelTimeTag(self)
        top_row_layout.addWidget(self.timetag_control_panel)

        # Add to layout
        main_layout.addLayout(top_row_layout)

        if system.simulation and hasattr(system.timetagger, 'parties'):
            self.pol_control_panel = ControlPanelPolarization(self)
            main_layout.addWidget(self.pol_control_panel)
        
        self.setLayout(main_layout)


if __name__ == "__main__":
    from tqt.widgets import palette

    app = QApplication(sys.argv)

    app.setStyle("Fusion")
    app.setPalette(palette)

    main = LabInterfaceApp()
    main.show()
    sys.exit(app.exec_())
