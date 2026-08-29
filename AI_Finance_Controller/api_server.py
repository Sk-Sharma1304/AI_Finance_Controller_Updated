"""
AI Finance Controller — API layer
===================================

Run with:

    uvicorn api_server:app --port 8000

Endpoints:
    GET  /api/health          -> service + model status
    GET  /api/results         -> demo-dataset pipeline output (cached)
    POST /api/rerun           -> forces the demo pipeline to re-run
    POST /api/upload          -> upload your own payments CSV and score it
                                  (sync for small files, async job for large ones)
    GET  /api/upload/{id}     -> fetch a scored upload's results
    GET  /api/jobs/{id}       -> poll an async upload's status
    GET  /api/audit/{id}      -> the audit-log trail for an upload

Auth: if API_KEYS is set (see auth.py), every /api/upload* and
/api/rerun call requires an `X-API-Key` header. /api/results and
/api/health stay open so the bundled demo works out of the box.
"""

from __future__ import annotations

import io
import logging
import math
import os
import time
import uuid
from typing import Any

import pandas as pd
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from logging_config import configure_logging
from auth import auth_enabled, get_actor
from rate_limit import RateLimitExceeded, check_and_consume_llm_budget, check_upload_rate_limit
from data_loader import DataValidationError, load_from_path, prepare_dataframe
from orchestrator.finance_orchestrator import run_pipeline
import db

configure_logging()
logger = logging.getLogger("api_server")

if not auth_enabled():
    logger.warning(
        "API_KEYS is not set -- auth is DISABLED. Every request is "
        "attributed to actor 'anonymous'. Set API_KEYS before "
        "deploying this anywhere reachable by untrusted clients."
    )

db.init_db()

TRANSACTIONS_FILE = "data/finance_controller_dataset.csv"
GROUND_TRUTH_FILE = "data/ground_truth.csv"
OUTPUT_DIR = "outputs"

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
# Files with more rows than this are scored in a background task and
# the endpoint returns immediately with a job id to poll, instead of
# holding the HTTP connection open for the whole pipeline run.
ASYNC_ROW_THRESHOLD = int(os.environ.get("ASYNC_ROW_THRESHOLD", "2000"))

app = FastAPI(title="AI Finance Controller API", version="1.2")

_origins = os.environ.get(
    "FRONTEND_ORIGIN", "http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    logger.info(
        "request handled",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round((time.time() - start) * 1000, 1),
        },
    )
    return response


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": exc.message},
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


_cache: dict[str, Any] = {}


