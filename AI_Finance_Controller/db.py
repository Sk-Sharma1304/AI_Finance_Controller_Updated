"""
Persistence layer
====================

Two tables:

  - ``uploads``    — one row per uploaded file: who, when, status,
                      summary, which model version scored it, and
                      the full scored transaction list (as JSON).
                      This replaces the in-memory ``_uploads`` dict
                      from the first pass, so results survive a
                      restart and work across multiple server
                      processes.

                      NOTE: storing the full transaction list as a
                      JSON blob in a DB column is a demo-scale
                      choice -- fine up to a few thousand rows. At
                      real volume, move the scored rows to object
                      storage (S3/GCS) and keep only a pointer +
                      the summary here.

  - ``audit_log``   — one row per transaction decision. Append-only
                      by convention (nothing in this module ever
                      updates or deletes a row). This is what makes
                      a HOLD_SETTLEMENT / BLOCK_DUPLICATE
                      recommendation auditable after the fact: who
                      / what scored it, when, with what model
                      version, and what the decision was.

Uses SQLAlchemy so the same code works against SQLite (default --
fine for small deployments / local dev) or Postgres (set
DATABASE_URL=postgresql://... in production). SQLite is genuinely
not a good fit for concurrent multi-process production traffic --
switch DATABASE_URL before deploying with more than one worker.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "sqlite:///./finance_controller.db"
)

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


class UploadRecord(Base):
    __tablename__ = "uploads"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    uploaded_by = Column(String, nullable=True)  # API key / user id, if auth is enabled
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="PENDING")  # PENDING | PROCESSING | DONE | FAILED
    row_count = Column(Integer, nullable=True)
    model_version = Column(String, nullable=True)
    summary_json = Column(Text, nullable=True)  # PipelineSummary, serialized
    transactions_json = Column(Text, nullable=True)  # scored rows, serialized
    error = Column(Text, nullable=True)


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    upload_id = Column(String, nullable=False, index=True)
    payment_id = Column(String, nullable=False, index=True)
    risk_score = Column(Float, nullable=True)
    risk_level = Column(String, nullable=True)
    final_decision = Column(String, nullable=True)
    recommended_action = Column(String, nullable=True)
    financial_impact = Column(Float, nullable=True)
    model_version = Column(String, nullable=True)
    actor = Column(String, nullable=True)  # who/what triggered the scoring run
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def create_upload(session, filename: str, uploaded_by: str | None) -> UploadRecord:
    record = UploadRecord(filename=filename, uploaded_by=uploaded_by, status="PROCESSING")
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def mark_upload_done(
    session, upload_id: str, row_count: int, model_version: str,
    summary: dict, transactions: list[dict],
) -> None:
    record = session.get(UploadRecord, upload_id)
    if not record:
        return
    record.status = "DONE"
    record.row_count = row_count
    record.model_version = model_version
    record.summary_json = json.dumps(summary)
    record.transactions_json = json.dumps(transactions)
    session.commit()


def mark_upload_failed(session, upload_id: str, error: str) -> None:
    record = session.get(UploadRecord, upload_id)
    if not record:
        return
    record.status = "FAILED"
    record.error = error
    session.commit()


def write_audit_log(session, upload_id: str, records: list[dict], model_version: str, actor: str | None) -> None:
    """Bulk-inserts one audit row per scored transaction. Append-only:
    this function never updates an existing row, even if the same
    upload_id is written twice (shouldn't happen, but if it does,
    both runs stay in the trail rather than one silently overwriting
    the other)."""

    entries = [
        AuditLogEntry(
            upload_id=upload_id,
            payment_id=str(r.get("payment_id")),
            risk_score=r.get("risk_score"),
            risk_level=r.get("risk_level"),
            final_decision=r.get("final_decision"),
            recommended_action=r.get("recommended_action"),
            financial_impact=r.get("financial_impact"),
            model_version=model_version,
            actor=actor,
        )
        for r in records
    ]
    session.bulk_save_objects(entries)
    session.commit()


def get_upload(session, upload_id: str) -> UploadRecord | None:
    return session.get(UploadRecord, upload_id)


def get_audit_log_for_upload(session, upload_id: str) -> list[AuditLogEntry]:
    return (
        session.query(AuditLogEntry)
        .filter(AuditLogEntry.upload_id == upload_id)
        .order_by(AuditLogEntry.created_at)
        .all()
    )
