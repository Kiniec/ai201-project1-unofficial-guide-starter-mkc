"""
app.py  
Gradio web UI for the Unofficial Guide RAG pipeline.

Usage
-----
    python app.py
Then open http://127.0.0.1:7860 in your browser.
"""

import os
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from generate_response import generate_response  # noqa: E402 (needs .env loaded first)


# ── Backend ───────────────────────────────────────────────────────────────────

def ask(question: str):
    """RAG pipeline wrapper for Gradio."""
    if not question or not question.strip():
        return "_Please enter a question._", ""

    try:
        result = generate_response(question.strip())

        sources_lines = []
        for s in result["sources"]:
            url = s["url"]
            if url.startswith("http"):
                sources_lines.append(f"- **{s['source']}** — [{url}]({url})")
            else:
                sources_lines.append(f"- **{s['source']}** — `{url}`")

        sources_md = "\n".join(sources_lines) if sources_lines else "_No sources retrieved._"
        return result["answer"], sources_md

    except Exception as exc:
        return f"**Error:** {exc}", ""


# ── Content ───────────────────────────────────────────────────────────────────

HEADER = """
# The Unofficial Guide
### Housing & Food Resources for Dallas-Area College Students

More than **1.5 million** college students face homelessness during their collegiate career.
This guide helps Dallas-area students quickly find local shelters, food pantries, emergency
funds, and student support programs.

> Answers come **only** from verified local sources — the guide will tell you when it
> doesn't have enough information rather than guess.
"""

HOW_TO = """
### How to use
1. Type your question in the box below, **or** click an example question to load it
2. Press **Ask** or hit Enter
3. Read the grounded answer, then check the **Sources** section to verify
"""

EXAMPLES = [
    ["What colleges in Dallas have emergency support for students?"],
    ["What are the intake hours for Dallas Life?"],
    ["What are the intake days for Dallas Life?"],
    ["Where can I get food on the campus of UT Dallas?"],
    ["What do I need to bring to Dallas Life for intake?"],
    ["What emergency housing resources are available in Dallas?"],
    ["Does Dallas College help students experiencing homelessness?"],
    ["What are the hours for the food pantry at Holy Trinity?"],
]

PLACEHOLDER = "e.g. Where can I get emergency food near UT Dallas?"

FOOTER = """
---
*Built with [Gradio](https://gradio.app) · Retrieval by [ChromaDB](https://www.trychroma.com) ·
Embeddings: all-MiniLM-L6-v2 · Generation: Groq llama-3.3-70b-versatile*
"""


# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks(title="The Unofficial Guide — Dallas Student Resources") as demo:

    gr.Markdown(HEADER)
    gr.Markdown(HOW_TO)

    with gr.Row():
        question_box = gr.Textbox(
            label="Your question",
            placeholder=PLACEHOLDER,
            lines=2,
            scale=5,
        )
        ask_btn = gr.Button("Ask", variant="primary", scale=1, min_width=80)

    gr.Examples(
        examples=EXAMPLES,
        inputs=question_box,
        label="Example questions — click any to load",
    )

    gr.Markdown("---")

    answer_box = gr.Markdown(
        value="_Your answer will appear here._",
        label="Answer",
    )

    with gr.Accordion("Sources", open=True):
        sources_box = gr.Markdown(
            value="_Sources will appear here after you ask a question._"
        )

    gr.Markdown(FOOTER)

    # Wire events
    ask_btn.click(fn=ask, inputs=question_box, outputs=[answer_box, sources_box])
    question_box.submit(fn=ask, inputs=question_box, outputs=[answer_box, sources_box])


if __name__ == "__main__":
    # theme= moved to launch() in Gradio 6.x (was gr.Blocks() in earlier versions)
    demo.launch(theme='allenai/gradio-theme')
    #demo.launch(theme="gstaff/xkcd")
    
