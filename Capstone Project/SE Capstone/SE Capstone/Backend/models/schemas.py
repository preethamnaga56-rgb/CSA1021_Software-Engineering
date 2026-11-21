from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class ServiceCategory(str, Enum):
    EMERGENCY = "emergency_assistance"
    UTILITY = "utility_outage"
    TRANSIT = "transit_pass"
    PERMITS = "building_permit"
    TAX = "municipal_tax"
    GENERAL = "general_inquiry"

class TicketPriority(str, Enum):
    P1_CRITICAL = "P1_CRITICAL"
    P2_HIGH = "P2_HIGH"
    P3_MEDIUM = "P3_MEDIUM"
    P4_ROUTINE = "P4_ROUTINE"

class TicketStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    RESOLVED = "RESOLVED"
    SLA_BREACHED = "SLA_BREACHED"

class CivicTicketCreate(BaseModel):
    citizen_name: str
    citizen_email: str
    category: ServiceCategory
    district: str = "District 4 - Metro Center"
    summary: str
    details: Optional[str] = None

class CivicTicket(BaseModel):
    id: str
    citizen_name: str
    citizen_email: str
    category: ServiceCategory
    priority: TicketPriority
    district: str
    summary: str
    details: Optional[str] = None
    status: TicketStatus
    created_at: float
    assigned_pod_id: Optional[str] = None
    processing_time_ms: Optional[float] = None
    sla_seconds: float
    sla_remaining_seconds: float

class PodState(str, Enum):
    STARTING = "STARTING"
    READY = "READY"
    TERMINATING = "TERMINATING"

class PodMetrics(BaseModel):
    id: str
    node_name: str
    state: PodState
    cpu_percent: float
    memory_mb: float
    active_requests: int
    uptime_seconds: float
    processed_count: int

class ClusterTelemetry(BaseModel):
    timestamp: float
    cluster_name: str
    current_replicas: int
    target_replicas: int
    ready_replicas: int
    pending_replicas: int
    terminating_replicas: int
    total_rps: float
    avg_cpu_percent: float
    avg_memory_mb: float
    avg_latency_ms: float
    queue_depth: int
    p95_latency_ms: float
    p99_latency_ms: float
    sla_compliance_rate: float
    pods: List[PodMetrics]

class HPADecision(BaseModel):
    timestamp: float
    current_replicas: int
    reactive_desired_replicas: int
    predictive_desired_replicas: int
    final_target_replicas: int
    scaling_action: str
    reason: str
    cooldown_remaining_sec: float

class ModelAccuracyMetrics(BaseModel):
    r2_score: float
    mae: float
    rmse: float
    mape_percent: float
    interval_coverage_pct: float
    sample_size: int
    algorithm_name: str
    ensemble_weights: Dict[str, float] = Field(default_factory=dict)

class PredictionPoint(BaseModel):
    step_minute: int
    timestamp: float
    forecasted_rps: float
    lower_bound_rps: float
    upper_bound_rps: float
    recommended_replicas: int

class PredictiveTelemetry(BaseModel):
    forecast_horizon_minutes: int
    model_type: str
    confidence_interval: float
    trend_direction: str
    predictions: List[PredictionPoint]
    surge_alert: bool
    surge_probability: float
    accuracy: Optional[ModelAccuracyMetrics] = None
    feature_importance: Optional[Dict[str, float]] = None

class WorkloadScenarioRequest(BaseModel):
    scenario: str
    target_rps: Optional[float] = None
    chaos_pod_failure: Optional[bool] = False
