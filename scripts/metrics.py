#!/usr/bin/env python3
"""Deterministic call metrics — the numbers the lenses must not guess.

Usage: python3 metrics.py <workdir>   (reads transcript.txt + meta.json, writes metrics.json, prints a summary)

Reps = speakers whose participant email ends in @oneaway.io, or whose name matches a known rep.
Everything here is a heuristic signal for the lenses to confirm against the text, never a verdict.
"""
import json, re, sys
from pathlib import Path

KNOWN_REPS = {"mark glazer", "xavier caffrey", "oleg deduchenko", "tom", "hannah guevara"}
PRICE_RE = re.compile(r"\$\s?\d|\d+(\.\d)?\s?k\s?(per|a|/)\s?month|\bprice|\bpricing|\bcost\b|\bretainer|\bbudget|\bdeposit|\bfee\b|\bhow much (do|would|does|will)\b.*\b(pay|charge|cost)", re.I)
OFFER_RE = re.compile(r"\bpilot|\bfree (trial|campaign)|\bwhat (we|you) (get|do)|\bthe offer|\bdeliverables?\b|\bguarantee", re.I)
NEXT_RE = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|tomorrow|next week|\d{1,2}(:\d\d)?\s?(am|pm)|invite|calendar|calendly|book(ed)? (a|the)|schedule)\b", re.I)
PROSPECT_OWNS_RE = re.compile(r"(i'?ll send (you )?(my|a) (calendar|calendly|link|invite)|drop me (a note|some options)|let me (check|think|speak|get back)|i'?ll get back)", re.I)
TAG_Q = re.compile(r"(\b(right|okay|ok|correct|yeah|no|huh)(, [A-Z][a-z]+)?\?$|make sense\?$|sound (good|fair|right|ok|okay)\?$|does that work( for you)?\?$|you know( what i mean)?\?$|know what i'?m saying\?$|isn'?t it\?$|how are you( doing)?\?$|can you hear me\?$)", re.I)
# Small talk and clarifications are questions, but not discovery: they don't count toward the Gong 11-14 range.
SMALLTALK_Q = re.compile(r"how are (you|y'?all)\b|how (are )?you doing|how'?s it going|time ?zone|meeting link|in the chat\b|"
                         r"to join\b|waiting (for|on)\b|share (my|your) screen|how('?s| is| was) (your|the) (day|week|weekend|morning)|where are you (guys )?(calling|based|located|dialing)|can you (hear|see) me|camera|what time is it|weather|what was that|say that again|come again|sorry\?$|pardon|you there\?|am i (on )?mute|call you\b|your (last |first )?name\b|(which|what) name\b|how do you say (it|that|your)\b|how old\b|your (son|daughter|kids?|children|wife|husband|partner|family|mom|dad|mother|father|health)\b|go by\b|pronounce", re.I)
# Open vs closed: the first clause that starts with a question word decides, after fillers ("And then number two
# is, what has been done…", "Yes, roughly, how many…", "Like, why…"). "Can you walk me through…" asks for a story, so
# it counts as open. Whatever leads with is/do/can/would… is closed; a question with no clear head is closed.
OPEN_HEAD = re.compile(r"(how|what|which|where|when|who|whose|why|tell me|walk me|talk me|describe|help me understand|"
                       r"(can|could|would) you (tell|walk|talk|share|explain|describe|help me understand|give me a sense)|"
                       r"(would|will|are) you (be )?able to (tell|walk|talk|share|explain|describe)|tell me more)\b", re.I)
CLOSED_HEAD = re.compile(r"(is|are|was|were|am|do|does|did|can|could|would|will|should|shall|have|has|had|may|might|"
                         r"isn'?t|aren'?t|wasn'?t|don'?t|doesn'?t|didn'?t|can'?t|couldn'?t|wouldn'?t|won'?t|any)\b", re.I)
FILLER = re.compile(r"^(so|and|but|or|okay|ok|like|yes|yeah|then|sorry|um+|uh+|well|now|also|actually|just|roughly|"
                    r"basically|anyway|right|great|cool|perfect|oh|hmm|number \w+ is|first|second|lastly|i mean|you know|"
                    r"by the way|quickly|maybe|got it|can i (just )?(ask|know)( you)?|let me ask( you)?|quick question|i'?m curious|you said)\b[\s,]*", re.I)


