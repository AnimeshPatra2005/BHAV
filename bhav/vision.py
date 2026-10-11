"""Gemini vision: photo -> candidate waste category.

Returns a ranked guess plus alternatives rather than a single answer, because the
UI is built to confirm with the user instead of asserting. A model that is 70%
sure and says so is more useful here than one that is wrong confidently.
"""
from __future__ import annotations

import functools
import json
import mimetypes
import os
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from . import routing

# 3.6 Flash, not 3.8. 3.8 was returning 503 under load and its heavier default
# reasoning adds latency this task does not need - identifying a bottle is not a
# long-horizon problem. Retries below still cover transient 503s on 3.6.
# Add more models here (comma-separated) only if you want a fallback chain.
MODEL_CHAIN = [
    m.strip() for m in os.environ.get(
        "BHAV_MODEL_CHAIN", "gemini-3.6-flash"
    ).split(",") if m.strip()
]

_RETRYABLE = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "overloaded")
_MAX_ATTEMPTS = 3

_PROMPT = """You identify household items so they can be routed for disposal in Delhi.

Pick the single best matching category id from this list, plus up to two
alternatives the item could plausibly be instead.

{catalogue}

Rules:
- Answer with category ids from the list, never invented ones.
- confidence is your honest probability for the top pick, 0.0 to 1.0.
- If NOTHING on the list genuinely fits, still give the closest id but set
  confidence below 0.45 and say plainly in `note` that this item has no proper
  category yet. Do not dress up a poor match as a confident answer - a wrong
  route stated firmly is worse than an admitted gap.
- If the photo is unclear or shows several items, say so in `note` and lower confidence.
- If an item could be either a CFL/fluorescent tube or an LED tube, say so explicitly
  in `note` and offer both as candidates. The disposal routes differ and guessing
  wrong here matters.
- If you see any battery, power bank or device containing a cell, mention it in `note`
  even if it is not your top pick.

Return only JSON of this shape:
{{"category_id": "...", "confidence": 0.0, "alternatives": ["...", "..."],
  "visible_label": "what you actually see, in a few words", "note": "..."}}"""


def _catalogue() -> str:
    lines = []
    for c in routing.categories():
        lines.append(f"- {c['id']}: {c['name']} (e.g. {', '.join(c['aliases'][:4])})")
    return "\n".join(lines)


@functools.lru_cache(maxsize=1)
def _client() -> genai.Client:
    """Cached so the Client stays referenced.

    Returning a fresh Client here and immediately chaining off it leaves the
    Client as an unreferenced temporary: Python finalises it, closing the
    underlying httpx connection mid-request, and the call dies with
    "Cannot send a request, as the client has been closed."
    """
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set. Copy .env.example and fill it in.")
    return genai.Client(api_key=key)


def identify(image_path: str | Path) -> dict[str, Any]:
    """Identify the item in an image. Returns the parsed guess dict."""
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"No such image: {path}")

    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"

    contents = [
        types.Part.from_bytes(data=path.read_bytes(), mime_type=mime),
        _PROMPT.format(catalogue=_catalogue()),
    ]
    raw, model_used = _generate(contents)

    result = _parse(raw)
    result["model_used"] = model_used
    return result


def _generate(contents: list[Any]) -> tuple[str | None, str]:
    """Call the first model in the chain that answers. Returns (text, model_id).

    Retries retryable errors with backoff, then falls to the next model. A demo
    that dies because one model is briefly overloaded is not a demo.
    """
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        # No temperature / top_p / top_k: Gemini 3.x rejects those sampling params.
        # thinking_level lives inside ThinkingConfig - setting it on
        # GenerateContentConfig directly is silently ignored. "low" because this is
        # a classification, not a reasoning task, and "medium" makes the user wait.
        thinking_config=types.ThinkingConfig(thinking_level="low"),
    )

    last_error: Exception | None = None
    for model_id in MODEL_CHAIN:
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = _client().models.generate_content(
                    model=model_id, contents=contents, config=config
                )
                return response.text, model_id
            except Exception as exc:
                last_error = exc
                if not any(tok in str(exc) for tok in _RETRYABLE):
                    raise  # a real error - do not mask it by trying another model
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(
        f"All models unavailable ({', '.join(MODEL_CHAIN)}). Last error: {last_error}"
    )


def _parse(raw: str | None) -> dict[str, Any]:
    """Parse the model's JSON defensively and drop any hallucinated ids."""
    fallback = {
        "category_id": None,
        "confidence": 0.0,
        "alternatives": [],
        "visible_label": "",
        "note": "Could not read the model response.",
    }
    if not raw:
        return fallback

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        fallback["note"] = f"Model did not return JSON: {raw[:200]}"
        return fallback

    valid = set(routing.category_ids())
    top = data.get("category_id")

    # The model occasionally answers with a plain label instead of an id.
    if top not in valid:
        recovered = routing.match_text(str(top or ""))
        top = recovered[0] if recovered else None

    alts = [a for a in data.get("alternatives", []) if a in valid and a != top]

    return {
        "category_id": top,
        "confidence": float(data.get("confidence") or 0.0),
        "alternatives": alts[:2],
        "visible_label": str(data.get("visible_label") or ""),
        "note": str(data.get("note") or ""),
    }
