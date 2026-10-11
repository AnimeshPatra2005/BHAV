"""Strands tools for Bhav.

Strands builds each tool's schema from its signature and docstring, so the
docstrings here are interface, not commentary.
"""
from __future__ import annotations

import os
from typing import Any

from strands import tool

from . import routing, vision


@tool
def identify_item(image_path: str) -> dict[str, Any]:
    """Identify what household item is in a photo.

    Returns a best-guess category id, a confidence between 0 and 1, and up to two
    alternative categories the item might be instead. Confidence below 0.75 means
    you must ask the user to confirm before routing.

    Args:
        image_path: Path to the photo on disk.
    """
    if os.environ.get("BHAV_DEBUG"):
        guess = vision.identify(image_path)  # let it raise, with the full traceback
    else:
        try:
            guess = vision.identify(image_path)
        except Exception as exc:
            # Say plainly that the call failed. Returning a bare empty result here
            # makes the agent apologise for not seeing the item, which hides a
            # broken API call behind what looks like a bad photo.
            return {
                "error": f"{type(exc).__name__}: {exc}",
                "tool_failed": True,
                "category_id": None,
                "confidence": 0.0,
                "note": "The vision call failed. This is a system error, not an "
                        "unclear photo. Tell the user the lookup failed.",
            }

    if guess["category_id"]:
        cat = routing.get_category(guess["category_id"])
        guess["category_name"] = cat["name"] if cat else None
    return guess


@tool
def lookup_route(category_id: str) -> dict[str, Any]:
    """Look up the correct disposal route for a waste category in Delhi.

    Returns one of four routes: SELL (has scrap value), BIN_DRY, BIN_WET, or
    SPECIAL (must not go in any bin - regulated or hazardous). Also returns the
    hazard note, the legal basis, and which fields are still unverified drafts.

    Args:
        category_id: A category id, e.g. lithium_cell or pooja_flowers.
    """
    cat = routing.get_category(category_id)
    if not cat:
        return {"error": f"Unknown category: {category_id}",
                "known_categories": routing.category_ids()}

    meta = routing.route_meta(cat["route"])
    return {
        "category_id": cat["id"],
        "category_name": cat["name"],
        "route": cat["route"],
        "route_verb": meta["verb"],
        "tone": meta["tone"],
        "bin_colour": meta["bin"],
        "hazard": cat.get("hazard"),
        "why_not_bin": cat.get("why_not_bin"),
        "steps": cat.get("steps", []),
        "learn": cat.get("learn"),
        "legal_basis": cat.get("legal_basis"),
        "destination": cat.get("destination"),
        "has_reuse_route": bool(cat.get("reuse")),
        "no_monetary_value": cat.get("no_monetary_value", False),
        "incentive_lever": cat.get("incentive_lever"),
        "unverified_fields": routing.unverified_fields(category_id),
    }


@tool
def find_facility(category_id: str) -> dict[str, Any]:
    """Find where to actually take an item, for the Rohini / DTU demo area.

    Returns matching facilities with a verified flag. An unverified facility has
    no phone number yet and must be presented as "not yet confirmed" rather than
    as a real place to go.

    Args:
        category_id: A category id, e.g. cfl_tube.
    """
    facs = routing.facilities_for(category_id)
    if not facs:
        return {"category_id": category_id, "facilities": [],
                "note": "No facility slot defined for this category yet."}

    return {
        "category_id": category_id,
        "area": routing.anchor()["label"],
        "facilities": [
            {
                "name": f["name"],
                "type": f["type"],
                "authorised": f["authorised"],
                "verified": f["verified"],
                "phone": f["phone"],
                "address": f["address"],
                "lat": f.get("lat"),
                "lon": f.get("lon"),
                "maps_query": f.get("maps_query"),
                "notes": f["notes"],
            }
            for f in facs
        ],
        "any_verified": any(f["verified"] for f in facs),
    }


@tool
def estimate_value(category_id: str, approx_kg: float = 1.0) -> dict[str, Any]:
    """Estimate what an item is worth in rupees if it has scrap value.

    Returns a range, or no_value when the category has no resale market. Always
    returns a `verified` flag - an unverified price must be shown as an estimate,
    never stated as the going rate.

    Args:
        category_id: A category id, e.g. copper.
        approx_kg: Rough weight in kg. Defaults to 1.
    """
    cat = routing.get_category(category_id)
    if not cat:
        return {"error": f"Unknown category: {category_id}"}

    per_kg = cat.get("value_per_kg_inr")
    per_item = cat.get("value_per_item_inr")
    verified = "value_per_kg_inr" not in cat.get("verify", []) and \
               "value_per_item_inr" not in cat.get("verify", [])

    if per_item:
        return {"category_id": category_id, "basis": "per_item",
                "range_inr": per_item, "verified": verified,
                "note": "Varies hugely with condition and model."}

    if not per_kg:
        return {"category_id": category_id, "basis": "none", "no_value": True,
                "verified": True,
                "note": "No resale market. Use the safety framing instead of a price."}

    low, high = per_kg
    return {
        "category_id": category_id,
        "basis": "per_kg",
        "rate_inr_per_kg": per_kg,
        "approx_kg": approx_kg,
        "range_inr": [round(low * approx_kg, 1), round(high * approx_kg, 1)],
        "verified": verified,
        "note": "Scrap rates move constantly. Unverified rates are drafts."
                if not verified else "",
    }


@tool
def get_reuse(category_id: str) -> dict[str, Any]:
    """Get reuse or repurposing options, when the item has a genuine reuse route.

    Only some categories have one. Returns has_reuse false for the rest - do not
    invent a reuse idea for an item that does not have one.

    Args:
        category_id: A category id, e.g. old_clothes.
    """
    cat = routing.get_category(category_id)
    if not cat:
        return {"error": f"Unknown category: {category_id}"}

    reuse = cat.get("reuse")
    if not reuse:
        return {"category_id": category_id, "has_reuse": False}

    return {
        "category_id": category_id,
        "has_reuse": True,
        "is_primary_route": reuse.get("primary", False),
        "note": reuse.get("note", ""),
        # TODO: swap for OpenSearch retrieval over the curated reuse corpus.
        "corpus": "NOT_WIRED",
    }


ALL_TOOLS = [identify_item, lookup_route, find_facility, estimate_value, get_reuse]
