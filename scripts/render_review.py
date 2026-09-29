#!/usr/bin/env python3
"""Render the shareable call-review page (OneAway brand) from the scorecard and the judge's notes.

Usage: python3 render_review.py <workdir>
Reads  <workdir>/scorecard.json (score.py), judge.json (the orchestrator), metrics.json, transcript.txt,
       timing.json (optional, grain_timing.py), ~/.claude/call-review/reps/*.json, <skill>/assets/fonts.css,
       <skill>/references/oneaway-context.md (the claims lint).
Writes <workdir>/review.html — publish it with the Artifact tool.
Exit 3: over the reading budget (first screen ≤ SKIM_WORDS; plus the script ≤ TOTAL_WORDS).
Exit 4: the claims lint failed — a line we wrote for the exec states a figure or a sweeping claim about OneAway
        that isn't in the transcript or the context pack. Fix the line (or phrase it as a question); never
        invent positioning, prices or "what we see across clients".

judge.json (every quote comes from scorecard evidence; `line` is its transcript line):
{
  "headline": "≤ 8 words: the main line of the call",
  "verdict":  "≤ 30 words: what happened and where it left the deal",
  "worked":   [{"text": "...", "line": 23, "quote": "..."}],                       1–2, recoveries count
  "items":    {"<move id>": "≤ 12 words: what happened on this move"},
  "focus":    {"<exec name>": {"why": {"text": "...", "line": 22, "quote": "..."}, "say_instead": "...", "drill": "..."}},
  "script":   {"with": "Jamie", "steps": [{"step": "Open", "move": "open", "cue": "≤ 14 words: when to say it",
                "line": 22, "quote": "...", "say": "the line" | ["question 1", "question 2"]}]},   call order, ≤ 6 steps
  "trust_note": "only when trust isn't clean",
  "fit": [{"label": "Deal value", "value": "...", "known": true}],
  "recovery_email": "ONLY when the prospect was clearly put off or a claim needs correcting (a fix); needs recovery_reason",
  "recovery_reason": "why this call needs one"
}
"""
import datetime
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rubric import ITEMS, ITEM_BY_ID, CHECK_BY_ID, CALL_TYPES, STATUS  # noqa: E402
from grain_timing import load as load_timing, moment, link as grain_link  # noqa: E402

SKIM_WORDS, TOTAL_WORDS = 400, 1200  # 2 min at a careful 200 wpm; 5 min at 240 wpm
SKILL = Path(__file__).resolve().parent.parent
HOME = Path.home() / ".claude" / "call-review"
e = lambda s: html.escape(str(s if s is not None else ""), quote=True)  # noqa: E731
SWEEPING = re.compile(r"\b(we only|we aim at|we always|we never|we guarantee|guaranteed?|clients like you|"
                      r"what we (usually |typically )?see|across (our )?clients|most of our clients|our clients (usually|typically))\b", re.I)


OUTCOME_GLOSS = {"moved_forward": "{them} is interested and the next step is booked.",
                 "left_open": "{them} is interested, but the next step is in {them}'s hands.",
                 "stalled": "No clear interest or path forward yet."}
RESULT_WORD = {"met": "done", "missed": "not done", "na": "didn't apply"}


def ms_label(ms):
    return f"{ms // 60000:02d}:{ms // 1000 % 60:02d}"


