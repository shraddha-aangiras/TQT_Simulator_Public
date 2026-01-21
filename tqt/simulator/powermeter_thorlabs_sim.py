import random
import numpy as np

class PowerMeter:
    def __init__(self, visa_address=None, noise_enabled=False):
        self.connected_laser = None
        self.noise_enabled = noise_enabled
        print(f"[SIM] Virtual Power Meter initialized on {visa_address} (Noise: {self.noise_enabled})")

    def attach_laser(self, laser_instance):
        """Link to the virtual laser to read its state."""
        self.connected_laser = laser_instance

    def get_power(self):
        reading = 0.0

        if self.connected_laser and self.connected_laser.is_emission_on:
            reading = self.connected_laser.power / 1000

        # For noise (to change if needed). Need to add noise_enabled = True parameter 
        if self.noise_enabled:
            noise_source_1 = abs(random.gauss(0.0001, 0.00005))
            noise_source_2 = random.gauss(0, 0.01 * reading) 
            reading += (noise_source_1 + noise_source_2)
        return max(0.0, reading)

    def close(self):
        print("[SIM] Virtual Power Meter closed")