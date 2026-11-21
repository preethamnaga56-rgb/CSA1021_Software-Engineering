from fastapi import APIRouter, Response
from Backend.services.cluster_simulator import cluster_simulator
from Backend.services.predictive_engine import predictive_engine
from Backend.services.workload_generator import workload_manager

router = APIRouter(tags=["Cloud-Native Prometheus Metrics"])

@router.get("/metrics")
def prometheus_metrics():
    """
    Exposes OpenMetrics / Prometheus standard text format for K8s HPA custom metrics adapter.
    """
    active_pods = [p for p in cluster_simulator.pods if p.state.value != "TERMINATING"]
    ready_pods = [p for p in cluster_simulator.pods if p.state.value == "READY"]
    pending_pods = [p for p in cluster_simulator.pods if p.state.value == "STARTING"]
    terminating_pods = [p for p in cluster_simulator.pods if p.state.value == "TERMINATING"]
    
    current_rps = workload_manager.current_rps
    forecast = predictive_engine.forecast()
    predicted_rps = forecast.predictions[0].forecasted_rps if forecast.predictions else current_rps
    
    avg_cpu = sum(p.cpu_percent for p in cluster_simulator.pods) / len(cluster_simulator.pods) if cluster_simulator.pods else 0.0
    avg_latency_sec = (sum(cluster_simulator.recent_latencies) / len(cluster_simulator.recent_latencies)) / 1000.0 if cluster_simulator.recent_latencies else 0.025

    lines = [
        "# HELP civicscale_requests_total Total cumulative citizen requests processed",
        "# TYPE civicscale_requests_total counter",
        f"civicscale_requests_total {cluster_simulator.total_completed_requests}",
        "",
        "# HELP civicscale_current_rps Current incoming citizen requests per second",
        "# TYPE civicscale_current_rps gauge",
        f"civicscale_current_rps {current_rps:.2f}",
        "",
        "# HELP civicscale_predicted_rps Serverless ML forecasted RPS for next horizon",
        "# TYPE civicscale_predicted_rps gauge",
        f"civicscale_predicted_rps {predicted_rps:.2f}",
        "",
        "# HELP civicscale_pod_replicas Number of pods partitioned by lifecycle state",
        "# TYPE civicscale_pod_replicas gauge",
        f'civicscale_pod_replicas{{state="ready"}} {len(ready_pods)}',
        f'civicscale_pod_replicas{{state="pending"}} {len(pending_pods)}',
        f'civicscale_pod_replicas{{state="terminating"}} {len(terminating_pods)}',
        f'civicscale_pod_replicas{{state="total"}} {len(cluster_simulator.pods)}',
        "",
        "# HELP civicscale_cpu_utilization_percent Average CPU utilization across active pods",
        "# TYPE civicscale_cpu_utilization_percent gauge",
        f"civicscale_cpu_utilization_percent {avg_cpu:.2f}",
        "",
        "# HELP civicscale_response_latency_seconds Average end-to-end response latency",
        "# TYPE civicscale_response_latency_seconds gauge",
        f"civicscale_response_latency_seconds {avg_latency_sec:.4f}",
        "",
        "# HELP civicscale_queue_depth Pending citizen requests awaiting worker thread assignment",
        "# TYPE civicscale_queue_depth gauge",
        f"civicscale_queue_depth {cluster_simulator.queue_depth}",
        "",
        "# HELP civicscale_sla_compliance_ratio Percentage of citizen requests meeting strict SLA requirements",
        "# TYPE civicscale_sla_compliance_ratio gauge",
        f"civicscale_sla_compliance_ratio {cluster_simulator.sla_breach_count}"
    ]
    return Response(content="\n".join(lines) + "\n", media_type="text/plain; version=0.0.4; charset=utf-8")
