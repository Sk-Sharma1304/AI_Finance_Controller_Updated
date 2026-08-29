"""
Data Loader / Validator
========================

This is what makes the pipeline work on a CSV a user actually
uploads, instead of only the bundled demo dataset.

Two things used to make that impossible:

1. ``expected_settlement`` used to come from a separate
   ``ground_truth.csv`` "answer key" file that only exists for the
   synthetic demo data. It turns out that value is not actually
   independent information -- it's a deterministic function of the
   other columns already on every payment:

       expected_settlement = payment_amount - fee - tax - refund + adjustment

   Verified against all 100 rows of the bundled dataset (8/8
   scenario types, 100% match). So we compute it instead of
   requiring a lookup file.

2. Every scoring agent downstream (risk, investigation, decision,
   action) used to branch on a ``scenario`` column that only the
   synthetic dataset has (it's literally the injected-fraud-type
   label). That's the part that made "upload your own CSV" a
   contradiction -- a real settlement file was never going to have
   an answer key column. That logic has been rewritten (see
   ``agents/risk_agent.py`` etc.) to work off signals that are
   always computable: reconciliation severity, duplicate detection,
   the ML anomaly flag, and financial impact.

This module owns schema validation + column normalization so every
entry point (CLI, API upload, orchestrator) goes through the same
checks instead of each reimplementing them slightly differently.
"""

from __future__ import annotations

import pandas as pd

# Columns a payments CSV must have. Everything else is optional /
# defaulted, so a plain gateway settlement export should "just work".
REQUIRED_COLUMNS = ["payment_id", "payment_amount", "actual_settlement"]

# Optional numeric columns that default to 0 when absent, since a
# lot of real settlement exports simply omit refund/adjustment
# columns when there weren't any that day.
OPTIONAL_NUMERIC_COLUMNS = ["fee", "tax", "refund", "adjustment"]

MAX_ROWS = 50_000  # sane upper bound for a synchronous request; see roadmap


class DataValidationError(ValueError):
    """Raised when an uploaded CSV can't be safely scored.

    Carries a list of human-readable problems so the API can return
    all of them at once instead of one-error-per-request-cycle.
    """

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_formula_injection(df: pd.DataFrame) -> pd.DataFrame:
    """Neutralizes CSV/spreadsheet formula injection.

    If a cell like ``=cmd(...)`` or ``@SUM(...)`` from an uploaded
    file is later exported to CSV/XLSX and opened in Excel/Sheets by
    someone on the finance team, it can execute as a formula. This
    prefixes any string cell that starts with a formula-triggering
    character with a single quote, which spreadsheet applications
    render as literal text instead of evaluating.
    """

    df = df.copy()
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].apply(
            lambda v: ("'" + v) if isinstance(v, str) and v.startswith(DANGEROUS_PREFIXES) else v
        )
    return df


def validate_columns(df: pd.DataFrame) -> list[str]:
    """Returns a list of blocking problems (empty list = OK)."""

    errors: list[str] = []

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        errors.append(
            "Missing required column(s): "
            + ", ".join(missing)
            + f". A payments CSV must include: {', '.join(REQUIRED_COLUMNS)}."
        )

    if len(df) == 0:
        errors.append("The file has no data rows.")

    if len(df) > MAX_ROWS:
        errors.append(
            f"File has {len(df)} rows, which exceeds the {MAX_ROWS}-row "
            "limit for a single synchronous run. Split the file or use "
            "the batch/async endpoint (see production roadmap)."
        )

    if "payment_id" in df.columns and df["payment_id"].duplicated().any():
        dupe_count = int(df["payment_id"].duplicated().sum())
        errors.append(
            f"{dupe_count} duplicate payment_id value(s) found. "
            "payment_id must be unique per row -- if two rows share an "
            "id they can't be told apart downstream."
        )

    return errors


def _coerce_numeric(df: pd.DataFrame, column: str, errors: list[str]) -> None:
    if column not in df.columns:
        return
    coerced = pd.to_numeric(df[column], errors="coerce")
    bad_rows = int(coerced.isna().sum() - df[column].isna().sum())
    if bad_rows > 0:
        errors.append(
            f"Column '{column}' has {bad_rows} value(s) that aren't "
            "numeric and couldn't be parsed."
        )
    df[column] = coerced


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Validates and normalizes a raw uploaded/loaded transactions
    DataFrame into the shape every agent expects.

    Raises ``DataValidationError`` if the file can't be safely
    scored. Does NOT require a scenario or ground-truth column --
    if one is present (e.g. the bundled demo dataset) it's carried
    through for transparency/display only, never used for scoring.
    """

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = _sanitize_formula_injection(df)

    errors = validate_columns(df)
    if errors:
        raise DataValidationError(errors)

    numeric_errors: list[str] = []
    for col in ["payment_amount", "actual_settlement"] + OPTIONAL_NUMERIC_COLUMNS:
        _coerce_numeric(df, col, numeric_errors)
    if numeric_errors:
        raise DataValidationError(numeric_errors)

    for col in OPTIONAL_NUMERIC_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = df[col].fillna(0.0)

    if df["payment_amount"].isna().any() or (df["payment_amount"] <= 0).any():
        bad = int((df["payment_amount"].isna() | (df["payment_amount"] <= 0)).sum())
        raise DataValidationError(
            [f"{bad} row(s) have a missing or non-positive payment_amount."]
        )

    df["amount"] = df["payment_amount"]

    # --- the key change: compute expected_settlement instead of
    # requiring a separate ground-truth/answer-key file ---
    if "expected_settlement" not in df.columns:
        df["expected_settlement"] = (
            df["payment_amount"]
            - df["fee"]
            - df["tax"]
            - df["refund"]
            + df["adjustment"]
        )

    # actual_settlement may legitimately be missing (that's exactly
    # what "missing settlement" means) -- keep NaN, don't coerce to 0.

    return df


def load_from_path(transactions_path: str, ground_truth_path: str | None = None) -> pd.DataFrame:
    """Back-compat loader for the CLI / demo dataset. If a
    ground-truth file is supplied (only true for the bundled demo
    data) its `scenario` column is merged in for display/eval
    purposes only -- it is never read by any scoring agent."""

    transactions = pd.read_csv(transactions_path)

    if ground_truth_path:
        try:
            ground_truth = pd.read_csv(ground_truth_path)
            merge_cols = [
                c for c in ["payment_id", "scenario"] if c in ground_truth.columns
            ]
            transactions = transactions.merge(
                ground_truth[merge_cols], on="payment_id", how="left"
            )
        except FileNotFoundError:
            pass

    return prepare_dataframe(transactions)
