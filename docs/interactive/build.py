"""Build the interactive flashcards + mind map pages from their single sources.

    python docs/interactive/build.py [--fragments DIR]

Sources : docs/flashcards/flashcards.json, docs/MINDMAP.md
Outputs : docs/interactive/flashcards.html, docs/interactive/mindmap.html (standalone; open in any browser)
          --fragments DIR also writes skeleton-less copies (used for publishing as hosted pages)
"""
import argparse
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent


def inline_md(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


def parse_mindmap(md: str):
    block = re.search(r"```mermaid\s*\nmindmap\n(.*?)```", md, re.S).group(1)
    root, stack = None, []
    for line in block.splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        text = line.strip()
        m = re.match(r"root\(\((.*)\)\)", text)
        if m:
            text = m.group(1).replace("<br/>", " · ")
        tag = None
        t = re.match(r"(.*) · (now|next|later)$", text)
        if t:
            text, tag = t.group(1), t.group(2)
        node = {"text": text, "tag": tag, "kids": []}
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if stack:
            stack[-1][1]["kids"].append(node)
        else:
            root = node
        stack.append((indent, node))
    prompts = [inline_md(p) for p in re.findall(r"^\d+\. (.+)$", md.split("## Prompts", 1)[1].split("##", 1)[0], re.M)]
    rows = [r for r in md.split("## Suggested first sprint", 1)[1].splitlines() if r.startswith("|")]
    cells = lambda r: [inline_md(c.strip()) for c in r.strip("|").split("|")]
    sprint = {"head": cells(rows[0]), "rows": [cells(r) for r in rows[2:]]}
    return root, prompts, sprint


def standalone(fragment: str) -> str:
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            "</head>\n<body>\n" + fragment + "\n</body>\n</html>\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fragments", type=Path)
    args = ap.parse_args()

    cards = json.loads((DOCS / "flashcards" / "flashcards.json").read_text())
    tree, prompts, sprint = parse_mindmap((DOCS / "MINDMAP.md").read_text())
    j = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")

    pages = {
        "flashcards.html": (HERE / "_flashcards.tmpl.html").read_text().replace("/*__DATA__*/null", j(cards)),
        "mindmap.html": (HERE / "_mindmap.tmpl.html").read_text()
            .replace("/*__TREE__*/null", j(tree))
            .replace("/*__PROMPTS__*/null", j(prompts))
            .replace("/*__SPRINT__*/null", j(sprint)),
    }
    for name, frag in pages.items():
        (HERE / name).write_text(standalone(frag))
        if args.fragments:
            args.fragments.mkdir(parents=True, exist_ok=True)
            (args.fragments / name).write_text(frag)
        print(f"wrote {name}")


if __name__ == "__main__":
    main()
