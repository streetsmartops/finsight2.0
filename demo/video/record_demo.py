"""
FinSight — captioned demo-video recorder
========================================

Drives the *real* running cockpit with a headless browser, overlays on-screen
captions, and writes:

    demo/video/out/finsight_demo.mp4   H.264 video (captions burned in)
    demo/video/out/finsight_demo.srt   the same captions as a subtitle track
    demo/video/out/narration.md        timestamped voice-over script

Every scene is defined once in SCENES, so the video, subtitles and narration
can never drift apart. Re-record after any UI change:

    ./demo/demo.sh --offline            # start the cockpit (template mode)
    python demo/video/record_demo.py    # ~2.5 min recording

Requires: playwright (Python) + ffmpeg. Chromium is located via
FINSIGHT_CHROMIUM, /opt/pw-browsers/chromium, or `playwright install chromium`.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from playwright.sync_api import Page, sync_playwright

OUT = Path(__file__).resolve().parent / "out"
W, H = 1440, 900
WORDS_PER_SEC = 2.5          # calm presenter pace

# --------------------------------------------------------------------------- #
# Overlay helpers (injected into the page)
# --------------------------------------------------------------------------- #

OVERLAY_JS = """
(() => {
  if (window.__fs) return;
  const css = document.createElement('style');
  css.textContent = `
    #fs-cap{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);
      max-width:1100px;padding:14px 26px;border-radius:12px;z-index:99999;
      background:rgba(6,10,16,.88);color:#E8EEF5;border:1px solid #35E0A1;
      font:500 21px/1.4 system-ui,-apple-system,Segoe UI,sans-serif;
      box-shadow:0 8px 30px rgba(0,0,0,.5);transition:opacity .35s;opacity:0;text-align:center}
    #fs-cap b{color:#35E0A1}
    #fs-card{position:fixed;inset:0;z-index:100000;display:flex;flex-direction:column;
      align-items:center;justify-content:center;gap:18px;background:#070B11;
      color:#E8EEF5;font-family:system-ui,-apple-system,Segoe UI,sans-serif;
      transition:opacity .5s;opacity:0;pointer-events:none;text-align:center;padding:40px}
    #fs-card h1{font-size:64px;margin:0;letter-spacing:-1px}
    #fs-card h1 span{color:#35E0A1}
    #fs-card p{font-size:26px;margin:0;color:#9FB0C2;max-width:1000px;line-height:1.45}
    .fs-hl{outline:3px solid #35E0A1 !important;outline-offset:6px;border-radius:10px;
      transition:outline-color .3s}
  `;
  document.head.appendChild(css);
  const cap = document.createElement('div'); cap.id = 'fs-cap'; document.body.appendChild(cap);
  const card = document.createElement('div'); card.id = 'fs-card'; document.body.appendChild(card);
  window.__fs = {
    cap(html){ cap.innerHTML = html; cap.style.opacity = html ? 1 : 0; },
    card(html){ card.innerHTML = html; card.style.opacity = html ? 1 : 0; },
    hl(sel){ document.querySelectorAll('.fs-hl').forEach(e=>e.classList.remove('fs-hl'));
             if(!sel) return; const el = document.querySelector(sel);
             if(el){ el.classList.add('fs-hl'); el.scrollIntoView({behavior:'smooth', block:'center'}); } },
  };
})();
"""


def overlay(page: Page) -> None:
    page.evaluate(OVERLAY_JS)


def caption(page: Page, html: str) -> None:
    page.evaluate("h => window.__fs.cap(h)", html)


def card(page: Page, html: str) -> None:
    page.evaluate("h => window.__fs.card(h)", html)


def highlight(page: Page, selector: str | None) -> None:
    page.evaluate("s => window.__fs.hl(s)", selector)


def section_of(child_id: str) -> str:
    """CSS selector for the panel that contains #child_id."""
    return f"section:has(#{child_id}), .panel:has(#{child_id}), div.card:has(#{child_id})"


