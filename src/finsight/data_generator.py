"""
FinSight — Synthetic Data Generator
====================================

Generates realistic AWS billing + utilization telemetry for a multi-tenant
Enterprise CX SaaS estate, modeled on a representative Cloud Operations footprint:

    - 167 AWS single-tenant (ST) and multi-tenant (MT) deployments
    - ~$5M annualized cloud spend
    - Three product lines: Engage, Analyze, Assist
    - Regional spread across us-east-1, us-west-2, eu-west-1, ap-southeast-1

The generator is fully deterministic given a seed, so every run of the
notebook and the API reproduces the same numbers. It deliberately injects
three classes of signal so the downstream ML has something real to find:

    1. Trend + weekly seasonality  -> Capacity-Mngt-App (forecasting) can learn it
    2. Cost anomalies (spikes)      -> Cost-Mngt-App (anomaly detection) flags them
    3. Capacity-pressure ramps      -> Capacity-Mngt-App threshold breaches fire

No production data is used. This is synthetic by construction.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Estate definition — a representative Enterprise CX SaaS Cloud Operations footprint
# --------------------------------------------------------------------------- #

PRODUCTS = {
    # product       : (n_deployments, base_daily_usd, growth_per_day, tenancy)
    # base_daily_usd is the product-line daily run-rate before regional/service
    # allocation. Calibrated so the estate annualizes to ~$5M.
    "Engage":         (74, 5400.0, 2.1, "MT"),   # multi-tenant engagement suite
    "Analyze":        (58, 4300.0, 1.6, "MT"),   # multi-tenant analytics suite
    "Assist":         (35, 3600.0, 4.8, "ST"),   # single-tenant real-time assist (fast-growing)
}

REGIONS = {
    "us-east-1":      0.46,
    "us-west-2":      0.22,
    "eu-west-1":      0.20,
    "ap-southeast-1": 0.12,
}

SERVICES = {
    # service : (share_of_spend, base_utilization_pct)
    "EKS-Compute":  (0.38, 0.61),
    "EC2":          (0.19, 0.55),
    "RDS":          (0.14, 0.48),
    "S3":           (0.08, 0.30),
    "DataTransfer": (0.07, 0.40),
    "Observability":(0.09, 0.52),   # Datadog / monitoring
    "Lambda":       (0.05, 0.35),
}

# Anomaly catalog — each is a realistic FinOps incident the model should catch.
# (day_index, region, service, multiplier, root_cause)
INJECTED_ANOMALIES = [
    (47,  "us-east-1",      "DataTransfer", 3.4, "Cross-AZ chatter from mis-scheduled MT replication"),
    (88,  "ap-southeast-1", "EKS-Compute",  2.1, "HPA misconfig left Assist pods over-provisioned"),
    (123, "eu-west-1",      "RDS",          2.8, "Orphaned read-replica left running after a failover test"),
    (151, "us-west-2",      "Observability",2.3, "Debug log verbosity shipped to prod, Datadog ingest spike"),
    (172, "us-east-1",      "EKS-Compute",  1.9, "Black-Friday-style load test not torn down"),
]

DEFAULTS = dict(
    n_days=180,
    seed=42,
)


# --------------------------------------------------------------------------- #
# Generators
# --------------------------------------------------------------------------- #

def _daily_cost_series(rng: np.random.Generator, n_days: int) -> pd.DataFrame:
    """Per-day, per-product, per-region, per-service cost in USD."""
    rows = []
    start = pd.Timestamp("2025-01-01")

    for product, (n_dep, base, growth, tenancy) in PRODUCTS.items():
        for region, region_share in REGIONS.items():
            for service, (svc_share, _util) in SERVICES.items():
                for d in range(n_days):
                    date = start + pd.Timedelta(days=d)

                    # 1. Linear-ish growth (business expanding)
                    trend = base + growth * d

                    # 2. Weekly seasonality — lower on weekends for interactive
                    #    workloads, flat for batch/storage.
                    dow = date.dayofweek
                    if service in ("EKS-Compute", "EC2", "Lambda", "DataTransfer"):
                        weekly = 1.0 - 0.18 * (dow >= 5)   # ~18% dip on weekends
                    else:
                        weekly = 1.0

                    # 3. Month-boundary billing bumps (reserved/commitment cycles)
                    month_bump = 1.06 if date.day <= 2 else 1.0

                    # Allocate to region + service
                    cost = trend * region_share * svc_share * weekly * month_bump

                    # 4. Noise
                    cost *= rng.normal(1.0, 0.05)

                    rows.append(
                        (date, product, tenancy, region, service, max(cost, 0.0))
                    )

    df = pd.DataFrame(
        rows,
        columns=["date", "product", "tenancy", "region", "service", "cost_usd"],
    )

    # 5. Inject anomalies on top of the clean signal
    for day_idx, region, service, mult, cause in INJECTED_ANOMALIES:
        date = start + pd.Timedelta(days=day_idx)
        mask = (
            (df["date"] == date)
            & (df["region"] == region)
            & (df["service"] == service)
        )
        df.loc[mask, "cost_usd"] *= mult
        df.loc[mask, "anomaly_cause"] = cause

    if "anomaly_cause" not in df.columns:
        df["anomaly_cause"] = pd.NA

    return df


def _utilization_series(rng: np.random.Generator, n_days: int) -> pd.DataFrame:
    """
    Per-day utilization (%) for the compute fleet, with a deliberate
    capacity-pressure ramp on Assist/EKS in us-east-1 so Capacity-Mngt-App's
    forecast crosses the 80% headroom threshold near the end of the window.
    """
    rows = []
    start = pd.Timestamp("2025-01-01")

    for product, (_n, _b, _g, tenancy) in PRODUCTS.items():
        for region in REGIONS:
            base_util = SERVICES["EKS-Compute"][1]

            # Assist in us-east-1 ramps hard — this is the capacity story.
            pressure = (
                0.0012 if (product == "Assist" and region == "us-east-1") else 0.0003
            )

            for d in range(n_days):
                date = start + pd.Timedelta(days=d)
                dow = date.dayofweek

                util = base_util + pressure * d
                util += 0.06 if dow < 5 else -0.04          # weekday load
                util += rng.normal(0.0, 0.025)              # noise
                util = float(np.clip(util, 0.05, 0.99))

                rows.append((date, product, region, tenancy, util * 100.0))

    return pd.DataFrame(
        rows, columns=["date", "product", "region", "tenancy", "utilization_pct"]
    )


def generate(n_days: int = DEFAULTS["n_days"], seed: int = DEFAULTS["seed"]):
    """
    Build the full synthetic dataset.

    Returns
    -------
    cost_df : tidy daily cost rows (product x region x service)
    util_df : tidy daily utilization rows (product x region)
    """
    rng = np.random.default_rng(seed)
    cost_df = _daily_cost_series(rng, n_days)
    util_df = _utilization_series(rng, n_days)
    return cost_df, util_df


def annualized_spend(cost_df: pd.DataFrame) -> float:
    """Project the observed daily run-rate to an annual figure."""
    daily_avg = cost_df.groupby("date")["cost_usd"].sum().mean()
    return float(daily_avg * 365.0)


if __name__ == "__main__":
    cost, util = generate()
    print(f"Cost rows:        {len(cost):,}")
    print(f"Utilization rows: {len(util):,}")
    print(f"Date range:       {cost['date'].min().date()} -> {cost['date'].max().date()}")
    print(f"Annualized spend: ${annualized_spend(cost):,.0f}")
    print(f"Injected anomalies: {cost['anomaly_cause'].notna().sum()} line-items")
