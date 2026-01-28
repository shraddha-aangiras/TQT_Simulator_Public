import time
import random
import os
import numpy as np
from itertools import product
from collections import Counter
import itertools

BIN_RESOLUTION_NS = 0.15625
JITTER_SIGMA_NS = 1.0

def complex_array(arr):
    return np.array(arr, dtype=complex)

def CT(matrix): 
    return np.conj(np.transpose(matrix))

def Proj(vec): 
    return np.matmul(vec, CT(vec))

def rot(angle): 
    return np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])

def HWP(angle): # Half-wave plate rotation matrix
    return rot(angle) @ np.array([[1, 0], [0, -1]]) @ rot(-1*angle)

def QWP(angle): # Quarter-wave plate rotation matrix
    return rot(angle) @ np.array([[1, 0], [0, -1j]]) @ rot(-1*angle)

vec0 = complex_array([[1],[0]])
vec1 = complex_array([[0],[1]])
Id = complex_array([[1,0],[0,1]])

class QuantumParty:
    """
    Represents one observer (e.g., Alice).
    """
    def __init__(self, name, ch_0_idx, ch_1_idx):
        self.name = name
        self.channels = [ch_0_idx, ch_1_idx]
        
        self.hwp_angle = 0.0
        self.qwp_angle = 0.0

        self.has_qwp = True

        self.pbs_ops = [Proj(vec0), Proj(vec1)]
        self.ops = [] 
        self.update_operators()

    def set_waveplates(self, hwp, qwp):
        """Set waveplate angles in radians."""
        self.hwp_angle = hwp
        self.qwp_angle = qwp
        self.update_operators()

    def update_operators(self):
        """
        Calculate effective operators: E = W_dag * P_pbs * W
        """
        W = HWP(self.hwp_angle) @ QWP(self.qwp_angle) if self.has_qwp else HWP(self.hwp_angle)
        self.ops = [CT(W) @ op @ W for op in self.pbs_ops]

    def qwp_toggle(self):
        self.has_qwp = not self.has_qwp
        print("Toggled:", self.has_qwp)
        self.update_operators()

