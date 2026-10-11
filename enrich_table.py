"""Add per-category teaching content to the Delhi routing table.

Three new fields per category:
  why_not_bin - what actually happens if this specific item goes in the bag.
                Replaces a generic reminder that talked about batteries while
                the user was looking at flowers.
  steps       - concrete preparation steps. The useful, non-obvious ones, not
                "dispose of responsibly".
  learn       - a YouTube SEARCH url, only where watching beats reading.
                A search, never a video id: inventing ids would mean shipping
                links that may be dead or point at something else entirely.

Run once:  .venv/Scripts/python.exe enrich_table.py
"""
from __future__ import annotations

import io
import json
from urllib.parse import quote_plus

PATH = "data/delhi_routing_table.json"


def yt(q: str) -> str:
    return f"https://www.youtube.com/results?search_query={quote_plus(q)}"


EXTRA: dict[str, dict] = {
    "newspaper": {
        "why_not_bin": "Paper tipped in with wet waste turns to pulp within hours and "
                       "stops being sellable. It is the easiest money in the house to lose.",
        "steps": [
            "Keep it dry. Damp raddi is refused or paid at half rate.",
            "Stack flat and tie with string, not tape - tape has to be picked off.",
            "Weigh it yourself first. Spring scales under-read in the buyer's favour.",
            "Ask the rate per kilo before you hand it over, not after.",
        ],
    },
    "cardboard": {
        "why_not_bin": "Loose boxes fill the bin in minutes and the collector often "
                       "refuses them. Flattened, the same boxes are a paid stream.",
        "steps": [
            "Strip packing tape and plastic couriers labels off.",
            "Flatten every box - buyers pay by weight but refuse bulky loose cartons.",
            "Keep it dry; wet corrugate loses most of its value.",
            "An intact sturdy box is worth more resold to a small online seller than as scrap.",
        ],
    },
    "pet_bottle": {
        "why_not_bin": "A capped bottle is mostly trapped air. It fills the bag, and if it "
                       "still has liquid in it, it wets everything sellable around it.",
        "steps": [
            "Empty it completely and give it a rinse.",
            "Take the cap off - it is a different polymer and is sold separately.",
            "Crush it flat so it stops taking up space.",
            "Keep clear PET away from coloured. Clear fetches a noticeably better rate.",
        ],
    },
    "mixed_plastic": {
        "why_not_bin": "There is no buyer for multilayer film anywhere in the chain. Worse, "
                       "dropping it into the recycling sack contaminates the plastic around "
                       "it that someone was going to be paid for.",
        "steps": [
            "Do not put it in the recycling sack. It devalues the whole bag.",
            "Shake out crumbs and food so it does not rot the dry waste.",
            "Dry bin is the honest answer. Nobody downstream wants this.",
            "The only real reduction here is buying fewer, larger packs.",
        ],
    },
    "iron_steel": {
        "why_not_bin": "Steel is endlessly recyclable and has real cash value. In a bin it "
                       "goes to landfill and someone mines fresh ore instead.",
        "steps": [
            "Empty out any plastic or rubber handles - buyers deduct for them.",
            "Keep steel separate from aluminium. Mixed metal is paid at the lower rate.",
            "A magnet sticks to steel and iron. That is your free sorting test.",
        ],
    },
    "aluminium": {
        "why_not_bin": "Recycling aluminium uses a fraction of the energy of smelting it "
                       "new, and it is one of the highest-paying things in your kitchen. "
                       "Binned, both are wasted.",
        "steps": [
            "Magnet test: a magnet does NOT stick to aluminium but does stick to steel. "
            "This one check stops you being paid the steel rate for aluminium.",
            "Rinse off food residue.",
            "Crush cans to save space; foil should be balled up tight, not left loose.",
        ],
    },
    "copper": {
        "why_not_bin": "Copper is the single highest-value thing most households throw out. "
                       "It is also why cable is burned in the open, which is the dirty way "
                       "to recover it.",
        "steps": [
            "Never burn insulation off. It releases dioxins and buyers pay less for "
            "fire-damaged copper anyway.",
            "Strip insulation with a knife if you can - bright bare copper pays far more "
            "than insulated wire.",
            "Keep copper apart from brass. They look similar and are priced differently.",
        ],
        "learn": yt("how to strip copper wire safely for scrap"),
    },
    "glass_bottle": {
        "why_not_bin": "Loose broken glass in a bag is a direct injury risk to the person "
                       "who opens it by hand - and that is how most of Delhi's waste is sorted.",
        "steps": [
            "Rinse out residue so it does not attract pests.",
            "If it is broken, wrap the pieces in thick newspaper and write GLASS on it.",
            "Intact jars are worth more on your own kitchen shelf than at the scrap rate.",
        ],
    },
    "lithium_cell": {
        "why_not_bin": "A crushed lithium cell ignites. In a collection vehicle that means "
                       "a fire with a person standing next to it, and landfill fires at "
                       "Ghazipur and Bhalswa have started this way.",
        "steps": [
            "Tape over both terminals with insulating tape. A loose cell shorting against "
            "metal in a bag is the single most common way these catch fire.",
            "Never puncture, crush or try to open it.",
            "If it is swollen or hot, keep it away from anything flammable and do not "
            "carry it in a pocket or bag against other metal.",
            "Store it somewhere cool and dry until you can reach a registered recycler.",
        ],
        "learn": yt("how to safely store and dispose lithium battery"),
    },
    "lead_acid_battery": {
        "why_not_bin": "These have enough resale value that they reliably get bought - the "
                       "problem is who buys them. Informal breaking spills sulphuric acid "
                       "and is a serious source of lead poisoning in children nearby.",
        "steps": [
            "Keep it upright. A tipped battery leaks acid.",
            "Exchange it at the dealer when buying the replacement - that is the normal "
            "and safest route, and you still get the trade-in value.",
            "Be wary of the buyer offering the most cash. That is often the one breaking "
            "it open in the open air.",
        ],
    },
    "cfl_tube": {
        "why_not_bin": "Each tube holds a small amount of mercury vapour. Snapped in a bag "
                       "it is released right where someone is sorting by hand.",
        "steps": [
            "Do not snap it to fit the bin. That is the moment the mercury is released.",
            "Slide it back into the old carton, or wrap it in thick paper and label it.",
            "If one does break, open the windows, leave the room for 15 minutes, and sweep "
            "with stiff card - never a vacuum, which sprays the vapour around.",
        ],
        "learn": yt("what to do if CFL tube light breaks mercury safety"),
    },
    "led_bulb": {
        "why_not_bin": "No mercury, but the driver circuit inside is electronics, and "
                       "electronics in landfill leach metals into groundwater.",
        "steps": [
            "No special handling - it is not a mercury risk like CFL.",
            "Keep it with your other small e-waste rather than making a separate trip.",
        ],
    },
    "mobile_phone": {
        "why_not_bin": "A phone holds recoverable gold, silver and copper, plus a lithium "
                       "cell. It also holds your accounts, photos and bank apps.",
        "steps": [
            "Sign out of your accounts FIRST, then factory reset. A reset alone can leave "
            "you still signed in on some devices.",
            "Remove the SIM and the memory card. People forget the memory card.",
            "If it still switches on, resale or donation returns far more than recycling.",
            "If the back is swollen, treat it as a damaged lithium cell, not a phone.",
        ],
        "learn": yt("how to wipe android phone before selling factory reset"),
    },
    "mixed_ewaste": {
        "why_not_bin": "Chargers and cables are mostly copper in plastic. The informal way "
                       "to get that copper out is to burn the plastic off, which is one of "
                       "the dirtiest things done to Delhi's air.",
        "steps": [
            "Collect it up rather than binning items one at a time - a handful is worth a trip.",
            "Keep any item with a battery in it separate from plain cables.",
            "Hand it to an authorised recycler, not to anyone who will burn it for the copper.",
        ],
    },
    "expired_medicine": {
        "why_not_bin": "Antibiotics reaching landfill and groundwater drive drug resistance. "
                       "Flushing them is worse, not better - it puts them straight into water. "
                       "Loose tablets in a bin are also a poisoning risk to children and animals.",
        "steps": [
            "Do not flush, and do not tip loose tablets into the bin.",
            "Leave them in the original blister and box so the hospital can identify them.",
            "Scratch out your name and the patient details on the label first.",
            "Take them to a hospital collection box, where they enter the bio-medical "
            "waste stream and are incinerated properly.",
        ],
    },
    "pooja_flowers": {
        "why_not_bin": "Flowers themselves rot down harmlessly. What does the damage is "
                       "everything tied into the garland - plastic thread, foil, pins - "
                       "which goes into the Yamuna with it and never leaves.",
        "steps": [
            "Pull the garland apart and strip out the plastic thread, foil and any pins. "
            "This is the step almost everyone skips, and it is the one that matters.",
            "Do not immerse in the Yamuna or any drain. It is prohibited and it is what "
            "chokes the river.",
            "Petals go in the green wet bin, or straight into a compost bin or pot.",
            "If you compost at home, mix flowers with dry leaves or newspaper - flowers "
            "alone turn into a wet, smelling mat.",
        ],
        "learn": yt("how to compost pooja flowers at home nirmalya composting"),
    },
    "used_cooking_oil": {
        "why_not_bin": "Poured down the drain it congeals and is a major cause of sewer "
                       "blockage, and what gets through reaches the Yamuna. Re-fried, it "
                       "is a genuine health hazard.",
        "steps": [
            "Let it cool completely first.",
            "Strain out the food bits through a cloth or sieve.",
            "Store it in a sealed plastic bottle - never pour it down the sink or drain.",
            "Do not reuse it for frying repeatedly; repeatedly heated oil is the actual risk.",
        ],
        "learn": yt("how to store and dispose used cooking oil safely India RUCO"),
    },
    "old_clothes": {
        "why_not_bin": "Textiles are one of the fastest-growing landfill streams, and "
                       "wearable clothing being binned while someone nearby needs it is "
                       "the plainest kind of waste there is.",
        "steps": [
            "Wash it before donating. Unwashed donations are usually thrown away.",
            "Split wearable from unwearable - they go to completely different places.",
            "Unwearable cotton still has a market as industrial cleaning rags.",
            "Pair and tie shoes together so they do not get separated in sorting.",
        ],
    },
    "furniture": {
        "why_not_bin": "Bulky items are excluded from normal door-to-door collection, which "
                       "is exactly why mattresses and sofas end up abandoned on Delhi roadsides.",
        "steps": [
            "Do not leave it out on the street - it will sit there for weeks.",
            "If it is repairable, a second-hand dealer or carpenter will take it.",
            "Mattresses are the hardest item here; check for a bulky-waste pickup before "
            "assuming anyone will collect it.",
        ],
    },
    "cnd_debris": {
        "why_not_bin": "Roadside malba is a significant share of Delhi's PM10 - it is ground "
                       "to dust by traffic and goes straight into the air you breathe.",
        "steps": [
            "Keep it damp and covered while it is stored. Dry malba becomes airborne dust.",
            "Never tip it on a roadside or into a drain.",
            "Bag it rather than loose-piling it so it can actually be collected.",
        ],
    },
    "sanitary_waste": {
        "why_not_bin": "Delhi's waste is still largely sorted by hand. Unwrapped sanitary "
                       "waste in a mixed bag is a direct health risk to the person doing "
                       "that sorting.",
        "steps": [
            "Wrap it in paper - not in another plastic bag, which makes it invisible to "
            "the person handling it.",
            "Mark the wrap, even just an X. SWM Rules class this as domestic hazardous, "
            "and the marking is what warns the handler.",
            "Keep it out of both the wet and the dry bag.",
        ],
    },
    "kitchen_waste": {
        "why_not_bin": "This is roughly half your waste by weight, and it is the stream that "
                       "ruins the others - once it is mixed in, the paper, card and plastic "
                       "around it stop being sellable.",
        "steps": [
            "Keep it strictly in the green bin. Mixed in, it devalues everything else.",
            "Drain liquids before binning - weight is what makes collection expensive.",
            "Home composting works in a flat: layer wet kitchen scraps with dry leaves, "
            "paper or cocopeat, roughly half and half.",
            "If your compost smells, it needs more dry material and more air, not less waste.",
        ],
        "learn": yt("home composting kitchen waste in apartment India beginners"),
    },
}


def main() -> None:
    d = json.load(io.open(PATH, encoding="utf-8"))
    missing, done = [], 0

    for cat in d["categories"]:
        extra = EXTRA.get(cat["id"])
        if not extra:
            missing.append(cat["id"])
            continue
        cat.update(extra)
        done += 1

    d["_meta"]["content_note"] = (
        "why_not_bin / steps / learn are teaching content, written to be specific to "
        "the item. learn is always a YouTube SEARCH url, never a video id - a search "
        "cannot rot or point at the wrong thing."
    )

    io.open(PATH, "w", encoding="utf-8").write(
        json.dumps(d, ensure_ascii=False, indent=2))

    print(f"enriched {done}/{len(d['categories'])} categories")
    if missing:
        print("NO CONTENT FOR:", ", ".join(missing))
    print("with a how-to video:",
          sum(1 for c in d["categories"] if c.get("learn")))
    print("total steps written:",
          sum(len(c.get("steps", [])) for c in d["categories"]))


if __name__ == "__main__":
    main()
