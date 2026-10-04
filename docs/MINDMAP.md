# FinSight 2.0 — Ideation mind map

Use this as a workshop canvas. The centre and first ring describe **what exists today**. The outer branches are **ideas**, each tagged with a horizon:
`· now` small, could ship this sprint · `· next` a quarter · `· later` strategic.

An interactive version (collapsible, filterable by horizon, with an outline view for phones) is at [`docs/interactive/mindmap.html`](interactive/mindmap.html). Open it locally in any browser.
Regenerate it after editing this file with `python docs/interactive/build.py`.

```mermaid
mindmap
  root((FinSight 2.0<br/>grounded cloud intelligence))
    Today
      Capacity-Mngt-App
        Ridge + temporal features
        95% interval
        80% breach → CRITICAL/WARNING/WATCH
      Cost-Mngt-App
        Median + MAD robust z ≥ 4
        Period attribution
      RAG layer
        32 fact cards
        TF-IDF + relevance floor
        Claude or template
      Cockpit + REST API
      Demo kit
        demo.sh · Docker · smoke test
        Captioned video
    Data sources
      AWS CUR via Athena · next
      CloudWatch / Container Insights · next
      Azure Cost Mgmt + GCP Billing export · later
      Kubecost per-namespace cost · next
      Datadog usage API · next
      Commitments: RI / Savings Plans coverage · next
    Engine ideas
      Capacity
        Per-service capacity, not just EKS · now
        Scenario: what if traffic +20% · next
        Prophet / holiday effects behind same interface · next
        Lead-time aware alerts: procurement days · later
      Cost
        Min $ filter, cut 36 low-value flags · now
        Day-of-month feature for billing bumps · now
        Unit economics: cost per tenant / per call · next
        Commit planning: optimal SP purchase · later
        Feedback loop: label flags real/noise → supervised · later
    RAG + conversation
      Multi-turn memory: follow-ups · next
      Embeddings + hybrid search when cards exceed ~1k · next
      Time-aware facts: as-of dates, freshness · now
      Answer confidence from retrieval score · now
      Eval harness: golden Q→fact set, CI gate · now
      Tool-use: LLM calls engines for on-demand what-ifs · later
    Channels
      Slack / Teams bot on POST /api/ask · next
      Weekly exec digest email · next
      Board-pack PDF export · later
      MCP server so any agent can query FinSight · next
    Actions + automation
      Auto-ticket on CRITICAL: Jira / PagerDuty · next
      Guardrail PRs: teardown, log level, replica cleanup · later
      Budget alerts per product owner · next
      Closed-loop: verify fix, re-baseline · later
    Trust + governance
      SSO / RBAC + per-tenant data isolation · next
      Audit log of every question + cited facts · now
      PII-free prompts, key in secrets manager · now
      Restrict CORS, rate limits · now
      Model cards for each engine · next
    Audiences + GTM
      CXO cockpit
      FinOps analyst workbench · next
      PE portfolio roll-up across companies · later
      MSP / consultancy white-label · later
    Platform + SRE
      Persist cards, scheduled rebuild · next
      OpenTelemetry traces on /api/ask · now
      Helm chart / Terraform module · next
      SLOs: p95 ask latency, freshness · next
```

---

## Prompts for the ideation session

1. **Trust:** what's the *one* number a CFO would check first, and is it a fact card yet?
2. **Precision:** 36 of 51 anomaly flags are low-value. What's the right cost of a false positive for this audience?
3. **Action:** for each CRITICAL, who gets paged, and what's the default remediation?
4. **Channel:** where do executives actually ask questions today: Slack, email, or a board pack?
5. **Scale:** at what corpus size does TF-IDF stop being enough? (Measure it; don't guess.)
6. **Moat:** which ideas *strengthen* the grounding contract, and which would weaken it?

## Suggested first sprint (all `[now]`)
| Idea | Effort | Why first |
|---|---|---|
| Golden-question eval harness in CI | S | Locks in grounding quality before anything else changes |
| Min-$ / day-of-month anomaly filter | S | Cuts noise in the most visible panel |
| Audit log of question → cited facts | S | Governance story for finance |
| Answer confidence from retrieval score | S | Lets the UI say "low confidence" before declining |
| OpenTelemetry on `/api/ask` | S | SRE-grade observability of the AI path |