class Page:
    def __init__(self, wd):
        self.wd = Path(wd)
        self.sc = json.loads((self.wd / "scorecard.json").read_text())
        self.j = json.loads((self.wd / "judge.json").read_text())
        self.m = json.loads((self.wd / "metrics.json").read_text())
        self.timing = load_timing(self.wd)
        self.side = {str(t["line"]): t["us"] for t in self.m.get("talk_map", [])}
        self.reps = self.sc["reps"]
        self.meta = json.loads((self.wd / "meta.json").read_text()) if (self.wd / "meta.json").exists() else {}
        self.people = participants(self.meta, self.reps)
        pros = [p.strip() for p in (self.sc["call"].get("prospect") or "").split(",") if p.strip()]
        self.them_name = pros[0].split()[0] if len(pros) == 1 else (self.sc["call"].get("company") or "Them")
        self.us_name = self.reps[0].split()[0] if len(self.reps) == 1 else "We"

    # ---- time, links, quotes ------------------------------------------------------------------------
    def ms_of(self, line, quote=None):
        if not line:
            return None
        if self.timing:
            return moment(self.timing, line, quote)
        mnt = (self.m.get("line_minute") or {}).get(str(line))
        return None if mnt is None else int(mnt * 60000)

    def when(self, line, quote=None):
        """▶ 09:16 linking into Grain at that moment (exact), or ~07:54 as plain text (estimated)."""
        ms = self.ms_of(line, quote)
        if ms is None:
            return ""
        if self.timing:
            return f'<a class="t" href="{e(grain_link(self.timing, line, quote))}" target="_blank" rel="noopener" title="Play this moment">▶ {ms_label(ms)}</a>'
        return f'<span class="t est" title="estimated from word position">~{ms_label(ms)}</span>'

    def lines_to_times(self, text):
        """Reviewer notes cite transcript lines ("L22"); readers need moments ("▶ 09:16")."""
        esc = e(text)
        def sub(m):
            t = self.when(int(m.group(1)))
            return t or m.group(0)
        return re.sub(r"\b(?:L|[Ll]ine )(\d{1,4})\b", sub, esc)

    def q(self, quote, line):
        if not quote:
            return ""
        return f'<q class="{"us" if self.side.get(str(line)) else "them"}">{e(quote)}</q>'

    # ---- marks --------------------------------------------------------------------------------------
    def status(self, move_id):
        """A plain word, never a symbol that needs a legend: Good / Partly / Work on."""
        sc = self.sc["items"].get(move_id, {}).get("score")
        return f'<span class="sw s{sc if sc is not None else "na"}">{STATUS.get(sc, "N/A")}</span>'

    def focus_moves(self):
        out = {}
        for name in self.reps:
            cid = (((rep_file(name) or {}).get("active") or {}).get("check") or {}).get("id")
            if cid in CHECK_BY_ID:
                out[name] = CHECK_BY_ID[cid]["item"]
            elif cid in ITEM_BY_ID:
                out[name] = cid
        return out

    def fingerprint(self):
        focus = set(self.focus_moves().values())
        cols = "".join(f'<a class="col{" focus" if it["id"] in focus else ""}" href="#r-{it["id"]}" title="{e(it["name"])}: '
                       f'{STATUS.get(self.sc["items"].get(it["id"], {}).get("score"), "N/A")}">{self.cells(it["id"])}</a>' for it in ITEMS)
        return f'<div class="fp" aria-label="Sixteen checks: one column per move, key check on top">{cols}</div>'

    # ---- first screen -------------------------------------------------------------------------------
    def focus_applies(self, name):
        """False when this exec's focus couldn't be measured on this call (e.g. the other exec opened)."""
        rep = rep_file(name) or {}
        a = rep.get("active") or {}
        h = next((x for x in rep.get("history", []) if x.get("call_id") == self.sc["call"].get("id") and x.get("focus_id") == a.get("id")), None)
        return not (h and h.get("hit") is None)

    def focus_card(self, name):
        rep = rep_file(name) or {}
        a = rep.get("active") or {}
        jf = (self.j.get("focus") or {}).get(name, {})
        h = next((x for x in reversed(rep.get("history", [])) if x.get("call_id") == self.sc["call"].get("id") and x.get("focus_id") == a.get("id")), None)
        streak, need = int(a.get("streak", 0)), int(a.get("fixed_after", 3))
        dots = ""
        state = "new focus" if not h else ("done this call" if h.get("hit") else "not yet" if h.get("hit") is False else "n/a this call")
        move = self.focus_moves().get(name)
        why = jf.get("why") or {}
        step = next((st for st in (self.j.get("script") or {}).get("steps", []) if st.get("move") == move and isinstance(st.get("say"), str)), None)
        if step:
            jf = {**jf, "say_instead": step["say"]}
        first = name.split()[0]
        if h and h.get("hit") is None:  # the focus couldn't apply to this exec on this call: keep the card to one line
            return (f'<section class="focus compact" id="focus-{e(first.lower())}" aria-label="Focus for {e(first)}">'
                    f'<p class="label">Your one change, {e(first)} · n/a this call</p><p class="behaviour sm">{e(a.get("behavior", ""))}</p></section>')
        return f'''<section class="focus" id="focus-{e(first.lower())}" aria-label="Focus for {e(first)}">
  <p class="label">Your one change, {e(first)}{(" · " + e(ITEM_BY_ID[move].get("page", ITEM_BY_ID[move]["name"]))) if move else ""}
     {f'<span class="streak">done {streak} call{"s" if streak != 1 else ""} in a row · {need} in a row and it becomes a habit</span>' if streak else ""}</p>
  <p class="behaviour">{e(a.get("behavior", "No focus set yet"))}</p>
  {f'<p class="why">{"This call:" if h and h.get("hit") else "Why:"} {self.when(why.get("line"), why.get("quote"))} {e(why.get("text", ""))}</p>' if why else ""}
  {f'<p class="say"><span class="qm">“</span>{e(jf["say_instead"])}</p>' if jf.get("say_instead") else ""}
  {f'<p class="drill">Before the next call: {e(jf["drill"])}</p>' if jf.get("drill") else ""}
</section>'''

    def numbers(self):
        segs = self.m.get("talk_map") or []
        if not segs:
            return ""
        s0 = min(s["start"] for s in segs)
        s1 = max(s["start"] + s["width"] for s in segs) or 1
        span = (s1 - s0) or 1
        pos = lambda f: (f - s0) / span  # noqa: E731
        lanes = ""
        for us, who in ((True, self.us_name if self.us_name != "We" else "OneAway"), (False, self.them_name)):
            rects = "".join(f'<rect x="{pos(s["start"]) * 1000:.1f}" y="0" width="{max(s["width"] / span * 1000, 1.2):.1f}" height="10"/>'
                            for s in segs if s["us"] == us)
            lanes += f'<div class="lane {"us" if us else "them"}"><span class="who">{e(who)}</span><svg viewBox="0 0 1000 10" preserveAspectRatio="none" aria-hidden="true">{rects}</svg></div>'
        # Ends of the bar: the first and last word, in recording time.
        first_line, last_line = segs[0]["line"], segs[-1]["line"]
        t0 = self.ms_of(first_line) or 0
        if self.timing:
            t1 = self.timing["lines"][str(last_line)]["end_ms"]
        else:
            t1 = int(float((self.m.get("call") or {}).get("minutes") or 0) * 60000)
        est = "" if self.timing else "~"
        starts = {str(s["line"]): s for s in segs}
        notes = ""
        fq = (self.m.get("rep_question_lines") or [{}])[0].get("line")
        if fq and str(fq) in starts:
            x = min(96, max(0, pos(starts[str(fq)]["start"]) * 100))
            place = f"left:{x:.1f}%" if x < 55 else f"right:{100 - x:.1f}%;text-align:right"  # keep the label on screen
            notes += f'<span class="tick" style="{place}">↑ first question {self.when(fq)}</span>'
        lm = self.m.get("rep_longest_monologue") or {}
        if lm.get("line") and str(lm["line"]) in starts:
            a = starts[str(lm["line"])]
            b = starts.get(str(lm.get("to_line") or lm["line"]), a)
            x0, x1 = pos(a["start"]) * 100, pos(b["start"] + b["width"]) * 100
            dur = self.duration(lm)
            row2 = " row2"  # always on its own row: side-by-side labels collide on a phone
            mid = (x0 + x1) / 2
            anchor = " at-left" if mid < 30 else (" at-right" if mid > 70 else "")  # labels near an edge anchor inward
            notes += f'<span class="bracket{row2}{anchor}" style="left:{x0:.1f}%;width:{max(x1 - x0, 3):.1f}%"><em>longest answer, {e(dur)}</em></span>'
        rows = self.verdict_rows()
        return f'''<section class="numbers" aria-labelledby="num-h"><h2 id="num-h">The numbers</h2>
  <div class="tiles">{self.stat_tiles()}</div>
</section>'''

    def seconds(self, lm):
        if self.timing and str(lm.get("line")) in self.timing["lines"]:
            end_line = str(lm.get("to_line") or lm["line"])
            return (self.timing["lines"].get(end_line, self.timing["lines"][str(lm["line"])])["end_ms"] - self.timing["lines"][str(lm["line"])]["start_ms"]) / 1000
        return (lm.get("words") or 0) / 150 * 60

    def stat_tiles(self):
        """Four graphic tiles: each shows the number AND a picture of it against the aim."""
        panel = {r["key"]: r for r in self.sc["panel"]}
        ct = CALL_TYPES[self.sc["call_type"]]
        tiles = []

        def tile(status, big, label, graphic, aim, tip=""):
            word, cls = ("Good", "s2") if status == "ok" else ("Work on", "s0")
            t = f' title="{e(tip)}"' if tip else ""
            return (f'<div class="tile"{t}><p class="tstat"><span class="sw {cls}">{word}</span></p><p class="tbig">{big}</p>'
                    f'<p class="tlabel">{e(label)}</p><div class="tgfx">{graphic}</div><p class="taim">{e(aim)}</p></div>')

        # 1. talk time: split bar with the aim marker
        us = self.sc["panel_raw"].get("us_pct") or 0
        aim = ct["talk_max"]
        gfx = (f'<div class="split"><span class="us" style="width:{us}%"></span><span class="them" style="width:{100 - us}%"></span>'
               f'<i class="mark" style="left:{aim}%"><b>{aim}%</b></i></div>'
               f'<div class="legend2"><span><i class="us"></i>{e(self.us_name if self.us_name != "We" else "OneAway")}</span><span><i class="them"></i>{e(self.them_name)}</span></div>')
        tiles.append(tile(panel.get("talk", {}).get("status", "ok"), f"{us}%", f"of the talking was {self.us_name if self.us_name != 'We' else 'us'}",
                          gfx, f"aim: under {aim}%"))

        # 2. questions: one square per question, filled = open-ended
        n = self.m.get("rep_questions") or 0
        op = self.m.get("rep_open_question_pct") or 0
        k = round(n * op / 100)
        sq = "".join(f'<i class="q{" on" if i < k else ""}"></i>' for i in range(n))
        tiles.append(tile(panel.get("questions", {}).get("status", "ok"), f'{k}<small> of {n}</small>', "questions were open-ended",
                          f'<div class="dots">{sq}</div><p class="tkey"><i class="q on"></i>open <i class="q"></i>yes/no</p>',
                          "aim: at least half open-ended", "Open-ended = can't be answered with yes or no"))

        # 3. longest answer: bar against the 1½-minute marker
        lm = self.m.get("rep_longest_monologue") or {}
        sec = self.seconds(lm) if lm else 0
        scale = max(sec, 180) * 1.08
        big = f"{sec:.0f}<small> s</small>" if sec < 90 else f"{sec / 60:.1f}<small> min</small>"
        gfx = (f'<div class="bar"><span class="fill" style="width:{min(100, sec / scale * 100):.1f}%"></span>'
               f'<i class="mark" style="left:{90 / scale * 100:.1f}%"><b>1½ min</b></i></div>')
        tiles.append(tile("ok" if (lm.get("words") or 0) <= 250 else "bad", big, "longest answer without a question", gfx, "aim: under 1½ minutes"))

        # 4. problems followed up: one square per problem
        pains = (self.sc.get("evidence") or {}).get("pains") or []
        if pains:
            got = sum(1 for p in pains if p.get("followed_up_line"))
            sq = "".join(f'<i class="q{" on" if p.get("followed_up_line") else ""}"></i>' for p in pains)
            tiles.append(tile("ok" if got == len(pains) else "bad", f'{got}<small> of {len(pains)}</small>',
                              f"problems {self.them_name} raised got a follow-up question",
                              f'<div class="dots big">{sq}</div><p class="tkey"><i class="q on"></i>followed up <i class="q"></i>not</p>',
                              "aim: all of them (listed in Part 3)"))
        return "".join(tiles)

    def duration(self, lm):
        if self.timing and str(lm.get("line")) in self.timing["lines"]:
            end_line = str(lm.get("to_line") or lm["line"])
            ms = self.timing["lines"].get(end_line, self.timing["lines"][str(lm["line"])])["end_ms"] - self.timing["lines"][str(lm["line"])]["start_ms"]
            sec = ms / 1000
        else:
            sec = (lm.get("words") or 0) / 150 * 60
        return f"{sec:.0f} seconds" if sec < 90 else f"{sec / 60:.1f} minutes"

    def verdict_rows(self):
        panel = {r["key"]: r for r in self.sc["panel"]}
        rows = []
        word = lambda st: ("Good", "met") if st == "ok" else ("Work on", "missed")  # noqa: E731
        us = self.sc["panel_raw"].get("us_pct") or 0
        ct = CALL_TYPES[self.sc["call_type"]]
        if "talk" in panel:
            rows.append((panel["talk"]["status"], f"{self.us_name} talked {us}%, {self.them_name} {100 - us}%",
                         f"aim: {self.us_name if self.us_name != 'We' else 'us'} under {ct['talk_max']}%", ""))
        if "questions" in panel:
            n = self.m.get("rep_questions") or 0
            op = self.m.get("rep_open_question_pct") or 0
            k = round(n * op / 100)
            lead = "only " if k * 2 < n else ""
            lo = int(re.match(r"(\d+)", panel["questions"]["guide"]).group(1)) if re.match(r"\d", panel["questions"]["guide"]) else 0
            aim = "aim: at least half open-ended" if n >= lo else f"aim: at least {lo}, half of them open-ended"
            rows.append((panel["questions"]["status"], f"{n} questions, {lead}{k} open-ended", aim,
                         "Open-ended = can't be answered with yes or no"))
        lm = self.m.get("rep_longest_monologue") or {}
        if lm:
            rows.append(("ok" if (lm.get("words") or 0) <= 250 else "bad", f"Longest answer: {self.duration(lm)}", "aim: under 1½ minutes", ""))
        pains = (self.sc.get("evidence") or {}).get("pains") or []
        if pains:
            got = sum(1 for p in pains if p.get("followed_up_line"))
            rows.append(("ok" if got == len(pains) else "bad", f"Of the {len(pains)} problems {self.them_name} raised, {got} got a follow-up question",
                         "aim: all of them (listed in the receipts)", "A follow-up question before answering"))
        out = ""
        for st, text, aim, tip in rows:
            w, cls = word(st)
            out += (f'<li{f" title={chr(34)}{e(tip)}{chr(34)}" if tip else ""}><span class="sw {"s2" if cls == "met" else "s0"}">{w}</span>'
                    f'<span class="tx">{e(text)}</span><span class="aim">{e(aim)}</span></li>')
        return out

    def first_screen(self):
        sc, j = self.sc, self.j
        o = sc["outcome"]
        caps = "".join(f' <span class="cap">({e(c)})</span>' for c in sc.get("caps_applied", []))
        worked = "".join(f'<li>{e(w.get("text"))} {self.when(w.get("line"), w.get("quote"))}</li>' for w in (j.get("worked") or [])[:2])
        steps = {s.get("move") for s in (j.get("script") or {}).get("steps", [])}
        board = ""
        for it in ITEMS:
            r = sc["items"].get(it["id"], {})
            if r.get("score") is None:
                continue
            nxt = f'<a class="tonext" href="#s-{it["id"]}">What to say next time ↓</a>' if it["id"] in steps else ""
            board += (f'<li><details class="row" id="m-{it["id"]}"><summary>{self.status(it["id"])}<span class="nm">{e(it.get("page", it["name"]))}</span>'
                      f'<span class="tx">{e((j.get("items") or {}).get(it["id"], ""))}</span><span class="chev" aria-hidden="true"></span></summary>'
                      f'<div class="exp"><p class="qq">{e(it["question"])}</p>{self.move_checks(it)}{nxt}</div></details></li>')
        tr = sc["trust"]
        tword, tcls = {"clean": ("Clean", "s2"), "tighten": ("Tighten", "s1"), "fix": ("Fix", "s0")}.get(tr["verdict"], ("Clean", "s2"))
        flagged = tr.get("top", [])  # score.py picks the ≤3 lines worth showing; tone lines never count
        if flagged:
            ttx = e(tr["line"])
            word = lambda v: "not accurate" if v in ("FALSE", "BANNED") else "could be tighter"  # noqa: E731
            claims = "".join(f'<li class="ck"><p class="meta2"><b>{word(cl.get("verdict", ""))}</b> · {self.when(cl.get("line"), cl.get("quote"))}</p>'
                             f'<p>{self.q(cl.get("quote"), cl.get("line"))}</p>'
                             f'{("<p class=note>Better: " + self.lines_to_times(cl["correct"]) + "</p>") if cl.get("correct") else ""}</li>' for cl in flagged)
            trust = (f'<li><details class="row" id="m-trust"><summary><span class="sw {tcls}">{tword}</span><span class="nm">What we claimed</span>'
                     f'<span class="tx">{ttx}</span><span class="chev" aria-hidden="true"></span></summary><div class="exp"><ul class="cks">{claims}</ul></div></details></li>')
        else:
            trust = (f'<li><div class="row static"><span class="sw {tcls}">{tword}</span><span class="nm">What we claimed</span>'
                     f'<span class="tx">{e(tr["line"])}</span></div></li>')
        focus = "".join(self.focus_card(r) for r in self.reps)
        return f'''
<section class="hero">
  <div class="hl">
    <p class="outcome"><span>{e(o["label"])}</span><span>·</span><span><b>{sc["score"]:.1f}</b><span class="of">/10</span></span>{caps}</p>
    <p class="gloss">{e(OUTCOME_GLOSS[o["id"]].format(them=self.them_name))} {e(o["label"])} calls score {o["low"]:.0f}–{o["high"]:.0f}.</p>
    <h1>{e(j.get("headline", ""))}</h1>
    <p class="verdict">{e(j.get("verdict", ""))}</p>
    {"".join(f'<p class="pointer"><a href="#next">Your one change, {e(n.split()[0])}: {e((rep_file(n) or {}).get("active", {}).get("behavior", ""))} ↓</a></p>' for n in self.reps if (rep_file(n) or {}).get("active") and self.focus_applies(n))}
  </div>
</section>
<div class="part" id="how"><p class="part-label">Part 1 · How the call went</p>
{f'<section class="worked"><h2>What worked</h2><ul>{worked}</ul></section>' if worked else ""}
<section class="moves" id="moves" aria-labelledby="moves-h"><h2 id="moves-h">Each part of the call</h2>
  <p class="hint">Tap a part to see what happened.</p>
  <ol class="board">{board}{trust}</ol>
</section>
{self.numbers()}
</div>''', focus

    # ---- the script ---------------------------------------------------------------------------------
    def script(self):
        sc = self.j.get("script") or {}
        focus = set(self.focus_moves().values())
        items = ""
        for st in sc.get("steps", []):
            say = st.get("say")
            say_html = ("<ol class='asks'>" + "".join(f"<li>{e(x)}</li>" for x in say) + "</ol>") if isinstance(say, list) \
                else f'<p class="say"><span class="qm">“</span>{e(say)}</p>'
            tag = '<span class="tag">your one change</span>' if st.get("move") in focus else ""
            items += (f'<li id="s-{e(st.get("move", ""))}"><p class="step">{e(st.get("step", ""))}{tag}</p>'
                      f'<p class="cue">{e(st.get("cue", ""))} {self.when(st.get("line"), st.get("quote"))}</p>{say_html}</li>')
        if not items:
            return ""
        return f'''<section class="script" aria-labelledby="sc-h"><h2 id="sc-h">Next call{(" with " + e(sc["with"])) if sc.get("with") else ""}</h2>
  <p class="sub">Your script, in call order. Each cue shows the moment from last time.</p><ol class="steps">{items}</ol>
  <p class="source">Offer lines reuse what was offered on this call, reshaped; change the offer to fit the client. About $6.2k a month is the usual starting point, not a price list: quote your own number for the scope you describe.</p></section>'''

    def email(self):
        if not self.j.get("recovery_email"):
            return ""
        return f'''<section class="email" aria-labelledby="em-h"><h2 id="em-h">Recovery email</h2><p class="muted">{e(self.j.get("recovery_reason", ""))}</p>
  <pre id="email-text">{e(self.j["recovery_email"])}</pre><button type="button" id="copy-email">Copy email</button></section>'''

    def move_checks(self, it):
        r = self.sc["items"].get(it["id"], {})
        out = ""
        for ck in it["checks"]:
            c = (r.get("checks") or {}).get(ck["id"], {})
            res = c.get("result", "na")
            out += (f'<li class="ck {res}"><p class="cl"><span class="kind">{"Key" if ck.get("key") else "Supporting"}</span>{e(ck["label"])}</p>'
                    f'<p class="meta2"><b>{RESULT_WORD.get(res, res)}</b>{(" · " + e(c["rep"])) if c.get("rep") and c.get("rep") != "both" else ""}'
                    f'{(" · " + self.when(c.get("line"), c.get("quote"))) if c.get("line") else ""}</p>'
                    f'{("<p>" + self.q(c.get("quote"), c.get("line")) + "</p>") if c.get("quote") else ""}'
                    f'{("<p class=note>" + self.lines_to_times(c["note"]) + "</p>") if c.get("note") else ""}'
                    f'{self.measured_examples(ck["id"], c)}</li>')
        return f'<ul class="cks">{out}</ul>'

    def speaker(self, line):
        if not hasattr(self, "_spk"):
            self._spk = {i: l.split(":", 1)[0].strip() for i, l in
                         enumerate((self.wd / "transcript.txt").read_text().splitlines(), 1) if ":" in l}
        return self._spk.get(line)

    def measured_examples(self, cid, c):
        """A measured check is only a number; show the real moments behind it so anyone can check the count."""
        rep = c.get("rep") if c.get("rep") not in (None, "both") else None
        clip = lambda t, n=110: t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"  # noqa: E731
        rows = []
        if cid == "listen.questions":
            qs = [q for q in self.m.get("rep_question_lines", []) if "open" in q and (not rep or self.speaker(q["line"]) == rep)]
            # Examples should read cleanly: pick questions nearest ~14 words, shown in call order.
            meaty = lambda xs, n: sorted(sorted(xs, key=lambda q: abs(len(q["q"].split()) - 14))[:n], key=lambda q: q["line"])  # noqa: E731
            closed, opened = [q for q in qs if not q["open"]], [q for q in qs if q["open"]]
            picks = ([("Closed", q) for q in meaty(closed, 2)] + [("Open", q) for q in meaty(opened, 1)]) if c.get("result") == "missed" \
                else [("Open", q) for q in meaty(opened, 2)]
            rows = [(k, self.when(q["line"], " ".join(q["q"].split()[:4])), f"“{e(clip(q['q']))}”") for k, q in picks]
            if qs:
                rows.append(("Count", "", f"{len(opened)} open of {len(qs)} questions they answered (small talk and “does that sound fair?” checks left out)"))
        elif cid == "teach.short":
            lm = ((self.m.get("per_rep") or {}).get(rep) or {}).get("longest_monologue") if rep else self.m.get("rep_longest_monologue")
            if lm and lm.get("line"):
                text = next((l.split(":", 1)[1] for i, l in enumerate((self.wd / "transcript.txt").read_text().splitlines(), 1)
                             if i == lm["line"] and ":" in l), "")
                start = " ".join(text.split()[:14])
                rows = [("Longest", self.when(lm["line"], " ".join(text.split()[:4])), f"{lm['words']:,} words, starting “{e(start)}…”")]
        if not rows:
            return ""
        return '<ul class="ex">' + "".join(f'<li><span class="exk">{k}</span>{(t + " ") if t else ""}{x}</li>' for k, t, x in rows) + "</ul>"

    def receipts(self):
        """Part 3 · The evidence: open by default, grouped by part of the call, readable on a phone."""
        sc = self.sc
        nums = "".join(f'<tr><th scope="row">{e(r["label"])}</th><td class="num">{e(r["display"])}</td><td class="muted">{e(r["guide"])}</td></tr>' for r in sc["panel"])
        fit = "".join(f'<div><dt>{e(f.get("label"))}</dt><dd>{e(f.get("value"))} <span class="muted">{"known" if f.get("known") else "assumed"}</span></dd></div>'
                      for f in self.j.get("fit") or [])
        o = sc["outcome"]
        timing = ("Every ▶ opens the recording in Grain at that moment (for OneAway teammates signed in to Grain)."
                  if self.timing else "Times are estimated (~) because this recording isn't link-shared in Grain; share it there to get exact, clickable times.")
        return f'''<div class="part" id="evidence"><p class="part-label">Part 3 · The evidence</p>
<section class="evidence" aria-labelledby="ev-h"><h2 id="ev-h">The detail behind the numbers</h2>
  <p class="sub">Each part of the call in Part 1 opens to show its own evidence. {timing}</p>
  {self.pains_table()}
  <details class="more" open><summary>All the numbers and how the score works</summary>
    <div class="tablewrap"><table class="checks">{nums}</table></div>
    {f'<h3>Does the deal pay back?</h3><dl class="fit">{fit}</dl>' if fit else ""}
    <p class="muted">{e(o["label"])} calls score {o["low"]:.0f}–{o["high"]:.0f}. Within that range, each part's key check counts 70% and its supporting check 30%. Good = both checks happened; Partly = one of them; Work on = neither. Quotes that couldn't be found word for word in the transcript were thrown out ({len(sc.get("rejected_evidence", []))} this call).</p>
  </details>
</section></div>'''

    def pains_table(self):
        pains = (self.sc.get("evidence") or {}).get("pains") or []
        if not pains:
            return ""
        items = "".join(f'<li class="ck {"met" if p.get("followed_up_line") else "missed"}"><p class="meta2"><b>{"followed up " if p.get("followed_up_line") else "not followed up"}</b>'
                        f'{self.when(p["followed_up_line"]) if p.get("followed_up_line") else ""} · raised {self.when(p.get("line"), p.get("quote"))}</p>'
                        f'<p>{self.q(p.get("quote"), p.get("line"))}</p></li>' for p in pains)
        return f'<article class="ev" id="r-problems"><h3>Problems {e(self.them_name)} raised</h3><p class="qq">Did each one get a follow-up question before we answered?</p><ul class="cks">{items}</ul></article>'

    def call_card(self, facts):
        pp = self.people
        dom = (f' <a class="dom" href="https://{e(pp["domain"])}" target="_blank" rel="noopener">{e(pp["domain"])} ↗</a>' if pp["domain"] else "")
        emails = f'<p class="em">{" · ".join(e(x) for x in pp["them_emails"])}</p>' if pp["them_emails"] else ""
        return f'''<div class="callcard">
    <div class="side"><p class="lbl">Call with</p><p class="co">{e(pp["company"])}{dom}</p>
      <p class="ppl">{e(", ".join(pp["them"]))}</p>{emails}</div>
    <div class="side"><p class="lbl">OneAway</p><p class="ppl">{e(", ".join(pp["us"]))}</p></div>
  </div>
  <p class="facts">{e(facts)}</p>'''

    def render(self):
        call, sc = self.sc["call"], self.sc
        try:
            when = datetime.datetime.strptime((call.get("date") or "")[:16], "%Y-%m-%d %H:%M").strftime("%b %-d, %Y")
        except ValueError:
            when = call.get("date", "")
        ct = CALL_TYPES.get(sc["call_type"], {}).get("label", sc["call_type"])
        rec = self.timing["url"] if self.timing else (call.get("grainUrl") or call.get("portalUrl"))
        facts = " · ".join(x for x in [when, ct, f'{call.get("minutes", "")} min'] if x)
        first, focus = self.first_screen()
        read = self.script()
        part2 = f'<div class="part" id="next"><p class="part-label">Part 2 · What to do next</p>{focus}{read}{self.email()}</div>'
        page = f'''<title>{e((call.get("company") or call.get("title", ""))[:40])} Call Review</title>
<style>
{FONTS.read_text() if FONTS.exists() else ""}
{CSS}
</style>
<div class="wrap">
<header class="meta"><div class="row1"><p class="brand"><span>&lt;</span>oneaway<span>&gt;</span> <em>// call review</em></p>
  {f'<a class="rec" href="{e(rec)}" target="_blank" rel="noopener">▶ Recording</a>' if rec else ""}</div>
  {self.call_card(facts)}</header>
{first}
{part2}
{self.receipts()}
</div>
<script>
(function(){{var b=document.getElementById("copy-email");if(!b)return;b.addEventListener("click",function(){{var t=document.getElementById("email-text").innerText;
try{{navigator.clipboard.writeText(t).then(function(){{b.textContent="Copied"}},sel)}}catch(x){{sel()}}
function sel(){{var r=document.createRange();r.selectNodeContents(document.getElementById("email-text"));var s=getSelection();s.removeAllRanges();s.addRange(r);b.textContent="Selected, press Copy"}}}});}})();
</script>'''
        (self.wd / "review.html").write_text(page)
        return first + focus, read

    # ---- the claims lint: our own lines pass the same trust gate as the rep's -------------------------
    def lint(self):
        sources = ((self.wd / "transcript.txt").read_text() + "\n" + (SKILL / "references" / "oneaway-context.md").read_text()).lower()
        norm_src = re.sub(r"[\s,]", "", sources)
        lines = []
        for name, f in (self.j.get("focus") or {}).items():
            lines += [f.get("say_instead", ""), f.get("drill", "")]
        for st in (self.j.get("script") or {}).get("steps", []):
            lines += st["say"] if isinstance(st.get("say"), list) else [st.get("say", "")]
        lines.append(self.j.get("recovery_email", "") or "")
        # The "Better:" rewrites under flagged claims are our words too.
        lines += [c.get("correct", "") for c in self.sc["trust"].get("claims", []) if c.get("verdict") != "TRUE"]
        problems = []
        for ln in filter(None, lines):
            for fig in re.findall(r"\$\s?\d[\d,.]*\s?[kKmM]?(?:\s?[–-]\s?\$?\d[\d,.]*\s?[kKmM]?)?|\d+(?:\.\d+)?\s?%", ln):
                for part in re.split(r"[–-]", fig):
                    p = re.sub(r"[\s,$]", "", part).lower()
                    bare = p.rstrip("%")  # "1.5%" in our line may be "1.5" in the transcript
                    if p and p not in norm_src and p.rstrip("k") + "000" not in norm_src and not (p.endswith("%") and re.search(r"(?<![\d.])" + re.escape(bare) + r"(?![\d])", sources)):
                        problems.append(f"figure {fig!r} is in neither the transcript nor the context pack: {ln[:90]!r}")
                        break
            for m in SWEEPING.finditer(ln):
                if m.group(0).lower() not in sources:
                    problems.append(f"sweeping claim {m.group(0)!r} isn't backed by the context pack: {ln[:90]!r}")
        # Names, never he/she: we don't know anyone's pronouns. Checks every sentence we show that isn't a verbatim quote.
        shown = [c.get("note", "") for it in self.sc["items"].values() for c in (it.get("checks") or {}).values()]
        shown += [c.get("correct", "") for c in self.sc["trust"].get("claims", []) if c.get("verdict") != "TRUE"]
        shown += [w.get("text", "") for w in self.j.get("worked") or []] + list((self.j.get("items") or {}).values())
        shown += [self.j.get("headline", ""), self.j.get("verdict", "")] + [st.get("cue", "") for st in (self.j.get("script") or {}).get("steps", [])]
        for t in filter(None, shown):
            m = re.search(r"\b(he|she|him|her|his|hers|himself|herself)\b", t, re.I)
            if m:
                problems.append(f"pronoun {m.group(0)!r} (use the person's name): {t[:90]!r}")
        if self.j.get("recovery_email") and not (self.sc["trust"]["verdict"] == "fix" or self.j.get("recovery_reason")):
            problems.append("recovery email without a reason: only for calls that damaged trust (set recovery_reason, or drop it)")
        return problems