# A question word right after "depends on", "about", "know"… is part of a statement, not a question.
EMBEDS = re.compile(r"\b(on|about|of|for|in|to|depends|know|see|understand|sure|wonder|ask|tell you)\W*$", re.I)


def is_open(q):
    before = ""  # the last clause with words in it: "it depends on, um, what you're looking for" is a statement
    for clause in re.split(r"[,;:—–]+|\s-\s", q):
        c = re.sub(r"^\W+", "", clause.strip())
        prev = None
        while c and c != prev:
            prev, c = c, FILLER.sub("", c).lstrip(" ,")
        if OPEN_HEAD.match(c) and not EMBEDS.search(before):
            return True
        if CLOSED_HEAD.match(c):
            return False
        if c:
            before = c
    return False


STOP = set("the a an and or to of in on for is are was were you your we our i it that this with be do does did can could would what how when why who at as so just like any have has where which what's how's where's right now there guys yeah okay really".split())


def load(workdir: Path):
    lines = workdir.joinpath("transcript.txt").read_text().splitlines()
    meta = json.loads(workdir.joinpath("meta.json").read_text())
    turns = []
    for i, raw in enumerate(lines, 1):
        m = re.match(r"^([^:]{1,60}):\s?(.*)$", raw)
        if m:
            turns.append({"line": i, "speaker": m.group(1).strip(), "text": m.group(2)})
        elif turns:  # continuation line
            turns[-1]["text"] += " " + raw
    return turns, meta


def rep_names(turns, meta):
    reps = set()
    for p in meta.get("participants", []):
        if (p.get("email") or "").lower().endswith("@oneaway.io") and p.get("name"):
            reps.add(p["name"].strip().lower())
    reps |= {s["speaker"].lower() for s in turns if s["speaker"].lower() in KNOWN_REPS}
    speakers = {t["speaker"] for t in turns}
    return {s for s in speakers if s.lower() in reps}


def words(t):
    return len(t.split())


def content_tokens(q):
    return {w for w in re.findall(r"[a-z']+", q.lower()) if w not in STOP and len(w) > 2}


