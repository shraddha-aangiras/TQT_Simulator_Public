from PyQt5 import Qt, QtCore
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSlider, QDoubleSpinBox


class SliderWithEdit(QWidget):
    def __init__(self, parent, min=0, max=100, step=1, unit="mW"):
        super(QWidget, self).__init__(parent)

        # SCALING FACTOR: Allows slider to handle decimals (e.g. 0.5)
        # 0.5 input * 100 scale = 50 integer steps
        self.scale = 100 

        layout = QVBoxLayout()

        self.slider = QSlider(QtCore.Qt.Horizontal) # Added Horizontal for better look
        self.slider.valueChanged.connect(self.slider_changed)
        
        # Scale the inputs for the slider (int only)
        self.slider.setMinimum(int(min * self.scale))
        self.slider.setMaximum(int(max * self.scale))
        self.slider.setSingleStep(int(step * self.scale))
        self.slider.setTickInterval(int(step * self.scale))

        self.edit = QDoubleSpinBox(self)
        self.edit.valueChanged.connect(self.spinbox_changed)
        self.edit.setSuffix(f" {unit}")

        # Spinbox keeps the original float values
        self.edit.setMinimum(min)
        self.edit.setMaximum(max)
        self.edit.setSingleStep(step)

        layout.addWidget(self.edit)
        layout.addWidget(self.slider)

        layout.addStretch()
        self.setLayout(layout)

    def slider_changed(self):
        # Convert Slider (Int) -> SpinBox (Float)
        value = self.slider.value() / self.scale
        # Block signals to prevent infinite loops between slider and spinbox
        self.edit.blockSignals(True)
        self.edit.setValue(value)
        self.edit.blockSignals(False)

    def spinbox_changed(self):
        # Convert SpinBox (Float) -> Slider (Int)
        value = self.edit.value() * self.scale
        self.slider.blockSignals(True)
        self.slider.setValue(int(value))
        self.slider.blockSignals(False)

    def value(self):
        return self.edit.value()

    def setValue(self, val):
        self.edit.setValue(float(val))
        self.slider.setValue(int(val * self.scale))