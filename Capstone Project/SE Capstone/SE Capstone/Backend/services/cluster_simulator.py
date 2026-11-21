import time
import uuid
import math
import random
from typing import List, Dict, Optional
from Backend.config import config
from Backend.models.schemas import PodMetrics, PodState, ClusterTelemetry, HPADecision, PredictiveTelemetry

class VirtualPod:
    def __init__(self, pod_id: str, node_name: str):
        self.id = pod_id
        self.node_name = node_name
        self.state = PodState.STARTING
        self.creation_time = time.time()
        self.termination_start_time: Optional[float] = None
        self.cpu_percent = 5.0
        self.memory_mb = 128.0
        self.active_requests = 0
        self.processed_count = 0

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.creation_time

    def update_lifecycle(self):
        now = time.time()
        if self.state == PodState.STARTING:
            if now - self.creation_time >= config.POD_INIT_LATENCY_SECONDS:
                self.state = PodState.READY
        elif self.state == PodState.TERMINATING:
            if self.termination_start_time and (now - self.termination_start_time >= config.POD_TERMINATION_GRACE_PERIOD):
                return False
        return True

    def calculate_telemetry(self, assigned_rps: float):
        if self.state == PodState.READY:
            load_factor = assigned_rps / float(config.POD_CAPACITY_RPS)
            base_cpu = 6.0
            jitter = random.uniform(-2.5, 2.5)
            self.cpu_percent = max(4.0, min(100.0, base_cpu + (load_factor * 60.0) + jitter))
            self.memory_mb = 140.0 + (self.cpu_percent * 2.2) + random.uniform(-5.0, 5.0)
            self.active_requests = int(assigned_rps * random.uniform(0.8, 1.2))
            self.processed_count += int(assigned_rps)
        elif self.state == PodState.STARTING:
            self.cpu_percent = 28.0 + random.uniform(-4.0, 4.0)
            self.memory_mb = 110.0 + random.uniform(0, 10.0)
            self.active_requests = 0
        else:
            self.cpu_percent = max(1.0, self.cpu_percent * 0.4)
            self.active_requests = 0

    def to_metrics(self) -> PodMetrics:
        return PodMetrics(
            id=self.id,
            node_name=self.node_name,
            state=self.state,
            cpu_percent=round(self.cpu_percent, 1),
            memory_mb=round(self.memory_mb, 1),
            active_requests=self.active_requests,
            uptime_seconds=round(self.uptime_seconds, 1),
            processed_count=self.processed_count
        )


