# FinSight 2.0 — documentation and demo kit

| I want to… | Go to |
|---|---|
| **See it working in 3 minutes** | [Demo video](media/finsight_demo.mp4) (captioned) · [subtitles](media/finsight_demo.srt) · [narration script](media/narration.md) |
| **Run a live demo** | `./demo/demo.sh --offline`, then the [Presenter guide](../demo/PRESENTER_GUIDE.md) |
| **Get a shareable URL** | [Deploy recipes](../demo/deploy/README.md): Render · Fly.io · Cloud Run · VM |
| **Understand the system** | [Architecture](diagrams/ARCHITECTURE.md): context, containers, components, deployment |
| **Follow a number end to end** | [Data flow](diagrams/DATA_FLOW.md): DFD L0/L1, `/api/ask` sequence, fact-card lineage |
| **See specified behaviour** | [BDD flows](diagrams/BDD_FLOWS.md) + [Gherkin features](bdd/) with traceability to tests |
| **Do a specific task** | [How-to guide](HOW_TO.md): use, run, extend, troubleshoot |
| **Learn or teach it** | [Flashcards](flashcards/FLASHCARDS.md) (38 cards, 3 audiences) · [interactive](interactive/flashcards.html) · [Anki CSV](flashcards/finsight_anki.csv) |
| **Brainstorm what's next** | [Ideation mind map](MINDMAP.md) · [interactive](interactive/mindmap.html) |

## Regenerating generated files
| Output | Source | Command |
|---|---|---|
| `flashcards/FLASHCARDS.md`, `finsight_anki.csv` | `flashcards/flashcards.json` | `python docs/flashcards/build_flashcards.py` |
| `interactive/*.html` | `flashcards.json`, `MINDMAP.md` | `python docs/interactive/build.py` |
| `media/finsight_demo.*`, `narration.md` | `SCENES` in `demo/video/record_demo.py` | `make video` (server running), then add `--publish` |