BOT = re.compile(r"recorder|notetaker|note ?taker|fathom|tldv|otter|fireflies|read\.ai|meeting notes|^calendar@|grain", re.I)
GENERIC = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", "live.com", "proton.me", "protonmail.com"}


# Brand fonts are commercially licensed, so they stay local (git-ignored); without them the page uses system fonts.
FONTS = SKILL / "assets" / "fonts.css"

def participants(meta, reps):
    """Who was on the call: their side (names, emails, company domain) and ours. Bots and duplicates dropped."""
    them_emails, us = [], []
    for p in meta.get("participants", []):
        name, email = (p.get("name") or "").strip(), (p.get("email") or "").strip().lower()
        if BOT.search(name) or BOT.search(email):
            continue
        if email.endswith("@oneaway.io") or name in reps:
            # An exec who was invited but never spoke wasn't on the call.
            if name and name not in us and (not reps or name in reps):
                us.append(name)
        elif email and email not in them_emails:
            them_emails.append(email)
    domains = [em.split("@")[1] for em in them_emails if "@" in em and em.split("@")[1] not in GENERIC]
    domain = max(set(domains), key=domains.count) if domains else None
    names = [n.strip() for n in (meta.get("prospect") or "").split(",") if n.strip()]
    if not names:  # fall back to Grain's names, minus bots, ours and email-handle duplicates
        seen = set()
        for p in meta.get("participants", []):
            n = (p.get("name") or "").strip()
            if n and not BOT.search(n) and n not in reps and not (p.get("email") or "").endswith("@oneaway.io") and n.lower() not in seen:
                seen.add(n.lower()); names.append(n)
    company = meta.get("company") or (domain.split(".")[0].title() if domain else "")
    return {"company": company, "domain": domain, "them": names, "them_emails": them_emails, "us": us or list(reps)}


