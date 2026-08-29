import os
import sys

import pandas as pd

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from data_loader import load_from_path

from agents.reconciliation_agent import (
    run_reconciliation_agent
)

from agents.duplicates_detection_agent import (
    run_duplicate_agent
)

from agents.anomaly_agent import (
    run_anomaly_agent
)

from agents.risk_agent import (
    run_risk_agent
)

from agents.investigation_agent import (
    run_investigation_agent
)

from agents.llm_investigation_agent import (
    run_llm_investigation_agent
)

from agents.decision_agent import (
    run_decision_agent
)

from agents.action_agent import (
    run_action_agent
)


TRANSACTIONS_FILE = "data/finance_controller_dataset.csv"
GROUND_TRUTH_FILE = "data/ground_truth.csv"

OUTPUT_DIR = "outputs"

RECONCILIATION_OUTPUT = (
    "outputs/reconciliation_results.csv"
)

DUPLICATE_OUTPUT = (
    "outputs/duplicate_results.csv"
)

ANOMALY_OUTPUT = (
    "outputs/anomaly_results.csv"
)

RISK_OUTPUT = (
    "outputs/risk_results.csv"
)

INVESTIGATION_OUTPUT = (
    "outputs/investigation_results.csv"
)

DECISION_OUTPUT = (
    "outputs/final_decisions.csv"
)

LLM_INVESTIGATION_OUTPUT = (
    "outputs/llm_investigation_results.csv"
)

ACTION_OUTPUT = (
    "outputs/action_results.csv"
)


def print_header(title):

    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def load_data():
    """
    Load the bundled demo transaction feed for the CLI / smoke
    test run. ``scenario`` is merged in from ``ground_truth.csv``
    purely for display in this script's printouts -- no agent
    reads it. ``expected_settlement`` is computed directly from
    the raw payment fields by ``data_loader``, not looked up.

    For a real uploaded CSV, use ``run_pipeline(data_loader.
    prepare_dataframe(df))`` directly -- see api_server.py.
    """

    return load_from_path(
        TRANSACTIONS_FILE,
        GROUND_TRUTH_FILE
    )


def run_pipeline(df, llm_max_calls=None):
    """
    Runs the full 8-agent pipeline over an already-validated
    DataFrame (i.e. one that has been through
    ``data_loader.prepare_dataframe``) and returns the final,
    fully-annotated result. This is the single entry point shared
    by the CLI (``main`` below) and the API's ``/api/upload``
    endpoint, so both paths score transactions identically.

    ``llm_max_calls`` overrides the per-run LLM call cap (see
    agents/llm_investigation_agent.py) -- api_server.py passes 0
    here when an actor has exhausted their daily LLM budget
    (rate_limit.py), so the pipeline degrades to rule-based
    investigation only instead of failing the request.
    """

    result = run_reconciliation_agent(df)
    result = run_duplicate_agent(result)
    result = run_anomaly_agent(result)
    result = run_risk_agent(result)
    result = run_investigation_agent(result)
    result = run_llm_investigation_agent(result, max_calls=llm_max_calls)
    result = run_decision_agent(result)
    result = run_action_agent(result)

    return result


