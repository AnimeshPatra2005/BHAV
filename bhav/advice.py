"""Model-generated advice for a routed item.

The routing table stays the source of truth for the things that must be right and
auditable - which of the four routes it is, the legal basis, the hazard, the
scrap rate, which facility. Those are verified data and a model has no business
inventing them.

Everything in here is the opposite kind of content: the explanation and the
how-to. That has to be written per item, in context, by the model. Hardcoding it
meant every answer repeated the same couple of sentences no matter what the user
was actually holding.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Advice(BaseModel):
    """Teaching content for one routed item."""

    why_not_bin: str = Field(
        description=(
            "Two or three sentences on what actually happens to THIS specific item "
            "if it is thrown in with everything else. Concrete and physical: what "
            "breaks, catches fire, leaks, spoils, or gets lost. Write for the item "
            "in front of you - a reason about batteries is useless for flowers. "
            "Do not reach for the same stock line every time; most people are not "
            "near a river, so talk about what happens in the bag, the truck, the "
            "sorting yard or the ground, whichever is true here."
        )
    )
    steps: list[str] = Field(
        description=(
            "Three to five concrete preparation steps, in order, each one sentence. "
            "Only things that change the outcome: the part people get wrong, the "
            "safety step they skip, the thing that decides whether it is accepted "
            "or refused. No filler like 'dispose of responsibly' or 'be "
            "environmentally conscious'."
        )
    )
    in_short: list[str] = Field(
        description="Two short lines, at most 12 words each, summarising the decision."
    )
    needs_video: bool = Field(
        description=(
            "True only if there is a physical technique here that is genuinely "
            "easier to learn by watching than by reading - composting, stripping "
            "wire, handling a damaged cell, cleaning up a broken tube. False for "
            "anything whose whole instruction is 'put it in this bin' or 'sell it "
            "to the kabadiwala'. Judge the task honestly; most items do not need one."
        )
    )
    video_query: str = Field(
        default="",
        description=(
            "If needs_video, the YouTube search terms a person would actually type, "
            "in English, specific to the technique. Empty string otherwise. Search "
            "terms only - never a URL or a video id."
        )
    )


ADVICE_PROMPT = """Using what the tools just returned about this item, write the
teaching content for it.

Be specific to this exact item. Someone is holding it right now and wants to know
what to do and why it matters. Assume they are in Delhi but not next to a river.

Do not repeat the route or the price - those are already shown elsewhere on the
screen. Do not invent a facility, an address or a phone number. Decide honestly
whether a how-to video would actually help here, and say so."""
