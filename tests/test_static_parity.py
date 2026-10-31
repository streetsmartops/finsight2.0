"""
The GitHub Pages demo answers questions in the browser with a JS port of the
retriever + template composer. This test proves the port gives exactly the
same answer, citations and evidence as src/finsight/rag.py.

Skipped when Node.js is not installed.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "demo" / "static"))

from finsight import FinSightRAG, generate  # noqa: E402

QUESTIONS = [
    "Will we run out of capacity next quarter?",
    "Are we at risk of running out of capacity?",
    "Why did our cloud spend spike, and where?",
    "Why did our cloud spend spike?",
    "What is our annualized spend?",
    "What's driving our annualized spend?",
    "Is Assist in us-east-1 healthy?",
    "What happened with RDS in eu-west-1?",
    "Any anomalies in Observability for us-west-2?",
    "How is Engage doing in ap-southeast-1?",
    "Which region spends the most?",
    "What does Capacity-Mngt-App forecast for spend in 45 days?",
    "Tell me about EKS-Compute cost spikes",
    "DataTransfer problem in us-east-1?",
    "Is anything over the headroom threshold?",
    "How much does Analyze cost?",
    "What was the largest driver of the spend change?",
    "breach",
    "WHO WON THE CRICKET WORLD CUP?",
    "What is the airspeed velocity of an unladen swallow?",
    "",
    "us-east-1 us-east-1 us-east-1 capacity",
]

RUNNER = """
const fs = require("fs");
const { makeRAG } = require(process.argv[2]);
const rag = makeRAG(JSON.parse(fs.readFileSync(process.argv[3], "utf8")));
const qs = JSON.parse(fs.readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(qs.map(q => rag.ask(q))));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_js_port_matches_python(tmp_path, monkeypatch):
    from build import export_index

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)   # Python side must use the template too
    cost, util = generate()
    rag = FinSightRAG(cost, util)

    index_file = tmp_path / "rag_index.json"
    index_file.write_text(json.dumps(export_index(rag)))
    runner = tmp_path / "runner.js"
    runner.write_text(RUNNER)

    out = subprocess.run(
        ["node", str(runner), str(ROOT / "demo" / "static" / "finsight_static.js"), str(index_file)],
        input=json.dumps(QUESTIONS), capture_output=True, text=True, check=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    js_answers = json.loads(out.stdout)

    for q, js in zip(QUESTIONS, js_answers):
        py = rag.ask(q).to_dict()
        assert js["answer"] == py["answer"], f"answer differs for {q!r}"
        assert js["citations"] == py["citations"], f"citations differ for {q!r}"
        assert [e["id"] for e in js["evidence"]] == [e["id"] for e in py["evidence"]], \
            f"evidence differs for {q!r}"
        assert js["used_llm"] is False
