"""Render flashcards.json -> FLASHCARDS.md (GitHub) + finsight_anki.csv (Anki/Quizlet import).

    python docs/flashcards/build_flashcards.py
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "flashcards.json").read_text())

md = [f"# {data['title']}", "",
      "Three decks, one per audience. Click a question to reveal the answer.",
      "Import `finsight_anki.csv` into Anki or Quizlet (semicolon-separated: front;back;tags).",
      "For a flip-card study mode, open [`docs/interactive/flashcards.html`](../interactive/flashcards.html).", ""]
for d in data["decks"]:
    md.append(f"- [{d['name']}](#{d['id']}) · {len(d['cards'])} cards · {d['blurb']}")
for d in data["decks"]:
    md += ["", f"<a id=\"{d['id']}\"></a>", f"## {d['name']}", "", f"_{d['blurb']}_", ""]
    for i, c in enumerate(d["cards"], 1):
        md += [f"<details><summary><b>{i}. {c['q']}</b></summary>", "", c["a"], "", "</details>", ""]
(HERE / "FLASHCARDS.md").write_text("\n".join(md))

with open(HERE / "finsight_anki.csv", "w", newline="") as f:
    w = csv.writer(f, delimiter=";")
    for d in data["decks"]:
        for c in d["cards"]:
            w.writerow([c["q"], c["a"].replace("*", ""), f"finsight {d['id']}"])

print(f"{sum(len(d['cards']) for d in data['decks'])} cards -> FLASHCARDS.md, finsight_anki.csv")
