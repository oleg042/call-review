"""The call-review rubric — ONE source of truth for item and check ids, names and scoring.

Outcome first (moved forward / left open / stalled), then eight moves in call order with two yes/no checks each
(a key check and a supporting one), plus a soft claims check
(advice only, never changes the score). references/rubric.md explains every check
(what counts, examples, where it comes from); this file is what the scripts compute with. Change both together.
Ids are stable: rep focus files point at them (e.g. "discover.followup"). Never rename an id; retire it instead.
"""

ITEMS = [
    {"id": "open", "name": "Open", "page": "Opening", "when": "first minute",
     "question": "Did we say who we are, why we're here and the plan?",
     "checks": [
         {"id": "open.purpose", "key": True, "label": "Opened with who we are, why we're here and the plan for the call"},
         {"id": "open.their_goals", "label": "Asked what they want out of the call (or answered what they asked for)"},
     ]},
    {"id": "discover", "name": "Discover", "page": "Their problem", "when": "their problem",
     "question": "Did we dig into their problem before offering anything?",
     "checks": [
         {"id": "discover.followup", "key": True, "label": "Problems they raised got a follow-up question before we answered"},
         {"id": "discover.setup", "label": "Know how they get meetings today (channels, tools, who, volume, results)"},
     ]},
    {"id": "quantify", "name": "Quantify", "page": "What a win is worth", "when": "the number",
     "question": "Do we know what a win is worth to them?",
     "checks": [
         {"id": "quantify.deal_value", "key": True, "label": "Know what one new customer is worth to them"},
         {"id": "quantify.goal_vs_now", "label": "Know how many meetings or deals they need versus get today"},
     ]},
    {"id": "listen", "name": "Listen", "page": "Listening", "when": "the whole call",
     "question": "Did they feel heard?",
     "checks": [
         {"id": "listen.concerns", "key": True, "label": "Their worries were named back or explored, never brushed off"},
         {"id": "listen.questions", "label": "Asked enough questions, mostly open, none re-asked", "measured": True},
     ]},
    {"id": "teach", "name": "Teach", "page": "Showing expertise", "when": "when we explain",
     "question": "Did we sound like the experts?",
     "checks": [
         {"id": "teach.insight", "key": True, "label": "Shared one insight from what we see across clients, and they engaged"},
         {"id": "teach.short", "label": "Kept answers short (under ~90 seconds)", "measured": True},
     ]},
    {"id": "offer", "name": "Offer", "page": "The offer", "when": "what we'd do",
     "question": "Did they leave knowing what we'd do for them?",
     "checks": [
         {"id": "offer.stated", "key": True, "label": "Said plainly what we do, what they get and how we start"},
         {"id": "offer.fits", "label": "Sized it to them: enough market for the plan, and it pays back at their deal value"},
     ]},
    {"id": "price", "name": "Price", "page": "Price", "when": "money",
     "question": "Did we talk money plainly?",
     "checks": [
         {"id": "price.plain", "key": True, "label": "Money came up as a plain number or range, never 'it depends'"},
         {"id": "price.held", "label": "No discount for nothing: price moved only if scope moved"},
     ]},
    {"id": "close", "name": "Close", "page": "Next step", "when": "last 5 minutes",
     "question": "Did we leave with a booked next step?",
     "checks": [
         {"id": "close.booked", "key": True, "label": "Next step booked on the call: a date and time, or a specific agreed action"},
         {"id": "close.right_people", "label": "The person who decides will be there, and the purpose is agreed"},
     ]},
]

# Checks retired in v4 (2026-09-28): kept here so old focus files and history stay readable. Now coaching tips only.
RETIRED = ["open.time", "open.outcome", "discover.their_words", "discover.root_cause", "quantify.timing",
           "quantify.gap_confirmed", "listen.talk_share", "listen.everyone", "teach.ask_first", "teach.linked",
           "offer.options", "offer.success", "price.after_value", "price.reaction", "close.path", "close.tested"]

TRUST = {"id": "trust", "name": "What we claimed", "question": "Anything a prospect could check and find wrong, or that promises more than we can show?",
         "verdicts": {"clean": "Nothing worth changing", "tighten": "Lines that over-promise or can't be backed up",
                      "fix": "A line a prospect could check and find wrong"}}  # advice only: never changes the score

