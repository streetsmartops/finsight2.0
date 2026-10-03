# FinSight 2.0 demo — narration script

Timestamps match `finsight_demo.mp4`. Read at a calm pace; each line fits its scene.

| Time | On screen | Say |
|---|---|---|
| 00:01 | (title card) | FinSight 2.0 — the executive cloud intelligence layer. Ask your cloud estate a question in plain English and get a grounded, cited answer. |
| 00:11 | (title card) | Under the hood, two deterministic engines own every number. Capacity-Mngt-App forecasts utilisation and spend; Cost-Mngt-App detects anomalies and attributes cost. Their outputs become fact cards, and the RAG layer can only cite those facts. |
| 00:25 | The executive cockpit: one screen, three engines' worth of signal. | This is the cockpit. It's one FastAPI service with a static page — everything you see is computed live from a deterministic, seeded dataset of 167 AWS deployments. |
| 00:37 | KPI strip: ~$4.97M annualized spend · 51 anomalies · 1 CRITICAL capacity stream | The KPI strip answers the first question any executive asks: what's the run-rate, is anything on fire? About five million dollars annualised, fifty-one cost anomalies, and one critical capacity alert. |
| 00:50 | Capacity-Mngt-App: worst-first. Assist / us-east-1 is already over the 80% headroom line. | Capacity-Mngt-App ranks every product-region stream worst-first. Assist in us-east-1 is already above the eighty percent headroom threshold — status CRITICAL. |
| 00:59 | Cost-Mngt-App: spikes scored by robust z (median + MAD) — hover a row for the root cause. | Cost-Mngt-App scores each region-service stream against its own rolling median and MAD baseline, so a spike can't poison the baseline it's measured against. Each row carries a suspected root cause. |
| 01:11 | 45-day spend forecast with a 95% prediction interval — in-sample MAPE ≈ 1.2%. | And the forward view: a forty-five-day estate spend forecast with an honest prediction band. In-sample error is about one point two percent. |
| 01:21 | Now the point of FinSight: just ask. | But dashboards make executives hunt. FinSight lets them just ask. |
| 01:26 | Q1 — forward risk. Answer leads with the CRITICAL stream and cites [FACT-012]. | Will we run out of capacity next quarter? The retriever boosts facts with an elevated status, so the answer leads with the critical stream, cites FACT-012, and recommends an action. Underneath, you see the exact evidence it retrieved. |
| 01:42 | Q2 — backward look. Spike, baseline, z-score and suspected cause — all cited. | Why did spend spike, and where? Now the evidence is Cost-Mngt-App anomaly cards: the dollar spike, its baseline, the robust z-score and the suspected root cause. |
| 01:53 | Q3 — drill-down. Naming a region + service boosts exact-match facts. | Executives drill down naturally. Name a service and region, and the retriever boosts the facts that match those dimensions exactly — here, the orphaned RDS read-replica in eu-west-1. |
| 02:05 | Q4 — a health check on one stream: capacity and cost evidence together. | Is Assist in us-east-1 healthy? One question pulls capacity and cost facts together for the same stream — the kind of synthesis that takes an analyst an hour. |
| 02:17 | Q5 — off-domain. No evidence, no answer. FinSight declines instead of hallucinating. | And the guarantee that matters to finance: ask something outside the domain and FinSight declines. A relevance floor in the retriever means no evidence, no answer — it never dresses up irrelevant facts. |
| 02:31 | (title card) | Everything here is also an API. The same grounded answers, citations and evidence are one POST away, so FinSight can sit behind Slack, Teams, or an agent. |
| 02:43 | (title card) | FinSight 2.0: deterministic engines own the numbers, the language model only phrases them. Runs offline in template mode, or fluent with Claude — one command to demo. |