def main():
    workdir = Path(sys.argv[1])
    turns, meta = load(workdir)
    reps = rep_names(turns, meta)
    total = sum(words(t["text"]) for t in turns) or 1
    by_speaker = {}
    for t in turns:
        by_speaker[t["speaker"]] = by_speaker.get(t["speaker"], 0) + words(t["text"])
    share = {s: round(100 * w / total) for s, w in sorted(by_speaker.items(), key=lambda x: -x[1])}
    rep_share = sum(v for s, v in share.items() if s in reps)

    rep_turns = [t for t in turns if t["speaker"] in reps]
    # Monologues: Grain splits one long answer into several turns at pauses and screen-shares, so join consecutive
    # turns by the same speaker, letting through a tiny interjection from someone else ("mm-hm", "you have.").
    blocks = []
    for i, t in enumerate(turns):
        if blocks and blocks[-1]["speaker"] == t["speaker"]:
            blocks[-1]["words"] += words(t["text"]); blocks[-1]["last"] = t["line"]; continue
        prev = turns[i - 1] if i else None
        if (blocks and prev and words(prev["text"]) <= 3 and blocks[-1]["speaker"] == t["speaker"]) or \
           (len(blocks) >= 2 and prev and words(prev["text"]) <= 3 and blocks[-2]["speaker"] == t["speaker"] and blocks[-1]["line"] == prev["line"]):
            if blocks[-1]["line"] == (prev["line"] if prev else None) and blocks[-1]["speaker"] != t["speaker"]:
                blocks.pop()  # drop the interjection's own block; it's absorbed
            blocks[-1]["words"] += words(t["text"]); blocks[-1]["last"] = t["line"]; continue
        blocks.append({"speaker": t["speaker"], "line": t["line"], "last": t["line"], "words": words(t["text"])})
    rep_blocks = [b for b in blocks if b["speaker"] in reps]
    lb = max(rep_blocks, key=lambda b: b["words"], default=None)
    longest = {"line": lb["line"], "text": " " .join(["x"] * lb["words"]), "last": lb["last"]} if lb else None

    # Questions the rep asked (sentence-level), and near-duplicates of an earlier rep question.
    questions = []
    for t in rep_turns:
        for sent in re.split(r"(?<=[?.!])\s+", t["text"]):
            # Real questions only: skip tag questions ("…, right?", "Does that make sense?") and fragments.
            if sent.strip().endswith("?") and words(sent) >= 4 and not TAG_Q.search(sent.strip()) and not SMALLTALK_Q.search(sent):
                questions.append({"line": t["line"], "q": sent.strip()[:160]})
    # "Real" questions = the rep's question near the END of a turn that the prospect then answers.
    # Questions buried inside a monologue are rhetorical; they don't count toward discovery.
    idx = {t["line"]: i for i, t in enumerate(turns)}
    answered = []
    for t in rep_turns:
        i = idx[t["line"]]
        nxt = turns[i + 1] if i + 1 < len(turns) else None
        if not nxt or nxt["speaker"] in reps:
            continue
        tail_sents = [x for x in re.split(r"(?<=[?.!])\s+", t["text"].strip()) if x][-2:]
        q = next((x for x in reversed(tail_sents) if x.strip().endswith("?") and words(x) >= 4 and not TAG_Q.search(x.strip()) and not SMALLTALK_Q.search(x)), None)
        if q:
            answered.append({"line": t["line"], "q": q.strip()[:160], "open": is_open(q)})
    repeats = []
    for j, q in enumerate(questions):
        a = content_tokens(q["q"])
        for p in questions[:j]:
            b = content_tokens(p["q"])
            # Short questions ("Where am I at?") share one word with anything; a re-ask needs 3+ content words each.
            if len(a) >= 3 and len(b) >= 3 and len(a & b) / len(a | b) >= 0.5 and q["line"] != p["line"]:
                repeats.append({"line": q["line"], "repeats_line": p["line"], "q": q["q"]})
                break

    def first(regex, pool):
        for t in pool:
            if regex.search(t["text"]):
                return {"line": t["line"], "speaker": t["speaker"], "by_rep": t["speaker"] in reps}
        return None

    # The prospect stating their OWN deal size ("ACV", "contract value", "$200K average") is not a price
    # conversation — skip those lines so the flag means "our price came up".
    DEAL_SIZE = re.compile(r"\bACV\b|contract value|average to start|deal size|a year\b|per year|every year|figures|revenue", re.I)
    ASKS_THEIR_ACV = re.compile(r"contract value|\bACV\b|how much do they pay|do they pay you", re.I)
    price_pool = [t for t in turns if (t["speaker"] in reps and not ASKS_THEIR_ACV.search(t["text"])) or (t["speaker"] not in reps and not DEAL_SIZE.search(t["text"]))]
    price_first = first(PRICE_RE, price_pool)
    offer_first = first(OFFER_RE, turns)
    tail = turns[int(len(turns) * 0.7):]
    next_step_lines = [{"line": t["line"], "speaker": t["speaker"], "by_rep": t["speaker"] in reps, "text": t["text"][:140]} for t in tail if NEXT_RE.search(t["text"])]
    prospect_owns = [{"line": t["line"], "text": t["text"][:140]} for t in tail if t["speaker"] not in reps and PROSPECT_OWNS_RE.search(t["text"])]

    # Approximate minute marks: position by cumulative words, scaled to the call's length.
    minutes = float(meta.get("minutes") or 0)
    cum, acc = {}, 0
    for t in turns:
        cum[t["line"]] = acc
        acc += words(t["text"])
    def minute_at(line):
        return round(cum.get(line, 0) / total * minutes, 1) if minutes else None
    switches = sum(1 for a, b in zip(turns, turns[1:]) if a["speaker"] != b["speaker"])
    quarters = [0, 0, 0, 0]
    for q in answered:
        quarters[min(3, int(cum.get(q["line"], 0) / total * 4))] += 1

    # ---- per-rep and technique signals (lens B/D evidence; the reviewer confirms each) ----
    WHY_Q = re.compile(r"(^|[,;:—–]\s*)\W*(so,?\s+|and\s+|but\s+|like,?\s+)?why\b", re.I)
    LABEL = re.compile(r"\b(it|that) (sounds|seems|looks|feels) like\b|\byou (sound|seem)\b", re.I)

    def open_share(qs):
        return round(100 * sum(1 for q in qs if is_open(q["q"])) / len(qs)) if qs else None

    labels, mirrors = [], []
    for i, t in enumerate(turns):
        if t["speaker"] not in reps:
            continue
        if LABEL.search(t["text"]):
            labels.append({"line": t["line"], "speaker": t["speaker"], "text": t["text"][:140]})
        prev = turns[i - 1] if i else None
        if prev and prev["speaker"] not in reps and words(t["text"]) <= 6:
            # Voss: a mirror repeats the LAST 1-3 words of what they said. Filler and greetings never count.
            FILLER = {"yeah", "yes", "okay", "good", "great", "going", "doing", "hey", "hello", "thanks", "sure", "got", "cool", "right", "fine", "well", "nice"}
            tail = {w.lower().strip(".,?!'\"") for w in prev["text"].split()[-3:]}
            said = {w.lower().strip(".,?!'\"") for w in t["text"].split()}
            echo = {w for w in said & tail if w not in STOP and w not in FILLER and len(w) > 2}
            if echo:
                mirrors.append({"line": t["line"], "speaker": t["speaker"], "text": t["text"], "echoes": prev["text"][-80:]})

    per_rep = {}
    for r in sorted(reps):
        rt = [t for t in turns if t["speaker"] == r]
        rb = [b for b in rep_blocks if b["speaker"] == r]
        lgb = max(rb, key=lambda b: b["words"], default=None)
        lg = {"line": lgb["line"], "text": " ".join(["x"] * lgb["words"]), "last": lgb["last"]} if lgb else None
        rq = [q for q in answered if any(t["line"] == q["line"] for t in rt)]
        first_q_line = rq[0]["line"] if rq else None
        words_before_q = sum(words(t["text"]) for t in rt if first_q_line is None or t["line"] < first_q_line)
        per_rep[r] = {
            "talk_share_pct": share.get(r, 0),
            "longest_monologue": {"line": lg["line"], "words": words(lg["text"]), "approx_minutes": round(words(lg["text"]) / 150, 1)} if lg else None,
            "monologues_over_250_words": [b["line"] for b in rb if b["words"] > 250],
            "questions_answered": len(rq),
            "open_question_pct": open_share(rq),
            "why_questions": [q["line"] for q in rq if WHY_Q.search(q["q"])],
            "words_before_first_answered_question": words_before_q,
            "labels": [x["line"] for x in labels if x["speaker"] == r],
            "mirrors": [x["line"] for x in mirrors if x["speaker"] == r],
            "repeated_questions": [x["line"] for x in repeats if any(t["line"] == x["line"] for t in rt)],
        }
    offer_first_rep = first(OFFER_RE, rep_turns)

    n = len(turns) or 1
    out = {
        "call": {k: meta.get(k) for k in ("id", "title", "date", "minutes", "portalUrl")},
        "reps": sorted(reps),
        "turns": len(turns),
        "talk_share_pct": share,
        "rep_talk_share_pct": rep_share,
        "rep_longest_monologue": {"line": longest["line"], "to_line": longest["last"], "words": words(longest["text"]), "approx_minutes": round(words(longest["text"]) / 150, 1)} if longest else None,
        "rep_questions": len(answered),
        "rep_question_lines": answered,
        "rep_questions_raw_incl_rhetorical": len(questions),
        "rep_repeated_questions": repeats,
        "price_first_mentioned": price_first,
        "price_first_position_pct": round(100 * price_first["line"] / n) if price_first else None,
        "price_first_minute": minute_at(price_first["line"]) if price_first else None,
        "rep_longest_monologue_minute": minute_at(longest["line"]) if longest else None,
        "speaker_switches_per_min": round(switches / minutes, 1) if minutes else None,
        "rep_questions_by_quarter": quarters,
        "offer_first_mentioned": offer_first,
        "next_step_signals_in_last_30pct": next_step_lines,
        "prospect_owns_next_step_signals": prospect_owns,
        "rep_open_question_pct": open_share(answered),
        "rep_why_questions": [q["line"] for q in answered if WHY_Q.search(q["q"])],
        "label_candidates": labels,
        "mirror_candidates": mirrors,
        "offer_first_by_rep": offer_first_rep,
        "offer_first_minute": minute_at(offer_first_rep["line"]) if offer_first_rep else None,
        "per_rep": per_rep,
        # Approximate minute mark of every line (by word position × call length) — reps can't use line numbers,
        # they need a time to jump to in the recording. Always shown with a "~".
        "line_minute": {str(t["line"]): minute_at(t["line"]) for t in turns} if minutes else {},
        # Talk map: one segment per turn, as fractions of the call's words, us vs them.
        "talk_map": [{"line": t["line"], "us": t["speaker"] in reps, "start": round(cum[t["line"]] / total, 4),
                      "width": round(words(t["text"]) / total, 4)} for t in turns],
        "flags": [],
    }
    f = out["flags"]
    if rep_share > 55: f.append(f"rep talked {rep_share}% (target 40-50% on discovery)")
    if longest and words(longest["text"]) > 300: f.append(f"rep monologue of {words(longest['text'])} words at line {longest['line']} (~{out['rep_longest_monologue']['approx_minutes']} min)")
    if repeats: f.append(f"{len(repeats)} rep question(s) repeat an earlier one")
    if quarters[0] and sum(quarters[1:]) == 0: f.append("all rep questions in the first quarter, none after")
    if not price_first: f.append("price never mentioned")
    elif not price_first["by_rep"]: f.append(f"prospect raised price first (line {price_first['line']})")
    if prospect_owns: f.append("prospect holds the next step (" + "; ".join(f"L{p['line']}" for p in prospect_owns) + ")")
    if not next_step_lines: f.append("no dated/scheduled next step detected near the end")

    # Exact timings from Grain (grain_timing.py), when available: exact minute marks and talk share by speaking time.
    tp = workdir / "timing.json"
    if tp.exists():
        timing = json.loads(tp.read_text())
        out["timing"] = "exact"
        out["line_minute"] = {k: round(v["start_ms"] / 60000, 3) for k, v in timing["lines"].items()}
        spoken = sum(timing["talk_ms"].values()) or 1
        us_ms = sum(ms for name, ms in timing["talk_ms"].items() if name in reps)
        out["talk_share_basis"] = "speaking time"
        out["rep_talk_share_pct"] = round(100 * us_ms / spoken)
        for r in per_rep:
            per_rep[r]["talk_share_pct"] = round(100 * timing["talk_ms"].get(r, 0) / spoken)
        dur_ms = timing.get("duration_ms") or 1
        out["duration_min"] = round(dur_ms / 60000, 2)
        out["talk_map"] = [{"line": t["line"], "us": t["speaker"] in reps,
                            "start": round(timing["lines"][str(t["line"])]["start_ms"] / dur_ms, 4),
                            "width": round((timing["lines"][str(t["line"])]["end_ms"] - timing["lines"][str(t["line"])]["start_ms"]) / dur_ms, 4)}
                           for t in turns if str(t["line"]) in timing["lines"]]
    else:
        out["timing"] = "estimated"
        out["talk_share_basis"] = "words"
    workdir.joinpath("metrics.json").write_text(json.dumps(out, indent=2))
    print(f"{meta.get('title')} | reps: {', '.join(sorted(reps)) or 'NONE DETECTED'} | {len(turns)} turns")
    print("talk share: " + ", ".join(f"{s} {p}%" for s, p in share.items()))
    if longest: print(f"rep longest monologue: {words(longest['text'])} words at L{longest['line']}")
    print(f"rep questions answered by the prospect: {len(answered)} (raw incl. rhetorical {len(questions)}; repeats: {len(repeats)}) by quarter {quarters} · switches/min {out['speaker_switches_per_min']}")
    print(f"price first: {price_first}")
    print(f"open questions: {out['rep_open_question_pct']}% · why-questions: {len(out['rep_why_questions'])} · label candidates: {len(labels)} · mirror candidates: {len(mirrors)}")
    for r, v in per_rep.items():
        lm = v["longest_monologue"] or {}
        print(f"  {r}: talk {v['talk_share_pct']}% · longest {lm.get('words')}w · Qs {v['questions_answered']} ({v['open_question_pct']}% open) · {v['words_before_first_answered_question']} words before first real question")
    for x in f: print("FLAG:", x)


if __name__ == "__main__":
    main()