def main():

    print_header(
        "AI FINANCE CONTROLLER"
    )

    print(
        "Starting multi-agent financial control pipeline..."
    )

    # =========================================================
    # Make sure the outputs folder exists
    # =========================================================

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    # =========================================================
    # Load data
    # =========================================================

    df = load_data()

    print(
        f"\nLoaded {len(df)} transactions."
    )

    # =========================================================
    # 1. RECONCILIATION AGENT
    # =========================================================

    print_header(
        "1. RECONCILIATION AGENT"
    )

    reconciliation_result = (
        run_reconciliation_agent(df.copy())
    )

    reconciliation_result.to_csv(
        RECONCILIATION_OUTPUT,
        index=False
    )

    print(
        "Reconciliation completed."
    )

    # =========================================================
    # 2. DUPLICATE AGENT
    # =========================================================

    print_header(
        "2. DUPLICATE DETECTION AGENT"
    )

    duplicate_result = (
        run_duplicate_agent(
            reconciliation_result
        )
    )

    duplicate_result.to_csv(
        DUPLICATE_OUTPUT,
        index=False
    )

    print(
        "Duplicate detection completed."
    )

    # =========================================================
    # 3. ANOMALY AGENT
    # =========================================================

    print_header(
        "3. ANOMALY DETECTION AGENT"
    )

    anomaly_result = (
        run_anomaly_agent(
            duplicate_result
        )
    )

    anomaly_result.to_csv(
        ANOMALY_OUTPUT,
        index=False
    )

    print(
        "Anomaly detection completed."
    )

    # =========================================================
    # 4. RISK ASSESSMENT AGENT
    # =========================================================

    print_header(
        "4. RISK ASSESSMENT AGENT"
    )

    risk_result = (
        run_risk_agent(
            anomaly_result
        )
    )

    risk_result.to_csv(
        RISK_OUTPUT,
        index=False
    )

    print(
        "Risk assessment completed."
    )

    # =========================================================
    # 5. INVESTIGATION AGENT
    # =========================================================

    print_header(
        "5. INVESTIGATION AGENT"
    )

    investigation_result = (
        run_investigation_agent(
            risk_result
        )
    )

    investigation_result.to_csv(
        INVESTIGATION_OUTPUT,
        index=False
    )

    print(
        "Investigation completed."
    )

    # =========================================================
    # 5.5 LLM INVESTIGATION AGENT (OpenAI)
    # =========================================================

    print_header(
        "5.5. LLM INVESTIGATION AGENT"
    )

    llm_result = (
        run_llm_investigation_agent(
            investigation_result
        )
    )

    llm_result.to_csv(
        LLM_INVESTIGATION_OUTPUT,
        index=False
    )

    print(
        "LLM enrichment completed."
    )

    # =========================================================
    # 6. DECISION AGENT
    # =========================================================

    print_header(
        "6. DECISION AGENT"
    )

    decision_result = (
        run_decision_agent(
            llm_result
        )
    )

    decision_result.to_csv(
        DECISION_OUTPUT,
        index=False
    )

    print(
        "Final decisions generated."
    )

    # =========================================================
    # 7. ACTION AGENT
    # =========================================================

    print_header(
        "7. ACTION AGENT"
    )

    action_result = (
        run_action_agent(
            decision_result
        )
    )

    action_result.to_csv(
        ACTION_OUTPUT,
        index=False
    )

    print(
        "Recommended actions generated."
    )

    # =========================================================
    # FINAL SUMMARY
    # =========================================================

    print_header(
        "FINAL FINANCIAL CONTROLLER SUMMARY"
    )

    print(
        f"Total transactions : {len(action_result)}"
    )

    if "final_decision" in action_result.columns:

        print(
            "\nDecision distribution:"
        )

        print(
            action_result[
                "final_decision"
            ].value_counts()
        )

    if "risk_level" in action_result.columns:

        print(
            "\nRisk distribution:"
        )

        print(
            action_result[
                "risk_level"
            ].value_counts()
        )

    if "recommended_action" in action_result.columns:

        print(
            "\nRecommended actions:"
        )

        print(
            action_result[
                "recommended_action"
            ].value_counts()
        )

    # =========================================================
    # HIGH PRIORITY TRANSACTIONS
    # =========================================================

    if "final_decision" in action_result.columns:

        high_priority = action_result[
            action_result["final_decision"]
            == "CONFIRMED_HIGH_PRIORITY"
        ]

        print_header(
            "HIGH PRIORITY TRANSACTIONS"
        )

        columns = [
            "payment_id",
            "scenario",
            "risk_level",
            "risk_score",
            "financial_impact",
            "investigation_summary",
            "recommended_action"
        ]

        available_columns = [
            column
            for column in columns
            if column in high_priority.columns
        ]

        if len(high_priority) > 0:

            print(
                high_priority[
                    available_columns
                ].to_string(index=False)
            )

        else:

            print(
                "No high priority transactions."
            )

    print_header(
        "PIPELINE COMPLETED SUCCESSFULLY"
    )


if __name__ == "__main__":
    main()