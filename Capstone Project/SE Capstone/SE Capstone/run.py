"""
CivicScale Application Launcher
Starts the FastAPI API Gateway with Serverless ML & Serves Frontend on http://localhost:8000
"""

import uvicorn
import sys
import os

if __name__ == "__main__":
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    if curr_dir not in sys.path:
        sys.path.insert(0, curr_dir)

    print("=" * 70)
    print(" CIVICSCALE: CLOUD-NATIVE PUBLIC SERVICE PLATFORM")
    print(" Segregated Architecture: [Frontend] | [Backend] | [API]")
    print("=" * 70)
    print(" >> Starting Gateway Server on http://localhost:8000")
    print(" >> Citizen Public Portal: http://localhost:8000")
    print(" >> Interactive API Explorer: http://localhost:8000/docs")
    print(" >> Prometheus Metrics: http://localhost:8000/metrics")
    print("=" * 70)

    uvicorn.run(
        "API.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