def rep_file(name):
    for p in (HOME / "reps").glob("*.json"):
        d = json.loads(p.read_text())
        if d.get("name") == name:
            return d
    return None


def count(fragment):
    text = re.sub(r"<svg.*?</svg>|<style.*?</style>|<script.*?</script>|<div class=\"exp\">.*?</div></details>"
                  r"|<p class=\"tkey\">.*?</p>|<div class=\"legend2\">.*?</div>", " ", fragment, flags=re.S)  # glance labels aren't reading
    return len(re.sub(r"<[^>]+>", " ", html.unescape(text)).split())


CSS = r"""
:root{
  --paper:#F5F0E8;--card:#FBF9F5;--ink:#1F1F1F;--ink2:#4A4744;--muted:#76706A;--line:#DCD5C9;
  --orange:#FD4F03;--orange-ink:#B83A00;--cobalt:#1438FF;
  --display:'OA Pixel','OA Mono',ui-monospace,monospace;--body:'Telegraf','Helvetica Neue',Arial,sans-serif;
  --mono:'OA Mono',ui-monospace,SFMono-Regular,Menlo,monospace;--supply:'OA Supply','OA Mono',ui-monospace,monospace;
  color-scheme:light;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#0D0D0D;--card:#161616;--ink:#EBEBEB;--ink2:#C2C2C2;--muted:#8E8E8E;--line:#2A2A2A;
  --orange:#FE5410;--orange-ink:#FF7A45;--cobalt:#7D90FB;color-scheme:dark}}
:root[data-theme="dark"]{
  --paper:#0D0D0D;--card:#161616;--ink:#EBEBEB;--ink2:#C2C2C2;--muted:#8E8E8E;--line:#2A2A2A;
  --orange:#FE5410;--orange-ink:#FF7A45;--cobalt:#7D90FB;color-scheme:dark}
body{background:var(--paper);color:var(--ink);font:16px/1.6 var(--body);-webkit-font-smoothing:antialiased}
.wrap{max-width:760px;margin:0 auto;padding-inline:20px;padding-block:28px 72px;display:flex;flex-direction:column;gap:52px}
a{color:inherit;text-decoration:none}a:focus-visible,button:focus-visible,summary:focus-visible{outline:2px solid var(--orange);outline-offset:3px}
h1,h2,h3,p{margin:0}h1,h2{text-wrap:balance;font-weight:400}
h1{font:400 clamp(32px,6vw,44px)/1.08 var(--display);letter-spacing:-.01em;max-width:18ch}
h2{font:400 22px/1.2 var(--display);margin-bottom:16px}
.muted{color:var(--muted)}
.meta{display:flex;flex-direction:column;gap:4px;margin-bottom:-20px}
.row1{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.brand{font:14px var(--supply);color:var(--ink)}.brand span{color:var(--orange)}.brand em{font:13px var(--mono);font-style:normal;color:var(--muted);margin-left:6px}
.rec{font:13px var(--mono);color:var(--ink2)}.rec:hover{color:var(--orange-ink)}
.facts{font:13px/1.5 var(--mono);color:var(--ink2)}
.callcard{display:grid;grid-template-columns:1fr auto;gap:12px 32px;padding:14px 0 12px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin:10px 0 8px}
.callcard .side{display:flex;flex-direction:column;gap:3px}
.callcard .lbl{font:11px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.callcard .co{font:700 19px/1.3 var(--body);color:var(--ink)}
.callcard .dom{font:400 13px var(--mono);color:var(--ink2);margin-left:6px;white-space:nowrap}.callcard .dom:hover{color:var(--orange-ink)}
.callcard .ppl{font-size:16px;color:var(--ink)}
.callcard .em{font:12.5px var(--mono);color:var(--ink2);word-break:break-all}
.t{font:12.5px var(--mono);color:var(--ink2);white-space:nowrap;font-variant-numeric:tabular-nums}.t.est{color:var(--muted)}
a.t:hover{color:var(--orange-ink);text-decoration:underline;text-underline-offset:3px}
q{font-style:normal}q::before{content:"“"}q::after{content:"”"}q.us{color:var(--orange-ink)}q.them{color:var(--cobalt)}
.label{font:12px var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
/* hero */
.hero{display:block}
.hl{display:flex;flex-direction:column;gap:12px}
.outcome{font:400 24px/1.15 var(--display);color:var(--ink);display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 10px}
.outcome b{font:400 40px/1 var(--display);color:var(--ink)}.outcome .of{font-size:18px;color:var(--muted)}.cap{font:13px var(--mono);color:var(--orange-ink)}
.verdict{font-size:19px;line-height:1.45;color:var(--ink2);max-width:56ch}
.gloss{font-size:14px;color:var(--muted);margin-top:-6px}
.source{font-size:13px;color:var(--muted);margin-top:18px}
.pointer{font-size:15px;border-left:3px solid var(--orange);padding-left:12px;max-width:56ch}.pointer a:hover{color:var(--orange-ink)}
.fpbox{padding-top:30px}
.fp{display:flex;gap:5px}
.fp .col{display:flex;padding:3px;border:1px solid transparent;border-radius:3px}.fp .col.focus{border-color:var(--orange)}
.c{display:inline-block;width:10px;height:10px;border:1.5px solid var(--ink);flex:none}
.c.met{background:var(--ink)}.c.half{background:linear-gradient(90deg,var(--ink) 50%,transparent 0)}.c.na{border-style:dotted;opacity:.4}
.sw{font:12px var(--mono);text-transform:uppercase;letter-spacing:.05em;white-space:nowrap}
.sw.s2{color:var(--ink)}.sw.s1{color:var(--ink2)}.sw.s0{color:var(--ink);font-weight:700;text-decoration:underline;text-decoration-thickness:1.5px;text-underline-offset:3px}.sw.sna{color:var(--muted)}
.part{display:flex;flex-direction:column;gap:44px}
.part-label{font:12px var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);border-top:1px solid var(--ink);padding-top:10px;margin-bottom:-24px}
/* focus */
.focus{border-left:3px solid var(--orange);padding:4px 0 4px 20px;display:flex;flex-direction:column;gap:10px}
.focus .label{display:flex;flex-wrap:wrap;gap:4px 14px;align-items:center}
.streak{display:inline-flex;gap:4px;align-items:center;text-transform:none;letter-spacing:0}
.streak i{width:10px;height:10px;border-radius:50%;border:1.5px solid var(--muted);display:inline-block}.streak i.on{background:var(--ink);border-color:var(--ink)}
.streak em{font-style:normal;margin-left:4px}
.behaviour{font:700 22px/1.3 var(--body);max-width:34ch}.behaviour.sm{font-size:16px;font-weight:400;color:var(--ink2)}
.focus.compact{border-left-color:var(--line);gap:4px}
.why{font-size:15px;color:var(--ink2)}
.say{font-size:19px;line-height:1.45;color:var(--ink);text-indent:-.55em;padding-left:.55em;max-width:58ch}
.qm{font:400 1.2em/0 var(--display);color:var(--orange)}
.drill{font-size:14px;color:var(--muted)}
.worked ul{margin:0;padding-left:18px;display:grid;gap:6px}
/* moves */
.hint{font-size:13px;color:var(--muted);margin:-8px 0 10px}
.board{list-style:none;margin:0;padding:0;border-top:1px solid var(--line)}
.board>li{border-bottom:1px solid var(--line)}
.row summary,.row.static{display:grid;grid-template-columns:72px 110px 1fr 18px;gap:12px;align-items:center;padding:10px 0;font-size:15px;cursor:pointer;list-style:none}
.row.static{cursor:default}
.row summary::-webkit-details-marker{display:none}
.row summary:hover .nm{text-decoration:underline;text-underline-offset:3px}
.board .nm{font-weight:700}.board .tx{color:var(--ink2)}
.chev{width:8px;height:8px;border-right:1.5px solid var(--muted);border-bottom:1.5px solid var(--muted);transform:rotate(45deg);justify-self:center;margin-top:-4px;transition:transform .15s}
.row[open] .chev{transform:rotate(-135deg);margin-top:4px}
.exp{padding:2px 0 16px 84px;display:flex;flex-direction:column;gap:10px}
.exp .qq{font-size:14px;color:var(--muted)}
.tonext{font:13px var(--mono);color:var(--orange-ink);align-self:flex-start}
/* numbers */
.talk{margin:0;display:flex;flex-direction:column;gap:4px}
.lanes{display:flex;flex-direction:column;gap:4px}
.lane{display:grid;grid-template-columns:88px 1fr;gap:10px;align-items:center}
.lane .who{font:13px var(--mono);color:var(--ink2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lane svg{width:100%;height:10px;display:block}.lane.us rect{fill:var(--orange)}.lane.them rect{fill:var(--cobalt)}
.axis,.notes{margin-left:98px}
.axis{display:flex;justify-content:space-between;font:11px var(--mono);color:var(--muted)}
.notes{position:relative;height:50px;font:12px var(--mono);color:var(--ink2)}
.tick{position:absolute;top:0;white-space:nowrap}
.bracket{position:absolute;top:0;height:8px;border:1px solid var(--muted);border-top:0}
.bracket.row2{top:22px}
.bracket em{position:absolute;top:10px;left:50%;transform:translateX(-50%);font-style:normal;white-space:nowrap}
.bracket.at-left em{left:0;transform:none}.bracket.at-right em{left:auto;right:0;transform:none}
.tiles{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.tile{border:1px solid var(--line);border-radius:4px;padding:14px 16px;display:flex;flex-direction:column;gap:6px;background:var(--card)}
.tbig{font:400 34px/1 var(--display);color:var(--ink)}.tbig small{font-size:16px;color:var(--muted)}
.tlabel{font-size:14px;color:var(--ink2);min-height:2.6em}
.tgfx{padding:8px 0 2px}.taim{font:12px var(--mono);color:var(--muted)}
.split,.bar{position:relative;height:14px;display:flex;border-radius:2px;background:var(--line);margin-top:14px}
.split .us{background:var(--orange)}.split .them{background:var(--cobalt)}
.bar .fill{background:var(--orange);border-radius:2px}
.mark{position:absolute;top:-6px;bottom:-4px;width:0;border-left:2px dashed var(--ink)}
.mark b{position:absolute;top:-16px;left:0;transform:translateX(-50%);font:600 11px var(--mono);color:var(--ink);white-space:nowrap}
.legend2{display:flex;gap:14px;font:12px var(--mono);color:var(--ink2);margin-top:8px}.legend2 i{display:inline-block;width:9px;height:9px;margin-right:5px}
.legend2 i.us{background:var(--orange)}.legend2 i.them{background:var(--cobalt)}
.dots{display:flex;flex-wrap:wrap;gap:4px}.dots .q{width:13px;height:13px}.dots.big .q{width:20px;height:20px}
.q{display:inline-block;border:1.5px solid var(--ink);border-radius:2px;vertical-align:-1px}.q.on{background:var(--ink)}
.tkey{font:11.5px var(--mono);color:var(--muted);display:flex;gap:6px;align-items:center;margin-top:6px}.tkey .q{width:9px;height:9px;margin-left:6px}.tkey .q:first-child{margin-left:0}
.verdicts{list-style:none;margin:16px 0 0;padding:0;display:grid;gap:10px}
.verdicts li{display:grid;grid-template-columns:72px 1fr auto;gap:10px;align-items:baseline;font-size:16px}
.verdicts .aim{font-size:13px;color:var(--muted);white-space:nowrap}
/* script */
.script .sub{font-size:14px;color:var(--muted);margin:-8px 0 18px}
.steps{list-style:none;margin:0;padding:0;display:grid;gap:22px;counter-reset:s}
.steps>li{display:flex;flex-direction:column;gap:4px;padding-left:28px;position:relative;counter-increment:s}
.steps>li::before{content:counter(s);position:absolute;left:0;top:1px;font:12px var(--mono);color:var(--muted)}
.step{font-weight:700;display:flex;gap:10px;align-items:baseline}
.tag{font:11px var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--orange-ink);font-weight:400}
.cue{font-size:14px;color:var(--muted)}
.steps .say{font-size:17px}
.asks{margin:2px 0 0;padding-left:18px;display:grid;gap:4px;font-size:17px}
/* email, receipts */
.email{display:flex;flex-direction:column;gap:10px}
.email pre{white-space:pre-wrap;font:15px/1.55 var(--body);background:var(--card);border:1px solid var(--line);padding:16px;margin:0;border-radius:4px}
button{align-self:flex-start;font:13px var(--mono);background:var(--orange);color:#1a1a1a;border:0;padding:8px 14px;border-radius:3px;cursor:pointer}
.evidence{display:flex;flex-direction:column;gap:28px}.evidence .sub{font-size:14px;color:var(--muted);margin:-8px 0 0}
.ev h3{font:700 18px/1.3 var(--body);display:flex;gap:12px;align-items:baseline}.ev .qq{font-size:14px;color:var(--muted);margin:2px 0 10px}
.cks{list-style:none;margin:0;padding:0;display:grid;gap:14px}
.ex{list-style:none;margin:8px 0 0;padding:0;display:grid;gap:6px;font-size:14px;color:var(--ink2)}.ex .exk{display:inline-block;min-width:64px;font:11px var(--mono);text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}.ex .t{margin-right:6px}
.ck{border-left:2px solid var(--line);padding-left:14px;display:flex;flex-direction:column;gap:3px;font-size:15px}
.ck.missed{border-left-color:var(--ink)}
.cl{font-weight:700}.kind{font:11px var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-right:8px;font-weight:400}
.meta2{font:12.5px var(--mono);color:var(--ink2)}.meta2 b{font-weight:400;text-transform:uppercase;letter-spacing:.05em;color:var(--ink)}
.note{color:var(--ink2)}.instead{color:var(--ink)}
.more summary{cursor:pointer;font:14px var(--mono);color:var(--ink2);padding:10px 0;border-top:1px solid var(--line)}
.more[open]{display:flex;flex-direction:column;gap:14px}
.tablewrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:left;padding:8px 10px 8px 0;border-bottom:1px solid var(--line);vertical-align:top}
table tr:first-child th{font:11px var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:400}
th[scope=row]{font-weight:400}.num{white-space:nowrap}.checks td:last-child{min-width:240px}
.key{font:10px var(--mono);color:var(--orange-ink);text-transform:uppercase;margin-left:4px}.instead{color:var(--ink)}
.fit{margin:0;display:grid;gap:4px}.fit div{display:grid;grid-template-columns:170px 1fr;gap:12px}.fit dt{color:var(--muted)}.fit dd{margin:0}
@media (max-width:640px){
  .wrap{gap:40px}.hero{grid-template-columns:1fr}.fpbox{padding-top:0}.callcard{grid-template-columns:1fr}
  .row summary,.row.static{grid-template-columns:64px 1fr 18px;gap:2px 10px}.board .tx{grid-column:2 / 3;font-size:14px}.chev{grid-row:1;grid-column:3}
  .exp{padding-left:0}
  .lane{grid-template-columns:64px 1fr}.axis,.notes{margin-left:74px}
  .verdicts li{grid-template-columns:64px 1fr;gap:0 10px}.verdicts .aim{grid-column:2;white-space:normal}
  .tiles{grid-template-columns:1fr}.tlabel{min-height:0}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""


def main():
    wd = Path(sys.argv[1])
    page = Page(wd)
    problems = page.lint()
    if problems:
        print("CLAIMS LINT FAILED — our own lines must pass the trust gate too:")
        for p in problems:
            print("  -", p)
        sys.exit(4)
    first, read = page.render()
    sw, rw = count(first), count(read)
    print(f"wrote {wd / 'review.html'} ({(wd / 'review.html').stat().st_size // 1024} KB)")
    print(f"reading budget: first screen {sw}/{SKIM_WORDS} words (~{sw / 200:.1f} min) · with the script {sw + rw}/{TOTAL_WORDS} words (~{(sw + rw) / 240:.1f} min)")
    if sw > SKIM_WORDS or sw + rw > TOTAL_WORDS:
        print("OVER BUDGET: tighten judge.json and re-render")
        sys.exit(3)


if __name__ == "__main__":
    main()
