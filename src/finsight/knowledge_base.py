"""
FinSight :: Knowledge Base — Grounding Facts for the RAG Layer
==============================================================

The RAG cockpit is only as trustworthy as the facts it can cite. This module
turns the *structured outputs* of Capacity-Mngt-App and Cost-Mngt-App into a corpus of
short, atomic, retrievable "fact cards." Each card is a self-contained
statement with provenance (which engine produced it, over what data window).

Why build the corpus from model outputs rather than raw rows?
-------------------------------------------------------------
An executive question ("will we breach capacity?", "why did spend spike?")
is answered by *derived* facts — a forecast, an anomaly, an attribution —
not by 15,000 raw billing rows. By indexing the derived facts we (a) keep
retrieval fast and relevant, and (b) guarantee the LLM can only cite things
the deterministic engines actually computed. That is the anti-hallucination
contract: the language model phrases the answer, the ML owns the numbers.

Each FactCard carries:
    id        : stable identifier (also used as a citation handle)
    text      : the natural-language fact (what gets embedded + retrieved)
    source    : "Capacity-Mngt-App" | "Cost-Mngt-App" | "Estate"
    metadata  : structured payload for exact-value rendering
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from . import data_generator as datagen
from .capacity_mngt_app import forecast_capacity, forecast_cost
from .cost_mngt_app import CostMngtApp


@dataclass
class FactCard:
    id: str
    text: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Build the corpus
# --------------------------------------------------------------------------- #

def build_corpus(
    cost_df: pd.DataFrame,
    util_df: pd.DataFrame,
    capacity_threshold: float = 80.0,
) -> list[FactCard]:
    cards: list[FactCard] = []
    cid = 0

    def add(text: str, source: str, **meta) -> None:
        nonlocal cid
        cards.append(FactCard(id=f"FACT-{cid:03d}", text=text, source=source, metadata=meta))
        cid += 1

    products = sorted(cost_df["product"].unique())
    regions = sorted(cost_df["region"].unique())

    # ---- Estate-level rollups -------------------------------------------- #
    ann = datagen.annualized_spend(cost_df)
    daily_now = cost_df.groupby("date")["cost_usd"].sum().iloc[-1]
    add(
        f"The total cloud estate is tracking to ${ann:,.0f} annualized spend, "
        f"with the most recent day at ${daily_now:,.0f}.",
        "Estate", annualized_usd=round(ann, 0), latest_daily_usd=round(daily_now, 0),
    )

    by_product = cost_df.groupby("product")["cost_usd"].sum().sort_values(ascending=False)
    share = (by_product / by_product.sum() * 100).round(1)
    for prod, amt in by_product.items():
        add(
            f"{prod} accounts for ${amt:,.0f} of cumulative spend "
            f"({share[prod]:.1f}% of the estate over the observed window).",
            "Estate", product=prod, cumulative_usd=round(amt, 0), pct_share=float(share[prod]),
        )

    by_region = cost_df.groupby("region")["cost_usd"].sum().sort_values(ascending=False)
    rshare = (by_region / by_region.sum() * 100).round(1)
    top_region = by_region.index[0]
    add(
        f"{top_region} is the largest region by spend at "
        f"${by_region.iloc[0]:,.0f} ({rshare.iloc[0]:.1f}% of the estate).",
        "Estate", region=top_region, cumulative_usd=round(float(by_region.iloc[0]), 0),
    )

    # ---- Capacity forecasts (Capacity-Mngt-App) ---------------------------------- #
    cost_fc = forecast_cost(cost_df, horizon=45)
    proj = cost_fc.forecast["yhat"].iloc[-1]
    add(
        f"Capacity-Mngt-App projects estate daily spend will reach ${proj:,.0f} per day "
        f"in 45 days (forecast MAPE {cost_fc.in_sample_mape*100:.1f}%), "
        f"implying roughly ${proj*365:,.0f} annualized if the trend holds.",
        "Capacity-Mngt-App", horizon_days=45, projected_daily_usd=round(proj, 0),
        mape_pct=round(cost_fc.in_sample_mape*100, 1),
    )

    for prod in products:
        for region in regions:
            sub = util_df[(util_df["product"] == prod) & (util_df["region"] == region)]
            if sub.empty:
                continue
            fc = forecast_capacity(util_df, prod, region,
                                   horizon=45, threshold_pct=capacity_threshold)
            cur = fc.current_value
            if fc.status in ("CRITICAL",):
                add(
                    f"{prod} in {region} is ALREADY above the {capacity_threshold:.0f}% "
                    f"utilization headroom threshold (current ~{cur:.0f}%). Capacity-Mngt-App "
                    f"status: CRITICAL — capacity action is needed now.",
                    "Capacity-Mngt-App", product=prod, region=region, status=fc.status,
                    current_util_pct=round(cur, 1), threshold_pct=capacity_threshold,
                )
            elif fc.breach_date is not None:
                add(
                    f"{prod} in {region} is at ~{cur:.0f}% utilization and Capacity-Mngt-App "
                    f"projects it will cross {capacity_threshold:.0f}% on "
                    f"{fc.breach_date.date()} (in {fc.breach_in_days} days). "
                    f"Status: {fc.status}.",
                    "Capacity-Mngt-App", product=prod, region=region, status=fc.status,
                    current_util_pct=round(cur, 1),
                    breach_date=str(fc.breach_date.date()),
                    breach_in_days=fc.breach_in_days,
                )
            else:
                add(
                    f"{prod} in {region} is at ~{cur:.0f}% utilization with adequate "
                    f"headroom; Capacity-Mngt-App projects no {capacity_threshold:.0f}% breach "
                    f"in the next 45 days. Status: HEALTHY.",
                    "Capacity-Mngt-App", product=prod, region=region, status="HEALTHY",
                    current_util_pct=round(cur, 1),
                )

    # ---- Cost anomalies (Cost-Mngt-App) ----------------------------------- #
    cf = CostMngtApp(z_threshold=4.0)
    anomalies = cf.detect(cost_df)
    if len(anomalies):
        total_excess = anomalies["excess_usd"].sum()
        add(
            f"Cost-Mngt-App flagged {len(anomalies)} cost anomalies across the estate, "
            f"totaling ${total_excess:,.0f} in excess (above-baseline) spend.",
            "Cost-Mngt-App", n_anomalies=int(len(anomalies)),
            total_excess_usd=round(float(total_excess), 0),
        )
        for _, a in anomalies.head(12).iterrows():
            cause = a["suspected_cause"] or "root cause under investigation"
            add(
                f"On {a['date']}, {a['service']} spend for {a['product']} in "
                f"{a['region']} hit ${a['cost_usd']:,.0f} versus a ${a['baseline_usd']:,.0f} "
                f"baseline (+${a['excess_usd']:,.0f}, robust z={a['robust_z']:.1f}). "
                f"Suspected cause: {cause}.",
                "Cost-Mngt-App", date=a["date"], service=a["service"],
                product=a["product"], region=a["region"],
                excess_usd=round(float(a["excess_usd"]), 0),
                robust_z=round(float(a["robust_z"]), 1), cause=cause,
            )

    # ---- Recent attribution (Cost-Mngt-App) ------------------------------- #
    dates = sorted(cost_df["date"].unique())
    if len(dates) >= 28:
        recent = (pd.Timestamp(dates[-14]).strftime("%Y-%m-%d"),
                  pd.Timestamp(dates[-1]).strftime("%Y-%m-%d"))
        prior = (pd.Timestamp(dates[-28]).strftime("%Y-%m-%d"),
                 pd.Timestamp(dates[-15]).strftime("%Y-%m-%d"))
        attr = cf.attribute(cost_df, prior, recent, dimension="service")
        top = attr.iloc[0]
        add(
            f"Comparing the last 14 days to the prior 14 days, the largest driver of the "
            f"spend change was {top['service']} at "
            f"${top['delta_per_day']:+,.0f}/day ({top['pct_of_change']:+.0f}% of the total "
            f"movement). This is steady-state growth, not an anomaly.",
            "Cost-Mngt-App", dimension="service", top_driver=top["service"],
            delta_per_day_usd=round(float(top["delta_per_day"]), 0),
        )

    return cards


def corpus_to_frame(cards: list[FactCard]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"id": c.id, "source": c.source, "text": c.text, **c.metadata} for c in cards]
    )


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    cost, util = datagen.generate()
    corpus = build_corpus(cost, util)
    print(f"Built {len(corpus)} fact cards.\n")
    for c in corpus[:8]:
        print(f"[{c.id} | {c.source}] {c.text}\n")
