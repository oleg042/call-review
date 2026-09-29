#!/usr/bin/env python3
"""Merge the reviewers' checks, verify every quote, fill the measured checks, score the eight moves.

Usage: python3 score.py <workdir> <call_type>        call_type: discovery | proposal | negotiation | client
Reads  <workdir>/transcript.txt, meta.json, metrics.json, reviewer-*.json
Writes <workdir>/scorecard.json; replaces this call's rows in ~/.claude/call-review/history.csv (one row per exec).

Reviewer JSON (see references/reviewer-prompt.md):
{
  "checks":   {"<check id>": {"result": "met|missed|na", "rep": "<exec name>|both", "line": 12, "quote": "exact words",
                              "note": "why", "instead": "exact line to say", "override": false}},
  "evidence": {"pains": [...], "cost_questions": [...], "concerns": [...], "participants": [...], "fit_inputs": {...}},
  "claims":   [{"line": 14, "quote": "...", "speaker": "...", "verdict": "TRUE|OVERSTATED|MISLEADING|UNPROVABLE|FALSE|BANNED", "correct": "..."}],
  "strengths": [{"line": 5, "quote": "...", "rep": "...", "point": "..."}],
  "fit_math": "one line"
}
Rules: a "met" needs a quote found on its cited line (±1) or it is dropped to "na" and listed as rejected;
a "missed" may cite the moment, or cite nothing when the thing never happened (say so in the note).
Measured checks (listen.talk_share, listen.questions, teach.short, teach.ask_first) come from metrics.json;
a reviewer can override one only with "override": true and a note (e.g. Grain mixed up two speakers).
"""
import csv, datetime, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rubric import ITEMS, CHECK_BY_ID, CALL_TYPES, OUTCOMES, RETIRED, applies, item_score, move_craft, outcome_of, call_score  # noqa: E402

HIST = Path.home() / ".claude" / "call-review" / "history.csv"
HIST_COLS = ["reviewed_at", "call_date", "call_id", "title", "rep", "call_type", "outcome", "score"] + [it["id"] for it in ITEMS] + \
            ["trust", "talk", "longest", "pitch", "questions", "pains", "cost_qs", "price_at", "repeats"]
MEASURED = {"listen.questions", "teach.short"}


def norm(s):
    return re.sub(r"[^a-z0-9$%]+", " ", (s or "").lower()).strip()


def quote_ok(lines, line_no, quote):
    q = norm(quote)
    if not q or not isinstance(line_no, int):
        return False
    return any(1 <= n <= len(lines) and q in norm(lines[n - 1]) for n in (line_no, line_no - 1, line_no + 1))


def measured(metrics, call_type, reps):
    """The two checks a script can settle, with who they belong to."""
    per = metrics.get("per_rep") or {}
    out = {}
    open_pct = metrics.get("rep_open_question_pct")
    repeats = metrics.get("rep_repeated_questions") or []
    # Half open means nothing with two questions: ask at least ~5 per 30 minutes (under half of Gong's 11-14).
    mins = (metrics.get("call") or {}).get("minutes") or 30
    asked, min_q = metrics.get("rep_questions") or 0, max(3, round(5 * mins / 30))
    ok_q = asked >= min_q and (open_pct or 0) >= 50 and not repeats
    out["listen.questions"] = {"result": "met" if ok_q else "missed", "rep": "both",
                               "line": repeats[0]["line"] if repeats else None,
                               "note": f"{asked} questions, {open_pct}% open, {len(repeats)} re-asked "
                                       f"(met: at least {min_q} for a {mins}-minute call, half open, none re-asked)"}
    lm = metrics.get("rep_longest_monologue") or {}
    worst = max(per.items(), key=lambda kv: (kv[1].get("longest_monologue") or {}).get("words", 0), default=(None, {}))
    long_ = (lm.get("words") or 0) > 250
    out["teach.short"] = {"result": "missed" if long_ else "met", "rep": worst[0] if long_ else "both", "line": lm.get("line"),
                          "note": f"longest answer {lm.get('words')} words ({dur(lm.get('words') or 0)}); met: under ~250 words"}
    return out


def dur(words):
    """Spoken length of N words at ~150 wpm, in the unit a person would say it."""
    sec = words / 150 * 60
    return f"~{sec:.0f} s" if sec < 90 else f"~{sec / 60:.1f} min"


