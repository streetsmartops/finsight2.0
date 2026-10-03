# FinSight 2.0 — Architecture

Four views, from outside to inside: **system context → containers → components → deployment**.
All diagrams are Mermaid and render natively on GitHub.

> One rule shapes everything below: **the deterministic engines own every number; the
> language model only phrases them.** Every box is there to enforce or exploit that.

---

## 1. System context

Who uses FinSight and what it depends on.

```mermaid
flowchart LR
    exec(["👔 CXO / PE investor<br/><i>asks in plain English</i>"])
    eng(["🛠️ SRE / FinOps engineer<br/><i>reads tables, calls API</i>"])
    bot(["🤖 Slack / Teams bot<br/><i>future channel</i>"])

    subgraph FS["FinSight 2.0"]
        core["Executive Cloud<br/>Intelligence Layer"]
    end

    data[("Cloud billing +<br/>utilization telemetry<br/><i>synthetic, seed=42</i>")]
    claude["Anthropic Claude API<br/><i>optional</i>"]

    exec -->|"browser · cockpit"| core
    eng -->|"REST · /api/*"| core
    bot -.->|"POST /api/ask"| core
    data -->|"generated in-process"| core
    core -.->|"facts in, prose out<br/>(only if ANTHROPIC_API_KEY set)"| claude
```

---

## 2. Containers

One Python process. Data and engines are built **once at startup** and cached in
`api.main.State`, so every request is read-only and fast.

```mermaid
flowchart TB
    browser["🖥️ Browser<br/><b>Executive Cockpit</b><br/>api/static/index.html<br/><i>vanilla JS + inline SVG chart</i>"]

    subgraph proc["Python process · uvicorn"]
        direction TB
        api["<b>FastAPI app</b> · api/main.py<br/>GET /api/health · /overview · /capacity<br/>/anomalies · /forecast/cost<br/>POST /api/ask"]
        state[("<b>State</b> (in-memory)<br/>cost_df · util_df<br/>32 FactCards · FinSightRAG")]
        pkg["<b>finsight</b> package · src/finsight/<br/>data_generator · capacity_mngt_app<br/>cost_mngt_app · knowledge_base · rag"]
        api --> state
        api --> pkg
        state -.built by.-> pkg
    end

    claude["Anthropic Messages API"]

    browser -->|"fetch JSON"| api
    pkg -.->|"rag._compose_llm()"| claude
```

---

## 3. Components

How the five modules depend on each other. Arrows point from producer to consumer.

```mermaid
flowchart LR
    subgraph data["Data layer"]
        gen["<b>data_generator.py</b><br/>generate(seed=42)<br/>3 products × 4 regions × 7 services<br/>180 days · 5 injected incidents<br/>Assist/us-east-1 capacity ramp"]
    end

    subgraph engines["Deterministic engines — own the numbers"]
        cap["<b>capacity_mngt_app.py</b><br/>Capacity-Mngt-App<br/>Ridge on trend + DoW + Fourier<br/>±1.96σ interval · 80% breach detect<br/>status: CRITICAL/WARNING/WATCH/HEALTHY"]
        cost["<b>cost_mngt_app.py</b><br/>Cost-Mngt-App<br/>rolling median + MAD robust z ≥ 4<br/>+ per-day period attribution"]
    end

    subgraph rag["Grounding + conversation — phrases the numbers"]
        kb["<b>knowledge_base.py</b><br/>build_corpus() → FactCard[]<br/>id · text · source · metadata"]
        ret["<b>rag.Retriever</b><br/>TF-IDF (1–2 grams, stopwords)<br/>relevance floor 0.04<br/>+ dimension & risk boosts"]
        comp["<b>rag.FinSightRAG</b><br/>Claude w/ strict grounding prompt<br/>↳ deterministic template fallback"]
    end

    gen -->|"cost_df"| cap
    gen -->|"util_df"| cap
    gen -->|"cost_df"| cost
    gen -->|"annualized_spend"| kb
    cap -->|"Forecast objects"| kb
    cost -->|"anomalies + attribution"| kb
    kb -->|"FactCards"| ret
    ret -->|"top-k evidence"| comp

    api["api/main.py"]:::ext
    cap --> api
    cost --> api
    comp --> api
    classDef ext fill:#1f2937,stroke:#35E0A1,color:#E8EEF5
```

### Design decisions at a glance

| Decision | Choice | Why (and what it rules out) |
|---|---|---|
| Forecaster | Ridge regression on engineered temporal features | ~180 points: interpretable, reproducible, honest residual-based interval. An LSTM would overfit and be unexplainable to finance. |
| Anomaly detector | Rolling median + MAD robust z-score | The baseline is not poisoned by the spike it is hunting; every flag is explainable. No labels needed. |
| What RAG indexes | **Derived facts**, not raw billing rows | 32 cards vs ~15k rows: retrieval stays relevant and every citable number was computed by an engine. |
| Retriever | Local TF-IDF + relevance floor | No vector-DB service to run; an off-domain query scores below the floor → empty evidence → honest decline. |
| Composer | Claude with a strict grounding prompt; template fallback | Fluent when a key is present; still works fully offline; never crashes the cockpit. |
| State | Built once at startup, in memory | Deterministic seed → identical numbers across notebook, API, tests and the demo video. |

---

## 4. Deployment options

The same image runs everywhere; `$PORT` is honoured so PaaS platforms need no changes.

```mermaid
flowchart TB
    subgraph local["Laptop — live demo"]
        l1["./demo/demo.sh<br/>.venv + pytest + uvicorn :8000<br/>+ smoke_test.sh"]
    end
    subgraph docker["Any Docker host"]
        d1["docker compose up --build<br/>python:3.11-slim · non-root<br/>HEALTHCHECK /api/health"]
    end
    subgraph cloud["Shareable URL"]
        c1["Render<br/>render.yaml"]
        c2["Fly.io<br/>fly.toml"]
        c3["Cloud Run / any VM<br/>docker run -e PORT"]
    end
    img[["finsight:demo image<br/>Dockerfile"]]
    img --> d1
    img --> c1
    img --> c2
    img --> c3
    key{{"ANTHROPIC_API_KEY?"}}
    key -->|"unset → template mode<br/>(offline-safe)"| l1
    key -->|"set → Claude composes"| d1
```

See [`demo/deploy/README.md`](../../demo/deploy/README.md) for the exact commands.
