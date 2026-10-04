# FinSight 2.0 — How-to guide

Task-oriented instructions, grouped by who's doing the task. Each recipe is copy-pasteable and was run against this repo.

- **Using FinSight** (executives and investors): [ask a good question](#ask-a-good-question) · [read an answer](#read-an-answer) · [read the cockpit](#read-the-cockpit)
- **Running FinSight** (presenters and operators): [run it locally](#run-it-locally) · [run in Docker](#run-it-in-docker) · [turn on fluent LLM answers](#turn-on-fluent-llm-answers) · [deploy a shareable URL](#deploy-a-shareable-url) · [re-record the demo video](#re-record-the-demo-video)
- **Extending FinSight** (engineers): [call the API](#call-the-api) · [use it as a Python library](#use-it-as-a-python-library) · [tune the engines](#tune-the-engines) · [add a new fact card](#add-a-new-fact-card) · [plug in real AWS data](#plug-in-real-aws-data) · [add a test](#add-a-test)
- [Troubleshooting](#troubleshooting)

---

## Using FinSight

### Ask a good question
FinSight answers questions about **capacity headroom, spend and cost anomalies** for the estate (products **Engage, Analyze, Assist** and regions **us-east-1, us-west-2, eu-west-1, ap-southeast-1**).

| Intent | Works well | Why |
|---|---|---|
| Forward risk | *Will we run out of capacity next quarter?* | Words such as "run out", "risk" and "breach" trigger *risk intent*, which ranks CRITICAL and WARNING facts first. |
| Backward cause | *Why did our cloud spend spike, and where?* | "spike" and "anomaly" boost Cost-Mngt-App anomaly cards. |
| Drill-down | *What happened with RDS in eu-west-1?* | Naming a product, region or service adds +0.15 to exactly matching facts. |
| Health check | *Is Assist in us-east-1 healthy?* | Pulls capacity and cost facts for one stream. |
| Run-rate | *What's driving our annualized spend?* | Estate rollups, the forecast and attribution. |

Tips: use the exact names (`us-east-1`, not "Virginia"; `EKS-Compute`, not "Kubernetes").
If FinSight answers *"I don't have a grounded fact…"*, the question is outside what the engines computed. That's the system working as designed, not a failure.

### Read an answer
- **`FACT-012`** chips are citations. Each one maps to a line in *Evidence retrieved* below the answer.
- **Evidence** shows the source engine (`Capacity-Mngt-App`, `Cost-Mngt-App` or `Estate`) and the exact fact text.
- **Badge:** `LLM` means Claude phrased the answer. `template` means the deterministic composer did. The numbers are identical either way.
- **Recommended action** is appended when there's a CRITICAL capacity stream or an anomaly in the evidence.

### Read the cockpit
| Panel | What it tells you | Statuses and colours |
|---|---|---|
| KPI strip | Annualized run-rate · anomaly count and excess $ · capacity streams that are CRITICAL or WARNING · org footprint | red value means at least one CRITICAL |
| Capacity status | Top 8 product × region streams, worst first | **CRITICAL**: 7-day average ≥ 80% now. **WARNING**: breach within 30 days. **WATCH**: breach in 31–45 days. **HEALTHY**: no breach in 45 days |
| Cost anomalies | Top 6 spikes by excess $ (hover for the suspected cause) | `z` is the robust z-score; ≥ 4 is flagged |
| Spend forecast | Last 60 days (grey), next 45 days (green) with a 95% band | MAPE tag is the in-sample error |

---

## Running FinSight

### Run it locally
```bash
git clone https://github.com/streetsmartops/finsight2.0 && cd finsight2.0
./demo/demo.sh --offline        # venv → deps → 14 tests → server :8000 → smoke test
# open http://localhost:8000
./demo/demo.sh --stop           # when done
```
Prefer manual steps?
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
PYTHONPATH=src pytest tests -v
./run.sh                         # or: make run
```
`make help` lists every shortcut (`make demo`, `make test`, `make smoke` and so on).
Use `PORT=8010 ./demo/demo.sh` if port 8000 is taken.

### Run it in Docker
```bash
docker compose up --build                     # http://localhost:8000
FINSIGHT_PORT=8080 docker compose up --build  # different host port
./demo/demo.sh --docker                       # build + start + smoke test in one go
```

### Turn on fluent LLM answers
```bash
export ANTHROPIC_API_KEY=sk-ant-...
./demo/demo.sh                     # or: ANTHROPIC_API_KEY=... docker compose up
curl -s localhost:8000/api/health  # "llm_configured": true
```
The model is set in `FinSightRAG(model=...)` in `src/finsight/rag.py`.
If a call fails, FinSight falls back to the template and appends a note. The cockpit never errors.
Never commit the key: `.env` is already git-ignored.

### Deploy a shareable URL
See [`demo/deploy/README.md`](../demo/deploy/README.md) for Render, Fly.io, Cloud Run and VM recipes.
The API has no auth, so keep deployments to synthetic data or put them behind SSO.

### Re-record the demo video
```bash
./demo/demo.sh --offline
pip install playwright               # Chromium: /opt/pw-browsers or `playwright install chromium`
python demo/video/record_demo.py --publish
```
This writes `docs/media/finsight_demo.mp4`, a matching `.srt`, and `narration.md` with timestamps.
To change the story, edit the `SCENES` list in `demo/video/record_demo.py`. The video, subtitles and script are all generated from it.

---

## Extending FinSight

### Call the API
| Method | Path | Returns |
|---|---|---|
| GET | `/api/health` | `{status, llm_configured, facts_indexed}` |
| GET | `/api/overview` | annualized $, latest daily $, anomaly count and excess, capacity status counts |
| GET | `/api/capacity` | `rows[]`: product, region, current_util_pct, status, breach_date, breach_in_days (worst-first) |
| GET | `/api/anomalies` | top 15 `rows[]`: date, product, region, service, cost, baseline, excess, robust_z, suspected_cause |
| GET | `/api/forecast/cost` | last 60 days of `history[]`, 45 days of `forecast[]` (yhat, lower, upper), `mape_pct` |
| POST | `/api/ask` | body `{question}` → `{question, answer, citations[], used_llm, evidence[]}` |

```bash
curl -s -X POST localhost:8000/api/ask -H 'Content-Type: application/json' \
  -d '{"question":"Why did our cloud spend spike?"}' | python -m json.tool
```
Interactive OpenAPI docs are at `/docs` (they need internet access for the Swagger UI assets).

### Use it as a Python library
```python
import sys; sys.path.insert(0, "src")
from finsight import generate, forecast_capacity, CostMngtApp, FinSightRAG

cost, util = generate(seed=42)
print(forecast_capacity(util, "Assist", "us-east-1").summary())
print(CostMngtApp().detect(cost).head())
print(FinSightRAG(cost, util).ask("Is Assist in us-east-1 healthy?").answer)
```
Each module also runs on its own: `PYTHONPATH=src python -m finsight.rag` (or `.cost_mngt_app`, `.capacity_mngt_app`, `.knowledge_base`, `.data_generator`).

### Tune the engines
| Knob | Where | Default | Effect |
|---|---|---|---|
| Headroom threshold | `forecast_capacity(threshold_pct=)`, `build_corpus(capacity_threshold=)` | 80 | when a stream turns CRITICAL or WARNING |
| Forecast horizon | `forecast_capacity(horizon=)` | 45 | how far ahead breaches are looked for |
| Ridge strength | `CapacityMngtApp(alpha=)` | 2.0 (capacity), 5.0 (cost) | higher means a smoother trend |
| Interval width | `CapacityMngtApp(interval_z=)` | 1.96 | ≈95% band |
| Anomaly sensitivity | `CostMngtApp(z_threshold=)` | 4.0 | lower means more flags |
| Baseline window | `CostMngtApp(window=)` | 21 days | longer means a steadier baseline |
| Relevance floor | `Retriever.search(min_score=)` | 0.04 | higher means more declines |
| Evidence size | `FinSightRAG.ask(k=)` | 6 | how many facts reach the composer |

The API hard-codes some of these (`z_threshold=4.0`, `horizon=45`). Change them in `api/main.py` too, so the cockpit and the corpus stay consistent.

### Add a new fact card
Every new kind of answer starts as a card in `src/finsight/knowledge_base.py::build_corpus`:
```python
add(
    f"Reserved-instance coverage for {region} is {cov:.0f}%, below the 70% target.",
    "Cost-Mngt-App",            # source tag shown in the evidence panel
    region=region,              # metadata keys product/region/service get retrieval boosts
    status="WARNING",           # CRITICAL/WARNING/WATCH get risk-intent boosts
    coverage_pct=round(cov, 1),
)
```
Rules: compute the number in an engine, never in the card text. Keep one fact per card. Include the dimension names verbatim so TF-IDF can match them.

### Plug in real AWS data
Replace `generate()` with loaders that return the **same two frames**:
- `cost_df`: `date, product, tenancy, region, service, cost_usd, anomaly_cause` (from AWS CUR via Athena; map cost-allocation tags to `product`; `anomaly_cause` can be `NA`)
- `util_df`: `date, product, region, tenancy, utilization_pct` (from CloudWatch or Container Insights, as a daily mean)

Then swap the call in `api/main.py::_bootstrap`. The engines, corpus, RAG and cockpit need no changes.
Next steps after that: rebuild the corpus on a schedule, and remove the hard-coded `deployments: 167` and `team_size: 91` in `/api/overview`.

### Add a test
Tests live in `tests/test_finsight.py`, and the scenarios they prove are listed in [`docs/diagrams/BDD_FLOWS.md`](diagrams/BDD_FLOWS.md#traceability-scenario--proof).
Two known gaps are good first tests: the `Forecast.status` 30/31-day boundary, and the LLM → template fallback (monkeypatch `anthropic.Anthropic` to raise).
```bash
PYTHONPATH=src pytest tests -v -k grounded
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: finsight` | `src/` isn't on the path | `export PYTHONPATH=$PWD/src` (`demo.sh`, `run.sh` and the Makefile do this for you) |
| Cockpit shows "api offline" | server not running, or wrong port | `./demo/demo.sh --offline`, then check `.demo-server.log` |
| Answer says "LLM composition unavailable" | bad key, network or model name | check the key and `FinSightRAG(model=...)`; the template answer shown is still correct |
| Every question is declined | the question shares no words with any fact | use product, region or service names; or lower `min_score` (carefully) |
| `/docs` page is blank | Swagger assets come from a CDN | use the `curl` examples above, or allow internet access |
| `docker build` fails at `pip install` behind a corporate proxy | the build can't reach PyPI or doesn't trust the proxy CA | `docker build --network host --build-arg HTTPS_PROXY=$HTTPS_PROXY .` and install the proxy's CA in the image |
| Slow first load (~10 s) | engines run at startup | expected; the smoke test waits for it |