def panel(metrics, call_type, reps, evidence, checks, minutes):
    ct = CALL_TYPES[call_type]
    per = metrics.get("per_rep") or {}
    multi = len(reps) > 1
    split = lambda f: (" (" + " · ".join(f"{r.split()[0]} {f(v)}" for r, v in per.items()) + ")") if multi else ""  # noqa: E731
    us = metrics.get("rep_talk_share_pct") or 0
    lm = metrics.get("rep_longest_monologue") or {}
    lead = min((v.get("words_before_first_answered_question", 0) for v in per.values()), default=0)
    nq, op = metrics.get("rep_questions") or 0, metrics.get("rep_open_question_pct")
    lo, hi = (max(1, round(11 * minutes / 30)), max(2, round(14 * minutes / 30))) if minutes else (11, 14)
    pains = evidence.get("pains") or []
    followed = sum(1 for p in pains if p.get("followed_up_line"))
    cost_qs = len(evidence.get("cost_questions") or [])
    pf = metrics.get("price_first_mentioned")
    pm = metrics.get("price_first_minute")
    after = (checks.get("price.after_value") or {}).get("result")
    repeats = len(metrics.get("rep_repeated_questions") or [])

    def st(ok, warn=False):
        return "ok" if ok else ("warn" if warn else "bad")
    rows = [
        {"key": "talk", "label": "Talk share, us vs them", "display": f"{us}% / {100 - us}%" + split(lambda v: f"{v['talk_share_pct']}%"),
         "short": f"{us}%", "guide": f"us ≤ {ct['talk_max']}%", "status": st(us <= ct["talk_max"], us <= ct["talk_max"] + 7)},
        {"key": "longest", "label": "Longest answer", "display": f"{lm.get('words', 0)} words · {dur(lm.get('words', 0))}",
         "short": f"{lm.get('words', 0)}w", "guide": "≤ 250 words", "status": st((lm.get("words") or 0) <= 250, (lm.get("words") or 0) <= 350)},
        {"key": "pitch", "label": "Talk before the first real question", "display": f"{lead} words · {dur(lead)}",
         "short": f"{lead}w", "guide": f"≤ {ct['pitch_max_words']} words", "status": st(lead <= ct["pitch_max_words"], lead <= ct["pitch_max_words"] * 1.5)},
        {"key": "questions", "label": "Questions they answered", "display": f"{nq} · {op if op is not None else 0}% open" + split(lambda v: str(v["questions_answered"])),
         "short": f"{nq}·{op or 0}%", "guide": f"{lo}–{hi}, half open" if minutes else "11–14, half open",
         "status": st(nq >= lo and (op or 0) >= 50, nq >= lo or (op or 0) >= 50)},
        {"key": "pains", "label": "Problems they raised, dug into first", "display": f"{followed} of {len(pains)}" if pains else "none raised",
         "short": f"{followed}/{len(pains)}", "guide": "all", "status": "na" if not pains else st(followed == len(pains), followed * 2 >= len(pains))},
        {"key": "cost_qs", "label": "Questions about what the problem costs them", "display": str(cost_qs),
         "short": str(cost_qs), "guide": "2+", "status": st(cost_qs >= 2, cost_qs == 1)},
        {"key": "price_at", "label": "Price first raised",
         "display": "never" if not pf else f"~{int(pm or 0):02d}:{int(round(((pm or 0) % 1) * 60)) % 60:02d} · by {'us' if pf['by_rep'] else 'them'}" + (" · after value" if after == "met" else " · before value" if after == "missed" else ""),
         "short": "never" if not pf else f"{int(pm or 0)}′", "guide": "call 1, after value",
         "status": "bad" if not pf and call_type != "client" else ("ok" if after == "met" else "warn") if pf else "na"},
        {"key": "repeats", "label": "Questions re-asked", "display": str(repeats), "short": str(repeats), "guide": "0", "status": st(repeats == 0)},
    ]
    return rows, {"us_pct": us}


