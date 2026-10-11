"""Baseline comparison: bare Gemini vs Bhav on the same questions.

Not a benchmark - evidence for the "why not just ask Gemini" question, which a
judge will ask. Writes baseline_results.md.

Run:  .venv/Scripts/python.exe compare_baseline.py
"""
from __future__ import annotations

import os
import textwrap

from google import genai
from google.genai import types

from bhav import routing  # noqa: F401  - loads .env

MODEL = "gemini-3.6-flash"

# Deliberately phrased as a Delhi resident would ask, with no system prompt and
# no tools: this is what the user gets if they skip Bhav and open Gemini.
PROBES = [
    ("facility_hallucination",
     "I have an old CFL tube light to throw away. I live in Rohini, Delhi. "
     "Where exactly do I take it? Give me a specific place."),
    ("us_default_medicine",
     "I have a box of expired medicines at home in Delhi. How do I dispose of them?"),
    ("false_optimism_wrapper",
     "I have an empty chips packet. Can it be recycled? What should I do with it?"),
    ("pooja_flowers",
     "I have flowers and garlands left over from pooja at home in Delhi. "
     "How should I dispose of them?"),
    ("scrap_price",
     "How much is old newspaper (raddi) worth per kg in Delhi right now?"),
]


def ask(client: genai.Client, prompt: str) -> str:
    r = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="low")),
    )
    return (r.text or "").strip()


def main() -> None:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    out = ["# Bare Gemini baseline", "",
           f"Model: `{MODEL}`, no system prompt, no tools.", "",
           "What a Delhi resident gets if they skip Bhav and just open Gemini.", ""]

    for name, prompt in PROBES:
        print(f"-- {name}")
        try:
            answer = ask(client, prompt)
        except Exception as exc:
            answer = f"(call failed: {type(exc).__name__}: {exc})"
        out += [f"## {name}", "", f"**Asked:** {prompt}", "",
                "**Gemini answered:**", "",
                textwrap.indent(answer, "> ").replace("\n>", "\n> "), ""]

    with open("baseline_results.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    print("\nwrote baseline_results.md")


if __name__ == "__main__":
    main()
