"""Route resolution over the Delhi waste routing table.

Deliberately has no LLM dependency: everything here is testable without an API key,
which is what lets the routing logic be trusted while the vision layer is still shaky.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Display contract for the four routes. SPECIAL must never be rendered as a
# variant of a bin - that distinction is the product.
ROUTE_META: dict[str, dict[str, Any]] = {
    "SELL": {
        "verb": "Sell it",
        "tone": "value",
        "colour": "#1a7f37",
        "shows_price": True,
        "bin": None,
    },
    "BIN_DRY": {
        "verb": "Dry bin",
        "tone": "neutral",
        "colour": "#6b7280",
        "shows_price": False,
        "bin": "blue",
    },
    "BIN_WET": {
        "verb": "Wet bin",
        "tone": "neutral",
        "colour": "#15803d",
        "shows_price": False,
        "bin": "green",
    },
    "SPECIAL": {
        "verb": "Do NOT bin this",
        "tone": "danger",
        "colour": "#b91c1c",
        "shows_price": False,
        "bin": None,
    },
}


@functools.lru_cache(maxsize=1)
def _table() -> dict[str, Any]:
    with open(DATA_DIR / "delhi_routing_table.json", encoding="utf-8") as fh:
        return json.load(fh)


@functools.lru_cache(maxsize=1)
def _facilities() -> dict[str, Any]:
    with open(DATA_DIR / "delhi_facilities.json", encoding="utf-8") as fh:
        return json.load(fh)


@functools.lru_cache(maxsize=1)
def _by_id() -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in _table()["categories"]}


def categories() -> list[dict[str, Any]]:
    return _table()["categories"]


def category_ids() -> list[str]:
    return [c["id"] for c in categories()]


def get_category(category_id: str) -> dict[str, Any] | None:
    return _by_id().get(category_id)


def match_text(text: str) -> list[str]:
    """Candidate category ids for a free-text label, best first.

    Alias substring matching only. The vision layer is expected to return a
    category id directly; this exists for typed input and for recovering when
    the model answers with a plain English label instead of an id.
    """
    needle = text.strip().lower()
    if not needle:
        return []

    exact: list[str] = []
    partial: list[str] = []
    for c in categories():
        if needle == c["id"]:
            return [c["id"]]
        haystack = [c["id"], c["name"].lower(), *(a.lower() for a in c["aliases"])]
        if any(needle == h for h in haystack):
            exact.append(c["id"])
        elif any(needle in h or h in needle for h in haystack):
            partial.append(c["id"])
    return exact + partial


def facilities_for(category_id: str) -> list[dict[str, Any]]:
    return [
        f for f in _facilities()["facilities"]
        if category_id in f["serves_categories"]
    ]


def route_meta(route: str) -> dict[str, Any]:
    return ROUTE_META[route]


def anchor() -> dict[str, Any]:
    return _facilities()["_meta"]["anchor_point"]


def unverified_fields(category_id: str) -> list[str]:
    """Which fields on this category are still unconfirmed drafts.

    Call this before putting a number on screen. An entry listing
    value_per_kg_inr here must not have its price presented as fact.
    """
    c = get_category(category_id)
    return list(c.get("verify", [])) if c else []
