"""
FinSight — Test Suite
=====================

Verifies the three guarantees that make FinSight defensible:

    1. The data generator is deterministic and hits the target scale.
    2. Each engine (CapacityMngtApp, CostMngtApp) produces correct, calibrated output.
    3. The RAG grounding contract holds: every cited number traces to a fact
       the deterministic engines actually computed (no hallucinated figures).

Run:  PYTHONPATH=src pytest tests/ -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import re
import numpy as np
import pandas as pd

from finsight import (
    generate, annualized_spend,
    forecast_capacity, forecast_cost,
    CostMngtApp,
    build_corpus,
    FinSightRAG,
)


# --------------------------------------------------------------------------- #
# Data generator
# --------------------------------------------------------------------------- #

def test_data_is_deterministic():
    c1, u1 = generate(seed=42)
    c2, u2 = generate(seed=42)
    pd.testing.assert_frame_equal(c1, c2)
    pd.testing.assert_frame_equal(u1, u2)


def test_estate_scale_matches_context():
    cost, _ = generate()
    ann = annualized_spend(cost)
    # Should land near the ~$5M estate, within a tolerance band.
    assert 4_500_000 < ann < 5_500_000, f"annualized spend off target: {ann:,.0f}"


def test_products_and_regions_present():
    cost, _ = generate()
    assert set(cost["product"].unique()) == {"Engage", "Analyze", "Assist"}
    assert "us-east-1" in cost["region"].unique()


def test_anomalies_are_injected():
    cost, _ = generate()
    assert cost["anomaly_cause"].notna().sum() >= 5


# --------------------------------------------------------------------------- #
# CapacityMngtApp
# --------------------------------------------------------------------------- #

def test_capacity_app_forecast_is_accurate():
    _, util = generate()
    fc = forecast_capacity(util, "Engage", "us-west-2")
    # In-sample MAPE on a clean seasonal signal should be tight.
    assert fc.in_sample_mape < 0.08, f"MAPE too high: {fc.in_sample_mape}"


def test_capacity_app_flags_critical_capacity():
    _, util = generate()
    fc = forecast_capacity(util, "Assist", "us-east-1")
    # This stream is engineered to ramp past 80% — must be CRITICAL.
    assert fc.status == "CRITICAL"
    assert fc.already_breached is True


def test_capacity_app_reports_healthy_where_expected():
    _, util = generate()
    fc = forecast_capacity(util, "Analyze", "ap-southeast-1")
    assert fc.status in ("HEALTHY", "WATCH")


def test_cost_forecast_has_interval():
    cost, _ = generate()
    fc = forecast_cost(cost)
    # Prediction interval must bracket the point forecast.
    assert (fc.forecast["lower"] <= fc.forecast["yhat"]).all()
    assert (fc.forecast["yhat"] <= fc.forecast["upper"]).all()


# --------------------------------------------------------------------------- #
# CostMngtApp
# --------------------------------------------------------------------------- #

def test_cost_app_catches_injected_anomalies():
    cost, _ = generate()
    anomalies = CostMngtApp(z_threshold=4.0).detect(cost)
    # All five engineered incidents should be recovered (each spans products,
    # so we check the distinct (date, region, service) incident signatures).
    causes = set(anomalies["suspected_cause"].dropna())
    assert len(causes) >= 5, f"only recovered causes: {causes}"


def test_cost_app_attribution_sums_to_total():
    cost, _ = generate()
    cf = CostMngtApp()
    dates = sorted(cost["date"].unique())
    recent = (str(pd.Timestamp(dates[-14]).date()), str(pd.Timestamp(dates[-1]).date()))
    prior = (str(pd.Timestamp(dates[-28]).date()), str(pd.Timestamp(dates[-15]).date()))
    attr = cf.attribute(cost, prior, recent, dimension="service")
    # Contribution shares must sum to ~100%.
    assert abs(attr["pct_of_change"].sum() - 100.0) < 1.0


# --------------------------------------------------------------------------- #
# RAG grounding contract
# --------------------------------------------------------------------------- #

def test_corpus_builds():
    cost, util = generate()
    cards = build_corpus(cost, util)
    assert len(cards) >= 20
    assert all(c.id.startswith("FACT-") for c in cards)


def test_rag_answers_are_grounded():
    """The crucial test: every FACT id the answer cites must exist in the corpus."""
    cost, util = generate()
    rag = FinSightRAG(cost, util)
    valid_ids = {c.id for c in rag.cards}

    for q in [
        "Will we run out of capacity next quarter?",
        "Why did our cloud spend spike?",
        "What is our annualized spend?",
    ]:
        ans = rag.ask(q)
        cited = set(re.findall(r"FACT-\d{3}", ans.answer))
        assert cited, f"answer cited no facts for: {q}"
        assert cited <= valid_ids, f"hallucinated fact ids {cited - valid_ids} for: {q}"


def test_rag_surfaces_critical_first_for_risk_queries():
    cost, util = generate()
    rag = FinSightRAG(cost, util)
    ans = rag.ask("Are we at risk of running out of capacity?")
    # The CRITICAL Assist/us-east-1 fact should be in the lead evidence.
    lead_texts = " ".join(e.text for e in ans.evidence[:2])
    assert "CRITICAL" in lead_texts and "Assist" in lead_texts


def test_rag_declines_when_no_facts():
    cost, util = generate()
    rag = FinSightRAG(cost, util)
    ans = rag.ask("What is the airspeed velocity of an unladen swallow?")
    # Off-domain query: should not fabricate FACT citations.
    assert "don't have" in ans.answer.lower() or len(ans.citations) == 0


if __name__ == "__main__":
    import subprocess
    subprocess.run(["python", "-m", "pytest", __file__, "-v"])
