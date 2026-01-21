#### This is before adding an initial scan as cache!
import time
import random
import os
import numpy as np
from functools import reduce

def complex_array(arr):
    return np.array(arr, dtype=complex)

def CT(matrix): 
    return np.conj(np.transpose(matrix))

def Proj(vec): 
    return np.matmul(vec, CT(vec))

vec0 = complex_array([[1],[0]])
vec1 = complex_array([[0],[1]])
Id = complex_array([[1,0],[0,1]])

Proj0 = Proj(vec0) #|0><0|
Proj1 = Proj(vec1) #|1><1|

class QuantumParty:
    """
    Represents one observer (e.g., Alice).
    Instead of angles, we now manually hold the measurement operators
    for her two detectors (ch_0 and ch_1).
    """
    def __init__(self, name, ch_0_idx, ch_1_idx):
        self.name = name
        self.ch_0 = ch_0_idx 
        self.ch_1 = ch_1_idx 
        
        # Standard Z-Basis measurement
        self.op_for_ch0 = Proj0.copy()
        self.op_for_ch1 = Proj1.copy()

    def set_operators(self, op_ch0, op_ch1):
        """
        Manually set the measurement matrices for this party's detectors.
        Example: To measure X-basis, set op_ch0 to |+><+| and op_ch1 to |-><-|
        """
        self.op_for_ch0 = np.array(op_ch0, dtype=complex)
        self.op_for_ch1 = np.array(op_ch1, dtype=complex)

    def get_operator(self, active_channels_set):
        """
        Returns the combined operator for this party based on active channels.
        """

        relevant_ops = []

        if self.ch_0 in active_channels_set:
            relevant_ops.append(self.op_for_ch0)
        
        if self.ch_1 in active_channels_set:
            relevant_ops.append(self.op_for_ch1)

        if not relevant_ops:
            return Id
        
        combined_op = relevant_ops[0]
        for op in relevant_ops[1:]:
            combined_op = combined_op @ op

        return combined_op 