class KubernetesClusterSimulator:
    def __init__(self):
        self.cluster_name = config.CLUSTER_NAME
        self.nodes = config.NODE_NAMES
        self.pods: List[VirtualPod] = []
        self.last_hpa_eval_time = time.time()
        self.last_scale_down_time = time.time()
        self.latest_hpa_decision: Optional[HPADecision] = None
        self.queue_depth = 0
        self.recent_latencies: List[float] = [25.0] * 20
        self.sla_breach_count = 0
        self.total_completed_requests = 0
        
        for i in range(config.HPA_MIN_REPLICAS):
            pod = VirtualPod(
                pod_id=f"civic-worker-{uuid.uuid4().hex[:6]}",
                node_name=self.nodes[i % len(self.nodes)]
            )
            pod.state = PodState.READY
            pod.cpu_percent = 18.0
            self.pods.append(pod)

    def _get_next_node(self) -> str:
        node_counts = {n: 0 for n in self.nodes}
        for p in self.pods:
            if p.state != PodState.TERMINATING:
                node_counts[p.node_name] += 1
        return min(node_counts, key=node_counts.get)

    def trigger_pod_failure_chaos(self) -> Optional[str]:
        ready_pods = [p for p in self.pods if p.state == PodState.READY]
        if not ready_pods:
            return None
        killed_pod = random.choice(ready_pods)
        self.pods.remove(killed_pod)
        return killed_pod.id

    def evaluate_hpa_step(self, current_rps: float, forecast_telemetry: PredictiveTelemetry) -> HPADecision:
        now = time.time()
        ready_pods = [p for p in self.pods if p.state == PodState.READY]
        active_pods = [p for p in self.pods if p.state != PodState.TERMINATING]
        current_count = len(active_pods)
        
        # 1. Reactive calculation
        if ready_pods:
            avg_cpu = sum(p.cpu_percent for p in ready_pods) / len(ready_pods)
        else:
            avg_cpu = 100.0

        target_cpu = float(config.HPA_TARGET_CPU_UTILIZATION)
        if ready_pods:
            raw_reactive = math.ceil(len(ready_pods) * (avg_cpu / target_cpu))
        else:
            raw_reactive = config.HPA_MIN_REPLICAS + 2

        reactive_desired = max(config.HPA_MIN_REPLICAS, min(config.HPA_MAX_REPLICAS, raw_reactive))

        # 2. Serverless Predictive calculation
        predictive_desired = config.HPA_MIN_REPLICAS
        if forecast_telemetry and forecast_telemetry.predictions:
            lead_window = forecast_telemetry.predictions[:3]
            max_lead_rps = max(p.forecasted_rps for p in lead_window)
            effective_capacity = config.POD_CAPACITY_RPS * (target_cpu / 100.0)
            pred_reps = math.ceil(max_lead_rps / effective_capacity)
            predictive_desired = max(config.HPA_MIN_REPLICAS, min(config.HPA_MAX_REPLICAS, pred_reps))

        # 3. Dynamic Arbitrator
        scaling_action = "STEADY"
        reason = "Current capacity matches target demand."
        
        if predictive_desired > current_count:
            target_reps = predictive_desired
            scaling_action = "SCALE_UP"
            reason = f"Proactive Predictive trigger: Forecasted surge to {predictive_desired} pods (overcoming {config.POD_INIT_LATENCY_SECONDS}s startup delay)."
        elif reactive_desired > current_count:
            target_reps = reactive_desired
            scaling_action = "SCALE_UP"
            reason = f"Reactive CPU trigger: Cluster CPU at {avg_cpu:.1f}% exceeds target {target_cpu}%."
        elif reactive_desired < current_count and predictive_desired < current_count:
            time_since_last_scaledown = now - self.last_scale_down_time
            if time_since_last_scaledown >= config.HPA_SCALE_DOWN_STABILIZATION_SEC:
                target_reps = max(current_count - 2, max(reactive_desired, predictive_desired))
                scaling_action = "SCALE_DOWN"
                reason = f"Workload stabilized; scaling down after {config.HPA_SCALE_DOWN_STABILIZATION_SEC}s cooldown window."
                self.last_scale_down_time = now
            else:
                target_reps = current_count
                scaling_action = "STEADY"
                cooldown_left = config.HPA_SCALE_DOWN_STABILIZATION_SEC - time_since_last_scaledown
                reason = f"Scale-down suppressed by HPA stabilization window ({cooldown_left:.1f}s cooldown remaining)."
        else:
            target_reps = current_count
            scaling_action = "STEADY"
            reason = f"Replica balance optimal. CPU: {avg_cpu:.1f}%, Active: {current_count} pods."

        if target_reps > current_count:
            max_allowed = current_count + config.HPA_SCALE_UP_RATE_LIMIT
            if target_reps > max_allowed:
                target_reps = max_allowed
                reason += f" (Capped by HPA velocity limit +{config.HPA_SCALE_UP_RATE_LIMIT})."

        target_reps = max(config.HPA_MIN_REPLICAS, min(config.HPA_MAX_REPLICAS, target_reps))

        # 4. Apply Pod Adjustments
        if target_reps > current_count:
            add_count = target_reps - current_count
            for _ in range(add_count):
                new_pod = VirtualPod(
                    pod_id=f"civic-worker-{uuid.uuid4().hex[:6]}",
                    node_name=self._get_next_node()
                )
                self.pods.append(new_pod)
        elif target_reps < current_count:
            remove_count = current_count - target_reps
            candidates = [p for p in self.pods if p.state != PodState.TERMINATING]
            candidates.sort(key=lambda p: (p.uptime_seconds, p.active_requests))
            for i in range(min(remove_count, len(candidates))):
                candidates[i].state = PodState.TERMINATING
                candidates[i].termination_start_time = now

        time_since_down = now - self.last_scale_down_time
        cooldown_remaining = max(0.0, config.HPA_SCALE_DOWN_STABILIZATION_SEC - time_since_down)

        decision = HPADecision(
            timestamp=now,
            current_replicas=current_count,
            reactive_desired_replicas=reactive_desired,
            predictive_desired_replicas=predictive_desired,
            final_target_replicas=target_reps,
            scaling_action=scaling_action,
            reason=reason,
            cooldown_remaining_sec=round(cooldown_remaining, 1)
        )
        self.latest_hpa_decision = decision
        return decision

    def step_simulation(self, current_rps: float, forecast_telemetry: PredictiveTelemetry) -> ClusterTelemetry:
        now = time.time()
        surviving_pods = []
        for p in self.pods:
            if p.update_lifecycle():
                surviving_pods.append(p)
        self.pods = surviving_pods

        self.evaluate_hpa_step(current_rps, forecast_telemetry)

        ready_pods = [p for p in self.pods if p.state == PodState.READY]
        num_ready = len(ready_pods)

        if num_ready > 0:
            rps_per_pod = current_rps / num_ready
            load_ratio = rps_per_pod / config.POD_CAPACITY_RPS
            if load_ratio <= 1.0:
                step_latency = 22.0 + (load_ratio * 25.0) + random.uniform(-3.0, 5.0)
            else:
                step_latency = 47.0 + math.pow(load_ratio - 1.0, 2) * 120.0 + random.uniform(5.0, 20.0)

            for p in ready_pods:
                p.calculate_telemetry(rps_per_pod)
        else:
            step_latency = 850.0
            rps_per_pod = 0.0

        for p in self.pods:
            if p.state != PodState.READY:
                p.calculate_telemetry(0.0)

        self.recent_latencies.append(step_latency)
        if len(self.recent_latencies) > 30:
            self.recent_latencies.pop(0)

        avg_latency = float(sum(self.recent_latencies) / len(self.recent_latencies))
        p95_latency = float(sorted(self.recent_latencies)[int(len(self.recent_latencies) * 0.95)])
        p99_latency = float(sorted(self.recent_latencies)[-1])

        total_cluster_capacity = num_ready * config.POD_CAPACITY_RPS
        if current_rps > total_cluster_capacity:
            unhandled = current_rps - total_cluster_capacity
            self.queue_depth = min(1200, int(self.queue_depth + unhandled * 0.25))
        else:
            self.queue_depth = max(0, int(self.queue_depth - (total_cluster_capacity - current_rps) * 0.4))

        if p95_latency > 250.0 or self.queue_depth > 300:
            self.sla_breach_count += 1
        
        self.total_completed_requests += int(current_rps)
        total_evals = max(1, self.total_completed_requests)
        sla_rate = max(88.0, 100.0 - (self.sla_breach_count * 100.0 / total_evals))

        avg_cpu = sum(p.cpu_percent for p in self.pods) / len(self.pods) if self.pods else 0.0
        avg_mem = sum(p.memory_mb for p in self.pods) / len(self.pods) if self.pods else 0.0

        return ClusterTelemetry(
            timestamp=now,
            cluster_name=self.cluster_name,
            current_replicas=len(self.pods),
            target_replicas=self.latest_hpa_decision.final_target_replicas if self.latest_hpa_decision else len(self.pods),
            ready_replicas=num_ready,
            pending_replicas=len([p for p in self.pods if p.state == PodState.STARTING]),
            terminating_replicas=len([p for p in self.pods if p.state == PodState.TERMINATING]),
            total_rps=round(current_rps, 1),
            avg_cpu_percent=round(avg_cpu, 1),
            avg_memory_mb=round(avg_mem, 1),
            avg_latency_ms=round(avg_latency, 1),
            queue_depth=self.queue_depth,
            p95_latency_ms=round(p95_latency, 1),
            p99_latency_ms=round(p99_latency, 1),
            sla_compliance_rate=round(sla_rate, 2),
            pods=[p.to_metrics() for p in self.pods]
        )

cluster_simulator = KubernetesClusterSimulator()
