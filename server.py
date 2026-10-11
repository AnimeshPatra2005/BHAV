"""Bhav web server.

Starlette rather than FastAPI on purpose: starlette, uvicorn and python-multipart
are already in the venv, and FastAPI 0.111 conflicts with the starlette that
strands-agents pulls in.

Run:  .venv/Scripts/python.exe server.py
"""
from __future__ import annotations

import json
import os
import traceback
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import uvicorn
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from bhav import routing
from bhav.advice import ADVICE_PROMPT, Advice
from bhav.agent import build_agent

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
UPLOADS = ROOT / "uploads"
UPLOADS.mkdir(exist_ok=True)

ALLOWED_SUFFIX = {".png", ".jpg", ".jpeg", ".webp", ".heic"}
MAX_BYTES = 12 * 1024 * 1024


def _flatten(content: Any) -> Any:
    """Tool results arrive as a list of {"text": ...} / {"json": ...} blocks."""
    if not isinstance(content, list):
        return content
    out = []
    for block in content:
        if isinstance(block, dict):
            if "json" in block:
                return block["json"]
            if "text" in block:
                out.append(block["text"])
        else:
            out.append(block)
    if not out:
        return None

    joined = "\n".join(str(o) for o in out)
    # Strands serialises a dict tool return to JSON *text*, not a json block, so
    # parse it back. Without this the result card gets a string it cannot read
    # and silently renders empty while the prose answer still looks fine.
    try:
        return json.loads(joined)
    except (json.JSONDecodeError, TypeError):
        return joined


def _trace_and_facts(agent: Any) -> tuple[list[dict], dict]:
    """Walk the message history for tool calls, pairing each with its result.

    Reading agent.messages rather than hooking callback_handler: the message
    history is a stable, documented surface, and the trace is what proves the
    agent actually orchestrated tools rather than answering from the prompt.
    """
    trace: list[dict] = []
    facts: dict[str, Any] = {}
    pending: list[str] = []

    for msg in getattr(agent, "messages", []) or []:
        for block in (msg.get("content") or []):
            if not isinstance(block, dict):
                continue
            if "toolUse" in block:
                tu = block["toolUse"]
                name = tu.get("name")
                pending.append(name)
                trace.append({"kind": "call", "name": name, "input": tu.get("input")})
            elif "toolResult" in block:
                tr = block["toolResult"]
                name = pending.pop(0) if pending else None
                payload = _flatten(tr.get("content"))
                trace.append({
                    "kind": "result", "name": name,
                    "status": tr.get("status"), "output": payload,
                })
                # Keep the structured payloads the result card renders from.
                if name and isinstance(payload, dict):
                    facts[name] = payload
    return trace, facts


def _video_url(advice: dict | None) -> str | None:
    """Build a YouTube SEARCH url from the model's query.

    The model supplies search terms, never a video id, and we build the url here.
    A model-invented id could be dead or point at something entirely different;
    a search cannot be wrong in that way.
    """
    if not advice or not advice.get("needs_video"):
        return None
    q = (advice.get("video_query") or "").strip()
    if not q:
        return None
    return "https://www.youtube.com/results?search_query=" + quote_plus(q)


def _card(facts: dict, advice: dict | None = None) -> dict:
    """Shape the four route states for the UI.

    SPECIAL never renders as a bin, and a category with no money never renders an
    empty price - those two rules live here so the UI cannot get them wrong.
    """
    route_info = facts.get("lookup_route") or {}
    value = facts.get("estimate_value") or {}
    facility = facts.get("find_facility") or {}
    reuse = facts.get("get_reuse") or {}
    ident = facts.get("identify_item") or {}

    route = route_info.get("route")
    meta = routing.ROUTE_META.get(route, {}) if route else {}

    price = None
    if value.get("basis") in {"per_kg", "per_item"} and value.get("range_inr"):
        low, high = value["range_inr"]
        price = {
            "low": low, "high": high,
            "verified": bool(value.get("verified")),
            "basis": value["basis"],
        }

    facs = facility.get("facilities") or []
    return {
        "anchor": routing.anchor(),
        "item": route_info.get("category_name") or ident.get("category_name"),
        "category_id": route_info.get("category_id"),
        "confidence": ident.get("confidence"),
        "alternatives": ident.get("alternatives") or [],
        "visible_label": ident.get("visible_label"),
        "model_used": ident.get("model_used"),
        "route": route,
        "route_verb": meta.get("verb"),
        "tone": meta.get("tone"),
        "bin_colour": meta.get("bin"),
        "hazard": route_info.get("hazard"),
        # Generated first, table copy only as a fallback if the model call failed.
        "why_not_bin": (advice or {}).get("why_not_bin")
                       or route_info.get("why_not_bin"),
        "steps": (advice or {}).get("steps") or route_info.get("steps") or [],
        "in_short": (advice or {}).get("in_short") or [],
        "learn": _video_url(advice) or route_info.get("learn"),
        "generated": bool(advice),
        "destination": route_info.get("destination"),
        "legal_basis": route_info.get("legal_basis"),
        # Two independent sources say "there is no money here": the category flag
        # (medicine) and estimate_value returning no_value (lithium cells, malba).
        # Either one must produce the explanatory line, not an empty space.
        "no_monetary_value": bool(route_info.get("no_monetary_value"))
                             or bool(value.get("no_value")),
        "price": price,
        "facilities": facs,
        "any_facility_verified": bool(facility.get("any_verified")),
        "reuse": reuse if reuse.get("has_reuse") else None,
    }


async def api_route(request):
    form = await request.form()
    upload = form.get("photo")
    if upload is None or not getattr(upload, "filename", ""):
        return JSONResponse({"error": "No photo uploaded."}, status_code=400)

    suffix = Path(upload.filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIX:
        return JSONResponse(
            {"error": f"Unsupported file type {suffix or '(none)'}."}, status_code=400)

    data = await upload.read()
    if len(data) > MAX_BYTES:
        return JSONResponse({"error": "Photo is too large."}, status_code=400)

    dest = UPLOADS / f"{uuid.uuid4().hex}{suffix}"
    dest.write_bytes(data)

    def _run():
        agent = build_agent()
        result = agent(f"I want to get rid of this. Photo is at: {dest}")
        trace, facts = _trace_and_facts(agent)

        # Second pass over the same conversation: the tools have established the
        # facts, now have the model write the explanation and how-to for THIS
        # item. Hardcoding that text made every answer read the same.
        advice = None
        try:
            advice = agent.structured_output(Advice, ADVICE_PROMPT).model_dump()
        except Exception:
            traceback.print_exc()  # fall back to the table's static copy

        return str(result), trace, facts, advice

    try:
        answer, trace, facts, advice = await run_in_threadpool(_run)
    except Exception as exc:
        traceback.print_exc()
        return JSONResponse(
            {"error": f"{type(exc).__name__}: {exc}"}, status_code=500)
    finally:
        dest.unlink(missing_ok=True)

    return JSONResponse(
        {"answer": answer, "card": _card(facts, advice), "trace": trace})


async def index(request):
    return FileResponse(STATIC / "index.html")


async def try_page(request):
    return FileResponse(STATIC / "try.html")


async def flow_page(request):
    return FileResponse(STATIC / "flow.html")


app = Starlette(routes=[
    Route("/", index),
    Route("/try", try_page),
    Route("/flow", flow_page),
    Route("/api/route", api_route, methods=["POST"]),
    Mount("/static", StaticFiles(directory=STATIC), name="static"),
])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port)
