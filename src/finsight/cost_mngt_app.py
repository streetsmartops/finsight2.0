"""
FinSight :: Cost-Mngt-App — Real-Time Cost Anomaly Detection & Attribution
=========================================================================

Cost-Mngt-App answers the backward-looking question:

    "Our cloud bill moved. Where did the money go, and is it a problem?"

It does two things an executive cockpit needs:

    1. ANOMALY DETECTION  — flag (region x service x day) cost points that
       deviate materially from their own recent baseline.
    2. ATTRIBUTION         — decompose any spend delta between two periods
       into the dimensions (product / region / service) that drove it, so
       the answer is "DataTransfer in us-east-1, +$X" not just "spend is up".

Technique (Module 2/3 mapping):
-------------------------------
Detection uses a **robust z-score on a rolling baseline** (median + MAD)
per (region, service) stream. MAD-based scoring is resistant to the very
spikes we are trying to catch, so the baseline doesn't get poisoned by the
anomaly itself. This is an unsupervised statistical detector — appropriate
when we have no labeled "this was a real incident" history at the start.

We deliberately keep it transparent rather than a black-box autoencoder:
in a FinOps governance setting the finance and engineering stakeholders must
be able to see *why* a charge was flagged. Interpretability is a feature.

Attribution is a deterministic contribution analysis — exact, explainable,
and the basis for the grounded answers the RAG layer cites.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# Anomaly detection
# --------------------------------------------------------------------------- #

@dataclass
class Anomaly:
    date: pd.Timestamp
    product: str
    region: str
    service: str
    cost_usd: float
    baseline_usd: float
    excess_usd: float
    robust_z: float
    suspected_cause: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "product": self.product,
            "region": self.region,
            "service": self.service,
            "cost_usd": round(self.cost_usd, 2),
            "baseline_usd": round(self.baseline_usd, 2),
            "excess_usd": round(self.excess_usd, 2),
            "robust_z": round(self.robust_z, 2),
            "suspected_cause": self.suspected_cause,
        }


class CostMngtApp:
    """Robust rolling z-score anomaly detector + period attribution engine."""

    def __init__(self, window: int = 21, z_threshold: float = 4.0):
        self.window = window
        self.z_threshold = z_threshold

    # ---- detection -------------------------------------------------------- #

    def detect(self, cost_df: pd.DataFrame) -> pd.DataFrame:
        """
        Return a DataFrame of detected anomalies across all
        (product, region, service) streams, scored by robust z.
        """
        # Aggregate to the stream granularity we score on.
        stream = (
            cost_df.groupby(["date", "product", "region", "service"], as_index=False)
            .agg(cost_usd=("cost_usd", "sum"),
                 suspected_cause=("anomaly_cause", "first"))
            .sort_values("date")
        )

        out = []
        for (product, region, service), grp in stream.groupby(["product", "region", "service"]):
            grp = grp.sort_values("date").reset_index(drop=True)
            costs = grp["cost_usd"].to_numpy(dtype=float)

            # Rolling robust baseline: median + MAD over a trailing window.
            for i in range(len(grp)):
                lo = max(0, i - self.window)
                ref = costs[lo:i]
                if len(ref) < max(7, self.window // 2):
                    continue
                med = np.median(ref)
                mad = np.median(np.abs(ref - med))
                # 1.4826 scales MAD to be comparable to std for normal data.
                scale = 1.4826 * mad if mad > 1e-9 else (np.std(ref) + 1e-9)
                z = (costs[i] - med) / scale
                if z >= self.z_threshold:
                    out.append(
                        Anomaly(
                            date=grp["date"].iloc[i],
                            product=product,
                            region=region,
                            service=service,
                            cost_usd=float(costs[i]),
                            baseline_usd=float(med),
                            excess_usd=float(costs[i] - med),
                            robust_z=float(z),
                            suspected_cause=grp["suspected_cause"].iloc[i]
                            if pd.notna(grp["suspected_cause"].iloc[i]) else None,
                        ).as_dict()
                    )

        res = pd.DataFrame(out)
        if len(res):
            res = res.sort_values("excess_usd", ascending=False).reset_index(drop=True)
        return res

    # ---- attribution ------------------------------------------------------ #

    def attribute(
        self,
        cost_df: pd.DataFrame,
        period_a: tuple[str, str],
        period_b: tuple[str, str],
        dimension: str = "service",
    ) -> pd.DataFrame:
        """
        Explain the spend change from period_a -> period_b, broken down by
        `dimension` (one of: product, region, service).

        Returns rows sorted by absolute contribution to the delta, each with
        the dollar change and its share of the total movement.
        """
        a0, a1 = pd.Timestamp(period_a[0]), pd.Timestamp(period_a[1])
        b0, b1 = pd.Timestamp(period_b[0]), pd.Timestamp(period_b[1])

        a = cost_df[(cost_df["date"] >= a0) & (cost_df["date"] <= a1)]
        b = cost_df[(cost_df["date"] >= b0) & (cost_df["date"] <= b1)]

        # Normalize to per-day so unequal-length periods compare fairly.
        a_days = max((a1 - a0).days + 1, 1)
        b_days = max((b1 - b0).days + 1, 1)

        a_sum = a.groupby(dimension)["cost_usd"].sum() / a_days
        b_sum = b.groupby(dimension)["cost_usd"].sum() / b_days

        merged = pd.DataFrame({"period_a_per_day": a_sum, "period_b_per_day": b_sum}).fillna(0.0)
        merged["delta_per_day"] = merged["period_b_per_day"] - merged["period_a_per_day"]
        total_delta = merged["delta_per_day"].sum()
        merged["pct_of_change"] = np.where(
            abs(total_delta) > 1e-9,
            100.0 * merged["delta_per_day"] / total_delta,
            0.0,
        )
        merged = merged.reindex(
            merged["delta_per_day"].abs().sort_values(ascending=False).index
        )
        return merged.round(2).reset_index()


# --------------------------------------------------------------------------- #
# Convenience
# --------------------------------------------------------------------------- #

def detect_anomalies(cost_df: pd.DataFrame, z_threshold: float = 4.0) -> pd.DataFrame:
    return CostMngtApp(z_threshold=z_threshold).detect(cost_df)


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from finsight import data_generator as g

    cost, _ = g.generate()
    cf = CostMngtApp(z_threshold=4.0)

    print("=== Detected anomalies (top 6 by $ excess) ===")
    an = cf.detect(cost)
    print(an.head(6).to_string(index=False))

    print("\n=== Attribution: last 14 days vs prior 14 days, by service ===")
    dates = sorted(cost["date"].unique())
    p_recent = (pd.Timestamp(dates[-14]).strftime("%Y-%m-%d"),
                pd.Timestamp(dates[-1]).strftime("%Y-%m-%d"))
    p_prior = (pd.Timestamp(dates[-28]).strftime("%Y-%m-%d"),
               pd.Timestamp(dates[-15]).strftime("%Y-%m-%d"))
    attr = cf.attribute(cost, p_prior, p_recent, dimension="service")
    print(attr.to_string(index=False))
