"""
FinSight :: RAG — Retrieval-Augmented Executive Q&A
===================================================

This is the conversational cockpit layer. It takes a natural-language
executive question, retrieves the most relevant grounding facts produced by
Capacity-Mngt-App and CostMngtApp, and composes a cited answer.

Architecture
------------
    question
       │
       ▼
   [ Retriever ]  TF-IDF over FactCard.text  ──►  top-k FactCards
       │
       ▼
   [ Composer ]   Anthropic Claude, constrained to ONLY use retrieved facts
       │           (deterministic template fallback if no API key)
       ▼
    grounded answer  +  [FACT-xxx] citations  +  the evidence used

Two design commitments that matter in an interview:

1. **Grounding contract.** The system prompt forbids the model from using
   any number not present in the retrieved facts. The deterministic engines
   own the math; the LLM only phrases it. This is how you get an exec-facing
   assistant finance can trust.

2. **Graceful degradation.** Retrieval is local TF-IDF (no vector DB
   service needed), and if `ANTHROPIC_API_KEY` is unset the composer falls
   back to a template that stitches the retrieved facts together. The repo
   therefore *always runs* in a clean clone — reviewers don't need a key to
   see it work, but a key unlocks fluent natural-language answers.
"""

from __future__ import annotations

import json
import os
import re
import textwrap
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .knowledge_base import FactCard, build_corpus


# --------------------------------------------------------------------------- #
# Retrieval
# --------------------------------------------------------------------------- #

class Retriever:
    """TF-IDF retriever over the grounding fact corpus."""

    def __init__(self, cards: list[FactCard]):
        self.cards = cards
        self._texts = [c.text for c in cards]
        # Char-aware tokenization helps match 'us-east-1', 'EKS-Compute', etc.
        # Stopwords removed so similarity is driven by domain content
        # ('capacity', 'spend', 'us-east-1') rather than filler ('is', 'the',
        # 'of') — otherwise an off-domain question can score high purely on
        # shared function words.
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            token_pattern=r"[A-Za-z0-9][A-Za-z0-9\-]+",
            stop_words="english",
            min_df=1,
        )
        self.matrix = self.vectorizer.fit_transform(self._texts)

    def search(self, query: str, k: int = 6, min_score: float = 0.04) -> list[tuple[FactCard, float]]:
        q = self.vectorizer.transform([query])
        sims = cosine_similarity(q, self.matrix)[0]

        # Relevance floor: if the *raw* TF-IDF similarity (before boosts) shows
        # essentially no lexical overlap with the corpus, the question is
        # off-domain. Returning nothing lets the composer decline honestly
        # rather than dressing up irrelevant facts. This is part of the
        # grounding contract — no evidence, no answer.
        max_raw_sim = float(sims.max()) if sims.size else 0.0
        if max_raw_sim < min_score:
            return []

        ql = query.lower()
        # Does the question express risk/forward concern? If so, rank facts
        # that carry an elevated status above benign ones.
        risk_intent = any(
            w in ql for w in
            ("run out", "breach", "risk", "headroom", "capacity", "out of",
             "problem", "spike", "anomaly", "wrong", "issue", "over")
        )

        boost = np.zeros_like(sims)
        for i, card in enumerate(self.cards):
            # Exact dimension hits the user named.
            for key in ("product", "region", "service"):
                val = str(card.metadata.get(key, "")).lower()
                if val and val in ql:
                    boost[i] += 0.15
            # Status-aware boost for risk-intent questions.
            if risk_intent:
                status = card.metadata.get("status", "")
                boost[i] += {"CRITICAL": 0.30, "WARNING": 0.20, "WATCH": 0.10}.get(status, 0.0)
                if "excess_usd" in card.metadata:
                    boost[i] += 0.10
        scored = sims + boost

        order = np.argsort(scored)[::-1][:k]
        # Only keep facts whose own raw similarity clears the floor — a global
        # boost shouldn't drag in a fact the query never lexically matched.
        return [
            (self.cards[i], float(scored[i]))
            for i in order
            if scored[i] > 0 and sims[i] >= min_score
        ]


# --------------------------------------------------------------------------- #
# Answer composition
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT = textwrap.dedent("""
    You are FinSight, an executive cloud-intelligence assistant for the
    enterprise's Cloud Operations leadership. You answer questions about cloud
    capacity, cost, and anomalies for an Enterprise CX SaaS estate (167 AWS
    deployments, ~$5M annual spend, products Engage / Analyze / Assist).

    STRICT GROUNDING RULES:
    - Use ONLY the facts provided in the <facts> block to support any claim.
    - NEVER invent, estimate, or round numbers that are not in the facts.
    - Every quantitative claim must cite the fact id it came from, like [FACT-007].
    - If the facts do not contain the answer, say so plainly and suggest what
      Capacity-Mngt-App or Cost-Mngt-App query would surface it.
    - Write for a busy executive: lead with the answer, 3-6 sentences, decisive.
    - When a capacity status is CRITICAL or a large anomaly exists, state the
      recommended action.
""").strip()