class TimeTagger:
    _num_channels = 16

    def __init__(self):
        print("[SIM] Virtual Time Tagger initialized (Poissonian Statistics)")
        self.logic_mode = True
        self.window_width = 3.0
        self.delays = [0.0] * self._num_channels
        self.thresholds = [0.5] * self._num_channels
        self.channel_efficiencies = [0.1] * self._num_channels

        self.dark_count_rate_on = 21700
        self.dark_count_rate_off = 1500
        self.dark_count_rate = self.dark_count_rate_off
        self.generation_efficiency = 10000.0

        self.laser = None
        self.laser_rate = 3 * 100000.0
        self.parties = []
        
        self._simulation_memory = Counter()
        self._last_duration = 1.0

        self.add_party("Alice", 1, 3)
        self.add_party("Bob", 2, 4)
        
        self.set_source_hwp(0)
        self.set_source_hwp(np.radians(0))
        self.set_waveplates("Alice", hwp_angle=0, qwp_angle=0)
        self.set_waveplates("Bob",   hwp_angle=0, qwp_angle=0)

        #self.channel_efficiencies[0] = 0.09
        #self.channel_efficiencies[1] = 0.08

        """## -- Remove later, test --
        PsiMinus = (np.kron(vec0, vec1) - np.kron(vec1, vec0)) / np.sqrt(2)
        StateHH  = np.kron(vec0, vec0)
        StateVV  = np.kron(vec1, vec1)
        
        Identity4 = np.eye(4, dtype=complex) / 4.0

        self.rho = (
            Proj(PsiMinus) * 0.95 + 
            Proj(StateHH)  * 0.02 + 
            Proj(StateVV)  * 0.02 + 
            Identity4      * 0.01
        )
        ## -- Remove later, test --"""

        # Test values
        """self.channel_efficiencies[0] = 0.5
        self.channel_efficiencies[1] = 0.6
        self.channel_efficiencies[2] = 0.7
        self.channel_efficiencies[3] = 0.8"""

    # --- Standard methods to match the actual TT ---

    def get_info(self):
        print("[SIM] FPGA Version: VIRT_POISSON_2.0 | Resolution: 156.25ps")

    def close(self):
        print("[SIM] Virtual Time Tagger closed")

    def switch_logic(self, mode="logic"):
        if isinstance(mode, str):
            self.logic_mode = (mode.lower() == "logic")
        else:
            self.logic_mode = not self.logic_mode
        state = "Logic (Counter)" if self.logic_mode else "Time Tag (Raw Stream)"
        print(f"[SIM] Switched to {state} Mode")

    def attach_laser(self, laser):
        self.laser = laser
        print("[SIM] Laser attached to Time Tagger")

    def read(self, time_s=1.0):
        # print("read (optimized with accidentals):")
        if time_s is None: time_s = 1.0
        temp_memory = Counter() 

        base_rate = 0.0
        if self.laser:
            if hasattr(self.laser, 'is_emission_on') and self.laser.is_emission_on:
                 base_rate = self.laser.power * self.laser_rate # laser rate
        
        if base_rate > 0:
            avg_events = base_rate * time_s
            total_photons = np.random.poisson(avg_events)
            
            # This generates counts for all parties
            # Serves as a sort of cache, so that readings are consistent
            if total_photons > 0:
                observable_probs = Counter() 
                outcomes = list(product([0, 1], repeat=len(self.parties)))
                
                for outcome in outcomes:
                    op_list = []
                    channels_ideal = []
                    
                    for i, result_idx in enumerate(outcome):
                        party = self.parties[i]
                        op_list.append(party.ops[result_idx])
                        channels_ideal.append(party.channels[result_idx])
                    
                    full_op = op_list[0]
                    for op in op_list[1:]:
                        full_op = np.kron(full_op, op)

                    p_ideal = np.real(np.trace(self.rho @ full_op))

                    if p_ideal <= 1e-9: continue

                    effs = [self.channel_efficiencies[ch-1] if 1<=ch<=self._num_channels else 0.0 for ch in channels_ideal]
                    
                    for detection_mask in product([0, 1], repeat=len(channels_ideal)):
                        p_loss_outcome = 1.0
                        actual_channels = []
                        
                        for k, detected in enumerate(detection_mask):
                            if detected == 1:
                                p_loss_outcome *= effs[k]
                                actual_channels.append(channels_ideal[k])
                            else:
                                p_loss_outcome *= (1 - effs[k])
                        
                        final_prob = p_ideal * p_loss_outcome
                        if actual_channels:
                            observable_probs[tuple(actual_channels)] += final_prob

                patterns = list(observable_probs.keys())
                probs = list(observable_probs.values())
                
                sum_p = sum(probs)
                if sum_p > 1.0: 
                    probs = [p/sum_p for p in probs]
                    sum_p = 1.0
                    
                probs_with_remainder = probs + [1.0 - sum_p] 
                
                # This adds Pr(correct)
                counts_distribution = np.random.multinomial(total_photons, probs_with_remainder)
                
                for i, count in enumerate(counts_distribution[:-1]):
                    if count > 0:
                        temp_memory[patterns[i]] += count

        """if self.laser and hasattr(self.laser, 'power') and len(self.parties) >= 2 and hasattr(self.laser, 'is_emission_on') and self.laser.is_emission_on:
            noise_rate = 27.8 * self.laser.power * 2
            avg_noise = noise_rate * time_s
            n_noise_events = np.random.poisson(avg_noise)
            if n_noise_events > 0:
                alice_chs = self.parties[0].channels
                bob_chs = self.parties[1].channels
                possible_pairs = list(itertools.product(alice_chs, bob_chs))
                pair_indices = np.random.randint(0, len(possible_pairs), n_noise_events)
                
                for idx in pair_indices:
                    pair_key = tuple(sorted(possible_pairs[idx]))
                    temp_memory[pair_key] += 1"""  

        avg_dark = self.dark_count_rate * time_s
        
        # Get all active channels to apply dark counts to
        active_channels = []
        for p in self.parties:
            active_channels.extend(p.channels)
        active_channels = sorted(list(set(active_channels)))

        for ch in active_channels:
            n_dark = np.random.poisson(avg_dark)
            if n_dark > 0:
                # Write to temp instead of self._simulation_memory
                temp_memory[(ch,)] += n_dark

        # Calculate total counts per channel to determine accidental rates
        channel_totals = Counter()
        for pattern, count in temp_memory.items(): # Read from temp
            for ch in pattern:
                channel_totals[ch] += count

        # Iterate over all pairs of channels to add accidental coincidences
        for ch_a, ch_b in itertools.combinations(active_channels, 2):
            N_a = channel_totals[ch_a]
            N_b = channel_totals[ch_b]
            
            if N_a == 0 or N_b == 0: continue

            R_a = N_a / time_s
            R_b = N_b / time_s
            
            # Convert window from ns to seconds
            w_seconds = self.window_width * 1e-9
            
            # Rate of accidentals = Ra * Rb * Window
            # [Pr(Meas_A) + Pr(Dark_A)] * [Pr(Meas_B) + Pr(Dark_B)] * Window
            avg_acc = R_a * R_b * w_seconds * time_s
            
            n_acc = np.random.poisson(avg_acc)
            
            # Final = Pr(correct) + [All Accidental Terms]
            if n_acc > 0:
                key = tuple(sorted((ch_a, ch_b)))
                temp_memory[key] += n_acc

        self._last_duration = time_s
        self._simulation_memory = temp_memory

    def get_count_data(self, channels: list):
        """
        Returns (time, count, rate).
        Applies the Overlap Function to simulate delay mismatch.
        """
        req_set = set(channels)
        total_counts = 0
        
        # If we are looking at >1 channel, we check the delay mismatch
        overlap_factor = 1.0
        
        if len(channels) == 2:
            # User Formula: Exp[-(dA - dB)^2 / (2 * sigma^2)]
            chA, chB = channels[0], channels[1]
            
            # Map channel 1-16 to index 0-15
            dA = self.delays[chA - 1] if 1 <= chA <= 16 else 0
            dB = self.delays[chB - 1] if 1 <= chB <= 16 else 0
            
            # Gaussian Overlap
            sigma = JITTER_SIGMA_NS
            delta = dA - dB
            overlap_factor = np.exp(-(delta**2) / (2 * sigma**2))
            
            # If the mismatch is huge, count is effectively zero
            if overlap_factor < 1e-5: overlap_factor = 0

        for pattern, count in self._simulation_memory.items():
            if req_set.issubset(pattern):
                total_counts += count

        total_counts = int(total_counts * overlap_factor)

        rate = total_counts / self._last_duration if self._last_duration > 0 else 0
        return self._last_duration, total_counts, rate
        

    def set_window_width(self, window=3.0):
        self.window_width = float(window)
        print(f"[SIM] Coincidence window set to {window} ns")

    def set_channel_time_delays(self, delays):
        self.delays = list(delays)
        print(f"[SIM] Delays updated: {delays[:3]}...")

    def set_channel_voltage_thresholds(self, thresholds):
        self.thresholds = list(thresholds)
        print(f"[SIM] Thresholds updated: {thresholds[:3]}...")
    
    # --- Entangled State Methods ---

    def add_party(self, name, ch_0, ch_1):
        new_party = QuantumParty(name, ch_0, ch_1)
        self.parties.append(new_party)
        print(f"[SIM] Added Party '{name}' on Channels {ch_0}/{ch_1}")

    def save_tags(self, io=None, filename="tags", time=1.0, convert=True):
        """
        Generates raw time tags that respect the CURRENT QUANTUM STATE.
        """
        print(f"[SIM] Generating {time}s of physics-based tags...")
        
        base_rate = 0.0
        if self.laser and self.laser.is_emission_on:
             base_rate = self.laser.power * self.laser_rate

        if base_rate == 0:
            self._write_tags_file(io, filename, [])
            return

        num_events = int(base_rate * time)
        
        probs_map = {}
        outcomes = list(product([0, 1], repeat=len(self.parties))) # 0=Ch_A, 1=Ch_B
        
        total_prob = 0
        for outcome in outcomes:
            op_list = []
            channels = []
            for i, result_idx in enumerate(outcome):
                p = self.parties[i]
                op_list.append(p.ops[result_idx])
                channels.append(p.channels[result_idx]) 
            
            full_op = op_list[0]
            for op in op_list[1:]:
                full_op = np.kron(full_op, op)
                
            p = np.real(np.trace(self.rho @ full_op))

            eff = 1.0
            for ch in channels:
                eff *= self.channel_efficiencies[ch-1] if 1<=ch<=16 else 0
                
            probs_map[tuple(channels)] = p * eff
            total_prob += p * eff

        tags = []

        intervals = np.random.exponential(1/base_rate, num_events)
        emission_times_s = np.cumsum(intervals)

        pair_keys = list(probs_map.keys())
        pair_probs = list(probs_map.values())
        
        sum_p = sum(pair_probs)
        prob_no_click = 1.0 - sum_p
        if prob_no_click < 0: prob_no_click = 0
        
        distribution = np.random.multinomial(num_events, pair_probs + [prob_no_click])
        
        current_event_idx = 0
        for i, count in enumerate(distribution[:-1]): 
            if count == 0: continue
            
            active_channels = pair_keys[i] 
            
            start_idx = current_event_idx
            end_idx = current_event_idx + count
            if end_idx > len(emission_times_s): break
            
            these_times = emission_times_s[start_idx:end_idx]
            current_event_idx += count
            
            for ch in active_channels:
                delay = self.delays[ch-1] if 1<=ch<=16 else 0
                jitter = np.random.normal(0, JITTER_SIGMA_NS, count)
        
                times_ns = (these_times * 1e9) + delay + jitter
                bins = (times_ns / BIN_RESOLUTION_NS).astype(np.int64)
                
                for b in bins:
                    tags.append([ch, b])
                    
        # Sort and Save
        tags.sort(key=lambda x: x[1])
        self._write_tags_file(io, filename, tags)
    
    def _write_tags_file(self, io, filename, tags_list):
        if io:
            file_path = io.path.joinpath(f"{filename}.txt")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "w") as f:
                f.write("Channel\tTime\n") 
                for row in tags_list:
                    f.write(f"{int(row[0])}\t{int(row[1])}\n")
            
            print(f"[SIM] Saved {len(tags_list)} tags to {file_path}")

    def set_waveplates(self, party_name, hwp_angle, qwp_angle):
        """
        Set the waveplates for a specific party (e.g. 'Alice')
        Angles in Radians.
        """
        found = False
        for party in self.parties:
            if party.name.lower() == party_name.lower():
                party.set_waveplates(hwp_angle, qwp_angle)
                print(f"[SIM] Set {party.name} Waveplates -> HWP: {hwp_angle:.2f}, QWP: {qwp_angle:.2f}")
                found = True
                break
        if not found:
            print(f"[SIM] Party '{party_name}' not found.")

    def set_source_hwp(self, hwp_angle):
        """
        Updates the source to simulate a Type-II SPDC Source.
        
        Physics: 
        Pump |H> -> Generates Pair |HV> (|01>)
        Pump |V> -> Generates Pair |VH> (|10>)
        
        To get the Singlet State (|HV> - |VH>):
        The Pump must be Anti-Diagonal (|H> - |V>), achieved by HWP @ -22.5 deg.
        """
        
        Pump_State = complex_array([[1], [0]]) 

        offset = 0 #np.radians(-45)
        effective_angle = hwp_angle + offset

        # Rotate the Pump Laser
        Rotated_Pump = HWP(effective_angle) @ Pump_State
        
        alpha = Rotated_Pump[0, 0] # Amplitude of Horizontal Pump
        beta  = Rotated_Pump[1, 0] # Amplitude of Vertical Pump
        
        # |01> = Alice H, Bob V
        State_HV = np.kron(vec0, vec1)
        # |10> = Alice V, Bob H
        State_VH = np.kron(vec1, vec0)
        
        self.entangled_state = (alpha * State_HV) - (beta * State_VH)
         
        # Normalize
        norm = np.linalg.norm(self.entangled_state)
        if norm > 0:
            self.entangled_state = self.entangled_state / norm

        epsilon = 0.03915 
        gamma = 0.06
        Id4 = np.eye(4, dtype=complex) / 4.0
        noise_state1 = Proj((np.kron(vec0, vec1) + np.kron(vec1, vec0))/ 2)

        self.rho = (1 - epsilon - gamma )*Proj(self.entangled_state) + epsilon * Id4 + gamma * noise_state1

    def set_ambient_light(self, lights_on=False):
        """
        Simulates turning the lab lights on or off.
        """
        if lights_on:
            self.dark_count_rate = self.dark_count_rate_on
            print(f"[SIM] Lab Lights ON: Dark count rate increased to {self.dark_count_rate} Hz")
        else:
            self.dark_count_rate = self.dark_count_rate_off
            print(f"[SIM] Lab Lights OFF: Dark count rate reduced to {self.dark_count_rate} Hz")
        