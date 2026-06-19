/**
 * FinSight — Capstone Deck Generator
 * ===================================
 * 8-slide PowerPoint per the UC Berkeley AI Business Strategies capstone
 * template, anchored on the FinSight Executive Cloud Intelligence Layer.
 *
 * Design identity carried from the repo's cockpit: dark slate instrument
 * panel, signal-green accent, monospace data. Motif = icon-in-circle headers.
 */

const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const FA = require("react-icons/fa");

// --------------------------------------------------------------------------- //
// Palette  (FinSight cockpit identity)
// --------------------------------------------------------------------------- //
const C = {
  bg:       "0B0F14",   // near-black slate
  panel:    "121821",
  panel2:   "1A2331",
  line:     "2A3848",
  ink:      "E6EDF3",
  inkDim:   "9AABBC",
  inkFaint: "6A7B8C",
  signal:   "35E0A1",   // brand green
  signalDk: "0E5C42",
  warn:     "F2B441",
  crit:     "FF5C6C",
  watch:    "5BC8FF",
  white:    "FFFFFF",
};

const FONT = "Arial";
const MONO = "Consolas";   // safe-list mono substitute behavior acceptable for labels

// --------------------------------------------------------------------------- //
// Icon rasterization
// --------------------------------------------------------------------------- //
async function icon(Comp, color = "#35E0A1", size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(Comp, { color, size: String(size) })
  );
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

// --------------------------------------------------------------------------- //
// Reusable slide furniture
// --------------------------------------------------------------------------- //
function makeShadow() {
  return { type: "outer", color: "000000", blur: 8, offset: 3, angle: 90, opacity: 0.30 };
}

// Eyebrow + title block, with a slide number token. Returns the y where body can start.
function header(slide, pres, opts) {
  const { num, eyebrow, title, iconData } = opts;
  // slide number (top-right, monospace)
  slide.addText(`0${num} / 08`, {
    x: 8.3, y: 0.32, w: 1.4, h: 0.3, align: "right",
    fontFace: MONO, fontSize: 9, color: C.inkFaint, charSpacing: 2,
  });
  // icon in a circle (the motif)
  if (iconData) {
    slide.addShape(pres.shapes.OVAL, {
      x: 0.5, y: 0.42, w: 0.62, h: 0.62,
      fill: { color: C.panel2 }, line: { color: C.signal, width: 1 },
    });
    slide.addImage({ data: iconData, x: 0.645, y: 0.565, w: 0.33, h: 0.33 });
  }
  // eyebrow
  slide.addText(eyebrow.toUpperCase(), {
    x: 1.28, y: 0.46, w: 7, h: 0.26, margin: 0,
    fontFace: MONO, fontSize: 9.5, color: C.signal, charSpacing: 3, bold: true,
  });
  // title
  slide.addText(title, {
    x: 1.26, y: 0.70, w: 8, h: 0.55, margin: 0,
    fontFace: FONT, fontSize: 25, color: C.ink, bold: true,
  });
  return 1.55;
}

function footerNote(slide, text) {
  slide.addText(text, {
    x: 0.5, y: 5.28, w: 9, h: 0.26, margin: 0,
    fontFace: MONO, fontSize: 7.5, color: C.inkFaint, italic: true,
  });
}

// A content card with subtle tint + shadow (no edge stripes — per skill)
function card(slide, pres, x, y, w, h, fill = C.panel) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: fill }, line: { color: C.line, width: 0.75 },
    shadow: makeShadow(),
  });
}

