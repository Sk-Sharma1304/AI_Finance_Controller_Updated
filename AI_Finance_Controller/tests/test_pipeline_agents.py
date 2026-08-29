"""
These tests are the regression guard for the core fix: the pipeline
must produce sensible, non-trivial risk/decision output on a plain
uploaded CSV that has NEVER seen a `scenario` column. Every fixture
here (`demo_dataframe`, `minimal_valid_df`) is deliberately built
without one.
"""

import pandas as pd

from agents.action_agent import run_action_agent
from agents.anomaly_agent import run_anomaly_agent
from agents.decision_agent import run_decision_agent
from agents.duplicates_detection_agent import run_duplicate_agent
from agents.investigation_agent import run_investigation_agent
from agents.reconciliation_agent import run_reconciliation_agent
from agents.risk_agent import run_risk_agent


def _run_up_to_risk(df):
    df = run_reconciliation_agent(df)
    df = run_duplicate_agent(df)
    df = run_anomaly_agent(df)
    df = run_risk_agent(df)
    return df


def test_no_scenario_column_anywhere_in_inputs(demo_dataframe, minimal_valid_df):
    assert "scenario" not in demo_dataframe.columns
    assert "scenario" not in minimal_valid_df.columns


def test_risk_scoring_produces_full_spread(demo_dataframe):
    """On the demo data (which has known injected exceptions), a
    healthy scoring engine should produce more than one risk level
    -- if everything comes back LOW, the signals aren't reaching the
    scorer."""
    result = _run_up_to_risk(demo_dataframe)
    levels = set(result["risk_level"].unique())
    assert levels.issuperset({"LOW"})
    assert len(levels) >= 3  # LOW plus at least two of MEDIUM/HIGH/CRITICAL
    assert result["risk_score"].between(0, 100).all()


def test_reconciled_transaction_is_low_risk(minimal_valid_df):
    """A transaction whose actual settlement exactly matches the
    computed expected settlement should score as clean."""
    result = _run_up_to_risk(minimal_valid_df.iloc[[1]].copy())  # p2: 500 == 500
    assert result.iloc[0]["reconciliation_status"] == "RECONCILED"
    assert result.iloc[0]["risk_level"] == "LOW"


def test_missing_settlement_is_flagged_high_risk():
    from data_loader import prepare_dataframe

    df = prepare_dataframe(pd.DataFrame({
        "payment_id": ["p1"],
        "payment_amount": [1000.0],
        "actual_settlement": [None],
    }))
    result = _run_up_to_risk(df)
    assert result.iloc[0]["reconciliation_status"] == "MISSING_SETTLEMENT"
    assert result.iloc[0]["risk_level"] in ("HIGH", "CRITICAL")


def test_large_discrepancy_outranks_small_discrepancy():
    from data_loader import prepare_dataframe

    df = prepare_dataframe(pd.DataFrame({
        "payment_id": ["small_gap", "big_gap"],
        "payment_amount": [1000.0, 1000.0],
        "actual_settlement": [990.0, 400.0],  # 1% off vs 60% off
    }))
    result = _run_up_to_risk(df)
    small = result[result["payment_id"] == "small_gap"].iloc[0]
    big = result[result["payment_id"] == "big_gap"].iloc[0]
    assert big["risk_score"] > small["risk_score"]


def test_decision_agent_flags_exceptions_without_scenario(demo_dataframe):
    df = _run_up_to_risk(demo_dataframe)
    df = run_investigation_agent(df)
    df["llm_risk_opinion"] = "NOT_EVALUATED"
    df["llm_confidence"] = None
    df["llm_reasoning"] = ""
    df = run_decision_agent(df)

    assert set(df["final_decision"].unique()) - {"NORMAL"}
    # Every non-RECONCILED / duplicate row must NOT be silently
    # marked NORMAL -- that would mean the exception detection
    # regressed back to depending on a label we don't have.
    has_issue = (df["reconciliation_status"] != "RECONCILED") | (df["duplicate_flag"])
    assert (df.loc[has_issue, "final_decision"] != "NORMAL").all()


def test_action_agent_recommends_hold_for_missing_settlement():
    from data_loader import prepare_dataframe

    df = prepare_dataframe(pd.DataFrame({
        "payment_id": ["p1"],
        "payment_amount": [5000.0],
        "actual_settlement": [None],
    }))
    df = _run_up_to_risk(df)
    df = run_investigation_agent(df)
    df["llm_risk_opinion"] = "NOT_EVALUATED"
    df["llm_confidence"] = None
    df["llm_reasoning"] = ""
    df = run_decision_agent(df)
    df = run_action_agent(df)

    row = df.iloc[0]
    assert row["final_decision"] in ("CONFIRMED_HIGH_PRIORITY", "FINANCIAL_EXCEPTION")
    assert row["recommended_action"] != "NO_ACTION"