def _clean(value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _row_to_json(row: "pd.Series") -> dict:
    record = {k: _clean(v) for k, v in row.to_dict().items()}
    record["duplicate_flag"] = bool(record.get("duplicate_flag", False))
    record["ml_anomaly"] = int(record.get("ml_anomaly", 1))
    evidence = record.get("evidence") or ""
    record["evidence"] = [
        e.strip() for e in str(evidence).split("|") if e.strip()
    ]
    return record


def _summarize(records: list[dict]) -> dict:
    decision_counts = {
        "NORMAL": 0,
        "FINANCIAL_EXCEPTION": 0,
        "ML_REVIEW": 0,
        "AI_ESCALATED_REVIEW": 0,
        "CONFIRMED_HIGH_PRIORITY": 0,
    }
    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    action_counts: dict[str, int] = {}

    total_impact = 0.0
    at_risk_impact = 0.0
    ml_anomalies = 0
    duplicates = 0
    llm_evaluated = 0

    for r in records:
        decision_counts[r["final_decision"]] = (
            decision_counts.get(r["final_decision"], 0) + 1
        )
        risk_counts[r["risk_level"]] = risk_counts.get(r["risk_level"], 0) + 1
        action_counts[r["recommended_action"]] = (
            action_counts.get(r["recommended_action"], 0) + 1
        )

        impact = r.get("financial_impact") or 0
        total_impact += impact
        if r["final_decision"] != "NORMAL":
            at_risk_impact += impact
        if r["ml_anomaly"] == -1:
            ml_anomalies += 1
        if r["duplicate_flag"]:
            duplicates += 1
        if r.get("llm_risk_opinion") != "NOT_EVALUATED":
            llm_evaluated += 1

    total = len(records)
    auto_cleared = decision_counts["NORMAL"]

    return {
        "total": total,
        "autoCleared": auto_cleared,
        "autoClearedPct": (auto_cleared / total * 100) if total else 0,
        "flagged": total - auto_cleared,
        "aiEscalated": decision_counts["AI_ESCALATED_REVIEW"],
        "confirmedHighPriority": decision_counts["CONFIRMED_HIGH_PRIORITY"],
        "mlAnomalies": ml_anomalies,
        "duplicates": duplicates,
        "totalImpact": total_impact,
        "atRiskImpact": at_risk_impact,
        "decisionCounts": decision_counts,
        "riskCounts": risk_counts,
        "actionCounts": action_counts,
        "llmEvaluated": llm_evaluated,
    }


def _to_payload(df: pd.DataFrame, source: str, filename: str | None = None) -> dict:
    records = [_row_to_json(row) for _, row in df.iterrows()]
    return {
        "transactions": records,
        "summary": _summarize(records),
        "generatedAt": time.time(),
        "llmEnabled": bool(os.environ.get("OPENAI_API_KEY")),
        "source": source,
        "filename": filename,
    }


def _build_demo_payload(persist: bool = True) -> dict:
    df = load_from_path(TRANSACTIONS_FILE, GROUND_TRUTH_FILE)
    df = run_pipeline(df)

    if persist:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        df.to_csv(os.path.join(OUTPUT_DIR, "action_results.csv"), index=False)

    payload = _to_payload(df, source="demo")
    _cache["data"] = payload
    return payload


def _score_and_persist(upload_id: str, raw_bytes: bytes, filename: str, actor: str) -> None:
    """Runs the pipeline and writes results + audit log. Shared by
    the synchronous and background-task code paths so both persist
    identically."""

    session = db.SessionLocal()
    try:
        raw_df = pd.read_csv(io.BytesIO(raw_bytes))
        df = prepare_dataframe(raw_df)

        row_count = len(df)
        llm_max_calls = None
        if not check_and_consume_llm_budget(actor, row_count):
            llm_max_calls = 0
            logger.warning(
                "daily LLM budget exhausted, degrading to rule-based only",
                extra={"actor": actor, "upload_id": upload_id},
            )

        result = run_pipeline(df, llm_max_calls=llm_max_calls)

        records = [_row_to_json(row) for _, row in result.iterrows()]
        summary = _summarize(records)
        model_version = str(result.get("anomaly_model_version", pd.Series(["unknown"])).iloc[0])

        db.mark_upload_done(session, upload_id, row_count, model_version, summary, records)
        db.write_audit_log(session, upload_id, records, model_version, actor)

        logger.info(
            "upload scored",
            extra={
                "upload_id": upload_id,
                "uploaded_filename": filename,
                "rows": row_count,
                "model_version": model_version,
                "actor": actor,
            },
        )
    except DataValidationError as exc:
        db.mark_upload_failed(session, upload_id, "; ".join(exc.errors))
        logger.warning("upload validation failed", extra={"upload_id": upload_id, "errors": exc.errors})
    except Exception as exc:  # noqa: BLE001 - persist failure, don't crash the worker
        db.mark_upload_failed(session, upload_id, str(exc))
        logger.exception("upload scoring failed", extra={"upload_id": upload_id})
    finally:
        session.close()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "auth_enabled": auth_enabled(),
        "llm_enabled": bool(os.environ.get("OPENAI_API_KEY")),
        "cached": "data" in _cache,
        "database": db.DATABASE_URL.split("://")[0],
    }


@app.get("/api/results")
def results(refresh: bool = False):
    """Returns the pipeline output for the bundled demo dataset.
    Cached after first run; pass ?refresh=true (or hit /api/rerun)
    to force a fresh run.
    """
    if refresh or "data" not in _cache:
        return _build_demo_payload()
    return _cache["data"]


@app.post("/api/rerun")
def rerun(actor: str = Depends(get_actor)):
    """Forces the demo pipeline to run again."""
    return _build_demo_payload()


