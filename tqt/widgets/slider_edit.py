from PyQt5 import Qt, QtCore
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSlider, QDoubleSpinBox, QSizePolicy


class SliderWithEdit(QWidget):
    def __init__(self, parent, min=0, max=100, step=1, unit="mW", vertical=False):
        super(QWidget, self).__init__(parent)

        # SCALING FACTOR: Allows slider to handle decimals (e.g. 0.5)
        # 0.5 input * 100 scale = 50 integer steps
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.scale = 100 

        self.slider = QSlider(QtCore.Qt.Horizontal)
        self.edit = QDoubleSpinBox(self)

        self.slider.valueChanged.connect(self.slider_changed)
        # Scale the inputs for the slider (int only)
        self.slider.setMinimum(int(min * self.scale))
        self.slider.setMaximum(int(max * self.scale))
        self.slider.setSingleStep(int(step * self.scale))
        self.slider.setTickInterval(int(step * self.scale))
        self.edit.valueChanged.connect(self.spinbox_changed)
        self.edit.setSuffix(f" {unit}")
        self.edit.setDecimals(2)
        self.edit.setMinimum(min)
        self.edit.setMaximum(max)
        self.edit.setSingleStep(step)

        if vertical:
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            self.setMinimumHeight(60) 
            self.edit.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(self.edit)
            layout.addWidget(self.slider)
        else:
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(5)
            self.setMinimumHeight(40)
            self.edit.setFixedWidth(70) 
            layout.addWidget(self.slider, 1) 
            layout.addWidget(self.edit)

        self.setLayout(layout)

    def sizeHint(self):
        return QtCore.QSize(150, 40)
    
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
        self.spinbox_changed()