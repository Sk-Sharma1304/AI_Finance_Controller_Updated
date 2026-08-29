import pandas as pd


class RiskAgent:
    """
    Turns the evidence already produced by upstream agents into a
    0-100 risk score and a LOW/MEDIUM/HIGH/CRITICAL level.

    IMPORTANT: this used to score off a ``scenario`` column that
    only exists in the synthetic demo dataset (it's literally the
    injected-fraud-type answer key). That made the whole pipeline
    unusable on a real uploaded CSV, which never has that column.

    This version scores off signals every upload actually has:
      - reconciliation_severity   (deviation_ratio-based, computed)
      - reconciliation_status     (missing settlement is worse than
                                    a plain discrepancy)
      - duplicate_risk            (from the Duplicate Detection Agent)
      - ml_anomaly                (from the IsolationForest agent)
      - financial_impact          (absolute rupee amount at risk)

    The weights are hand-tuned to land in roughly the same range as
    the original scenario-based scores (see README's "Known
    limitations" section: these should eventually be backtested
    against real outcome labels, not hand-tuned).
    """

    SEVERITY_SCORE = {
        "LOW": 0,
        "MEDIUM": 20,
        "HIGH": 35,
        "CRITICAL": 45,
    }

    DUPLICATE_SCORE = {
        "NONE": 0,
        "MEDIUM": 15,
        "HIGH": 25,
    }

    MISSING_SETTLEMENT_BONUS = 25
    ML_ANOMALY_BONUS = 20

    def calculate_risk(self, data):

        result = data.copy()

        # --------------------------------------------------
        # Financial impact (guard against missing upstream cols
        # if this agent is ever run standalone/out of order)
        # --------------------------------------------------

        if "financial_impact" not in result.columns:
            result["financial_impact"] = (
                result["expected_settlement"] - result["actual_settlement"]
            ).abs()

        result["financial_impact"] = result["financial_impact"].fillna(
            result["expected_settlement"].abs()
        )

        # --------------------------------------------------
        # Base score: how bad is the reconciliation deviation
        # --------------------------------------------------

        severity = result.get("reconciliation_severity", "LOW")
        result["risk_score"] = severity.map(self.SEVERITY_SCORE).fillna(0)

        # Missing settlement is treated as worse than an ordinary
        # discrepancy of the same deviation size -- money that
        # never arrived is a different kind of problem than money
        # that arrived short.
        if "reconciliation_status" in result.columns:
            result.loc[
                result["reconciliation_status"] == "MISSING_SETTLEMENT",
                "risk_score",
            ] += self.MISSING_SETTLEMENT_BONUS

        # --------------------------------------------------
        # Duplicate signal
        # --------------------------------------------------

        if "duplicate_risk" in result.columns:
            result["risk_score"] += (
                result["duplicate_risk"].map(self.DUPLICATE_SCORE).fillna(0)
            )

        # --------------------------------------------------
        # ML anomaly signal (independent statistical check)
        # --------------------------------------------------

        if "ml_anomaly" in result.columns:
            result.loc[
                result["ml_anomaly"] == -1, "risk_score"
            ] += self.ML_ANOMALY_BONUS

        # --------------------------------------------------
        # Increase risk based on absolute financial impact
        # --------------------------------------------------

        result.loc[result["financial_impact"] >= 500, "risk_score"] += 20

        result.loc[
            (result["financial_impact"] >= 250)
            & (result["financial_impact"] < 500),
            "risk_score",
        ] += 10

        # --------------------------------------------------
        # Cap score at 100
        # --------------------------------------------------

        result["risk_score"] = result["risk_score"].clip(lower=0, upper=100)

        # --------------------------------------------------
        # Convert score to risk level
        # --------------------------------------------------

        def get_risk_level(score):

            if score >= 70:
                return "CRITICAL"

            elif score >= 40:
                return "HIGH"

            elif score >= 20:
                return "MEDIUM"

            else:
                return "LOW"

        result["risk_level"] = result["risk_score"].apply(get_risk_level)

        return result


def run_risk_agent(df):

    agent = RiskAgent()

    return agent.calculate_risk(df)


def main():

    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    from data_loader import load_from_path
    from agents.reconciliation_agent import run_reconciliation_agent
    from agents.duplicates_detection_agent import run_duplicate_agent
    from agents.anomaly_agent import run_anomaly_agent

    print("\n========================================")
    print("AI FINANCE CONTROLLER")
    print("RISK AGENT")
    print("========================================")

    data = load_from_path(
        "data/finance_controller_dataset.csv",
        "data/ground_truth.csv",
    )

    data = run_reconciliation_agent(data)
    data = run_duplicate_agent(data)
    data = run_anomaly_agent(data)

    agent = RiskAgent()

    result = agent.calculate_risk(data)

    exceptions = result[result["reconciliation_status"] != "RECONCILED"]

    print(f"Total transactions : {len(result)}")
    print(f"Financial exceptions : {len(exceptions)}")

    print("\n========================================")
    print("RISK SUMMARY")
    print("========================================")

    print(result["risk_level"].value_counts())

    print("\n========================================")
    print("HIGH PRIORITY TRANSACTIONS")
    print("========================================")

    priority = result[result["risk_level"].isin(["HIGH", "CRITICAL"])].sort_values(
        "risk_score", ascending=False
    )

    columns = [
        "payment_id",
        "expected_settlement",
        "actual_settlement",
        "financial_impact",
        "risk_score",
        "risk_level",
    ]

    print(priority[columns].to_string(index=False))


if __name__ == "__main__":
    main()
