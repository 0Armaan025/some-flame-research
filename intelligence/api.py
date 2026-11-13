"""FLEX-PSI69 evidence intelligence - backend API.

Endpoints:
    GET  /health
    GET  /questions
    GET  /experiments
    POST /query                {"question_id": "Q1"[, "parameters": {...}]}
    POST /predict              (optional; delegates to the validated recorded-
                                outcome classifier in prediction/)
    GET  /evidence/{test_no}

Run:
    notebooks/.venv/bin/python -m uvicorn intelligence.api:app --port 8001

All answers are deterministic and traceable; the prediction endpoint is a
recorded-label classifier, not a physical fire-risk model.
"""

import json
import os
import sys
from collections import OrderedDict

from fastapi import FastAPI

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence_engine as engine
import explanations
import retrieval as R

app = FastAPI(
    title="FLEX-PSI69 Evidence Intelligence API",
    description=("Deterministic question-to-evidence engine over the FLEX-PSI69 "
                 "droplet-combustion release. No LLM; every number recomputed "
                 "from the raw table or quoted from frozen analysis artifacts."),
    version="1.0.0",
)


@app.get("/health")
def health():
    try:
        catalog = engine.load_catalog()
        recs = engine.records()
        return {"status": "ok", "records": len(recs),
                "questions": len(catalog["questions"]),
                "dataset": catalog["dataset"],
                "raw_sha256": R.sha256_of(R.raw_csv_path())}
    except Exception as exc:
        return {"status": "degraded", "detail": str(exc)}


@app.get("/questions")
def questions():
    catalog = engine.load_catalog()
    return OrderedDict(
        questions=catalog["questions"],
        engine=catalog["engine"],
        note=("use POST /query with {\"question_id\": \"Q1\"..\"Q7\"}; Q4 accepts "
              "an optional parameters object, e.g. {\"o2_mf\": 0.21}"))


@app.get("/experiments")
def experiments(fuel: str = None, outcome: str = None, series: str = None,
                has_flag: str = None, text: str = None, limit: int = 50):
    filters = {k: v for k, v in dict(fuel=fuel, outcome=outcome, series=series,
                                     flags=has_flag, text=text).items()
               if v is not None}
    return engine.list_experiments(filters, limit=limit)


@app.post("/query")
def query(payload: dict):
    qid = payload.get("question_id")
    if not qid:
        return {"error": "question_id required",
                "available": [q["id"] for q in engine.load_catalog()["questions"]]}
    try:
        answer = engine.answer_question(qid, payload.get("parameters"))
    except KeyError as exc:
        return {"error": str(exc)}
    problems = explanations.validate(answer)
    if problems:
        return {"error": "answer_contract_violation", "problems": problems}
    return answer


@app.post("/predict")
def predict(conditions: dict):
    """Optional recorded-outcome classifier (separate component).

    Returns a clear error payload when the validated model is unavailable.
    """
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))), "prediction"))
        import predict as engine_pred
    except Exception as exc:  # model or deps unavailable
        return {"error": "prediction_module_unavailable", "detail": str(exc),
                "note": ("the recorded-outcome classifier is an optional, "
                         "separately validated component; the evidence engine "
                         "works without it")}
    missing = [k for k in engine_pred.REQUIRED_INPUTS if k not in conditions]
    if missing:
        return {"error": "missing_required_inputs", "missing": missing,
                "required": list(engine_pred.REQUIRED_INPUTS)}
    return engine_pred.predict_outcome(conditions)


@app.get("/evidence/{test_no}")
def evidence_detail(test_no: str):
    try:
        return engine.experiment_detail(test_no)
    except KeyError as exc:
        return {"error": str(exc)}