"""
FinSight :: API — Executive Cockpit (FastAPI)
=============================================

API-first surface for the FinSight intelligence layer. Exposes the RAG
assistant and the underlying engine outputs as JSON endpoints, plus a single
static HTML cockpit that consumes them.

Run:
    uvicorn api.main:app --reload --port 8000
    open http://localhost:8000

Endpoints
---------
    GET  /                      -> the HTML cockpit (static)
    GET  /api/health           -> liveness + whether an LLM key is configured
    GET  /api/overview         -> estate KPIs for the dashboard cards
    GET  /api/capacity         -> per-product/region capacity status table
    GET  /api/anomalies        -> detected cost anomalies (CostMngtApp)
    GET  /api/forecast/cost    -> estate daily-spend forecast (CapacityMngtApp)
    POST /api/ask              -> { question } -> grounded RAG answer + evidence

The data + engines are built once at startup and cached in app state, so the
cockpit is responsive. Everything is deterministic given the seed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Make the package importable whether run from repo root or elsewhere.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from finsight import (                       # noqa: E402
    generate,
    annualized_spend,
    forecast_cost,
    forecast_capacity,
    CostMngtApp,
    build_corpus,
    FinSightRAG,
)

app = FastAPI(title="FinSight Executive Cockpit", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --------------------------------------------------------------------------- #
# Build data + engines once at startup
# --------------------------------------------------------------------------- #

class State:
    cost = None
    util = None
    cards = None
    rag = None


@app.on_event("startup")
def _bootstrap() -> None:
    State.cost, State.util = generate()
    State.cards = build_corpus(State.cost, State.util)
    State.rag = FinSightRAG(cards=State.cards)


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #

class AskRequest(BaseModel):
    question: str


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "facts_indexed": len(State.cards or []),
    }


@app.get("/api/overview")
def overview() -> dict:
    cost = State.cost
    ann = annualized_spend(cost)
    latest = float(cost.groupby("date")["cost_usd"].sum().iloc[-1])

    anomalies = CostMngtApp(z_threshold=4.0).detect(cost)
    n_anom = int(len(anomalies))
    excess = float(anomalies["excess_usd"].sum()) if n_anom else 0.0

    # Count capacity statuses
    statuses = {"CRITICAL": 0, "WARNING": 0, "WATCH": 0, "HEALTHY": 0}
    for prod in sorted(cost["product"].unique()):
        for region in sorted(cost["region"].unique()):
            fc = forecast_capacity(State.util, prod, region)
            statuses[fc.status] = statuses.get(fc.status, 0) + 1

    return {
        "annualized_spend_usd": round(ann, 0),
        "latest_daily_usd": round(latest, 0),
        "deployments": 167,
        "team_size": 91,
        "anomalies_detected": n_anom,
        "anomaly_excess_usd": round(excess, 0),
        "capacity_statuses": statuses,
    }


@app.get("/api/capacity")
def capacity() -> dict:
    rows = []
    for prod in sorted(State.cost["product"].unique()):
        for region in sorted(State.cost["region"].unique()):
            fc = forecast_capacity(State.util, prod, region)
            rows.append({
                "product": prod,
                "region": region,
                "current_util_pct": round(fc.current_value, 1),
                "status": fc.status,
                "breach_date": str(fc.breach_date.date()) if fc.breach_date is not None else None,
                "breach_in_days": fc.breach_in_days,
            })
    # Sort worst-first
    rank = {"CRITICAL": 0, "WARNING": 1, "WATCH": 2, "HEALTHY": 3}
    rows.sort(key=lambda r: (rank.get(r["status"], 9), -r["current_util_pct"]))
    return {"rows": rows}


@app.get("/api/anomalies")
def anomalies() -> dict:
    an = CostMngtApp(z_threshold=4.0).detect(State.cost)
    return {"rows": an.head(15).to_dict(orient="records")}


@app.get("/api/forecast/cost")
def forecast_cost_endpoint() -> dict:
    fc = forecast_cost(State.cost, horizon=45)
    hist = fc.history.copy()
    hist["date"] = hist["date"].dt.strftime("%Y-%m-%d")
    fut = fc.forecast.copy()
    fut["date"] = fut["date"].dt.strftime("%Y-%m-%d")
    return {
        "history": hist.tail(60).to_dict(orient="records"),
        "forecast": fut.to_dict(orient="records"),
        "mape_pct": round(fc.in_sample_mape * 100, 1),
    }


@app.post("/api/ask")
def ask(req: AskRequest) -> dict:
    ans = State.rag.ask(req.question)
    return ans.to_dict()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
