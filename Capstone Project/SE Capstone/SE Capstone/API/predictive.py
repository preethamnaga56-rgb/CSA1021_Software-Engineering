from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from Backend.models.schemas import PredictiveTelemetry, ModelAccuracyMetrics
from Backend.services.predictive_engine import predictive_engine

router = APIRouter(prefix="/api/predictive", tags=["Serverless Predictive Analytics"])

class PredictiveConfigUpdate(BaseModel):
    horizon_minutes: Optional[int] = None
    surge_sensitivity: Optional[float] = None
    confidence_level: Optional[float] = None

@router.get("/forecast", response_model=PredictiveTelemetry)
def get_predictive_forecast():
    """Executes serverless ML inference using Quantile Gradient Boosted Ensemble to predict workload and proactive replica requirements."""
    return predictive_engine.forecast()

@router.get("/accuracy")
def get_model_accuracy():
    """Returns continuous real-time model accuracy metrics including R², MAE, RMSE, MAPE, and Quantile Coverage."""
    forecast = predictive_engine.forecast()
    return {
        "model_type": forecast.model_type,
        "accuracy": forecast.accuracy,
        "feature_importance": forecast.feature_importance,
        "confidence_level": forecast.confidence_interval,
        "horizon_minutes": forecast.forecast_horizon_minutes
    }

@router.post("/config")
def update_predictive_config(update: PredictiveConfigUpdate):
    """Dynamically tunes serverless ML hyperparameters."""
    if update.horizon_minutes is not None:
        predictive_engine.prediction_horizon = max(5, min(30, update.horizon_minutes))
    if update.surge_sensitivity is not None:
        predictive_engine.surge_sensitivity = max(1.1, min(2.5, update.surge_sensitivity))
    if update.confidence_level is not None:
        predictive_engine.confidence_level = max(0.80, min(0.99, update.confidence_level))
    return {
        "status": "updated",
        "horizon_minutes": predictive_engine.prediction_horizon,
        "surge_sensitivity": predictive_engine.surge_sensitivity,
        "confidence_level": predictive_engine.confidence_level
    }
