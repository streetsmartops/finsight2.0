---
title: FinSight 2.0
emoji: 📊
colorFrom: green
colorTo: gray
sdk: docker
app_port: 8000
pinned: false
license: mit
short_description: Ask your cloud estate; get grounded, cited answers
---

# FinSight 2.0 — Executive Cloud Intelligence

Ask your cloud estate a question in plain English and get a grounded, cited answer.
Two deterministic engines own every number (capacity forecasting and cost anomaly detection). The language model only phrases them.
Off-topic questions are declined instead of answered with invented figures.

- Try it: *Will we run out of capacity next quarter?* · *Why did our cloud spend spike, and where?* · *What happened with RDS in eu-west-1?*
- Data is synthetic and deterministic (seed 42): 167 AWS deployments, ~$5M annual spend.
- Template mode by default. When the Space owner sets an `ANTHROPIC_API_KEY` secret, Claude phrases the answers.
- REST API: `POST /api/ask` with `{"question": "..."}`

Source, docs and a one-command local demo: https://github.com/streetsmartops/finsight2.0
