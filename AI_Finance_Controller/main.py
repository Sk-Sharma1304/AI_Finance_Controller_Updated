"""
AI Finance Controller
======================

Entry point for the multi-agent financial reconciliation and
fraud-control pipeline.

Run with:

    python main.py

This simply delegates to the orchestrator, which coordinates all
seven agents (Reconciliation, Duplicate Detection, Anomaly
Detection, Risk Assessment, Investigation, Decision, Action) end
to end and writes their results to the ``outputs/`` folder.
"""

from orchestrator.finance_orchestrator import main

if __name__ == "__main__":
    main()
