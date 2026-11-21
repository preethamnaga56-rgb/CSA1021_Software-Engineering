import time
import math
import random
from typing import Optional
from Backend.config import config

class WorkloadScenarioManager:
    def __init__(self):
        self.current_scenario: str = "normal"
        self.manual_target_rps: Optional[float] = None
        self.current_rps: float = 75.0
        self.scenario_start_time: float = time.time()
        self.peak_target_rps: float = 75.0

    def set_scenario(self, scenario: str, custom_rps: Optional[float] = None):
        self.current_scenario = scenario
        self.scenario_start_time = time.time()
        
        if scenario == "normal":
            self.peak_target_rps = 75.0
            self.manual_target_rps = None
        elif scenario == "morning_rush":
            self.peak_target_rps = 320.0
            self.manual_target_rps = None
        elif scenario == "storm_emergency":
            self.peak_target_rps = 640.0
            self.manual_target_rps = None
        elif scenario == "tax_deadline":
            self.peak_target_rps = 950.0
            self.manual_target_rps = None
        elif scenario == "custom":
            self.manual_target_rps = custom_rps if custom_rps is not None else 120.0
            self.peak_target_rps = self.manual_target_rps

    def compute_next_rps(self) -> float:
        """Calculates realistic, continuous traffic volume curve."""
        elapsed = time.time() - self.scenario_start_time

        if self.current_scenario == "custom":
            target = self.manual_target_rps or 100.0
            self.current_rps += (target - self.current_rps) * 0.35 + random.uniform(-2.0, 2.0)
            return max(5.0, self.current_rps)

        elif self.current_scenario == "normal":
            base = 70.0 + 15.0 * math.sin(elapsed * 0.08)
            jitter = random.gauss(0, 3.0)
            self.current_rps = max(35.0, base + jitter)
            return self.current_rps

        elif self.current_scenario == "morning_rush":
            progress = min(1.0, elapsed / 25.0)
            target = 75.0 + (self.peak_target_rps - 75.0) * progress
            self.current_rps = target + random.gauss(0, 8.0)
            return max(40.0, self.current_rps)

        elif self.current_scenario == "storm_emergency":
            progress = min(1.0, elapsed / 12.0)
            sigmoid = 1.0 / (1.0 + math.exp(-6.0 * (progress - 0.4)))
            target = 75.0 + (self.peak_target_rps - 75.0) * sigmoid
            self.current_rps = target + random.gauss(0, 15.0)
            return max(50.0, self.current_rps)

        elif self.current_scenario == "tax_deadline":
            progress = min(1.0, elapsed / 18.0)
            target = 80.0 + (self.peak_target_rps - 80.0) * (progress ** 1.3)
            self.current_rps = target + random.gauss(0, 22.0)
            return max(60.0, self.current_rps)

        return self.current_rps

workload_manager = WorkloadScenarioManager()
