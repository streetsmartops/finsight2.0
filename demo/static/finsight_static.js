/*
 * FinSight — static (serverless) runtime for GitHub Pages.
 *
 * The cockpit calls /api/*. Here those calls are answered in the browser:
 *   GET  /api/<x>   -> api/<x>.json, snapshotted from the real FastAPI app at build time
 *   POST /api/ask   -> the same retrieval + template composition as src/finsight/rag.py,
 *                      ported to JS and run over the exported TF-IDF index
 *
 * Parity with the Python implementation is checked by tests/test_static_parity.py.
 * Works in browsers and in Node (module.exports) so the parity test can drive it.
 */
(function (root) {
  "use strict";

  // ---------------------------------------------------------------- retrieval
  function makeRetriever(index) {
    const stop = new Set(index.stop_words);
    const vocab = index.vocab;            // term -> column
    const idf = index.idf;                // column -> idf
    const rows = index.rows.map(r => new Map(r));   // card -> Map(column -> weight), L2-normalised
    const TOKEN = /[A-Za-z0-9][A-Za-z0-9\-]+/g;      // TfidfVectorizer.token_pattern

    function vectorize(text) {
      const toks = (text.toLowerCase().match(TOKEN) || []).filter(t => !stop.has(t));
      const counts = new Map();
      const bump = t => { if (t in vocab) counts.set(vocab[t], (counts.get(vocab[t]) || 0) + 1); };
      toks.forEach(bump);                                              // unigrams
      for (let i = 0; i + 1 < toks.length; i++) bump(toks[i] + " " + toks[i + 1]);   // bigrams
      let norm = 0;
      const v = new Map();
      counts.forEach((c, j) => { const w = c * idf[j]; v.set(j, w); norm += w * w; });
      norm = Math.sqrt(norm);
      if (norm > 0) v.forEach((w, j) => v.set(j, w / norm));
      return v;
    }

    const RISK = ["run out", "breach", "risk", "headroom", "capacity", "out of",
                  "problem", "spike", "anomaly", "wrong", "issue", "over"];
    const STATUS_BOOST = { CRITICAL: 0.30, WARNING: 0.20, WATCH: 0.10 };

    function search(query, k = 6, minScore = 0.04) {
      const q = vectorize(query);
      const sims = rows.map(r => { let s = 0; q.forEach((w, j) => { const x = r.get(j); if (x) s += w * x; }); return s; });
      const maxRaw = sims.length ? Math.max(...sims) : 0;
      if (maxRaw < minScore) return [];                       // relevance floor: off-domain

      const ql = query.toLowerCase();
      const risk = RISK.some(w => ql.includes(w));
      const scored = index.cards.map((card, i) => {
        let b = 0;
        for (const key of ["product", "region", "service"]) {
          const val = String(card.metadata[key] ?? "").toLowerCase();
          if (val && ql.includes(val)) b += 0.15;
        }
        if (risk) {
          b += STATUS_BOOST[card.metadata.status] || 0;
          if ("excess_usd" in card.metadata) b += 0.10;
        }
        return { i, score: sims[i] + b };
      });
      scored.sort((a, b) => b.score - a.score || b.i - a.i);
      return scored.slice(0, k)
        .filter(s => s.score > 0 && sims[s.i] >= minScore)
        .map(s => index.cards[s.i]);
    }
    return { search };
  }

  // -------------------------------------------------------------- composition
  function composeTemplate(evidence) {
    if (!evidence.length) {
      return "I don't have a grounded fact that answers that. Try asking about " +
             "estate spend, a product/region's capacity headroom, or recent cost " +
             "anomalies — Capacity-Mngt-App and Cost-Mngt-App cover those.";
    }
    const lead = evidence.find(c => c.metadata.status === "CRITICAL") || evidence[0];
    const parts = [`${lead.text} [${lead.id}]`];
    evidence.slice(1, 3).forEach(c => parts.push(`${c.text} [${c.id}]`));
    let action = "";
    if (evidence.some(c => c.metadata.status === "CRITICAL")) {
      action = " Recommended action: rightsize or scale the affected workload " +
               "now and re-baseline the headroom alert.";
    } else if (evidence.some(c => "excess" in c.metadata)) {
      // Mirrors rag.py exactly, including its key check: metadata holds
      // "excess_usd", so this branch never fires there either. Keep in sync.
      action = " Recommended action: confirm the suspected root cause and apply " +
               "the corresponding guardrail (teardown, log-level, replica cleanup).";
    }
    return parts.join(" ") + action;
  }

  function makeRAG(index) {
    const retriever = makeRetriever(index);
    return {
      ask(question, k = 6) {
        const evidence = retriever.search(question, k);
        const answer = composeTemplate(evidence);
        const citations = [...new Set(answer.match(/FACT-\d{3}/g) || [])].sort();
        return {
          question, answer, citations, used_llm: false,
          evidence: evidence.map(c => ({ id: c.id, source: c.source, text: c.text })),
        };
      },
    };
  }

  // ------------------------------------------------------- browser fetch shim
  function installShim(base) {
    const realFetch = root.fetch.bind(root);
    let ragPromise = null;
    const rag = () => ragPromise ||= realFetch(base + "api/rag_index.json").then(r => r.json()).then(makeRAG);
    const json = obj => new Response(JSON.stringify(obj), { status: 200, headers: { "Content-Type": "application/json" } });

    root.fetch = async (input, opts = {}) => {
      const url = typeof input === "string" ? input : input.url;
      const m = url.match(/\/api\/([a-z/]+)$/);
      if (!m) return realFetch(input, opts);
      if (m[1] === "ask" && (opts.method || "GET").toUpperCase() === "POST") {
        const { question } = JSON.parse(opts.body || "{}");
        return json((await rag()).ask(String(question || "").slice(0, 500)));
      }
      return realFetch(base + "api/" + m[1].replace(/\//g, "_") + ".json");
    };
  }

  const api = { makeRetriever, makeRAG, composeTemplate, installShim };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else {
    root.FinSightStatic = api;
    installShim(document.currentScript ? new URL(".", document.currentScript.src).href : "./");
  }
})(typeof window !== "undefined" ? window : globalThis);