class TimeTagger:
    _num_channels = 16

    def __init__(self):
        print("[SIM] Virtual Time Tagger initialized")
        self.logic_mode = True
        self.window_width = 3.0
        self.delays = [0.0] * self._num_channels
        self.thresholds = [0.5] * self._num_channels

        self.channel_efficiencies = [1.0] * self._num_channels 

        # Test setup
        #self.channel_efficiencies[0] = 0.50  
        #self.channel_efficiencies[1] = 0.25 
        #self.channel_efficiencies[2] = 0.5 

        self.laser = None
        self._last_dt = 1.0
        
        self._measurement_cache = {}

        self.entanglement_enabled = True
        self.parties = []
        self.add_party("Alice", 1, 3)
        self.add_party("Bob", 2, 4)
        
        # Default: |Phi+> 
        self.entangled_state = (np.kron(vec0, vec0) + np.kron(vec1, vec1))/np.sqrt(2)

        self.rho = Proj(self.entangled_state)

    # --- Standard methods to match the actual TT ---

    def get_info(self):
        print("[SIM] FPGA Version: VIRT_1.0 | Resolution: 156.25ps")
        return

    def close(self):
        print("[SIM] Virtual Time Tagger closed")
        return

    def switch_logic(self, mode="logic"):
        if isinstance(mode, str):
            self.logic_mode = (mode.lower() == "logic")
        else:
            self.logic_mode = not self.logic_mode
        state = "Logic (Counter)" if self.logic_mode else "Time Tag (Raw Stream)"
        print(f"[SIM] Switched to {state} Mode")

    def read(self, time_s=None):
        if time_s is not None:
            self._last_dt = time_s
        else:
            self._last_dt = 1.0
            
        self._measurement_cache = {}
        return

    def get_count_data(self, channels: list):
        dt = self._last_dt
        valid_channels = sorted([ch for ch in channels if 1 <= ch <= self._num_channels])
        
        cache_key = tuple(valid_channels)

        if cache_key in self._measurement_cache:
            return self._measurement_cache[cache_key]

        if not valid_channels:
            return dt, 0, 0.0
    
        base_rate = 0.0
        if self.laser:
            if hasattr(self.laser, 'is_emission_on') and not self.laser.is_emission_on:
                base_rate = 0.0
            elif hasattr(self.laser, 'power'):
                base_rate = self.laser.power * 100000.0 

        combined_efficiency = 1.0
        active_delays = []

        for ch in valid_channels:
            idx = ch - 1
            combined_efficiency *= self.channel_efficiencies[idx]
            active_delays.append(self.delays[idx])
            
        alignment_factor = 1.0
        
        if len(valid_channels) > 1:
            delay_spread = max(active_delays) - min(active_delays)
            
            if delay_spread <= self.window_width:
                alignment_factor = 1.0
            else:
                alignment_factor = 0.0

        quantum_prob = 1.0
        final_op = self.parties[0].get_operator(set(valid_channels))
        for party in self.parties[1:]:
            final_op = np.kron(final_op, party.get_operator(set(valid_channels)))
        quantum_prob = np.real(np.trace(self.rho @ final_op))
        #print("Quantum prob", quantum_prob)
        current_rate = base_rate * combined_efficiency * alignment_factor * quantum_prob

        if current_rate > 0:
            noise = random.gauss(0, np.sqrt(current_rate / dt))
            current_rate = max(0, current_rate + noise)
        else:
            current_rate = 0.0
            
        counts = int(current_rate * dt)
        result = (dt, counts, current_rate)
        self._measurement_cache[cache_key] = result
        print(result)
        return result

    def set_window_width(self, window=3.0):
        self.window_width = float(window)
        print(f"[SIM] Coincidence window set to {window} ns")

    def set_channel_time_delays(self, delays):
        self.delays = list(delays)
        print(f"[SIM] Delays updated: {delays[:3]}...")

    def set_channel_voltage_thresholds(self, thresholds):
        self.thresholds = list(thresholds)
        print(f"[SIM] Thresholds updated: {thresholds[:3]}...")

    def attach_laser(self, laser):
        self.laser = laser
        print("[SIM] Laser attached to Time Tagger")

    def save_tags(self, io=None, filename="tags", time=1.0, convert=True):
        print(f"[SIM] 'Saving' {time}s of tags to {filename}.txt ...")
        
        if io:
            file_path = io.path.joinpath(f"{filename}.txt")
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w") as f:
                f.write("# Channel\tTime\n")
                
                current_t = 0
                num_events = 1000 
                
                for _ in range(num_events):
                    step = int(random.expovariate(1.0/10000.0))
                    current_t += step
                    
                    t1 = current_t + int(self.delays[0] * 1000)
                    f.write(f"1\t{t1}\n")
                    
                    jitter = random.randint(-500, 500)
                    t2 = current_t + int(self.delays[1] * 1000) + jitter
                    f.write(f"2\t{t2}\n")

            print(f"[SIM] File created at: {file_path}")
    
    # --- Entangled State Methods ---
    def add_party(self, name, ch_0, ch_1):
        """Dynamically add a new observer to the experiment."""
        new_party = QuantumParty(name, ch_0, ch_1)
        self.parties.append(new_party)
        print(f"[SIM] Added Party '{name}' on Channels {ch_0}/{ch_1}")

    def get_party(self, name_or_index):
        """Helper to retrieve a party object."""
        if isinstance(name_or_index, int):
            return self.parties[name_or_index]
        for p in self.parties:
            if p.name == name_or_index:
                return p
        return None

    def set_measurement_basis(self, party_name, hwp, qwp):
        """Sets basis for a specific party by name."""
        p = self.get_party(party_name)
        if p:
            p.set_basis(hwp, qwp)
        else:
            print(f"[SIM] Error: Party '{party_name}' not found.")

    def set_entanglement_state(self, state_matrix):
        """Sets the density matrix. Must match dimension 2^N where N is num parties."""
        self.rho = np.array(state_matrix, dtype=complex)
        self.entanglement_enabled = True