def ask(page: Page, question: str) -> None:
    highlight(page, "#q")
    page.fill("#q", "")
    page.type("#q", question, delay=38)
    time.sleep(0.4)
    page.click("#ask-btn")
    page.wait_for_selector("#answer .answer-card", timeout=60_000)
    time.sleep(0.3)
    highlight(page, "#answer")


# --------------------------------------------------------------------------- #
# Storyboard — single source of truth for video, SRT and narration
# --------------------------------------------------------------------------- #

@dataclass
class Scene:
    caption: str                     # on-screen caption (HTML allowed)
    narration: str                   # fuller voice-over line
    hold: float                      # seconds to keep the caption up after action
    action: Callable[[Page], None] = field(default=lambda p: None)
    is_card: bool = False            # full-screen title card instead of caption


def _title(p: Page) -> None:
    card(p, "<h1>Fin<span>Sight</span> 2.0</h1>"
            "<p>Ask your cloud estate a question in plain English.<br>"
            "Get a grounded, cited answer — every number traced to the model that computed it.</p>")


def _arch(p: Page) -> None:
    card(p, "<h1>How it works</h1>"
            "<p><b style='color:#35E0A1'>Capacity-Mngt-App</b> forecasts headroom (ridge regression) · "
            "<b style='color:#35E0A1'>Cost-Mngt-App</b> catches spend anomalies (robust z-score)<br>"
            "→ both emit <b>fact cards</b> → <b>RAG</b> retrieves the relevant facts → "
            "Claude (or a deterministic template) phrases a cited answer.</p>")


def _api_card(p: Page) -> None:
    """Show a live POST /api/ask round-trip, rendered in-page (no CDN needed)."""
    p.evaluate("""async () => {
      const q = "Is Assist in us-east-1 healthy?";
      const r = await (await fetch('/api/ask', {method:'POST',
        headers:{'Content-Type':'application/json'}, body: JSON.stringify({question:q})})).json();
      const slim = {question:r.question, citations:r.citations, used_llm:r.used_llm,
        answer:r.answer.slice(0,150)+'…',
        evidence:r.evidence.slice(0,2).map(e=>({id:e.id, source:e.source}))};
      const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;');
      window.__fs.card(`<h1 style="font-size:40px">One API, any channel</h1>
        <pre style="text-align:left;font:15px/1.5 ui-monospace,monospace;background:#0E1520;
          border:1px solid #243140;border-radius:10px;padding:18px 22px;max-width:1100px;
          white-space:pre-wrap;color:#C9D6E3"><span style="color:#35E0A1">$ curl -X POST localhost:8000/api/ask -H 'Content-Type: application/json' \\\\
       -d '{"question": "${q}"}'</span>

${esc(JSON.stringify(slim, null, 2))}</pre>`);
    }""")


def _clear_card(p: Page) -> None:
    card(p, "")