def main():
    workdir, call_type = Path(sys.argv[1]), sys.argv[2]
    if call_type not in CALL_TYPES:
        sys.exit(f"unknown call type {call_type}; use one of {list(CALL_TYPES)}")
    lines = (workdir / "transcript.txt").read_text().splitlines()
    metrics = json.loads((workdir / "metrics.json").read_text())
    meta = json.loads((workdir / "meta.json").read_text())
    reps = metrics.get("reps") or []
    minutes = float(meta.get("minutes") or 0)

    checks, evidence, claims, strengths, rejected, fit_math, outcome_ev = {}, {}, [], [], [], None, None
    for f in sorted(workdir.glob("reviewer-*.json")):
        data = json.loads(f.read_text())
        for cid, c in (data.get("checks") or {}).items():
            if cid not in CHECK_BY_ID:
                if cid not in RETIRED:
                    rejected.append(f"{f.name}: unknown check id {cid}")
                continue
            if c.get("result") == "met" and not quote_ok(lines, c.get("line"), c.get("quote")):
                rejected.append(f"{cid} L{c.get('line')}: quote not found — {c.get('quote')!r}")
                c = {**c, "result": "na", "note": (c.get("note") or "") + " [dropped: unverified quote]"}
            elif c.get("quote") and not quote_ok(lines, c.get("line"), c.get("quote")):
                rejected.append(f"{cid} L{c.get('line')}: quote not found — {c.get('quote')!r}")
                c = {**c, "quote": "", "note": (c.get("note") or "") + " [quote dropped: not found]"}
            checks[cid] = c
        for k, v in (data.get("evidence") or {}).items():
            evidence[k] = v
        for cl in data.get("claims") or []:
            if quote_ok(lines, cl.get("line"), cl.get("quote")):
                claims.append(cl)
            else:
                rejected.append(f"claim L{cl.get('line')}: {cl.get('quote')!r}")
        for s in data.get("strengths") or []:
            if not isinstance(s, dict):  # a reviewer wrote prose instead of {line, quote, rep, point}
                rejected.append(f"{f.name}: strength without a quote: {str(s)[:80]!r}")
                continue
            (strengths if quote_ok(lines, s.get("line"), s.get("quote")) else rejected).append(
                s if quote_ok(lines, s.get("line"), s.get("quote")) else f"strength L{s.get('line')}: {s.get('quote')!r}")
        fit_math = data.get("fit_math") or fit_math
        if data.get("outcome"):
            o = data["outcome"]
            for part in ("interest", "next_step"):
                if o.get(f"{part}_quote") and not quote_ok(lines, o.get(f"{part}_line"), o.get(f"{part}_quote")):
                    rejected.append(f"outcome {part} L{o.get(f'{part}_line')}: quote not found — {o.get(f'{part}_quote')!r}")
                    o[f"{part}_quote"] = ""
            outcome_ev = o

    for cid, m in measured(metrics, call_type, reps).items():
        if not (checks.get(cid) or {}).get("override"):
            checks[cid] = {**m, "measured": True}

    applicable = CALL_TYPES[call_type]["items"]
    items = {}
    for it in ITEMS:
        if it["id"] not in applicable:
            items[it["id"]] = {"score": None, "met": 0, "applicable": 0, "checks": {}}
            continue
        res = {c["id"]: ((checks.get(c["id"]) or {}).get("result", "missed") if applies(c, call_type) else "na") for c in it["checks"]}
        score, met, app, key_met = item_score(res, it)
        items[it["id"]] = {"score": score, "met": met, "applicable": app, "key_met": key_met, "craft": move_craft(res, it),
                           "checks": {c["id"]: checks.get(c["id"], {"result": "missed", "note": "no reviewer verdict"}) for c in it["checks"]}}

    # The claims check is advice, not a penalty: it never changes the score (Oleg, 2026-09-29).
    SEVERITY = {"FALSE": 0, "BANNED": 0, "MISLEADING": 1, "OVERSTATED": 2, "UNPROVABLE": 3}  # tone lines aren't claims
    flagged = sorted((c for c in claims if c.get("verdict") in SEVERITY), key=lambda c: SEVERITY[c["verdict"]])
    wrong = [c for c in flagged if SEVERITY[c["verdict"]] == 0]
    verdict = "fix" if wrong else ("tighten" if flagged else "clean")
    n = lambda k, word: f"{k} {word}{'' if k == 1 else 's'}"  # noqa: E731
    tline = (f"{n(len(wrong), 'line')} not accurate" + (f", {len(flagged) - len(wrong)} could be tighter" if len(flagged) > len(wrong) else "") if wrong else
             f"{n(len(flagged), 'line')} could be tighter" if flagged else f"{n(len(claims), 'claim')} checked, all accurate")

    # Outcome first: what the call achieved sets the range, the moves place the score inside it.
    if not outcome_ev:
        booked = (checks.get("close.booked") or {}).get("result") == "met"
        outcome_ev = {"interest": "some", "next_step": "scheduled" if booked else
                      ("prospect_owned" if metrics.get("prospect_owns_next_step_signals") else "none"),
                      "note": "derived: no reviewer outcome given"}
        rejected.append("outcome: no reviewer verdict, derived from close.booked; the judge should confirm")
    outcome = outcome_of(outcome_ev.get("interest", "none"), outcome_ev.get("next_step", "none"))
    raw, craft = call_score(outcome, [items[i].get("craft") for i in applicable])
    caps = []  # no score caps from claims any more
    final = min([raw] + [c[0] for c in caps])
    rows, raw_panel = panel(metrics, call_type, reps, evidence, checks, minutes)
    assert not {r["key"] for r in rows} & {it["id"] for it in ITEMS}, "a panel key collides with a move id in history.csv"

    call = {**(metrics.get("call") or {}), "company": meta.get("company"), "prospect": meta.get("prospect"), "grainUrl": meta.get("grainUrl"),
            "prospects": [p["name"] for p in meta.get("participants", []) if p.get("name") and p["name"] not in reps]}
    card = {"call": call, "call_type": call_type, "reps": reps, "score": final, "raw_score": raw, "craft": craft,
            "outcome": {"id": outcome, **OUTCOMES[outcome], **outcome_ev},
            "caps_applied": [c[1] for c in caps if c[0] < raw], "items": items,
            "trust": {"verdict": verdict, "line": tline, "claims": claims, "top": flagged[:3]},
            "panel": rows, "panel_raw": raw_panel, "strengths": strengths, "evidence": evidence, "fit_math": fit_math,
            "rejected_evidence": rejected}
    (workdir / "scorecard.json").write_text(json.dumps(card, indent=2))

    # History: one row per exec (the "your last 3" trend reads it). Re-scoring a call replaces its rows.
    old = list(csv.DictReader(HIST.open())) if HIST.exists() and HIST.read_text().startswith("reviewed_at,call_date,call_id,title,rep,call_type,outcome,") else []
    keep = [r for r in old if r.get("call_id") != call.get("id")]
    per = metrics.get("per_rep") or {}
    short = {r["key"]: r["short"] for r in rows}
    for rep in reps:
        v = per.get(rep, {})
        mine = dict(short)
        if len(reps) > 1:
            mine.update({"talk": f"{v.get('talk_share_pct', 0)}%", "longest": f"{(v.get('longest_monologue') or {}).get('words', 0)}w",
                         "pitch": f"{v.get('words_before_first_answered_question', 0)}w",
                         "questions": f"{v.get('questions_answered', 0)}·{v.get('open_question_pct') or 0}%",
                         "repeats": str(len(v.get("repeated_questions") or []))})
        keep.append({"reviewed_at": datetime.date.today().isoformat(), "call_date": call.get("date"), "call_id": call.get("id"),
                     "title": call.get("title"), "rep": rep, "call_type": call_type, "outcome": outcome, "score": final,
                     **{it["id"]: items[it["id"]]["score"] for it in ITEMS}, "trust": verdict, **mine})
    with HIST.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=HIST_COLS, extrasaction="ignore")
        w.writeheader(); w.writerows(keep)

    print(f"{OUTCOMES[outcome]['label'].upper()} · {final}/10 (craft {craft:.0%}){' — ' + '; '.join(card['caps_applied']) if card['caps_applied'] else ''}")
    for it in ITEMS:
        r = items[it["id"]]
        if r["score"] is not None:
            print(f"  {it['name']:<9} {['Work on', 'Partly', 'Good'][r['score']]:<8} key {'met' if r['key_met'] else 'missed' if r['key_met'] is False else 'n/a'}")
    print(f"  Trust     {verdict} — {tline}")
    print(f"evidence rejected: {len(rejected)}")
    for r in rejected:
        print("  REJECTED", r)


if __name__ == "__main__":
    main()
