import os
from pydantic import BaseModel

class SystemConfig:
    # Cluster Configuration
    CLUSTER_NAME: str = "civicscale-k8s-prod-us-east"
    NODE_COUNT: int = 3
    NODE_NAMES: list[str] = ["node-us-east-1a", "node-us-east-1b", "node-us-east-1c"]
    POD_CAPACITY_RPS: int = 40
    
    # HPA Configuration
    HPA_MIN_REPLICAS: int = 2
    HPA_MAX_REPLICAS: int = 24
    HPA_TARGET_CPU_UTILIZATION: int = 65
    HPA_SCALE_UP_RATE_LIMIT: int = 4
    HPA_SCALE_DOWN_STABILIZATION_SEC: int = 20
    
    # Predictive Analytics Configuration
    PREDICTION_HORIZON_STEPS: int = 15
    PREDICTIVE_WEIGHT: float = 0.65
    SURGE_THRESHOLD_FACTOR: float = 1.35
    
    # Pod Provisioning Simulation
    POD_INIT_LATENCY_SECONDS: float = 4.0
    POD_TERMINATION_GRACE_PERIOD: float = 3.0
    
    # SLA Response Targets (seconds)
    SLA_EMERGENCY: float = 0.8
    SLA_UTILITY: float = 1.5
    SLA_TRANSIT: float = 2.0
    SLA_PERMITS: float = 3.0
    SLA_TAX: float = 3.5

config = SystemConfig()
