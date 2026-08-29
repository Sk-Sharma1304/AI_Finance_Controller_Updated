"""
AI Finance Controller — Demo Dashboard
========================================

A Streamlit control-tower view over the pipeline's output. This is
the "demo surface" for the project: instead of judges reading raw
CSVs, they see a live queue, a risk breakdown, and — for any single
transaction — the full trail of what each of the 7 (or 8, with the
LLM step) agents concluded and why.

Run:

    python main.py            # generates outputs/*.csv
    streamlit run dashboard/app.py
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st


OUTPUT_DIR = "outputs"
FINAL_FILE = os.path.join(OUTPUT_DIR, "action_results.csv")

STAGE_FILES = {
    "Reconciliation": "reconciliation_results.csv",
    "Duplicate Detection": "duplicate_results.csv",
    "Anomaly Detection": "anomaly_results.csv",
    "Risk Assessment": "risk_results.csv",
    "Investigation": "investigation_results.csv",
    "LLM Investigation": "llm_investigation_results.csv",
    "Decision": "final_decisions.csv",
    "Action": "action_results.csv",
}

DECISION_COLORS = {
    "NORMAL": "#2ecc71",
    "FINANCIAL_EXCEPTION": "#f1c40f",
    "ML_REVIEW": "#f39c12",
    "AI_ESCALATED_REVIEW": "#9b59b6",
    "CONFIRMED_HIGH_PRIORITY": "#e74c3c",
}

RISK_COLORS = {
    "LOW": "#2ecc71",
    "MEDIUM": "#f1c40f",
    "HIGH": "#e67e22",
    "CRITICAL": "#e74c3c",
}


st.set_page_config(
    page_title="AI Finance Controller",
    page_icon="\U0001F9E0",
    layout="wide",
)


@st.cache_data
def load_data():

    if not os.path.exists(FINAL_FILE):
        return None

    return pd.read_csv(FINAL_FILE)


def kpi_row(df):

    total = len(df)

    normal = int((df["final_decision"] == "NORMAL").sum())

    flagged = total - normal

    ai_escalated = int(
        (df["final_decision"] == "AI_ESCALATED_REVIEW").sum()
    )

    total_impact = df.get(
        "financial_impact", pd.Series(dtype=float)
    ).sum()

    auto_cleared_pct = (normal / total * 100) if total else 0

    cols = st.columns(5)

    cols[0].metric("Total transactions", f"{total:,}")

    cols[1].metric(
        "Auto-cleared",
        f"{normal:,}",
        f"{auto_cleared_pct:.0f}% of volume",
    )

    cols[2].metric("Flagged for review", f"{flagged:,}")

    cols[3].metric(
        "AI-escalated (rules missed)", f"{ai_escalated:,}"
    )

    cols[4].metric(
        "Financial impact at risk",
        f"\u20b9{total_impact:,.0f}",
    )


def charts_row(df):

    left, right = st.columns(2)

    with left:

        st.subheader("Final decision breakdown")

        counts = (
            df["final_decision"]
            .value_counts()
            .rename_axis("decision")
            .reset_index(name="count")
        )

        fig = px.bar(
            counts,
            x="decision",
            y="count",
            color="decision",
            color_discrete_map=DECISION_COLORS,
            text="count",
        )

        fig.update_layout(
            showlegend=False, xaxis_title="", yaxis_title=""
        )

        st.plotly_chart(fig, width="stretch")

    with right:

        st.subheader("Risk level distribution")

        if "risk_level" in df.columns:

            counts = (
                df["risk_level"]
                .value_counts()
                .rename_axis("risk_level")
                .reset_index(name="count")
            )

            fig = px.pie(
                counts,
                names="risk_level",
                values="count",
                color="risk_level",
                color_discrete_map=RISK_COLORS,
                hole=0.45,
            )

            st.plotly_chart(fig, width="stretch")


def priority_queue(df):

    st.subheader("Priority queue")

    priority_decisions = [
        "CONFIRMED_HIGH_PRIORITY",
        "AI_ESCALATED_REVIEW",
        "FINANCIAL_EXCEPTION",
        "ML_REVIEW",
    ]

    queue = df[
        df["final_decision"].isin(priority_decisions)
    ].sort_values(
        "financial_impact", ascending=False
    )

    if queue.empty:
        st.info("Nothing in the review queue right now.")
        return

    if "reviewed" not in st.session_state:
        st.session_state.reviewed = {}

    display_columns = [
        c
        for c in [
            "payment_id",
            "scenario",
            "final_decision",
            "risk_level",
            "financial_impact",
            "recommended_action",
            "action_priority",
        ]
        if c in queue.columns
    ]

    for _, row in queue.iterrows():

        payment_id = row["payment_id"]

        status = st.session_state.reviewed.get(
            payment_id, "Pending"
        )

        with st.expander(
            f"{payment_id} — {row['final_decision']} "
            f"(\u20b9{row.get('financial_impact', 0):,.0f}) "
            f"[{status}]"
        ):

            info_col, action_col = st.columns([3, 1])

            with info_col:

                st.write(
                    {
                        col: row[col]
                        for col in display_columns
                        if col != "payment_id"
                    }
                )

                if "llm_narrative" in row and pd.notna(
                    row.get("llm_narrative")
                ) and row.get("llm_risk_opinion") not in (
                    "NOT_EVALUATED",
                    None,
                ):

                    st.markdown("**LLM opinion:**")
                    st.write(row["llm_narrative"])

            with action_col:

                approve = st.button(
                    "Approve", key=f"approve_{payment_id}"
                )

                hold = st.button(
                    "Hold / Escalate", key=f"hold_{payment_id}"
                )

                if approve:
                    st.session_state.reviewed[payment_id] = (
                        "Approved"
                    )
                    st.rerun()

                if hold:
                    st.session_state.reviewed[payment_id] = (
                        "Held"
                    )
                    st.rerun()

    st.caption(
        "Approve / Hold here is a demo-only UI action (kept in "
        "session state) — it doesn't write back to the pipeline. "
        "In production this would call an action-execution service."
    )


def transaction_drilldown(df):

    st.subheader("Transaction agent trail")

    payment_id = st.selectbox(
        "Pick a transaction to inspect",
        options=df["payment_id"].tolist(),
    )

    row = df[df["payment_id"] == payment_id].iloc[0]

    steps = [
        (
            "1. Reconciliation",
            row.get("reconciliation_status"),
            f"deviation ratio: "
            f"{row.get('deviation_ratio', float('nan')):.3f}"
            if pd.notna(row.get("deviation_ratio"))
            else "",
        ),
        (
            "2. Duplicate Detection",
            "DUPLICATE" if row.get("duplicate_flag") else "CLEAR",
            f"duplicate count: {row.get('duplicate_count', 1)}",
        ),
        (
            "3. Anomaly Detection (ML)",
            (
                "ANOMALY"
                if row.get("ml_anomaly") == -1
                else "NORMAL"
            ),
            "IsolationForest on settlement/deviation ratios",
        ),
        (
            "4. Risk Assessment",
            row.get("risk_level"),
            f"risk score: {row.get('risk_score')}",
        ),
        (
            "5. Investigation (rule-based)",
            row.get("investigation_recommendation", ""),
            row.get("investigation_summary", ""),
        ),
        (
            "5.5 LLM Investigation",
            row.get("llm_risk_opinion", "NOT_EVALUATED"),
            row.get("llm_narrative", ""),
        ),
        (
            "6. Decision",
            row.get("final_decision"),
            "",
        ),
        (
            "7. Action",
            row.get("recommended_action"),
            row.get("action_reason", ""),
        ),
    ]

    for title, headline, detail in steps:

        st.markdown(f"**{title}** — {headline}")

        if detail:
            st.caption(detail)


def main():

    st.title("\U0001F9E0 AI Finance Controller")

    st.caption(
        "Multi-agent reconciliation, anomaly detection and "
        "decisioning pipeline — control tower view."
    )

    df = load_data()

    if df is None:

        st.warning(
            "No pipeline output found. Run `python main.py` from "
            "the project root first, then reload this page."
        )

        return

    kpi_row(df)

    st.divider()

    charts_row(df)

    st.divider()

    tab1, tab2 = st.tabs(["Priority queue", "Transaction drill-down"])

    with tab1:
        priority_queue(df)

    with tab2:
        transaction_drilldown(df)


if __name__ == "__main__":
    main()
