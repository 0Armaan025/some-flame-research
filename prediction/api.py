"""FLEX PSI-69 Phase 6 - FastAPI service for the recorded-outcome predictor.

The human developer builds the frontend; this service is the stable backend
contract. Run:

    notebooks/.venv/bin/python -m uvicorn prediction.api:app --port 8000

Endpoints:
    GET  /health
    GET  /model-info
    GET  /features
    POST /predict

Response schemas are documented in prediction/README.md and in
deliverables/FRONTEND_INTEGRATION_GUIDE.md. All model outputs are statistical
associations of recorded outcome labels, never causal or physical claims.
"""

import os
import sys
from collections import OrderedDict

from fastapi import FastAPI

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import predict as engine

app = FastAPI(
    title="FLEX PSI-69 Recorded-Outcome Prediction API",
    description=("Predicts the recorded experimental outcome label "
                 "(Extinction / Disruption / Completion) from pre-outcome "
                 "conditions. Statistical associations only; not a physical "
                 "combustion model."),
    version="6.0.0",
)


@app.get("/health")
def health():
    try:
        info = engine.model_info()
        return {"status": "ok", "model_available": True,
                "model_version": info["model_version"],
                "selected_model": info["selected_model"]}
    except Exception as exc:  # no baseline-only mode yet
        return {"status": "degraded", "model_available": False, "detail": str(exc)}


@app.get("/model-info")
def model_info():
    return engine.model_info()


@app.get("/features")
def features():
    return {"features": engine.feature_spec(),
            "note": ("all features are pre-outcome, documented experimental "
                     "conditions; the unresolved burning-rate column and every "
                     "post-outcome quantity are deliberately excluded")}


@app.post("/predict")
def predict(conditions: dict):
    """Predict from pre-outcome conditions.

    Required keys: fuel, d0_mm, pressure_mmHg, o2_mf, n2_mf, co2_mf, he_mf.
    'diluent_type' is optional (recoded from the CO2/He fractions).
    """
    missing = [k for k in engine.REQUIRED_INPUTS if k not in conditions]
    if missing:
        return {"error": "missing_required_inputs", "missing": missing,
                "required": list(engine.REQUIRED_INPUTS)}
    response = engine.predict_outcome(conditions)
    return response
