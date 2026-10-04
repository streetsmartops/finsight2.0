# FinSight 2.0 — BDD Flows

Behaviour is specified in Gherkin under [`docs/bdd/`](../bdd/). This page draws each
feature as a **Given → When → Then** decision flow, then traces every scenario to the test that proves it.

| Feature file | Business question |
|---|---|
| [`01_capacity_forecasting.feature`](../bdd/01_capacity_forecasting.feature) | *Will we run out of headroom?* |
| [`02_cost_anomalies.feature`](../bdd/02_cost_anomalies.feature) | *Where did the money go?* |
| [`03_grounded_rag.feature`](../bdd/03_grounded_rag.feature) | *Can I trust the answer?* |
| [`04_cockpit_and_demo.feature`](../bdd/04_cockpit_and_demo.feature) | *Will the demo work on stage?* |

---

## Flow 1 — Capacity status decision

```mermaid
flowchart TD
    G1["GIVEN product × region utilization history<br/>AND threshold = 80%"]
    W1["WHEN Capacity-Mngt-App fits ridge<br/>(trend + DoW + Fourier) and forecasts 45 days"]
    D1{"7-day trailing<br/>avg ≥ 80%?"}
    D2{"Forecast yhat<br/>crosses 80%?"}
    D3{"breach_in_days<br/>≤ 30?"}
    T1["THEN status = CRITICAL<br/>'act now'"]:::crit
    T2["THEN status = WARNING<br/>breach date reported"]:::warn
    T3["THEN status = WATCH<br/>breach date reported"]:::watch
    T4["THEN status = HEALTHY"]:::ok
    G1 --> W1 --> D1
    D1 -- yes --> T1
    D1 -- no --> D2
    D2 -- no --> T4
    D2 -- yes --> D3
    D3 -- yes --> T2
    D3 -- no --> T3
    classDef crit fill:#4a1520,stroke:#ff5c7a,color:#fff
    classDef warn fill:#4a3a10,stroke:#f5b942,color:#fff
    classDef watch fill:#1d3350,stroke:#6aa8ff,color:#fff
    classDef ok fill:#0f3b2c,stroke:#35E0A1,color:#fff
```

## Flow 2 — Anomaly detection per point

```mermaid
flowchart TD
    G["GIVEN a product × region × service cost stream"]
    W["WHEN scoring day i"]
    D0{"≥ 10 prior days<br/>in the 21-day window?"}
    S["skip (warm-up)"]
    B["baseline = median(prior window)<br/>scale = 1.4826 × MAD<br/>(std if MAD ≈ 0)"]
    Z["z = (cost_i − median) / scale"]
    D1{"z ≥ 4.0?"}
    T1["THEN flag Anomaly<br/>cost · baseline · excess_usd · z · suspected cause"]:::crit
    T2["THEN normal"]:::ok
    R["Rank all flags by excess_usd ↓<br/>→ /api/anomalies · FactCards"]
    G --> W --> D0
    D0 -- no --> S
    D0 -- yes --> B --> Z --> D1
    D1 -- yes --> T1 --> R
    D1 -- no --> T2
    classDef crit fill:#4a1520,stroke:#ff5c7a,color:#fff
    classDef ok fill:#0f3b2c,stroke:#35E0A1,color:#fff
```

## Flow 3 — Grounded answer (the contract)

```mermaid
flowchart TD
    G["GIVEN 32 fact cards from the engines"]
    W["WHEN an executive asks a question"]
    V["TF-IDF cosine vs every card"]
    D0{"max raw similarity<br/>≥ 0.04?"}
    DEC["THEN decline:<br/>'I don't have a grounded fact…'<br/>evidence = [] · citations = []"]:::crit
    BO["Apply boosts<br/>+0.15 per named product/region/service<br/>risk intent → CRITICAL +.30 · WARNING +.20 · WATCH +.10 · anomaly +.10"]
    K["Keep top-6 whose own raw sim ≥ 0.04"]
    D1{"ANTHROPIC_API_KEY<br/>set?"}
    L["Claude composes<br/>ONLY from &lt;facts&gt;, must cite [FACT-xxx]"]
    D2{"call<br/>succeeded?"}
    TP["Template: CRITICAL card first<br/>+ 2 more + action cue"]
    OUT["THEN answer + citations (regex) + evidence<br/>every cited id ∈ corpus"]:::ok
    G --> W --> V --> D0
    D0 -- no --> DEC
    D0 -- yes --> BO --> K --> D1
    D1 -- yes --> L --> D2
    D2 -- yes --> OUT
    D2 -- no --> TP
    D1 -- no --> TP --> OUT
    classDef crit fill:#4a1520,stroke:#ff5c7a,color:#fff
    classDef ok fill:#0f3b2c,stroke:#35E0A1,color:#fff
```

## Flow 4 — Presenter's demo path

```mermaid
flowchart LR
    A["GIVEN a clean clone"] --> B["WHEN ./demo/demo.sh --offline"]
    B --> C["venv + deps"] --> D{"14 tests<br/>pass?"}
    D -- no --> X["stop — fix before stage"]:::crit
    D -- yes --> E["uvicorn :8000"] --> F{"smoke_test<br/>all ✓?"}
    F -- no --> X
    F -- yes --> G["THEN cockpit opens<br/>follow PRESENTER_GUIDE.md"]:::ok
    classDef crit fill:#4a1520,stroke:#ff5c7a,color:#fff
    classDef ok fill:#0f3b2c,stroke:#35E0A1,color:#fff
```

---

## Traceability: scenario → proof

| Scenario | Proven by | Type |
|---|---|---|
| CRITICAL stream is flagged | `test_capacity_app_flags_critical_capacity` | unit |
| HEALTHY stream is HEALTHY | `test_capacity_app_reports_healthy_where_expected` | unit |
| Forecast accuracy (MAPE < 8%) | `test_capacity_app_forecast_is_accurate` | unit |
| Interval brackets forecast | `test_cost_forecast_has_interval` | unit |
| Status from days-to-breach (Outline) | `Forecast.status` logic, no dedicated test | **gap** |
| All 5 incidents recovered | `test_cost_app_catches_injected_anomalies` | unit |
| Attribution sums to 100% | `test_cost_app_attribution_sums_to_total` | unit |
| CRITICAL first for risk questions | `test_rag_surfaces_critical_first_for_risk_queries` | unit |
| Every citation is in the corpus | `test_rag_answers_are_grounded` | unit (contract) |
| Off-domain is declined | `test_rag_declines_when_no_facts` | unit (contract) |
| LLM failure → template fallback | `FinSightRAG._compose` try/except, no dedicated test | **gap** |
| Dimension boost (RDS / eu-west-1) | covered by the demo video, Q3 | manual |
| One-command demo, panels, contract pre-flight | `demo/smoke_test.sh` | smoke |
| Container non-root + healthcheck + `$PORT` | verified while building this demo | manual |

**Suggested next tests** (both are small): a parametrised test of `Forecast.status` covering the 30/31-day boundary, and an LLM-fallback test that sets a dummy key and monkeypatches `anthropic.Anthropic` to raise.
