import os
import pandas as pd


class InvestigationAgent:

    def __init__(self):
        self.name = "Investigation Agent"

    def investigate(self, row):

        evidence = []
        explanation = []

        risk_level = str(
            row.get("risk_level", "")
        )

        financial_impact = row.get(
            "financial_impact",
            0
        )

        ml_anomaly = row.get(
            "ml_anomaly",
            1
        )

        duplicate_flag = row.get(
            "duplicate_flag",
            False
        )

        reconciliation_status = str(
            row.get("reconciliation_status", "")
        )

        reconciliation_severity = str(
            row.get("reconciliation_severity", "LOW")
        )

        deviation_ratio = row.get(
            "deviation_ratio",
            0
        )

        # =========================================================
        # Reconciliation investigation
        #
        # NOTE: this used to branch on a `scenario` column that only
        # exists in the synthetic demo dataset (it's the injected
        # fraud-type answer key). A real uploaded CSV never has it,
        # so this now reads the actual computed reconciliation
        # signals instead -- status, severity and deviation ratio --
        # which are available for any transaction.
        # =========================================================

        if reconciliation_status == "MISSING_SETTLEMENT":

            evidence.append(
                "Settlement amount is missing or incomplete."
            )

            explanation.append(
                "The transaction was processed but the expected "
                "settlement was not received."
            )

        elif reconciliation_status == "DISCREPANCY":

            try:
                deviation_pct = float(deviation_ratio) * 100
            except (TypeError, ValueError):
                deviation_pct = 0

            if reconciliation_severity in ("HIGH", "CRITICAL"):

                evidence.append(
                    f"Large settlement deviation ({deviation_pct:.1f}%) "
                    "from the expected amount."
                )

                explanation.append(
                    "The actual settlement differs substantially from "
                    "the expected settlement value."
                )

            elif reconciliation_severity == "MEDIUM":

                evidence.append(
                    f"Moderate settlement deviation ({deviation_pct:.1f}%) "
                    "from the expected amount."
                )

                explanation.append(
                    "A discrepancy exists between expected and observed "
                    "financial values."
                )

            else:

                evidence.append(
                    f"Minor settlement deviation ({deviation_pct:.1f}%) "
                    "from the expected amount."
                )

                explanation.append(
                    "A small discrepancy exists between expected and "
                    "observed financial values."
                )

        # =========================================================
        # ML investigation
        # =========================================================

        if ml_anomaly == -1:

            evidence.append(
                "Machine learning model classified the transaction "
                "as anomalous."
            )

            explanation.append(
                "The transaction has characteristics that differ "
                "significantly from normal transaction patterns."
            )

        # =========================================================
        # Duplicate investigation
        # =========================================================

        if duplicate_flag:

            duplicate_count = row.get("duplicate_count", 2)

            evidence.append(
                "Duplicate detection agent confirmed a duplicate "
                f"(matches {duplicate_count} transaction(s) with the "
                "same amount, order and time window)."
            )

        # =========================================================
        # Financial impact
        # =========================================================

        try:
            financial_impact = float(
                financial_impact
            )
        except:
            financial_impact = 0

        if financial_impact > 0:

            evidence.append(
                f"Financial impact: ₹{financial_impact:.2f}"
            )

        # =========================================================
        # Overall explanation
        # =========================================================

        if not explanation:

            explanation.append(
                "No significant financial anomaly was identified."
            )

        investigation_summary = " ".join(
            explanation
        )

        evidence_summary = " | ".join(
            evidence
        )

        # =========================================================
        # Recommendation
        # =========================================================

        if risk_level == "CRITICAL":

            recommendation = (
                "Immediate manual investigation and financial "
                "control review required."
            )

        elif risk_level == "HIGH":

            recommendation = (
                "Transaction should be investigated before "
                "financial settlement is finalized."
            )

        elif risk_level == "MEDIUM":

            recommendation = (
                "Transaction should be monitored and reviewed "
                "if additional anomalies occur."
            )

        else:

            recommendation = (
                "No immediate investigation required."
            )

        return {
            "investigation_summary": investigation_summary,
            "evidence": evidence_summary,
            "investigation_recommendation": recommendation
        }

    def run(self, df):

        result = df.copy()

        investigations = result.apply(
            self.investigate,
            axis=1
        )

        investigation_df = pd.DataFrame(
            investigations.tolist(),
            index=result.index
        )

        result = pd.concat(
            [
                result,
                investigation_df
            ],
            axis=1
        )

        return result


def run_investigation_agent(df):

    agent = InvestigationAgent()

    return agent.run(df)


if __name__ == "__main__":

    df = pd.read_csv(
        "outputs/risk_results.csv"
    )

    result = run_investigation_agent(df)

    os.makedirs("outputs", exist_ok=True)

    result.to_csv(
        "outputs/investigation_results.csv",
        index=False
    )

    print("=" * 50)
    print("INVESTIGATION AGENT")
    print("=" * 50)

    print(
        result[
            [
                "payment_id",
                "risk_level",
                "investigation_summary",
                "investigation_recommendation"
            ]
        ].head(20).to_string(index=False)
    )