SCENES: list[Scene] = [
    Scene("", "FinSight 2.0 — the executive cloud intelligence layer. Ask your cloud estate a "
              "question in plain English and get a grounded, cited answer.",
          5.0, _title, is_card=True),
    Scene("", "Under the hood, two deterministic engines own every number. Capacity-Mngt-App "
              "forecasts utilisation and spend; Cost-Mngt-App detects anomalies and attributes "
              "cost. Their outputs become fact cards, and the RAG layer can only cite those facts.",
          7.0, _arch, is_card=True),
    Scene("The <b>executive cockpit</b>: one screen, three engines' worth of signal.",
          "This is the cockpit. It's one FastAPI service with a static page — everything you "
          "see is computed live from a deterministic, seeded dataset of 167 AWS deployments.",
          4.5, lambda p: (_clear_card(p), highlight(p, None))),
    Scene("KPI strip: <b>~$4.97M</b> annualized spend · <b>51</b> anomalies · <b>1</b> CRITICAL capacity stream",
          "The KPI strip answers the first question any executive asks: what's the run-rate, "
          "is anything on fire? About five million dollars annualised, fifty-one cost anomalies, "
          "and one critical capacity alert.",
          5.5, lambda p: highlight(p, "#kpis")),
    Scene("<b>Capacity-Mngt-App</b>: worst-first. Assist / us-east-1 is already over the 80% headroom line.",
          "Capacity-Mngt-App ranks every product-region stream worst-first. Assist in us-east-1 "
          "is already above the eighty percent headroom threshold — status CRITICAL.",
          5.5, lambda p: highlight(p, "#capacity")),
    Scene("<b>Cost-Mngt-App</b>: spikes scored by robust z (median + MAD) — hover a row for the root cause.",
          "Cost-Mngt-App scores each region-service stream against its own rolling median and "
          "MAD baseline, so a spike can't poison the baseline it's measured against. Each row "
          "carries a suspected root cause.",
          5.5, lambda p: highlight(p, "#anomalies")),
    Scene("45-day spend forecast with a 95% prediction interval — in-sample MAPE ≈ 1.2%.",
          "And the forward view: a forty-five-day estate spend forecast with an honest "
          "prediction band. In-sample error is about one point two percent.",
          5.0, lambda p: highlight(p, "#chart")),
    Scene("Now the point of FinSight: <b>just ask</b>.",
          "But dashboards make executives hunt. FinSight lets them just ask.",
          2.5, lambda p: highlight(p, "#q")),
    Scene("Q1 — forward risk. Answer leads with the CRITICAL stream and cites <b>[FACT-012]</b>.",
          "Will we run out of capacity next quarter? The retriever boosts facts with an elevated "
          "status, so the answer leads with the critical stream, cites FACT-012, and recommends "
          "an action. Underneath, you see the exact evidence it retrieved.",
          7.0, lambda p: ask(p, "Will we run out of capacity next quarter?")),
    Scene("Q2 — backward look. Spike, baseline, z-score and suspected cause — all cited.",
          "Why did spend spike, and where? Now the evidence is Cost-Mngt-App anomaly cards: the "
          "dollar spike, its baseline, the robust z-score and the suspected root cause.",
          7.0, lambda p: ask(p, "Why did our cloud spend spike, and where?")),
    Scene("Q3 — drill-down. Naming a region + service boosts exact-match facts.",
          "Executives drill down naturally. Name a service and region, and the retriever boosts "
          "the facts that match those dimensions exactly — here, the orphaned RDS read-replica "
          "in eu-west-1.",
          7.0, lambda p: ask(p, "What happened with RDS in eu-west-1?")),
    Scene("Q4 — a health check on one stream: capacity <i>and</i> cost evidence together.",
          "Is Assist in us-east-1 healthy? One question pulls capacity and cost facts together "
          "for the same stream — the kind of synthesis that takes an analyst an hour.",
          7.0, lambda p: ask(p, "Is Assist in us-east-1 healthy?")),
    Scene("Q5 — off-domain. <b>No evidence, no answer.</b> FinSight declines instead of hallucinating.",
          "And the guarantee that matters to finance: ask something outside the domain and "
          "FinSight declines. A relevance floor in the retriever means no evidence, no answer — "
          "it never dresses up irrelevant facts.",
          6.5, lambda p: ask(p, "Who won the cricket world cup?")),
    Scene("", "Everything here is also an API. The same grounded answers, citations and evidence "
              "are one POST away, so FinSight can sit behind Slack, Teams, or an agent.",
          6.0, lambda p: _api_card(p), is_card=True),
    Scene("", "FinSight 2.0: deterministic engines own the numbers, the language model only "
              "phrases them. Runs offline in template mode, or fluent with Claude — one command "
              "to demo.",
          6.0, lambda p: card(p, "<h1>Fin<span>Sight</span> 2.0</h1>"
                                 "<p>Engines own the numbers · the LLM only phrases them · "
                                 "every claim cited.<br><br>"
                                 "<code style='color:#35E0A1'>./demo/demo.sh</code> &nbsp;·&nbsp; "
                                 "<code style='color:#35E0A1'>docker compose up</code></p>"),
          is_card=True),
]


