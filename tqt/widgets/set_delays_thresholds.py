from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit


class SetDelaysThresholds(QWidget):
    def __init__(self, parent, system, ui_config):
        super(QWidget, self).__init__(parent)
        self.system = system
        self.ui_config = ui_config

        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(1, 1)

        layout.addWidget(QLabel(f"Delays (ns)"), 2, 1)  # channel number labels
        layout.addWidget(QLabel(f"Thresholds (??)"), 3, 1)  # channel number labels

        self.delay_edits = []
        self.threshold_edits = []
        for channel, (threshold, delay) in enumerate(
            zip(
                self.system.config["TIMETAGGER_CHANNEL_THRESHOLDS"],
                self.system.config["TIMETAGGER_CHANNEL_DELAYS"],
            )
        ):
            layout.addWidget(
                QLabel(f"Channel {channel+1}"), 1, channel + 2
            )  # channel number labels

            delay_edit = QLineEdit(f"{delay}")
            delay_edit.returnPressed.connect(self.update_delays)
            self.delay_edits.append(delay_edit)
            layout.addWidget(delay_edit, 2, channel + 2)  # delays

            threshold_edit = QLineEdit(f"{threshold}")
            threshold_edit.returnPressed.connect(self.update_thresholds)
            self.threshold_edits.append(threshold_edit)
            layout.addWidget(threshold_edit, 3, channel + 2)  # thresholds

        # layout.setRowStretch(
        #     layout.rowCount(), layout.columnCount()
        # )  # removes weird stretching by allowing space on the bottom
        self.setLayout(layout)

    def update_delays(self):
        new_delays = []
        for delay_edit in self.delay_edits:
            delay_str = delay_edit.text()
            delay_num = float(delay_str)
            new_delays.append(delay_num)
        self.system.set_timetagger_delays(new_delays)

    def update_thresholds(self):
        new_thresholds = []
        for threshold_edit in self.threshold_edits:
            threshold_str = threshold_edit.text()
            threshold_num = float(threshold_str)
            new_thresholds.append(threshold_num)
        self.system.set_timetagger_thresholds(new_thresholds)
