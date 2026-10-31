"""
Build the static FinSight demo for GitHub Pages.

    python demo/static/build.py [--out site]

The real engines run once here: every GET endpoint is snapshotted through
FastAPI's TestClient (so the JSON is byte-for-byte what the server returns),
and the RAG retriever's fitted TF-IDF index is exported. In the browser,
finsight_static.js answers /api/* from those files and runs retrieval +
template composition locally, so free-text questions work with no server.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

GET_ENDPOINTS = ["health", "overview", "capacity", "anomalies", "forecast/cost"]

BANNER = """
<div id="fs-static-banner" style="display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center;justify-content:center;
  padding:9px 16px;background:#0F2A20;border-bottom:1px solid #1F5E45;color:#CFEFE2;
  font:13px/1.45 ui-monospace,Menlo,Consolas,monospace;text-align:center">
  <span><b style="color:#35E0A1">Live static demo</b> · the engines ran at build time; your questions are answered
  in your browser by the same retriever and template composer as the server (no LLM, nothing leaves the page).</span>
  <span style="display:flex;gap:12px;flex-wrap:wrap;justify-content:center">
    <a style="color:#35E0A1" href="media/finsight_demo.mp4">▶ Demo video</a>
    <a style="color:#35E0A1" href="flashcards.html">Flashcards</a>
    <a style="color:#35E0A1" href="mindmap.html">Mind map</a>
    <a style="color:#35E0A1" href="https://github.com/streetsmartops/finsight2.0">GitHub</a>
  </span>
</div>
"""


def export_index(rag) -> dict:
    """Serialise the fitted retriever so the JS port reproduces it exactly."""
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

    vec = rag.retriever.vectorizer
    assert vec.token_pattern == r"[A-Za-z0-9][A-Za-z0-9\-]+" and vec.ngram_range == (1, 2), \
        "Retriever config changed — update finsight_static.js to match"
    m = rag.retriever.matrix.tocsr()
    rows = [[[int(j), round(float(v), 10)] for j, v in zip(m.indices[m.indptr[i]:m.indptr[i + 1]],
                                                           m.data[m.indptr[i]:m.indptr[i + 1]])]
            for i in range(m.shape[0])]
    return {
        "stop_words": sorted(ENGLISH_STOP_WORDS),
        "vocab": {k: int(v) for k, v in vec.vocabulary_.items()},
        "idf": [round(float(x), 10) for x in vec.idf_],
        "rows": rows,
        "cards": [{"id": c.id, "source": c.source, "text": c.text,
                   "metadata": json.loads(json.dumps(c.metadata, default=str))} for c in rag.cards],
    }


def build(out: Path) -> None:
    from fastapi.testclient import TestClient
    import api.main as app_module

    if out.exists():
        shutil.rmtree(out)
    (out / "api").mkdir(parents=True)

    with TestClient(app_module.app) as client:      # runs the startup hook
        for ep in GET_ENDPOINTS:
            r = client.get(f"/api/{ep}")
            r.raise_for_status()
            data = r.json()
            if ep == "health":
                data["llm_configured"] = False      # the static demo never calls an LLM
                data["mode"] = "static"
            (out / "api" / f"{ep.replace('/', '_')}.json").write_text(json.dumps(data))
        index = export_index(app_module.State.rag)
    (out / "api" / "rag_index.json").write_text(json.dumps(index, separators=(",", ":")))

    # Cockpit page: same HTML as the server's, plus the shim and a banner.
    html = (ROOT / "api" / "static" / "index.html").read_text()
    html = html.replace("<body>", "<body>\n" + BANNER, 1)
    html = re.sub(r"(\n<script>)", '\n<script src="finsight_static.js"></script>\\1', html, count=1)
    (out / "index.html").write_text(html)
    shutil.copy(HERE / "finsight_static.js", out / "finsight_static.js")

    # Companion material.
    for name in ("flashcards.html", "mindmap.html"):
        src = ROOT / "docs" / "interactive" / name
        if src.exists():
            shutil.copy(src, out / name)
    media = ROOT / "docs" / "media"
    if media.exists():
        shutil.copytree(media, out / "media")
    (out / ".nojekyll").write_text("")

    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"static demo -> {out}  ({len(index['cards'])} facts, {len(index['vocab'])} terms, "
          f"{size / 1e6:.1f} MB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "site")
    build(ap.parse_args().out.resolve())