# --------------------------------------------------------------------------- #
# Recording
# --------------------------------------------------------------------------- #

def _ts(sec: float, sep: str = ",") -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def _chromium_path() -> str | None:
    """Prefer an explicit/preinstalled Chromium; else let Playwright resolve its own."""
    import os
    for cand in (os.environ.get("FINSIGHT_CHROMIUM"), "/opt/pw-browsers/chromium"):
        if cand and Path(cand).exists():
            return cand
    return None


def record(url: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.webm"):
        old.unlink()

    timeline: list[tuple[float, float, Scene]] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=_chromium_path())
        ctx = browser.new_context(
            viewport={"width": W, "height": H},
            record_video_dir=str(OUT),
            record_video_size={"width": W, "height": H},
            color_scheme="dark",
        )
        page = ctx.new_page()
        t0 = time.monotonic()
        page.goto(url)
        overlay(page)
        page.wait_for_selector("#capacity table", timeout=120_000)
        page.wait_for_selector("#chart svg", timeout=120_000)

        for sc in SCENES:
            start = time.monotonic() - t0
            if not sc.is_card:
                caption(page, sc.caption)
            sc.action(page)
            if sc.is_card:
                caption(page, "")
            # Hold long enough for the narration to be read aloud at a calm
            # pace, so a voice-over recorded against narration.md fits.
            spoken = len(sc.narration.split()) / WORDS_PER_SEC
            elapsed = time.monotonic() - t0 - start
            time.sleep(max(sc.hold, spoken - elapsed + 0.8))
            timeline.append((start, time.monotonic() - t0, sc))

        time.sleep(0.5)
        video_path = Path(page.video.path())
        ctx.close()
        browser.close()

    mp4 = OUT / "finsight_demo.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_path),
         "-c:v", "libx264", "-preset", "slow", "-crf", "26", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", str(mp4)],
        check=True,
    )
    video_path.unlink(missing_ok=True)

    # Subtitles + narration from the same timeline.
    import re
    strip = lambda s: re.sub(r"<[^>]+>", "", s)
    with open(OUT / "finsight_demo.srt", "w") as f:
        for i, (a, b, sc) in enumerate(timeline, 1):
            f.write(f"{i}\n{_ts(a)} --> {_ts(b)}\n{strip(sc.caption) or strip(sc.narration)}\n\n")
    with open(OUT / "narration.md", "w") as f:
        f.write("# FinSight 2.0 demo — narration script\n\n"
                "Timestamps match `finsight_demo.mp4`. Read at a calm pace; each line fits its scene.\n\n"
                "| Time | On screen | Say |\n|---|---|---|\n")
        for a, _b, sc in timeline:
            f.write(f"| {_ts(a, '.')[3:8]} | {strip(sc.caption) or '(title card)'} | {sc.narration} |\n")
    return mp4


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--publish", action="store_true",
                    help="also copy outputs into docs/media/ for the repo")
    args = ap.parse_args()
    mp4 = record(args.url)
    print(f"video     -> {mp4}")
    print(f"subtitles -> {OUT / 'finsight_demo.srt'}")
    print(f"narration -> {OUT / 'narration.md'}")
    if args.publish:
        media = Path(__file__).resolve().parents[2] / "docs" / "media"
        media.mkdir(parents=True, exist_ok=True)
        for name in ("finsight_demo.mp4", "finsight_demo.srt", "narration.md"):
            shutil.copy(OUT / name, media / name)
        print(f"published -> {media}")


if __name__ == "__main__":
    main()