CALL_TYPES = {
    "discovery":   {"label": "Discovery call", "talk_max": 55, "pitch_max_words": 300,
                    "items": ["open", "discover", "quantify", "listen", "teach", "offer", "price", "close"]},
    "proposal":    {"label": "Proposal call", "talk_max": 60, "pitch_max_words": 450,
                    "items": ["open", "discover", "quantify", "listen", "teach", "offer", "price", "close"]},
    "negotiation": {"label": "Negotiation call", "talk_max": 55, "pitch_max_words": 300,
                    "items": ["open", "listen", "offer", "price", "close"]},
    "client":      {"label": "Client call", "talk_max": 50, "pitch_max_words": 300,
                    "items": ["open", "listen", "close"]},
}

ITEM_BY_ID = {it["id"]: it for it in ITEMS}
CHECK_BY_ID = {c["id"]: {**c, "item": it["id"]} for it in ITEMS for c in it["checks"]}


def applies(check: dict, call_type: str) -> bool:
    """A check marked "only" applies to those call types; elsewhere it is n/a (never a miss)."""
    return call_type in check.get("only", [call_type])


# Down to earth: a check is met when it did its job, not when it was perfect.
STATUS = {2: "Good", 1: "Partly", 0: "Work on", None: "N/A"}


def item_score(results: dict, item: dict):
    """results: check id -> 'met' | 'missed' | 'na'. Returns (score 0/1/2 or None, met, applicable, key_met).

    Good (2)    = every check that applied was met.
    Partly (1)  = some were met (a met key check with a missed supporting one is Partly, not Good).
    Work on (0) = none.
    The label only; the score weights key 70 / supporting 30 either way (move_craft).
    """
    app = [c for c in item["checks"] if results.get(c["id"], "na") != "na"]
    if not app:
        return None, 0, 0, None
    met = sum(1 for c in app if results.get(c["id"]) == "met")
    key = next((c for c in item["checks"] if c.get("key")), None)
    key_met = None if key is None or results.get(key["id"], "na") == "na" else results.get(key["id"]) == "met"
    if met == len(app):
        return 2, met, len(app), key_met
    if met >= 1:
        return 1, met, len(app), key_met
    return 0, met, len(app), key_met


# The headline is what the call achieved. The moves decide where inside its range the score lands.
OUTCOMES = {
    "moved_forward": {"label": "Moved forward", "low": 7.0, "high": 10.0,
                      "means": "They showed interest and a specific next step was agreed or a next call scheduled."},
    "left_open":     {"label": "Left open", "low": 4.0, "high": 7.0,
                      "means": "They showed interest, but the next step is vague or in their hands."},
    "stalled":       {"label": "Stalled", "low": 1.0, "high": 4.0,
                      "means": "No real interest, or no path forward."},
}
KEY_WEIGHT = 0.7  # a move's craft: key check 70%, supporting check 30% (a supporting check that can't apply → key counts fully)


def move_craft(results: dict, item: dict):
    """0..1 for one move: the key check carries 0.7, the supporting check 0.3."""
    key = next(c for c in item["checks"] if c.get("key"))
    sup = [c for c in item["checks"] if not c.get("key")]
    k = results.get(key["id"], "na")
    s = [results.get(c["id"], "na") for c in sup]
    if k == "na" and all(x == "na" for x in s):
        return None
    k_val = 1.0 if k == "met" else 0.0
    s_app = [x for x in s if x != "na"]
    if not s_app:
        return k_val
    return KEY_WEIGHT * k_val + (1 - KEY_WEIGHT) * (sum(1 for x in s_app if x == "met") / len(s_app))


def outcome_of(interest: str, next_step: str) -> str:
    """interest: clear | some | none. next_step: scheduled | specific | vague | prospect_owned | none."""
    if interest in ("clear", "some") and next_step in ("scheduled", "specific"):
        return "moved_forward"
    if interest in ("clear", "some") and next_step in ("vague", "prospect_owned"):
        return "left_open"
    return "stalled"


def call_score(outcome: str, move_crafts: list) -> tuple:
    """Outcome sets the range; craft (each move's move_craft, averaged over applicable moves) places it."""
    vals = [c for c in move_crafts if c is not None]
    craft = sum(vals) / len(vals) if vals else 0.0
    o = OUTCOMES[outcome]
    return round(o["low"] + craft * (o["high"] - o["low"]), 1), round(craft, 2)
