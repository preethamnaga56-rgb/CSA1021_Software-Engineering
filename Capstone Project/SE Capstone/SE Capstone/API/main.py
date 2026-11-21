import os
import sys
import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add project root to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from Backend.config import config
from Backend.services.workload_generator import workload_manager
from Backend.services.predictive_engine import predictive_engine
from Backend.services.cluster_simulator import cluster_simulator
from Backend.services.civic_service import civic_desk

from API.civic import router as civic_router
from API.telemetry import router as telemetry_router
from API.predictive import router as predictive_router
from API.metrics import router as metrics_router

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

ws_manager = ConnectionManager()

# Background real-time telemetry loop
async def telemetry_background_worker():
    while True:
        try:
            current_rps = workload_manager.compute_next_rps()
            predictive_engine.record_telemetry(current_rps)
            forecast = predictive_engine.forecast()
            cluster_state = cluster_simulator.step_simulation(current_rps, forecast)
            civic_desk.update_tickets_lifecycle()

            payload = {
                "type": "TELEMETRY_UPDATE",
                "cluster": cluster_state.model_dump(),
                "hpa": cluster_simulator.latest_hpa_decision.model_dump() if cluster_simulator.latest_hpa_decision else None,
                "predictive": forecast.model_dump(),
                "scenario": {
                    "current": workload_manager.current_scenario,
                    "target_rps": workload_manager.peak_target_rps
                }
            }
            await ws_manager.broadcast(payload)
        except Exception as e:
            print(f"Error in telemetry worker: {e}")

        await asyncio.sleep(1.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(telemetry_background_worker())
    yield
    task.cancel()


app = FastAPI(
    title="CivicScale API Gateway",
    description="Cloud-Native Public Service Platform API with Serverless Predictive Autoscaling",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(civic_router)
app.include_router(telemetry_router)
app.include_router(predictive_router)
app.include_router(metrics_router)

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

# Mount Frontend static directory
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Frontend"))
if not os.path.exists(frontend_dir):
    # Fallback to lowercase frontend if exists
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
