"""
FinSight — Executive AI Intelligence Layer
==========================================

Unifies two production-style AIOps engines behind a RAG conversational layer:

    Capacity-Mngt-App  — predictive capacity & cost forecasting (time-series)
    Cost-Mngt-App      — cost anomaly detection & attribution (robust statistics)
    RAG layer    — grounds an LLM's answers in the engines' structured output

Public surface:
    generate()              -> synthetic AWS billing + utilization data
    forecast_capacity()     -> Capacity-Mngt-App capacity forecast
    forecast_cost()         -> Capacity-Mngt-App cost forecast
    CostMngtApp            -> anomaly detection + attribution
    build_corpus()          -> grounding fact cards for retrieval
    FinSightRAG             -> retrieval + LLM answer composition
"""

from .data_generator import generate, annualized_spend
from .capacity_mngt_app import CapacityMngtApp, forecast_capacity, forecast_cost, Forecast
from .cost_mngt_app import CostMngtApp, detect_anomalies, Anomaly
from .knowledge_base import build_corpus, corpus_to_frame, FactCard
from .rag import FinSightRAG, RAGAnswer, Retriever

__all__ = [
    "generate", "annualized_spend",
    "CapacityMngtApp", "forecast_capacity", "forecast_cost", "Forecast",
    "CostMngtApp", "detect_anomalies", "Anomaly",
    "build_corpus", "corpus_to_frame", "FactCard",
    "FinSightRAG", "RAGAnswer", "Retriever",
]

__version__ = "1.0.0"
