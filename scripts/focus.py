#!/usr/bin/env python3
"""Track each exec's focus behaviour across calls: did this call hit it, what's the streak, is it fixed?

Usage:
  python3 focus.py <workdir> <rep-key> [--result met|missed|na] [--value N]   # evaluate this call; override only when the judge must
  python3 focus.py --show <rep-key>             # print the rep's current focus, streak and history
  python3 focus.py --link <rep-key> <call_id> <url>   # record the published review page for that call
  python3 focus.py --list                       # all reps and their active focus

Rep files live at ~/.claude/call-review/reps/<rep-key>.json:
{
  "name": "Mark Glazer",
  "active": {"id": "follow-up-first", "behavior": "...", "why": "...",
             "check": {"kind": "check", "id": "discover.followup"}          # a rubric check, judged for THIS exec
                    | {"kind": "item", "id": "price", "op": ">=", "value": 2} # a whole move's score
                    | {"kind": "metric", "key": "rep_longest_monologue", "op": "<=", "value": 250},  # this exec's own number
             "fixed_after": 3, "streak": 0, "started": "2026-09-26"},
  "queue": [ {next focus objects, same shape, in priority order} ],
  "retired": [ {focus + "fixed_on"} ],
  "history": [ {"date", "call_id", "title", "focus_id", "value", "hit", "score"} ]
}
A focus is FIXED after `fixed_after` consecutive qualifying calls that hit it; then the next queued focus
becomes active. A call where the check can't be measured (criterion null) doesn't break or extend the streak.
"""
import json, operator, sys, datetime
from pathlib import Path

REPS = Path.home() / ".claude" / "call-review" / "reps"
OPS = {"<=": operator.le, "<": operator.lt, ">=": operator.ge, ">": operator.gt, "==": operator.eq}


def load(key):
    p = REPS / f"{key}.json"
    if not p.exists():
        sys.exit(f"no rep file {p}; create one (see the docstring) or pick from: {[x.stem for x in REPS.glob('*.json')]}")
    return p, json.loads(p.read_text())


def show(rep):
    a = rep.get("active") or {}
    print(f"{rep['name']} — focus: {a.get('behavior', 'none')} (streak {a.get('streak', 0)}/{a.get('fixed_after', '-')})")
    for h in rep.get("history", [])[-8:]:
        print(f"  {h['date']}  {'HIT ' if h['hit'] else ('MISS' if h['hit'] is False else 'n/a ')}  value={h['value']}  score={h.get('score')}  {h['title']}  {h.get('review_url', '')}")
    if rep.get("retired"):
        print("  fixed so far: " + ", ".join(f"{r['id']} ({r['fixed_on']})" for r in rep["retired"]))


def main():
    if sys.argv[1] == "--list":
        for p in sorted(REPS.glob("*.json")):
            show(json.loads(p.read_text()))
        return
    if sys.argv[1] == "--link":  # --link <rep-key> <call_id> <review url>: remember where this call's review page lives
        path, rep = load(sys.argv[2])
        for h in rep.get("history", []):
            if h.get("call_id") == sys.argv[3]:
                h["review_url"] = sys.argv[4]
        path.write_text(json.dumps(rep, indent=2))
        print(f"linked {sys.argv[3]} → {sys.argv[4]} for {rep['name']}")
        return
    if sys.argv[1] == "--show":
        show(load(sys.argv[2])[1])
        return
    workdir, key = Path(sys.argv[1]), sys.argv[2]
    # Optional judge override for multi-rep calls: `--value 1` = this rep's own result on the check,
    # judged from their own turns (the call-level criterion mixes both reps).
    override = float(sys.argv[sys.argv.index("--value") + 1]) if "--value" in sys.argv else None
    forced = sys.argv[sys.argv.index("--result") + 1] if "--result" in sys.argv else None
    path, rep = load(key)
    metrics = json.loads((workdir / "metrics.json").read_text())
    card = json.loads((workdir / "scorecard.json").read_text())
    a = rep.get("active")
    if not a:
        sys.exit("no active focus — pick one from the review and add it to the rep file")
    chk = a["check"]
    if chk["kind"] == "metric":
        # Prefer this exec's OWN number (metrics.per_rep) — a call-level number mixes both execs on shared calls.
        mine = (metrics.get("per_rep") or {}).get(rep["name"])
        per_key = chk["key"][4:] if chk["key"].startswith("rep_") else chk["key"]
        value = mine.get(per_key) if mine and per_key in mine else metrics.get(chk["key"])
        if isinstance(value, dict):  # e.g. rep_longest_monologue → words
            value = value.get("words")
    elif chk["kind"] == "item":
        value = (card.get("items", {}).get(chk["id"]) or {}).get("score")
    else:  # a single rubric check, attributed to whoever was responsible for it on this call
        c = next((cc for it in card.get("items", {}).values() for cid, cc in (it.get("checks") or {}).items() if cid == chk["id"]), {})
        owner = c.get("rep") or "both"
        value = c.get("result") if owner in ("both", rep["name"]) else "na"
    if override is not None:
        value = override
    if forced:
        value = forced
    if chk["kind"] == "check":
        hit = None if value in (None, "na") else value == "met"
    else:
        hit = None if value is None else OPS[chk["op"]](value, chk["value"])

    call = metrics.get("call") or {}
    if any(h.get("call_id") == call.get("id") and h.get("focus_id") == a["id"] for h in rep.get("history", [])):
        print("this call is already recorded for this focus — nothing changed")
        show(rep)
        return
    rep.setdefault("history", []).append({"date": call.get("date"), "call_id": call.get("id"), "title": call.get("title"),
                                          "focus_id": a["id"], "value": value, "hit": hit, "score": card.get("score")})
    # Streak = consecutive hits counting back from the most RECENT call (calls can be reviewed out of order).
    mine = sorted((h for h in rep["history"] if h.get("focus_id") == a["id"] and h.get("hit") is not None), key=lambda h: h.get("date") or "")
    streak = 0
    for h in reversed(mine):
        if not h["hit"]:
            break
        streak += 1
    a["streak"] = streak
    verdict = "n/a (not measurable on this call)" if hit is None else ("HIT" if hit else "MISS")
    target = "met" if chk["kind"] == "check" else f"{chk['op']} {chk['value']}"
    print(f"{rep['name']} · focus '{a['behavior']}' · this call: {verdict} (value {value}, target {target}) · streak {a['streak']}/{a['fixed_after']}")
    if a["streak"] >= a["fixed_after"]:
        rep.setdefault("retired", []).append({**a, "fixed_on": datetime.date.today().isoformat()})
        nxt = (rep.get("queue") or [None])[0]
        rep["active"] = {**nxt, "streak": 0, "started": datetime.date.today().isoformat()} if nxt else None
        rep["queue"] = (rep.get("queue") or [])[1:]
        print(f"FIXED: '{a['behavior']}'. Next focus: {nxt['behavior'] if nxt else 'none queued — pick one from this review'}")
    path.write_text(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
