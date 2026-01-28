import pathlib
import time
from ruamel.yaml import YAML
import importlib
import numpy as np

from tqt.utils.io import IO


class QuantumOpticalExperiment:
    """
    Allows for controlling the laser, time-taggers, and power meter within a single class.
    """

    def __init__(self, verbose=True, simulation=False):
        #from tqt.control.timetagger_uqd import TimeTagger
        #from tqt.control.laser_toptica import TOpticaLaser
        #from tqt.control.powermeter_thorlabs import PowerMeter
        
        self.verbose = verbose
        self.simulation = simulation
        self.config_filepath = pathlib.Path(__file__).parent.joinpath("config.yaml")
        self.config, self.yaml = self.load_config()

        self.io = IO()

        #self.laser = TOpticaLaser(port=self.config["LASER_COM_PORT"])
        self.laser = self.load_driver(
            module_base="laser_toptica",
            class_name="TOpticaLaser",
            port=self.config["LASER_COM_PORT"]
        )

        #self.timetagger = TimeTagger()
        self.timetagger = self.load_driver(
            module_base="timetagger_uqd",
            class_name="TimeTagger"
        )

        self.timetagger.get_info()
        self.timetagger.switch_logic()

        #self.powermeter = PowerMeter(self.config["POWERMETER_PORT"])
        self.powermeter = self.load_driver(
            module_base="powermeter_thorlabs",
            class_name="PowerMeter",
            visa_address=self.config["POWERMETER_PORT"]
        )

        if self.simulation:
            # Check if the virtual power meter has the 'attach_laser' method
            if hasattr(self.powermeter, 'attach_laser'):
                print(f"[SIM] Linking Power Meter to Laser...")
                self.powermeter.attach_laser(self.laser)
            if hasattr(self.timetagger, 'attach_laser'):
                print(f"[SIM] Linking Time Tagger to Laser...")
                self.timetagger.attach_laser(self.laser)

    def load_driver(self, module_base, class_name, *args, **kwargs):
        """
        If self.simulation is True, load the simulation driver.
        If self.simulation is False, TRY to load the real driver. If it fails, load the simulation driver.
        """

        if self.simulation:
            module_base = module_base + "_sim"
            if self.verbose:
                print(f"[Mode: SIM] Loading virtual {class_name}...")
            return self._import_driver("simulator", module_base, class_name, *args, **kwargs)
        
        #try:
        if self.verbose:
            print(f"[Mode: REAL] Loading real {class_name}...")
        return self._import_driver("control", module_base, class_name, *args, **kwargs)
        
        # This is not catching the right error. Need to test what error is raised when the real driver fails to load.
        """except(ImportError, RuntimeError, OSError) as e:
            print(f"Hardware Error ({class_name}): {e}")
            print(f"   -> Falling back to virtual driver.")
            return self._import_driver("virtual", module_base, class_name, *args, **kwargs)"""
        
        
    def _import_driver(self, subpackage, module_base, class_name, *args, **kwargs):
        """
        Helps for dynamic imports
        """
        full_module_path = f"tqt.{subpackage}.{module_base}"
        module = importlib.import_module(full_module_path)
        driver_class = getattr(module, class_name)
        
        return driver_class(*args, **kwargs)
    
    def close(self):
        self.laser.close()
        self.powermeter.close()
        self.timetagger.close()

    def load_config(self):
        yaml = YAML()
        yaml.explicit_start = True
        yaml.indent(mapping=3)
        yaml.preserve_quotes = True  # not necessary for your current input

        with open(self.config_filepath) as fp:
            config = yaml.load(fp)

        return config, yaml

    def save_config(self):
        with open(self.config_filepath, "w") as fp:
            self.yaml.dump(self.config, fp)

    def set_timetagger_window(self, window):
        print(f"Setting new time tagger window to: {window}")
        self.timetagger.set_window_width(window=window)
        self.config["COINCIDENCE_WINDOW_NS"] = window
        self.save_config()

    def set_timetagger_delays(self, delays):
        print(f"Setting new time tagger delays to: {delays}")
        self.timetagger.set_channel_time_delays(delays)
        self.config["TIMETAGGER_CHANNEL_DELAYS"] = delays
        self.save_config()

    def set_timetagger_thresholds(self, thresholds):
        print(f"Setting new time tagger thresholds to: {thresholds}")
        self.timetagger.set_channel_voltage_thresholds(thresholds)
        self.config["TIMETAGGER_CHANNEL_THRESHOLDS"] = thresholds
        self.save_config()
    
    def set_polarization(self, party_name, hwp_deg, qwp_deg):
        """
        Sets the waveplates for a specific party in the simulation.
        Converts Degrees (UI) to Radians (Physics Engine).
        """
        if self.simulation and hasattr(self.timetagger, 'set_waveplates'):
            # Convert degrees to radians
            hwp_rad = hwp_deg * (np.pi / 180.0)
            qwp_rad = qwp_deg * (np.pi / 180.0)
            
            print(f"Setting {party_name}: HWP={hwp_deg}°, QWP={qwp_deg}°")
            self.timetagger.set_waveplates(party_name, hwp_rad, qwp_rad)
        else:
            print("Polarization control is only available in Simulation mode.")


if __name__ == "__main__":
    system = QuantumOpticalExperiment()

    system.laser.on()
    system.timetagger.read(1)
    counts = system.timetagger.get_count_data([1])
    print(counts)

    time.sleep(1)

    system.laser.off()
    system.timetagger.read(1)
    counts = system.timetagger.get_count_data([1])
    print(counts)

    system.close()
