import os
import pandas as pd


class ActionAgent:

    def __init__(self):
        self.name = "Action Agent"

    def determine_action(self, row):

        decision = str(
            row.get("final_decision", "")
        )

        risk_level = str(
            row.get("risk_level", "")
        )

        reconciliation_status = str(
            row.get("reconciliation_status", "")
        )

        duplicate_flag = bool(
            row.get("duplicate_flag", False)
        )

        # =========================================================
        # CRITICAL
        #
        # NOTE: this used to pick the action by matching on a
        # `scenario` string that only the synthetic demo dataset
        # has. It now picks the action from the actual computed
        # outcome (missing settlement / duplicate / discrepancy),
        # which is available for any uploaded transaction.
        # =========================================================

        if (
            decision == "CONFIRMED_HIGH_PRIORITY"
            or risk_level == "CRITICAL"
        ):

            if reconciliation_status == "MISSING_SETTLEMENT":

                return {
                    "recommended_action":
                        "HOLD_SETTLEMENT",

                    "action_priority":
                        "IMMEDIATE",

                    "action_reason":
                        "Settlement discrepancy requires "
                        "immediate financial review."
                }

            elif duplicate_flag:

                return {
                    "recommended_action":
                        "BLOCK_DUPLICATE",

                    "action_priority":
                        "IMMEDIATE",

                    "action_reason":
                        "Duplicate transaction detected."
                }

            elif reconciliation_status == "DISCREPANCY":

                return {
                    "recommended_action":
                        "HOLD_AND_RECONCILE",

                    "action_priority":
                        "IMMEDIATE",

                    "action_reason":
                        "Settlement amount requires "
                        "reconciliation."
                }

            else:

                return {
                    "recommended_action":
                        "MANUAL_INVESTIGATION",

                    "action_priority":
                        "IMMEDIATE",

                    "action_reason":
                        "High financial risk detected."
                }

        # =========================================================
        # Financial exception
        # =========================================================

        elif decision == "FINANCIAL_EXCEPTION":

            return {
                "recommended_action":
                    "MANUAL_REVIEW",

                "action_priority":
                    "HIGH",

                "action_reason":
                    "Financial exception requires review."
            }

        # =========================================================
        # AI-escalated (rules said normal, LLM disagreed)
        # =========================================================

        elif decision == "AI_ESCALATED_REVIEW":

            llm_reason = row.get("llm_narrative", "")

            return {
                "recommended_action":
                    "AI_FLAGGED_MANUAL_REVIEW",

                "action_priority":
                    "HIGH",

                "action_reason":
                    "Rule-based checks scored this as normal, "
                    "but the LLM investigation agent flagged it "
                    "with high confidence"
                    + (f": {llm_reason}" if llm_reason else ".")
            }

        # =========================================================
        # Normal
        # =========================================================

        else:

            return {
                "recommended_action":
                    "NO_ACTION",

                "action_priority":
                    "LOW",

                "action_reason":
                    "Transaction is within acceptable "
                    "financial control limits."
            }

    def run(self, df):

        result = df.copy()

        actions = result.apply(
            self.determine_action,
            axis=1
        )

        action_df = pd.DataFrame(
            actions.tolist(),
            index=result.index
        )

        result = pd.concat(
            [
                result,
                action_df
            ],
            axis=1
        )

        return result


def run_action_agent(df):

    agent = ActionAgent()

    return agent.run(df)


if __name__ == "__main__":

    df = pd.read_csv(
        "outputs/final_decisions.csv"
    )

    result = run_action_agent(df)

    os.makedirs("outputs", exist_ok=True)

    result.to_csv(
        "outputs/action_results.csv",
        index=False
    )

    print("=" * 50)
    print("ACTION AGENT")
    print("=" * 50)

    print(
        result[
            [
                "payment_id",
                "final_decision",
                "recommended_action",
                "action_priority"
            ]
        ].head(20).to_string(index=False)
    )