@dataclass
class RAGAnswer:
    question: str
    answer: str
    citations: list[str]
    evidence: list[FactCard]
    used_llm: bool

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "citations": self.citations,
            "used_llm": self.used_llm,
            "evidence": [
                {"id": c.id, "source": c.source, "text": c.text} for c in self.evidence
            ],
        }


class FinSightRAG:
    """End-to-end retrieval + grounded composition."""

    def __init__(
        self,
        cost_df: Optional[pd.DataFrame] = None,
        util_df: Optional[pd.DataFrame] = None,
        cards: Optional[list[FactCard]] = None,
        model: str = "claude-sonnet-4-6",
    ):
        if cards is None:
            if cost_df is None or util_df is None:
                raise ValueError("Provide either cards or (cost_df, util_df).")
            cards = build_corpus(cost_df, util_df)
        self.cards = cards
        self.retriever = Retriever(cards)
        self.model = model

    # ---- public API ------------------------------------------------------- #

    def ask(self, question: str, k: int = 6) -> RAGAnswer:
        hits = self.retriever.search(question, k=k)
        evidence = [c for c, _ in hits]

        answer_text, used_llm = self._compose(question, evidence)
        citations = sorted(set(re.findall(r"FACT-\d{3}", answer_text)))
        return RAGAnswer(
            question=question,
            answer=answer_text,
            citations=citations,
            evidence=evidence,
            used_llm=used_llm,
        )

    # ---- composition ------------------------------------------------------ #

    def _facts_block(self, evidence: list[FactCard]) -> str:
        return "\n".join(f"[{c.id}] ({c.source}) {c.text}" for c in evidence)

    def _compose(self, question: str, evidence: list[FactCard]) -> tuple[str, bool]:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key and evidence:
            try:
                return self._compose_llm(question, evidence, api_key), True
            except Exception as exc:  # noqa: BLE001 — fall back, never crash the cockpit
                fallback = self._compose_template(question, evidence)
                return f"{fallback}\n\n(Note: LLM composition unavailable: {exc})", False
        return self._compose_template(question, evidence), False

    def _compose_llm(self, question: str, evidence: list[FactCard], api_key: str) -> str:
        import anthropic  # imported lazily so the repo runs without the SDK

        client = anthropic.Anthropic(api_key=api_key)
        user_msg = (
            f"<facts>\n{self._facts_block(evidence)}\n</facts>\n\n"
            f"Executive question: {question}"
        )
        resp = client.messages.create(
            model=self.model,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        return "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        ).strip()

    def _compose_template(self, question: str, evidence: list[FactCard]) -> str:
        """
        Deterministic, no-API answer: surface the strongest evidence and
        the recommended action, with citations. Always runnable.
        """
        if not evidence:
            return (
                "I don't have a grounded fact that answers that. Try asking about "
                "estate spend, a product/region's capacity headroom, or recent cost "
                "anomalies — Capacity-Mngt-App and Cost-Mngt-App cover those."
            )

        # Prioritize CRITICAL capacity and large anomalies in the lead line.
        lead = None
        for c in evidence:
            if c.metadata.get("status") == "CRITICAL":
                lead = c
                break
        if lead is None:
            lead = evidence[0]

        parts = [f"{lead.text} [{lead.id}]"]
        for c in evidence[1:3]:
            parts.append(f"{c.text} [{c.id}]")

        # Append an action cue when warranted.
        action = ""
        if any(c.metadata.get("status") == "CRITICAL" for c in evidence):
            action = (" Recommended action: rightsize or scale the affected workload "
                      "now and re-baseline the headroom alert.")
        elif any("excess" in c.metadata for c in evidence):
            action = (" Recommended action: confirm the suspected root cause and apply "
                      "the corresponding guardrail (teardown, log-level, replica cleanup).")

        return " ".join(parts) + action


# --------------------------------------------------------------------------- #
# Demo
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from finsight import generate

    cost, util = generate()
    rag = FinSightRAG(cost, util)

    questions = [
        "Will we run out of capacity anywhere in the next quarter?",
        "Why did our cloud spend spike, and where?",
        "What is our annualized cloud spend and what's driving it?",
        "Is Assist in us-east-1 healthy?",
    ]
    for q in questions:
        ans = rag.ask(q)
        print("Q:", q)
        print("A:", ans.answer)
        print("Citations:", ", ".join(ans.citations) or "none",
              "| LLM:" , ans.used_llm)
        print("-" * 80)
