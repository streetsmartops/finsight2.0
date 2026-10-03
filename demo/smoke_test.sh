#!/usr/bin/env bash
# Pre-flight check before going on stage: every endpoint + the grounding contract.
#   ./demo/smoke_test.sh [base_url]
set -euo pipefail
URL="${1:-http://localhost:8000}"

for i in $(seq 1 60); do
  curl -fsS "$URL/api/health" >/dev/null 2>&1 && break
  [[ $i == 60 ]] && { echo "✗ API did not come up at $URL" >&2; exit 1; }
  sleep 1
done

python3 - "$URL" <<'PY'
import json, sys, urllib.request
base = sys.argv[1]

def get(p):
    return json.load(urllib.request.urlopen(base + p, timeout=60))

def ask(q):
    req = urllib.request.Request(base + "/api/ask", json.dumps({"question": q}).encode(),
                                 {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))

ok = lambda m: print(f"  \033[32m✓\033[0m {m}")
h = get("/api/health"); ok(f"health: {h['facts_indexed']} facts indexed · LLM={'on' if h['llm_configured'] else 'template'}")
o = get("/api/overview"); ok(f"overview: ${o['annualized_spend_usd']:,.0f} annualized · {o['anomalies_detected']} anomalies · capacity {o['capacity_statuses']}")
c = get("/api/capacity"); ok(f"capacity: worst stream {c['rows'][0]['product']}/{c['rows'][0]['region']} = {c['rows'][0]['status']}")
a = get("/api/anomalies"); ok(f"anomalies: top excess +${a['rows'][0]['excess_usd']:,.0f} ({a['rows'][0]['service']} {a['rows'][0]['region']})")
f = get("/api/forecast/cost"); ok(f"forecast: {len(f['forecast'])}-day horizon · MAPE {f['mape_pct']}%")

r = ask("Will we run out of capacity next quarter?")
assert r["citations"], "in-domain answer must carry citations"
ids = {e["id"] for e in r["evidence"]}
assert set(r["citations"]) <= ids, "every citation must be retrieved evidence"
ok(f"ask (in-domain): cites {', '.join(r['citations'])}")

r = ask("Who won the cricket world cup?")
assert not r["citations"] and not r["evidence"], "off-domain question must be declined"
ok("ask (off-domain): declined — grounding contract holds")
print("\n  Demo ready.")
PY
