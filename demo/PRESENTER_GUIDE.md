# FinSight 2.0 — Presenter guide (live demo)

**Run time:** 8 minutes (short) or 15 minutes (with Q&A).
**Backup:** [`docs/media/finsight_demo.mp4`](../docs/media/finsight_demo.mp4), a 3½-minute recording of this same flow with captions and a voice-over. It can play unattended.

---

## T-minus 10 minutes: pre-flight

```bash
./demo/demo.sh --offline      # safest: no network or key needed
# or, for fluent answers:
export ANTHROPIC_API_KEY=sk-... && ./demo/demo.sh
```
Every smoke-test line must show ✓. Then:
- [ ] Browser at `http://localhost:8000`, zoom at 110–125% for the room, dark mode
- [ ] Header reads **"operational · 32 facts indexed"**
- [ ] Ask-box badge shows **LLM grounded** or **template mode**, whichever you intended
- [ ] Do notifications, Wi-Fi drop: the demo is fully local in `--offline` mode
- [ ] The backup video is open in another tab

If anything fails, run `./demo/demo.sh --stop`, then `./demo/demo.sh --offline`. If it still fails, play the video.

---

## The run of show

| # | Show | Say (the one-liner) | Expected on screen |
|---|---|---|---|
| 1 | Header + KPI strip | "One screen: run-rate, anomalies, capacity alerts." | **$4.97M** · **51** anomalies ($4,734 excess) · **1** capacity alert · 91 · 167 |
| 2 | Capacity table | "Worst-first. One stream is already over the 80% line." | **Assist / us-east-1 · 81.6% · CRITICAL · now** |
| 3 | Anomaly feed (hover a row) | "Each spike is scored against its own robust baseline, with a suspected cause." | top row **06-22 EKS-Compute us-east-1 +$562** |
| 4 | Forecast chart | "45 days forward, with an honest uncertainty band." | tag shows **MAPE 1.2%** |
| 5 | Ask chip: *Will we run out of capacity next quarter?* | "No hunting. Just ask." | cites **FACT-012**, plus the recommended action |
| 6 | Ask chip: *Why did our cloud spend spike, and where?* | "Backward-looking, same contract." | Observability us-west-2 debug-log spike, **FACT-029** |
| 7 | Type: *What happened with RDS in eu-west-1?* | "Name a dimension and the retriever narrows." | orphaned read-replica, **FACT-025/026/028** |
| 8 | Ask chip: *Is Assist in us-east-1 healthy?* | "Capacity and cost evidence in one answer." | **FACT-012, 020, 024** |
| 9 | Type: *Who won the cricket world cup?* | "And this is why finance can trust it." | **declines**, with empty evidence |
| 10 | Terminal: the curl below | "Same answer over a REST API, so Slack, Teams or an agent can use it." | JSON with `citations` |

```bash
curl -s -X POST localhost:8000/api/ask -H 'Content-Type: application/json' \
  -d '{"question":"Is Assist in us-east-1 healthy?"}' | python -m json.tool
```

**Close:** "The deterministic engines own every number. The language model only phrases them, and every claim is cited. If there's no evidence, there's no answer."

---

## Audience variants

| Audience | Lean into | Skip |
|---|---|---|
| **CXO** | Steps 1, 2, 5, 9. Frame it as "decisions in seconds, not analyst-hours". | Algorithms |
| **PE / investor** | Steps 1, 5, 9, then the grounding contract as a *risk control* and the TAM (any cloud-spend estate). | Container details |
| **Engineers** | Steps 3, 7, 9, 10, then open `src/finsight/rag.py` (the relevance floor and boosts) and `pytest -v`. | KPI narrative |

## Likely questions

| Question | Answer |
|---|---|
| *Is this real data?* | No. It's synthetic and deterministic (seed 42), modelled on a 167-deployment, ~$5M estate. The engines are data-agnostic; you'd swap in AWS CUR and CloudWatch exports. |
| *Why not an LSTM or a vector DB?* | About 180 points per series: ridge is more accurate *and* explainable. 32 derived facts don't need a vector DB, and TF-IDF gives us a clean relevance floor. |
| *What stops hallucination?* | Three things: (1) only engine-derived facts are indexed, (2) a relevance floor returns no evidence for off-domain questions, (3) the system prompt forbids numbers outside the facts and requires a `[FACT-xxx]` on each one. Tests enforce (2) and the citation rule. |
| *What if Claude is down?* | It falls back to the deterministic template automatically. The cockpit never errors. |
| *How would it scale?* | Swap the generator for CUR/Athena, run the engines on a schedule, persist the cards, and move to embeddings and a vector store when the corpus reaches thousands of cards. The contract stays the same. |

## If something goes wrong live

| Symptom | Fix |
|---|---|
| Header says "api offline" | `./demo/demo.sh --stop && ./demo/demo.sh --offline` |
| Port 8000 in use | `PORT=8010 ./demo/demo.sh --offline` |
| LLM answer is slow or errors | Restart with `--offline`. Template answers are instant and identical in substance. |
| Wi-Fi is gone | Already fine in `--offline` mode. Docker mode needs the image built beforehand. |
| Nothing works | Play `docs/media/finsight_demo.mp4`. |
