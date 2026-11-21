from fastapi import APIRouter, Body
from typing import Optional
from Backend.models.schemas import ClusterTelemetry, HPADecision, WorkloadScenarioRequest
from Backend.services.cluster_simulator import cluster_simulator
from Backend.services.predictive_engine import predictive_engine
from Backend.services.workload_generator import workload_manager

router = APIRouter(prefix="/api/telemetry", tags=["Cluster & Autoscaler Telemetry"])

@router.get("/cluster", response_model=ClusterTelemetry)
def get_cluster_telemetry():
    """Returns real-time Kubernetes cluster status, nodes, and pod metrics."""
    current_rps = workload_manager.compute_next_rps()
    forecast = predictive_engine.forecast()
    return cluster_simulator.step_simulation(current_rps, forecast)

@router.get("/hpa", response_model=HPADecision)
def get_hpa_telemetry():
    """Returns current Horizontal Pod Autoscaling metrics, target calculations and cooldown."""
    if cluster_simulator.latest_hpa_decision:
        return cluster_simulator.latest_hpa_decision
    current_rps = workload_manager.compute_next_rps()
    forecast = predictive_engine.forecast()
    return cluster_simulator.evaluate_hpa_step(current_rps, forecast)

@router.post("/scenario")
def set_workload_scenario(req: WorkloadScenarioRequest):
    """
    Switches active civic workload scenario (normal, morning_rush, storm_emergency, tax_deadline, custom).
    Also allows triggering chaos engineering pod failure.
    """
    workload_manager.set_scenario(req.scenario, custom_rps=req.target_rps)
    chaos_result = None
    if req.chaos_pod_failure:
        chaos_result = cluster_simulator.trigger_pod_failure_chaos()

    return {
        "status": "success",
        "scenario": workload_manager.current_scenario,
        "peak_target_rps": workload_manager.peak_target_rps,
        "chaos_pod_killed": chaos_result
    }

@router.post("/chaos/kill-pod")
def trigger_chaos_pod_failure():
    """Triggers an abrupt worker pod failure to test Kubernetes autonomous self-healing and recovery."""
    killed_pod_id = cluster_simulator.trigger_pod_failure_chaos()
    return {
        "status": "triggered" if killed_pod_id else "no_ready_pods",
        "killed_pod_id": killed_pod_id
    }
