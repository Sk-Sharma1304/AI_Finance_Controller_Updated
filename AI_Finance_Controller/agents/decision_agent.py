import pandas as pd


class DecisionAgent:

    def make_decisions(self, data):

        result = data.copy()

        # --------------------------------------------------
        # Default decision
        # --------------------------------------------------

        result["final_decision"] = "NORMAL"

        # --------------------------------------------------
        # High / Critical financial risk
        # --------------------------------------------------

        high_risk = result["risk_level"].isin(
            ["HIGH", "CRITICAL"]
        )

        # --------------------------------------------------
        # Financial exception + ML anomaly
        # --------------------------------------------------

        confirmed = (
            high_risk &
            (result["ml_anomaly"] == -1)
        )

        result.loc[
            confirmed,
            "final_decision"
        ] = "CONFIRMED_HIGH_PRIORITY"

        # --------------------------------------------------
        # Financial exception without ML confirmation
        #
        # NOTE: this used to check `scenario != "normal"`, a
        # column that only exists in the synthetic demo dataset
        # (the injected fraud-type answer key). It's replaced
        # with the actual computed reconciliation outcome: a
        # real discrepancy/missing settlement, or a confirmed
        # duplicate, is what makes something an exception --
        # not a label a real upload will never have.
        # --------------------------------------------------

        has_reconciliation_issue = (
            result["reconciliation_status"] != "RECONCILED"
        )

        has_duplicate_issue = result.get(
            "duplicate_flag", False
        ) == True  # noqa: E712 (works for both bool Series and scalar default)

        financial_review = (
            (has_reconciliation_issue | has_duplicate_issue) &
            ~confirmed
        )

        result.loc[
            financial_review,
            "final_decision"
        ] = "FINANCIAL_EXCEPTION"

        # --------------------------------------------------
        # ML anomaly without financial exception
        # --------------------------------------------------

        ml_review = (
            ~has_reconciliation_issue &
            ~has_duplicate_issue &
            (result["ml_anomaly"] == -1)
        )

        result.loc[
            ml_review,
            "final_decision"
        ] = "ML_REVIEW"

        # --------------------------------------------------
        # LLM escalation (optional layer)
        # --------------------------------------------------
        #
        # If the LLM Investigation Agent ran (see
        # agents/llm_investigation_agent.py) and it disagrees,
        # with high confidence, with a transaction the rules
        # marked NORMAL, escalate it instead of silently
        # trusting the rules. This is what lets the LLM step
        # actually change an outcome rather than just narrate
        # one the rules already decided.
        #
        # Backward compatible: if the LLM columns aren't
        # present (no API key / LLM agent skipped), this block
        # is a no-op and behaviour is identical to before.

        if "llm_risk_opinion" in result.columns:

            was_normal = result["final_decision"] == "NORMAL"

            llm_disagrees = (
                result["llm_risk_opinion"].isin(
                    ["HIGH", "CRITICAL"]
                )
                & (result["llm_confidence"] >= 0.7)
            )

            ai_escalated = was_normal & llm_disagrees

            result.loc[
                ai_escalated,
                "final_decision"
            ] = "AI_ESCALATED_REVIEW"

        return result


def run_decision_agent(df):

    agent = DecisionAgent()

    return agent.make_decisions(df)


def main():

    # --------------------------------------------------
    # Standalone smoke test.
    #
    # This rebuilds the same pipeline that the
    # orchestrator runs (reconciliation -> duplicates ->
    # anomaly -> risk -> decision) so this file can be
    # exercised on its own with:
    #
    #   python agents/decision_agent.py
    # --------------------------------------------------

    import os
    import sys

    sys.path.insert(
        0,
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
    )

    from agents.reconciliation_agent import (
        run_reconciliation_agent
    )
    from agents.duplicates_detection_agent import (
        run_duplicate_agent
    )
    from agents.anomaly_agent import run_anomaly_agent
    from agents.risk_agent import run_risk_agent
    from data_loader import load_from_path

    print("\n========================================")
    print("AI FINANCE CONTROLLER")
    print("DECISION AGENT")
    print("========================================")

    # `scenario` is merged in here purely for display in this
    # smoke test's printout below -- it is not read by any agent.
    data = load_from_path(
        "data/finance_controller_dataset.csv",
        "data/ground_truth.csv",
    )

    data = run_reconciliation_agent(data)
    data = run_duplicate_agent(data)
    data = run_anomaly_agent(data)
    data = run_risk_agent(data)

    result = run_decision_agent(data)

    print("\n========================================")
    print("FINAL DECISION SUMMARY")
    print("========================================")

    print(
        result["final_decision"].value_counts()
    )

    print("\n========================================")
    print("HIGH PRIORITY TRANSACTIONS")
    print("========================================")

    priority = result[
        result["final_decision"] ==
        "CONFIRMED_HIGH_PRIORITY"
    ].sort_values(
        "financial_impact",
        ascending=False
    )

    columns = [
        c for c in [
            "payment_id",
            "scenario",
            "risk_level",
            "risk_score",
            "financial_impact",
            "ml_anomaly",
            "final_decision"
        ] if c in priority.columns
    ]

    print(
        priority[columns].to_string(index=False)
    )


if __name__ == "__main__":
    main()