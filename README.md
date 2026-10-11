# Bhav

**क्या भाव? — what is this worth, and where does it actually go?**

Photograph something you want to get rid of. Bhav tells you which of four routes
it belongs to, what it's worth, and the preparation steps most people get wrong.

Built for the WeMakeDevs x AWS *Environmental Hacks* hackathon, Waste and Energy
track. Build It submission: runs locally on the Strands Agents SDK, no AWS
account required.

---

## The problem

Segregation doesn't fail in Delhi because nobody cares. It fails because the
rules are different for every object and you can't look them up while you're
standing over a bin holding the thing.

Out of the 23 common household items in this project's data, **10 should never
go in either bin.** Most people can't name three of them.

- A lithium cell gets crushed in a collection truck and starts a fire.
- A CFL tube snapped to fit the bin releases mercury next to the person sorting
  it by hand.
- Pooja flowers are harmless, but the plastic thread tied into the garland
  isn't, and nobody tells you to pull it out first.

## The idea

Delhi already sorts its waste pretty well. Newspaper, bottles and scrap metal
get separated in most homes, and that happens because the kabadiwala pays for
them. The habit exists. It just stops where the money stops.

So Bhav leads with rupees, not carbon. Where there genuinely is no money, it
says so plainly and gives you the safety reason instead.

## Four routes, not two

| Route | Meaning |
|---|---|
| `SELL` | Has scrap value. A kabadiwala or authorised buyer pays for this. |
| `BIN_DRY` | Dry bin. No value, but a recyclable stream. |
| `BIN_WET` | Wet bin. Compostable. |
| `SPECIAL` | **Must not go in either bin.** Regulated or hazardous route only. |

That fourth route is the point. Every other app treats disposal as a binary.

---

## How it works

```
photo
  │
  ▼
Strands Agents SDK  ──────────────┐
  │                               │ loops until it has what it needs
  ├─ identify_item    (Gemini vision → category + confidence)
  ├─ lookup_route     (routing table → route, hazard, legal basis)
  ├─ estimate_value   (routing table → ₹/kg, verified flag)
  ├─ find_facility    (facility data → authorised? verified?)
  └─ get_reuse        (routing table → is reuse better than disposal?)
  │                               │
  ▼ ◄─────────────────────────────┘
structured_output  (same conversation → why, steps, video decision)
  │
  ▼
result card
```

### The split that matters

**The table owns what must be right.** Route, legal basis, hazard class, scrap
rates, facilities. These are verified data, stored in
[`data/delhi_routing_table.json`](data/delhi_routing_table.json). A model has no
business inventing them, and when a rule changes you edit one line and every
user gets the new answer.

**The model owns the explaining.** The per-item reason, the steps, and the
decision about whether a how-to video would actually help. That has to be
written in context. Hardcoding it meant every answer repeated the same couple of
sentences no matter what you were holding.

### Honesty is a field, not a mood

Ask a chatbot where to drop a CFL tube in Rohini and it will give you a shop
name, a plot number and a landmark, with total confidence. You cannot tell
whether that place exists.

Bhav shows **"not yet confirmed"** on any facility that hasn't been verified by
phone, because `verified` is a boolean in the data. Same for prices: an
unconfirmed scrap rate is labelled an estimate.

[`baseline_results.md`](baseline_results.md) has the bare-Gemini comparison that
motivated this, including it answering a Delhi resident with Tesco and
Sainsbury's store drop-off points.

---

## AWS

This is a **Build It** submission. The AWS open source tool is the
**Strands Agents SDK**, used for:

- Five tools defined with the `@tool` decorator, schemas derived from type hints
  and docstrings — see [`bhav/tools.py`](bhav/tools.py).
- `strands.models.gemini.GeminiModel` as the provider, so the whole agent runs
  on a Gemini key with no AWS account — see [`bhav/agent.py`](bhav/agent.py).
- `Agent.structured_output()` for a second pass over the same conversation,
  returning validated Pydantic output — see [`bhav/advice.py`](bhav/advice.py).
- `agent.messages` read back to build the tool-call trace shown in the UI.

**AWS services: none.** The project is not deployed. Stating that rather than
listing services it doesn't use.

---

## Running it

Needs Python 3.11+ and a Gemini API key.

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt    # Windows
# source .venv/bin/activate && pip install -r requirements.txt # macOS / Linux

cp .env.example .env     # then put your key in it
python server.py
```

Then open <http://localhost:8000>.

| Route | What it is |
|---|---|
| `/` | Landing page, scroll-driven intro animation |
| `/try` | The app. Upload a photo, get a route |
| `/flow` | Standalone architecture animation, for recording |

### Configuration

| Variable | Default | Notes |
|---|---|---|
| `GEMINI_API_KEY` | — | Required |
| `BHAV_MODEL` | `gemini-3.6-flash` | 3.8 was ~20x slower on this task and 503'd under load |
| `BHAV_MODEL_CHAIN` | `gemini-3.6-flash` | Comma-separated fallback chain for the vision call |
| `BHAV_DEBUG` | unset | Set to `1` to let vision errors raise with a full traceback |

> **Free tier note.** One full run costs several Gemini requests (one per agent
> turn, plus vision, plus the advice pass). The free tier allows 20 requests per
> day *per model*, so you get two or three runs before a 429.

---

## Layout

```
bhav/
  agent.py      Strands agent, system prompt, model config
  tools.py      the five @tool functions
  vision.py     Gemini vision with retry and model fallback
  routing.py    route resolution over the table, no LLM dependency
  advice.py     Pydantic schema for the generated explanation
data/
  delhi_routing_table.json   23 categories: route, hazard, value, steps
  delhi_facilities.json      facility slots, with verified flags
static/
  index.html    landing page and scroll animation
  try.html      the app
  flow.html     architecture animation
  app.css       shared styling
server.py       Starlette app
compare_baseline.py  bare-Gemini comparison that justified building this
enrich_table.py      one-off migration that seeded the fallback copy
```

`routing.py` deliberately has no LLM dependency, so the routing logic is
testable without an API key.

---

## Honest limits

- **Delhi only**, and the facility data is anchored to Rohini / DTU.
- **Facilities are unverified.** Every entry with a non-empty `verify` array in
  the data is a draft. Phone numbers are deliberately `null` rather than
  plausible-looking invented ones.
- **Scrap rates move constantly** and the ones in the table are estimates until
  confirmed by phone.
- **23 categories is narrow.** If you photograph something outside them, the
  model is told to pick the closest match but drop its confidence below 0.45 and
  say there's no proper category yet. It will still sometimes be wrong.
- Not deployed, no auth, no persistence. It's a hackathon build.
