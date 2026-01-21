"""
Simulation of TOptica Laser Control Class
"""

class TOpticaLaser:
    def __init__(self, port="COM_SIM"):
        self.power = 0.0
        self.is_emission_on = False
        print(f"[SIM] Virtual Laser initialized on {port}")

    def on(self):
        self.is_emission_on = True
        print("[SIM] Laser Emission: ON")
        return b"ACK" # used by experiment to confirm command success. Not necessary, but prevents future crash

    def off(self):
        self.is_emission_on = False
        print("[SIM] Laser Emission: OFF")
        return b"ACK"

    def set_power(self, power=1, ch=1):
        self.power = float(power)
        print(f"[SIM] Laser Power set to {self.power} mW")
        return b"ACK"

    def close(self):
        print("[SIM] Virtual Laser closed")