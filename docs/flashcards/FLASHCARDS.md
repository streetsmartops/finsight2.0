# FinSight 2.0 flashcards

Three decks, one per audience. Click a question to reveal the answer.
Import `finsight_anki.csv` into Anki or Quizlet (semicolon-separated: front;back;tags).
For a flip-card study mode, open [`docs/interactive/flashcards.html`](../interactive/flashcards.html).

- [Executive (CXO)](#exec) · 12 cards · What it does, why it's trustworthy, what to do with it.
- [Investor (PE / VC)](#investor) · 10 cards · Value, moat, risk, and how it scales.
- [Engineer](#engineer) · 16 cards · Algorithms, internals, knobs, and tests.

<a id="exec"></a>
## Executive (CXO)

_What it does, why it's trustworthy, what to do with it._

<details><summary><b>1. What is FinSight in one sentence?</b></summary>

An executive cloud-intelligence layer: ask your cloud estate a question in plain English and get a grounded answer, where every number traces back to the engine that computed it.

</details>

<details><summary><b>2. Which two questions does FinSight answer?</b></summary>

Forward: *Will we run out of headroom, and what will it cost?* (Capacity-Mngt-App). Backward: *Where did the money go, and is it a problem?* (Cost-Mngt-App).

</details>

<details><summary><b>3. What is the grounding contract?</b></summary>

The deterministic engines own every number; the language model only phrases them. Answers may cite only engine-computed facts, and an off-domain question is declined.

</details>

<details><summary><b>4. What does a [FACT-012] chip mean?</b></summary>

A citation. It points to a specific fact card in the evidence panel, produced by a named engine. You can audit any sentence.

</details>

<details><summary><b>5. What does CRITICAL mean in the capacity table?</b></summary>

The stream's 7-day average utilization is already at or above the 80% headroom threshold. Act now: scale or rightsize, then re-baseline the alert.

</details>

<details><summary><b>6. WARNING vs WATCH vs HEALTHY?</b></summary>

WARNING: forecast crosses 80% within 30 days. WATCH: crosses in 31–45 days. HEALTHY: no breach in the 45-day horizon.

</details>

<details><summary><b>7. What's the headline in the demo estate?</b></summary>

~$4.97M annualized across 167 deployments; 51 cost anomalies ($4,734 excess); Assist in us-east-1 is CRITICAL at ~82% utilization.

</details>

<details><summary><b>8. What happens if I ask something unrelated?</b></summary>

FinSight declines: 'I don't have a grounded fact that answers that.' No evidence means no answer, so it never bluffs.

</details>

<details><summary><b>9. Do I need the LLM for FinSight to work?</b></summary>

No. Without an API key a deterministic template composes the answer from the same facts. The LLM adds fluency, not numbers.

</details>

<details><summary><b>10. How do I phrase a good question?</b></summary>

Name the intent and the dimension: 'Is Assist in us-east-1 healthy?', 'What happened with RDS in eu-west-1?'. Use exact product, region and service names.

</details>

<details><summary><b>11. What decision does the anomaly feed drive?</b></summary>

Confirm the suspected root cause and apply the guardrail: tear down the load test, fix the log level, or delete the orphaned replica.

</details>

<details><summary><b>12. Why should finance trust it more than a chatbot?</b></summary>

Because it can't invent numbers: retrieval only indexes engine outputs, a relevance floor blocks off-topic answers, and tests enforce that every citation exists.

</details>


<a id="investor"></a>
## Investor (PE / VC)

_Value, moat, risk, and how it scales._

<details><summary><b>1. What problem is worth paying for here?</b></summary>

Cloud spend is a top-3 cost line for SaaS. Executives can't get fast, trustworthy answers about capacity risk and bill movements without analyst time. FinSight turns hours into seconds.

</details>

<details><summary><b>2. Who is the buyer?</b></summary>

CIO, CTO or VP Cloud Ops, and the CFO's FinOps function at cloud-heavy SaaS companies. PE operating partners also use it for portfolio-wide cost diligence.

</details>

<details><summary><b>3. What's the defensible idea (moat)?</b></summary>

Grounded AI: numbers come from auditable models, and the LLM is only the interface. That trust property is what lets an AI assistant sit in front of finance and boards.

</details>

<details><summary><b>4. What is the key AI risk, and how is it controlled?</b></summary>

Hallucinated figures. Controlled in three layers: index only derived facts, a retrieval relevance floor, and a prompt that forbids uncited numbers. The citation rule is tested.

</details>

<details><summary><b>5. Operational risk if the AI vendor is down?</b></summary>

Low. It automatically falls back to a deterministic template with identical numbers. Retrieval is local, with no vector-DB dependency.

</details>

<details><summary><b>6. How does value show up in the demo?</b></summary>

It flags $4,734 of above-baseline spend across 51 points. All 5 injected incidents (~$4.2k, 15 flags) are recovered with root causes, and one CRITICAL capacity stream is caught before customers feel it, all from one screen.

</details>

<details><summary><b>7. What would it take to go from demo to product?</b></summary>

Connect AWS CUR and CloudWatch (the frames already match), schedule corpus rebuilds, add SSO and multi-tenancy, then add Azure and GCP plus Slack and Teams channels.

</details>

<details><summary><b>8. Why is the tech stack cheap to run?</b></summary>

One Python process, ridge regression, robust statistics and TF-IDF. No GPUs, no vector DB. LLM calls are small (at most 6 short facts) and optional.

</details>

<details><summary><b>9. Natural expansion path?</b></summary>

Recommendations to automated guardrails (auto-teardown, rightsizing PRs), budget and commit planning, unit economics (cost per tenant), and a multi-cloud and portfolio view for PE.

</details>

<details><summary><b>10. What's the one-line pitch?</b></summary>

Ask your cloud estate anything: every number cited, nothing invented.

</details>


<a id="engineer"></a>
## Engineer

_Algorithms, internals, knobs, and tests._

<details><summary><b>1. Capacity-Mngt-App model and features?</b></summary>

Ridge regression (alpha 2 for capacity, 5 for cost) on linear trend, 7 day-of-week one-hots, and 2 weekly Fourier harmonics (sin and cos at period 7).

</details>

<details><summary><b>2. How is the prediction interval computed?</b></summary>

yhat ± 1.96 × the standard deviation of in-sample residuals (ddof=1), giving about a 95% band.

</details>

<details><summary><b>3. How is 'already breached' decided?</b></summary>

Trailing 7-day mean ≥ threshold. This avoids reacting to a single noisy point. Otherwise the first forecast day with yhat ≥ threshold is the breach date.

</details>

<details><summary><b>4. Cost-Mngt-App detector formula?</b></summary>

Per (product, region, service) stream: z = (x_i − median(prior 21d)) / (1.4826 × MAD). Flag if z ≥ 4. It needs at least 10 prior points, and falls back to std if MAD ≈ 0.

</details>

<details><summary><b>5. Are all 51 anomalies real incidents?</b></summary>

No. 15 flags (~$4.2k) map to the 5 injected incidents. The other 36 are small (~$512 in total) and have no cause attached, likely month-start billing bumps the detector doesn't model. Fixes: a min-$ excess filter, a day-of-month feature, or a higher z.

</details>

<details><summary><b>6. Why median + MAD instead of mean + std?</b></summary>

Robustness. The spike being hunted can't inflate its own baseline, and 1.4826 × MAD matches std for normal data.

</details>

<details><summary><b>7. How does attribution work?</b></summary>

Per-day normalised spend by dimension for period A and period B. delta = B − A, and pct_of_change = delta / total delta. Rows are sorted by |delta|, and the shares sum to 100%.

</details>

<details><summary><b>8. What does the RAG index, and how big is it?</b></summary>

32 FactCards built from engine outputs (5 estate, 13 capacity, 14 cost), not the 15,120 raw cost rows. Each card has id, text, source and metadata.

</details>

<details><summary><b>9. Retriever configuration?</b></summary>

TF-IDF with 1–2-grams, English stopwords, and the token pattern [A-Za-z0-9][A-Za-z0-9-]+, so 'us-east-1' and 'EKS-Compute' stay whole. Cosine similarity, k=6.

</details>

<details><summary><b>10. What are the retrieval boosts?</b></summary>

+0.15 for each product, region or service named in the query. With risk intent: CRITICAL +0.30, WARNING +0.20, WATCH +0.10, anomaly cards +0.10.

</details>

<details><summary><b>11. How does the relevance floor work?</b></summary>

If the max raw cosine is below 0.04, return [] and the composer declines. Each returned card must also clear 0.04 on its own raw score, so boosts can't drag in unrelated facts.

</details>

<details><summary><b>12. How are citations extracted?</b></summary>

A regex FACT-\d{3} over the answer text. Tests assert the set is non-empty for in-domain questions and a subset of corpus ids.

</details>

<details><summary><b>13. When does LLM composition fall back?</b></summary>

When no API key is set, the evidence is empty, or any exception is raised (network, auth, model). The template leads with a CRITICAL card, adds 2 more and an action cue.

</details>

<details><summary><b>14. Why is everything reproducible?</b></summary>

generate(seed=42) uses numpy default_rng, and state is built once at startup. The notebook, API, tests and demo video show identical numbers.

</details>

<details><summary><b>15. How many tests, and which are the contract tests?</b></summary>

14. The contract tests are test_rag_answers_are_grounded and test_rag_declines_when_no_facts; test_rag_surfaces_critical_first_for_risk_queries covers ranking.

</details>

<details><summary><b>16. How do you swap in real data?</b></summary>

Return the same cost_df and util_df schemas from CUR/Athena and CloudWatch, then change api/main.py::_bootstrap. Nothing downstream changes.

</details>