// --------------------------------------------------------------------------- //
// Build
// --------------------------------------------------------------------------- //
(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";   // 10 x 5.625
  pres.author = "Sachin Narayanan";
  pres.title = "FinSight — Executive Cloud Intelligence Layer";

  // Pre-render icons
  const ic = {
    target:   await icon(FA.FaBullseye),
    strategy: await icon(FA.FaChessKnight),
    metric:   await icon(FA.FaTachometerAlt),
    tech:     await icon(FA.FaMicrochip),
    data:     await icon(FA.FaDatabase),
    humans:   await icon(FA.FaUsers),
    flask:    await icon(FA.FaFlask),
    chart:    await icon(FA.FaChartLine),
    brand:    await icon(FA.FaSatelliteDish, "#35E0A1", 256),
    bolt:     await icon(FA.FaBolt, "#F2B441", 256),
    warn:     await icon(FA.FaExclamationTriangle, "#FF5C6C", 256),
    search:   await icon(FA.FaSearch, "#5BC8FF", 256),
    check:    await icon(FA.FaCheckCircle, "#35E0A1", 256),
    gauge:    await icon(FA.FaTachometerAlt, "#35E0A1", 256),
    money:    await icon(FA.FaDollarSign, "#35E0A1", 256),
    shield:   await icon(FA.FaShieldAlt, "#35E0A1", 256),
    code:     await icon(FA.FaCode, "#9AABBC", 256),
  };

  // ===================================================================== //
  // SLIDE 0 — TITLE
  // ===================================================================== //
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // faint grid texture via thin lines (instrument panel feel) — sparse, not a stripe
    for (let i = 1; i < 6; i++) {
      s.addShape(pres.shapes.LINE, {
        x: 0, y: i * 0.94, w: 10, h: 0,
        line: { color: C.line, width: 0.5, transparency: 70 },
      });
    }

    // brand mark
    s.addShape(pres.shapes.OVAL, {
      x: 0.7, y: 0.62, w: 0.9, h: 0.9,
      fill: { color: C.panel2 }, line: { color: C.signal, width: 1.5 },
    });
    s.addImage({ data: ic.brand, x: 0.92, y: 0.84, w: 0.46, h: 0.46 });

    s.addText([
      { text: "Fin", options: { color: C.ink } },
      { text: "Sight", options: { color: C.signal } },
    ], { x: 1.8, y: 0.62, w: 7, h: 0.9, fontFace: FONT, fontSize: 44, bold: true, valign: "middle", margin: 0 });

    s.addText("EXECUTIVE CLOUD INTELLIGENCE LAYER", {
      x: 1.83, y: 1.48, w: 8, h: 0.3, margin: 0,
      fontFace: MONO, fontSize: 12, color: C.inkDim, charSpacing: 4,
    });

    // thesis line
    s.addText(
      "An AI decision layer that lets a CXO ask the cloud estate a question in plain English — and get a grounded, cited answer.",
      { x: 0.72, y: 2.25, w: 8.5, h: 0.7, fontFace: FONT, fontSize: 15, color: C.ink, lineSpacingMultiple: 1.2 }
    );

    // three engine chips
    const chips = [
      ["Capacity-Mngt-App", "capacity & cost forecasting", ic.gauge],
      ["Cost-Mngt-App", "cost anomaly detection", ic.money],
      ["RAG cockpit", "grounded executive Q&A", ic.search],
    ];
    chips.forEach((c, i) => {
      const x = 0.72 + i * 2.96;
      card(s, pres, x, 3.15, 2.76, 0.92, C.panel);
      s.addImage({ data: c[2], x: x + 0.18, y: 3.36, w: 0.3, h: 0.3 });
      s.addText(c[0], { x: x + 0.58, y: 3.30, w: 2.1, h: 0.3, margin: 0, fontFace: FONT, fontSize: 13, bold: true, color: C.ink });
      s.addText(c[1], { x: x + 0.58, y: 3.62, w: 2.1, h: 0.3, margin: 0, fontFace: MONO, fontSize: 8, color: C.inkDim });
    });

    // attribution footer
    s.addText(
      "Capstone · UC Berkeley Executive Education — AI & GenAI: Business Strategies and Applications",
      { x: 0.72, y: 4.74, w: 8.6, h: 0.26, margin: 0, fontFace: MONO, fontSize: 8.5, color: C.inkFaint, charSpacing: 1 }
    );
    s.addText("Sachin Narayanan · Director, Cloud Operations & AI-Augmented Engineering", {
      x: 0.72, y: 5.0, w: 8.6, h: 0.26, margin: 0, fontFace: MONO, fontSize: 8.5, color: C.inkFaint, charSpacing: 1,
    });
  }

  // ===================================================================== //
  // SLIDE 1 — PROBLEM
  // ===================================================================== //
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    header(s, pres, { num: 1, eyebrow: "The Problem", title: "Cloud answers are locked behind dashboards", iconData: ic.target });

    // Left: the problem narrative
    s.addText(
      "In an Enterprise CX SaaS estate — 167 AWS single- and multi-tenant deployments, ~$5M annual spend — the answers leadership needs are scattered across Datadog, Cost Explorer, and a dozen tabs. When a PE investor asks \u201care we about to run out of capacity, and why did the bill jump?\u201d, the answer takes an engineer hours to assemble.",
      { x: 0.5, y: 1.62, w: 5.2, h: 1.5, fontFace: FONT, fontSize: 12.5, color: C.ink, lineSpacingMultiple: 1.22 }
    );
    s.addText(
      "FinSight collapses that to one question box. It unifies predictive capacity forecasting and real-time cost attribution behind a retrieval-augmented interface, so a non-technical executive gets a decisive, cited answer in seconds.",
      { x: 0.5, y: 3.2, w: 5.2, h: 1.2, fontFace: FONT, fontSize: 12.5, color: C.inkDim, lineSpacingMultiple: 1.22 }
    );

    // Right: industry context card with stat callouts
    card(s, pres, 6.0, 1.62, 3.5, 3.3, C.panel);
    s.addText("INDUSTRY CONTEXT", {
      x: 6.25, y: 1.8, w: 3, h: 0.26, margin: 0, fontFace: MONO, fontSize: 9, color: C.signal, charSpacing: 2, bold: true,
    });
    const stats = [
      ["167", "AWS ST/MT deployments", C.ink],
      ["$5M", "annual cloud spend governed", C.signal],
      ["3", "product lines: Engage · Analyze · Assist", C.ink],
      ["91", "person cross-geo cloud org", C.ink],
    ];
    stats.forEach((st, i) => {
      const y = 2.18 + i * 0.66;
      s.addText(st[0], { x: 6.25, y, w: 1.1, h: 0.55, margin: 0, fontFace: MONO, fontSize: 26, bold: true, color: st[2], valign: "middle" });
      s.addText(st[1], { x: 7.35, y, w: 2.0, h: 0.55, margin: 0, fontFace: FONT, fontSize: 9.5, color: C.inkDim, valign: "middle" });
    });

    footerNote(s, "Enterprise CX SaaS · cloud operations · the gap between telemetry and an executive-ready answer");
  }

  // ===================================================================== //
  // SLIDE 2 — STRATEGY
  // ===================================================================== //
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    header(s, pres, { num: 2, eyebrow: "Strategy", title: "How FinSight generates business value", iconData: ic.strategy });

    const cols = [
      ["Improvement, not net-new", ic.check,
       "An overlay on existing observability (Datadog, Cost Explorer) — not a rip-and-replace. It turns telemetry already paid for into decisions, so adoption cost is low and value is immediate."],
      ["Competitive advantage", ic.shield,
       "Second-mover on the technique, first-mover internally. The moat isn't the models — it's the grounding contract over our own estate. Faster capacity + cost decisions during PE diligence directly protect valuation."],
      ["Financially viable", ic.money,
       "Investment: ~1 eng-quarter to build, marginal LLM inference cost. Return: avoided over-provisioning, faster anomaly catch, and analyst hours saved. Payback measured in a single prevented capacity incident."],
    ];
    cols.forEach((c, i) => {
      const x = 0.5 + i * 3.07;
      card(s, pres, x, 1.62, 2.87, 3.0, C.panel);
      s.addShape(pres.shapes.OVAL, { x: x + 0.22, y: 1.82, w: 0.5, h: 0.5, fill: { color: C.panel2 }, line: { color: C.signal, width: 1 } });
      s.addImage({ data: c[1], x: x + 0.335, y: 1.935, w: 0.27, h: 0.27 });
      s.addText(c[0], { x: x + 0.22, y: 2.42, w: 2.5, h: 0.5, margin: 0, fontFace: FONT, fontSize: 13.5, bold: true, color: C.ink });
      s.addText(c[2], { x: x + 0.22, y: 2.92, w: 2.5, h: 1.6, margin: 0, fontFace: FONT, fontSize: 10, color: C.inkDim, lineSpacingMultiple: 1.18 });
    });

    footerNote(s, "ROI components — Investment: build + inference · Return: avoided over-provisioning + faster anomaly catch + analyst time");
  }

  // ===================================================================== //
  // SLIDE 3 — METRICS
  // ===================================================================== //
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    header(s, pres, { num: 3, eyebrow: "Success Metrics", title: "What we measure, and what we do about it", iconData: ic.metric });

    const rows = [
      ["Forecast accuracy (MAPE)", "Capacity-Mngt-App must be trusted to act on. Tracks predicted vs. actual utilization/spend.", "> 10% \u2192 retrain / add features. < 5% \u2192 safe to automate capacity alerts.", C.signal],
      ["Anomaly precision / recall", "False alarms erode trust; misses cost money. Measured against confirmed incidents.", "Precision drop \u2192 raise z-threshold. Recall drop \u2192 lower it / shorten window.", C.watch],
      ["Answer grounding rate", "Every cited number must trace to an engine fact. The anti-hallucination guarantee.", "< 100% \u2192 block release. Any fabricated citation is a hard failure.", C.crit],
      ["Time-to-answer", "The core value prop: hours of analyst work \u2192 seconds.", "Rising \u2192 cache facts / tune retrieval. The exec-facing SLA.", C.ink],
    ];
    let y = 1.62;
    rows.forEach((r) => {
      card(s, pres, 0.5, y, 9.0, 0.82, C.panel);
      s.addText(r[0], { x: 0.7, y: y + 0.08, w: 2.2, h: 0.66, margin: 0, fontFace: FONT, fontSize: 11.5, bold: true, color: r[3], valign: "middle" });
      s.addText(r[1], { x: 3.0, y: y + 0.08, w: 3.2, h: 0.66, margin: 0, fontFace: FONT, fontSize: 9.3, color: C.inkDim, valign: "middle", lineSpacingMultiple: 1.1 });
      s.addText(r[2], { x: 6.35, y: y + 0.08, w: 3.0, h: 0.66, margin: 0, fontFace: MONO, fontSize: 8.6, color: C.ink, valign: "middle", lineSpacingMultiple: 1.12 });
      y += 0.92;
    });
    // column captions
    s.addText("METRIC", { x: 0.7, y: 1.46, w: 2, h: 0.18, margin: 0, fontFace: MONO, fontSize: 7.5, color: C.inkFaint, charSpacing: 2 });
    s.addText("WHY IT MAPS TO THE NEED", { x: 3.0, y: 1.46, w: 3, h: 0.18, margin: 0, fontFace: MONO, fontSize: 7.5, color: C.inkFaint, charSpacing: 2 });
    s.addText("ACTION ON THRESHOLD", { x: 6.35, y: 1.46, w: 3, h: 0.18, margin: 0, fontFace: MONO, fontSize: 7.5, color: C.inkFaint, charSpacing: 2 });

    footerNote(s, "Metrics chosen for actionability — each carries an explicit response when it crosses a floor or ceiling");
  }

  // ===================================================================== //
  // SLIDE 4 — TECHNOLOGY
  // ===================================================================== //
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    header(s, pres, { num: 4, eyebrow: "Technology", title: "Three AI techniques, one decision layer", iconData: ic.tech });

    const blocks = [
      ["Capacity-Mngt-App", "Supervised \u00b7 Time-Series", ic.gauge,
       ["Ridge regression on engineered temporal features (trend, day-of-week, weekly Fourier).",
        "Readily-available algorithm (scikit-learn) — no custom model needed.",
        "Trained per-stream on 180d history; objective: minimize forecast error + honest prediction interval."]],
      ["Cost-Mngt-App", "Unsupervised \u00b7 Statistics", ic.money,
       ["Robust z-score on rolling median + MAD baseline; resists spike-poisoning.",
        "No labels required at cold start — pure statistical detector.",
        "Plus deterministic attribution: decomposes any spend delta by product/region/service."]],
      ["RAG cockpit", "Retrieval + LLM", ic.search,
       ["TF-IDF retrieval over engine-derived fact cards \u2192 grounded composition with Claude.",
        "Adopts an available LLM; the IP is the grounding contract, not the model.",
        "No training — the engines own the numbers, the LLM only phrases them."]],
    ];
    blocks.forEach((b, i) => {
      const x = 0.5 + i * 3.07;
      card(s, pres, x, 1.62, 2.87, 3.15, C.panel);
      s.addImage({ data: b[2], x: x + 0.22, y: 1.82, w: 0.34, h: 0.34 });
      s.addText(b[0], { x: x + 0.66, y: 1.8, w: 2.1, h: 0.3, margin: 0, fontFace: FONT, fontSize: 14, bold: true, color: C.ink });
      s.addText(b[1].toUpperCase(), { x: x + 0.66, y: 2.1, w: 2.1, h: 0.22, margin: 0, fontFace: MONO, fontSize: 7.5, color: C.signal, charSpacing: 1 });
      const bullets = b[3].map((t) => ({ text: t, options: { bullet: { code: "2022", indent: 12 }, breakLine: true, paraSpaceAfter: 6 } }));
      s.addText(bullets, { x: x + 0.22, y: 2.46, w: 2.5, h: 2.2, margin: 0, fontFace: FONT, fontSize: 9.2, color: C.inkDim, lineSpacingMultiple: 1.1 });
    });

    footerNote(s, "Modules 2\u20135 mapping — supervised regression \u00b7 unsupervised anomaly detection \u00b7 retrieval-augmented generation");
  }

  // ===================================================================== //
  // SLIDE 5 — DATA
  // ===================================================================== //
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    header(s, pres, { num: 5, eyebrow: "Data", title: "Data we already own — and how it connects", iconData: ic.data });

    // Left: data sources flow
    const sources = [
      ["AWS Cost & Usage Report", "billing by account / service / region", ic.money],
      ["Utilization telemetry", "EKS / EC2 metrics via Datadog + Prometheus", ic.gauge],
      ["Incidents & runbooks", "PagerDuty + internal docs for root-cause context", ic.warn],
    ];
    s.addText("SOURCES — ALREADY IN OUR SYSTEMS", { x: 0.5, y: 1.58, w: 5, h: 0.24, margin: 0, fontFace: MONO, fontSize: 8.5, color: C.signal, charSpacing: 2, bold: true });
    sources.forEach((src, i) => {
      const y = 1.92 + i * 0.74;
      card(s, pres, 0.5, y, 4.6, 0.62, C.panel);
      s.addImage({ data: src[2], x: 0.68, y: y + 0.16, w: 0.3, h: 0.3 });
      s.addText(src[0], { x: 1.08, y: y + 0.08, w: 3.9, h: 0.28, margin: 0, fontFace: FONT, fontSize: 11, bold: true, color: C.ink });
      s.addText(src[1], { x: 1.08, y: y + 0.34, w: 3.9, h: 0.24, margin: 0, fontFace: MONO, fontSize: 7.8, color: C.inkDim });
    });

    // Right: ownership + integration card
    card(s, pres, 5.4, 1.58, 4.1, 3.32, C.panel2);
    s.addText("OWNERSHIP & INTEGRATION", { x: 5.62, y: 1.76, w: 3.6, h: 0.24, margin: 0, fontFace: MONO, fontSize: 8.5, color: C.signal, charSpacing: 2, bold: true });
    const pts = [
      "We own it. All three sources are first-party — no vendor data acquisition, no new licensing.",
      "Where it lives. CUR in S3; metrics in Datadog/Prometheus; incidents in PagerDuty + Git.",
      "Linking the systems. A daily ETL keys every record on (date, product, region, service) — the same join the engines and fact cards use.",
      "Is it data-hungry? Moderately. 180 days of daily data is enough for the seasonal forecast; the RAG layer needs only the derived facts, not raw rows.",
    ];
    const bl = pts.map((t) => ({ text: t, options: { bullet: { code: "2022", indent: 14 }, breakLine: true, paraSpaceAfter: 9 } }));
    s.addText(bl, { x: 5.62, y: 2.12, w: 3.66, h: 2.7, margin: 0, fontFace: FONT, fontSize: 10, color: C.ink, lineSpacingMultiple: 1.16 });

    footerNote(s, "Demo uses deterministic synthetic data (seed=42) modeling this exact schema — no production data leaves the estate");
  }

  // ===================================================================== //
  // SLIDE 6 — HUMANS & AI
  // ===================================================================== //
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    header(s, pres, { num: 6, eyebrow: "Humans & AI", title: "The organizational and ethical factors", iconData: ic.humans });

    const left = [
      ["Change required", "Leaders must trust an AI-phrased answer. Engineers must trust it won't hallucinate numbers into a board deck."],
      ["How we earn it", "Ship the grounding contract visibly — every answer shows its [FACT-xxx] citations and evidence. Trust is demonstrated, not asserted."],
    ];
    const right = [
      ["Human interaction", "Internal: CXO / PE / SRE leads query it directly. The cockpit keeps the human in the decision loop — it informs, it doesn't auto-act on spend."],
      ["Ethics & guardrails", "Cost attribution must not become individual blame. Forecasts carry uncertainty bands so no one over-trusts a point estimate. Off-domain questions are declined, not bluffed."],
    ];
    [["ADOPTION", left, 0.5], ["INTERACTION & ETHICS", right, 5.05]].forEach(([label, items, x]) => {
      s.addText(label, { x: x + 0.0, y: 1.58, w: 4, h: 0.24, margin: 0, fontFace: MONO, fontSize: 8.5, color: C.signal, charSpacing: 2, bold: true });
      items.forEach((it, i) => {
        const y = 1.92 + i * 1.42;
        card(s, pres, x, y, 4.45, 1.26, C.panel);
        s.addText(it[0], { x: x + 0.2, y: y + 0.12, w: 4.05, h: 0.3, margin: 0, fontFace: FONT, fontSize: 12.5, bold: true, color: C.ink });
        s.addText(it[1], { x: x + 0.2, y: y + 0.44, w: 4.05, h: 0.74, margin: 0, fontFace: FONT, fontSize: 9.6, color: C.inkDim, lineSpacingMultiple: 1.16 });
      });
    });

    footerNote(s, "Modules 7\u20138 — the human stays in the loop; the system informs decisions, it does not take spend actions autonomously");
  }

  // ===================================================================== //
  // SLIDE 7 — MEASUREMENT / EXPERIMENT
  // ===================================================================== //
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    header(s, pres, { num: 7, eyebrow: "Measurement", title: "An experiment to prove it works", iconData: ic.flask });

    // Design summary card (left)
    card(s, pres, 0.5, 1.62, 4.5, 3.25, C.panel);
    s.addText("EXPERIMENTAL DESIGN", { x: 0.72, y: 1.8, w: 4, h: 0.24, margin: 0, fontFace: MONO, fontSize: 8.5, color: C.signal, charSpacing: 2, bold: true });
    const design = [
      ["Design", "Randomized A/B on decision tasks. Control = current dashboards; Treatment = FinSight cockpit."],
      ["Population", "~24 cloud-ops leads & EMs, randomized to the two arms across a 6-week window."],
      ["Tasks", "Standardized prompts: \u201cIs any stream at capacity risk?\u201d \u00b7 \u201cExplain last week's spend delta.\u201d"],
    ];
    let yy = 2.16;
    design.forEach((d) => {
      s.addText(d[0], { x: 0.72, y: yy, w: 4.1, h: 0.24, margin: 0, fontFace: FONT, fontSize: 11, bold: true, color: C.ink });
      s.addText(d[1], { x: 0.72, y: yy + 0.26, w: 4.1, h: 0.6, margin: 0, fontFace: FONT, fontSize: 9.5, color: C.inkDim, lineSpacingMultiple: 1.15 });
      yy += 0.9;
    });

    // Metrics measured (right)
    card(s, pres, 5.2, 1.62, 4.3, 3.25, C.panel2);
    s.addText("WHAT WE MEASURE & COMPARE", { x: 5.42, y: 1.8, w: 4, h: 0.24, margin: 0, fontFace: MONO, fontSize: 8.5, color: C.signal, charSpacing: 2, bold: true });
    const meas = [
      ["Time-to-answer", "Treatment vs. control, per task. Primary endpoint."],
      ["Answer correctness", "Graded against ground-truth from the engines."],
      ["Decision confidence", "Self-rated 1\u20135; does grounding raise trust?"],
      ["Grounding rate", "% of cited numbers that trace to a real fact (target 100%)."],
    ];
    let my = 2.18;
    meas.forEach((m) => {
      s.addShape(pres.shapes.OVAL, { x: 5.42, y: my + 0.04, w: 0.16, h: 0.16, fill: { color: C.signal }, line: { color: C.signal, width: 0 } });
      s.addText(m[0], { x: 5.68, y: my - 0.04, w: 3.6, h: 0.26, margin: 0, fontFace: FONT, fontSize: 10.5, bold: true, color: C.ink });
      s.addText(m[1], { x: 5.68, y: my + 0.21, w: 3.6, h: 0.38, margin: 0, fontFace: FONT, fontSize: 8.7, color: C.inkDim, lineSpacingMultiple: 1.1 });
      my += 0.66;
    });

    footerNote(s, "Primary endpoint: time-to-answer (Treatment vs Control) · guardrail endpoint: grounding rate must hold at 100%");
  }

  // ===================================================================== //
  // SLIDE 8 — RESULTS / PROOF OF WORK (the working solution)
  // ===================================================================== //
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    header(s, pres, { num: 8, eyebrow: "Proof of Work", title: "Built, tested, and running — not a concept", iconData: ic.chart });

    // Cockpit screenshot (left, large)
    s.addImage({
      path: "../docs/deck_hero.png",
      x: 0.5, y: 1.6, w: 5.85, h: 3.0,
      sizing: { type: "contain", w: 5.85, h: 3.0 },
    });
    s.addText("Live FinSight cockpit — grounded answer with inline [FACT] citations", {
      x: 0.5, y: 4.64, w: 5.85, h: 0.24, margin: 0, fontFace: MONO, fontSize: 7.8, color: C.inkFaint, italic: true, align: "center",
    });

    // Proof points (right)
    const proof = [
      ["14 / 14", "tests passing — engines + grounding contract", ic.check],
      ["2.7%", "Capacity-Mngt-App forecast MAPE on capacity", ic.gauge],
      ["5 / 5", "injected cost anomalies recovered by Cost-Mngt-App", ic.money],
      ["100%", "answer grounding rate — zero fabricated citations", ic.shield],
    ];
    proof.forEach((p, i) => {
      const y = 1.62 + i * 0.78;
      card(s, pres, 6.55, y, 2.95, 0.66, C.panel);
      s.addImage({ data: p[2], x: 6.72, y: y + 0.18, w: 0.3, h: 0.3 });
      s.addText(p[0], { x: 7.1, y: y + 0.06, w: 0.92, h: 0.54, margin: 0, fontFace: MONO, fontSize: 15, bold: true, color: C.signal, valign: "middle" });
      s.addText(p[1], { x: 8.06, y: y + 0.06, w: 1.36, h: 0.54, margin: 0, fontFace: FONT, fontSize: 7.5, color: C.inkDim, valign: "middle", lineSpacingMultiple: 1.05 });
    });
    s.addText("Full repo: working engines · FastAPI cockpit · reproducible notebook · test suite", {
      x: 6.55, y: 4.78, w: 2.95, h: 0.5, margin: 0, fontFace: MONO, fontSize: 7.6, color: C.inkFaint, lineSpacingMultiple: 1.2,
    });

    footerNote(s, "Optional Slide 8 — deployment evidence · the system is demoable live and defensible in technical interviews");
  }

  await pres.writeFile({ fileName: "FinSight_Capstone.pptx" });
  console.log("Deck written: FinSight_Capstone.pptx");
})();
