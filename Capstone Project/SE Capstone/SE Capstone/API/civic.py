from fastapi import APIRouter, Query, Body, Response
from typing import Optional, Dict, Any
from Backend.services.civic_service import civic_desk
from Backend.services.cluster_simulator import cluster_simulator
import random

router = APIRouter(prefix="/api/civic", tags=["Public Civic Services"])

@router.get("/requests")
def list_public_requests(
    query: Optional[str] = None,
    agency: Optional[str] = None,
    district: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    sort_by: Optional[str] = "created_date",
    sort_dir: Optional[str] = "desc",
    page: int = 1,
    page_size: int = 15
):
    """
    Search, multi-attribute filter, sort, and paginate across 260+ authentic public 311 civic service requests.
    Provides sub-millisecond in-memory indexed lookups with zero inconvenience.
    """
    return civic_desk.get_public_requests(
        query=query,
        agency=agency,
        district=district,
        status=status,
        priority=priority,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size
    )

@router.post("/requests")
def submit_citizen_request(payload: Dict[str, Any] = Body(...)):
    """
    Submit a new public civic service request directly to the platform.
    Automatically assigns to an active scaled worker pod, geocodes coordinates, and atomically persists to disk.
    """
    ready_pods = [p for p in cluster_simulator.pods if p.state.value == "READY"]
    assigned_pod = random.choice(ready_pods).id if ready_pods else "k8s-ingress-buffer"
    return civic_desk.submit_public_request(payload, assigned_pod_id=assigned_pod)

@router.get("/export/csv")
def export_requests_csv(
    query: Optional[str] = None,
    agency: Optional[str] = None,
    district: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None
):
    """Exports filtered public 311 civic service dataset to standardized RFC 4180 CSV."""
    csv_content = civic_desk.export_csv(
        query=query,
        agency=agency,
        district=district,
        status=status,
        priority=priority
    )
    headers = {
        "Content-Disposition": "attachment; filename=public_311_service_requests.csv"
    }
    return Response(content=csv_content, media_type="text/csv", headers=headers)

@router.get("/export/json")
def export_requests_json(
    query: Optional[str] = None,
    agency: Optional[str] = None,
    district: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None
):
    """Exports filtered public 311 civic service dataset to formatted JSON."""
    json_content = civic_desk.export_json(
        query=query,
        agency=agency,
        district=district,
        status=status,
        priority=priority
    )
    headers = {
        "Content-Disposition": "attachment; filename=public_311_service_requests.json"
    }
    return Response(content=json_content, media_type="application/json", headers=headers)

@router.get("/analytics/summary")
def get_civic_analytics_summary():
    """Returns aggregated cross-agency SLA, district distribution, and hourly volume intelligence."""
    return civic_desk.get_detailed_analytics_summary()

@router.get("/tickets")
def list_legacy_tickets(limit: int = 25):
    res = civic_desk.get_public_requests(page=1, page_size=limit)
    return res["records"]
