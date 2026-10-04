# FinSight 2.0 — Data Flow

How a number gets from raw telemetry to a cited sentence in front of an executive.
Diagrams go from coarse to fine: **DFD level 0 → level 1 → the `/api/ask` pipeline → fact-card lineage**.

Figures quoted are what the default dataset (`seed=42`) produces.

---

## Level 0 — context DFD

```mermaid
flowchart LR
    U["Executive / Engineer"]
    P(("FinSight"))
    L["Claude API (optional)"]
    U -- "question" --> P
    P -- "cited answer + evidence" --> U
    P -- "KPIs, tables, forecast" --> U
    P -. "≤6 fact cards + question" .-> L
    L -. "phrased answer w/ [FACT-xxx]" .-> P
```

---

## Level 1 — processes and data stores

Numbered circles are processes, cylinders are in-memory stores.

```mermaid
flowchart TB
    G(("1 · Generate<br/>data_generator"))
    C[("D1 · cost_df<br/>15,120 rows<br/>date·product·region·service·cost_usd·anomaly_cause")]
    U[("D2 · util_df<br/>2,160 rows<br/>date·product·region·utilization_pct")]

    F(("2 · Forecast<br/>Capacity-Mngt-App"))
    A(("3 · Detect + attribute<br/>Cost-Mngt-App"))
    K(("4 · Build corpus<br/>knowledge_base"))
    KB[("D3 · FactCards<br/>32 cards")]
    R(("5 · Retrieve<br/>TF-IDF + boosts"))
    M(("6 · Compose<br/>Claude | template"))
    API(("7 · Serve<br/>FastAPI"))

    G --> C & U
    U -- "12 product×region series" --> F
    C -- "estate daily spend" --> F
    C -- "84 region×service×product streams" --> A
    C -- "annualized spend, shares" --> K
    F -- "status, breach date, MAPE" --> K
    A -- "51 anomalies, top driver" --> K
    K --> KB
    KB --> R
    R -- "top-k ≤ 6" --> M
    M -- "answer, citations, evidence" --> API
    F -- "/api/capacity · /api/forecast/cost" --> API
    A -- "/api/anomalies · /api/overview" --> API
```

| Store | Built | Lifetime | Size (seed 42) |
|---|---|---|---|
| D1 `cost_df` | `generate()` at startup | process | 3 products × 4 regions × 7 services × 180 days = **15,120** rows |
| D2 `util_df` | `generate()` at startup | process | 3 × 4 × 180 = **2,160** rows |
| D3 FactCards | `build_corpus()` at startup | process | **32** cards (5 estate · 13 capacity · 13 anomaly · 1 attribution) |

---

## The `/api/ask` pipeline (sequence)

```mermaid
sequenceDiagram
    autonumber
    actor E as Executive
    participant UI as Cockpit (index.html)
    participant API as FastAPI /api/ask
    participant RAG as FinSightRAG
    participant RET as Retriever
    participant LLM as Claude API
    E->>UI: types "Will we run out of capacity next quarter?"
    UI->>API: POST {question}
    API->>RAG: ask(question, k=6)
    RAG->>RET: search(question)
    RET->>RET: TF-IDF cosine vs 32 cards
    alt max raw similarity < 0.04 (off-domain)
        RET-->>RAG: [] (no evidence)
        RAG-->>API: decline message, citations=[]
    else in-domain
        RET->>RET: + 0.15 per named product/region/service<br/>+ status boost if risk intent (CRITICAL .30 · WARNING .20 · WATCH .10)<br/>+ 0.10 anomaly cards on risk intent
        RET-->>RAG: top-k cards (each with raw sim ≥ floor)
        alt ANTHROPIC_API_KEY set
            RAG->>LLM: system=grounding rules, user=<facts>…</facts> + question
            LLM-->>RAG: answer citing [FACT-xxx]
            Note over RAG,LLM: any exception → template fallback,<br/>cockpit never errors
        else no key
            RAG->>RAG: template: CRITICAL card first, +2 cards, + action cue
        end
        RAG->>RAG: citations = regex FACT-\d{3} over answer
        RAG-->>API: RAGAnswer
    end
    API-->>UI: {answer, citations, evidence, used_llm}
    UI-->>E: answer with highlighted citations + evidence panel
```

---

## Fact-card lineage

Every citable number comes from exactly one engine computation.

```mermaid
flowchart LR
    subgraph sources["Engine outputs"]
        s1["annualized_spend()<br/>groupby product / region"]
        s2["forecast_cost(h=45)"]
        s3["forecast_capacity() × 12<br/>threshold 80%"]
        s4["CostMngtApp.detect()<br/>z ≥ 4.0"]
        s5["CostMngtApp.attribute()<br/>last 14d vs prior 14d"]
    end
    subgraph cards["FactCards (source tag)"]
        f0["FACT-000…004 · Estate<br/>run-rate, product & region shares"]
        f5["FACT-005 · Capacity-Mngt-App<br/>spend projection + MAPE"]
        f6["FACT-006…017 · Capacity-Mngt-App<br/>per stream: HEALTHY / breach date / CRITICAL"]
        f18["FACT-018 · Cost-Mngt-App<br/>anomaly count + total excess"]
        f19["FACT-019…030 · Cost-Mngt-App<br/>top-12 anomalies w/ cause"]
        f31["FACT-031 · Cost-Mngt-App<br/>top spend driver"]
    end
    s1 --> f0
    s2 --> f5
    s3 --> f6
    s4 --> f18 & f19
    s5 --> f31
```

Each card also carries `metadata` (e.g. `status`, `product`, `region`, `excess_usd`).
The retriever reads metadata to apply boosts. The template composer reads it to pick the lead fact and the action cue.

---

## Cockpit refresh flow

On page load the cockpit fans out five independent calls. A failure in one panel never blanks another.

```mermaid
flowchart LR
    boot["boot()"] --> h["/api/health<br/>→ status + LLM badge"]
    boot --> o["/api/overview<br/>→ KPI strip"]
    boot --> c["/api/capacity<br/>→ worst-first table"]
    boot --> a["/api/anomalies<br/>→ top-6 feed"]
    boot --> f["/api/forecast/cost<br/>→ SVG chart + MAPE"]
    q["Ask box / chip / Enter"] --> ask["POST /api/ask<br/>→ answer card"]
```