@app.post("/api/upload")
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    actor: str = Depends(get_actor),
):
    """
    Accepts a user's own payments CSV and runs the full pipeline
    over it -- no scenario labels or ground-truth file required.

    Required columns: payment_id, payment_amount, actual_settlement
    Optional columns (default to 0 if absent): fee, tax, refund,
    adjustment. expected_settlement is computed automatically as
        payment_amount - fee - tax - refund + adjustment
    Optional columns that improve duplicate detection if present:
    merchant_id, transaction_date.

    Small files (<= ASYNC_ROW_THRESHOLD rows) are scored
    synchronously and returned immediately. Larger files are handed
    to a background task; the response has status "PROCESSING" and
    an id to poll at GET /api/jobs/{id}.
    """

    check_upload_rate_limit(actor)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    contents = await file.read()

    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File is {len(contents) / 1_000_000:.1f} MB, which "
                f"exceeds the {MAX_UPLOAD_BYTES / 1_000_000:.0f} MB limit."
            ),
        )

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        raw_df = pd.read_csv(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse the file as CSV: {exc}")

    try:
        validated = prepare_dataframe(raw_df)
    except DataValidationError as exc:
        raise HTTPException(status_code=422, detail={"errors": exc.errors})

    session = db.SessionLocal()
    try:
        record = db.create_upload(session, file.filename, actor)
        upload_id = record.id
    finally:
        session.close()

    if len(validated) > ASYNC_ROW_THRESHOLD:
        background_tasks.add_task(_score_and_persist, upload_id, contents, file.filename, actor)
        return {
            "uploadId": upload_id,
            "status": "PROCESSING",
            "message": (
                f"{len(validated)} rows exceeds the synchronous threshold "
                f"({ASYNC_ROW_THRESHOLD}); scoring in the background. "
                f"Poll GET /api/jobs/{upload_id}."
            ),
        }

    _score_and_persist(upload_id, contents, file.filename, actor)

    session = db.SessionLocal()
    try:
        record = db.get_upload(session, upload_id)
        if not record or record.status != "DONE":
            raise HTTPException(
                status_code=500,
                detail=(record.error if record else "Scoring failed unexpectedly."),
            )
        import json as _json

        return {
            "uploadId": upload_id,
            "status": "DONE",
            "transactions": _json.loads(record.transactions_json),
            "summary": _json.loads(record.summary_json),
            "generatedAt": time.time(),
            "llmEnabled": bool(os.environ.get("OPENAI_API_KEY")),
            "source": "upload",
            "filename": record.filename,
            "modelVersion": record.model_version,
        }
    finally:
        session.close()


@app.get("/api/jobs/{upload_id}")
def get_job(upload_id: str):
    session = db.SessionLocal()
    try:
        record = db.get_upload(session, upload_id)
        if not record:
            raise HTTPException(status_code=404, detail="Job not found.")
        return {
            "uploadId": record.id,
            "status": record.status,
            "filename": record.filename,
            "rowCount": record.row_count,
            "error": record.error,
        }
    finally:
        session.close()


@app.get("/api/upload/{upload_id}")
def get_upload(upload_id: str):
    session = db.SessionLocal()
    try:
        record = db.get_upload(session, upload_id)
        if not record:
            raise HTTPException(status_code=404, detail="Upload not found.")
        if record.status != "DONE":
            return {"uploadId": record.id, "status": record.status, "error": record.error}

        import json as _json

        return {
            "uploadId": upload_id,
            "status": "DONE",
            "transactions": _json.loads(record.transactions_json),
            "summary": _json.loads(record.summary_json),
            "generatedAt": time.time(),
            "llmEnabled": bool(os.environ.get("OPENAI_API_KEY")),
            "source": "upload",
            "filename": record.filename,
            "modelVersion": record.model_version,
        }
    finally:
        session.close()


@app.get("/api/audit/{upload_id}")
def get_audit(upload_id: str):
    """Returns the append-only audit trail for a scored upload --
    who/what scored it, with which model version, and what each
    transaction's decision was."""
    session = db.SessionLocal()
    try:
        entries = db.get_audit_log_for_upload(session, upload_id)
        return {
            "uploadId": upload_id,
            "entries": [
                {
                    "paymentId": e.payment_id,
                    "riskScore": e.risk_score,
                    "riskLevel": e.risk_level,
                    "finalDecision": e.final_decision,
                    "recommendedAction": e.recommended_action,
                    "financialImpact": e.financial_impact,
                    "modelVersion": e.model_version,
                    "actor": e.actor,
                    "createdAt": e.created_at.isoformat() if e.created_at else None,
                }
                for e in entries
            ],
        }
    finally:
        session.close()


@app.get("/")
def root():
    return {
        "service": "AI Finance Controller API",
        "endpoints": [
            "/api/health",
            "/api/results",
            "/api/rerun",
            "/api/upload (POST, multipart/form-data, field name 'file')",
            "/api/upload/{uploadId}",
            "/api/jobs/{uploadId}",
            "/api/audit/{uploadId}",
        ],
    }
