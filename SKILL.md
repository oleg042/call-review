---
name: call-review
description: >
  Reviews OneAway's sales calls and coaches the execs who ran them (founder Xavier, Mark, Oleg). Pulls the Grain
  transcript and Grain's exact timings, measures it (talk share, longest answer, questions asked, price timing,
  re-asks), judges the outcome first (moved forward / left open / stalled), then eight moves of agency selling
  (Open, Discover, Quantify, Listen, Teach, Offer, Price, Close) with two yes/no checks each, plus a soft check on
  what we claimed (advice only, never lowers the score). Publishes a OneAway-branded, shareable review page where every quote opens the recording at that
  moment: a 2-minute first screen, the lines to say next time, and receipts. Tracks ONE focus
  behaviour per exec from call to call until it's fixed. Use whenever the user shares a Grain or portal meeting
  link (…tasks?board=meetings&meeting=…), names a sales, discovery, proposal or demo call, or asks to judge,
  grade, review, tear down or coach a call or a rep, even if they only say "how about this call", "judge it" or
  "how is Mark doing". Not for written client updates, specs or email threads.
---

# Call review

**The job: make each exec measurably better on their next call**, in a format they will actually read. OneAway
sells a 5–20k USD/month retainer in two or three calls, so the rubric is built for agency selling, not for SaaS or
enterprise. Judge like a practical coach, not a grader: what did the call achieve, what worked (recoveries count),
the ONE thing to change, and exactly what to say. A call that moved forward is a good call even if it wasn't perfect.

Everything scored lives in `scripts/rubric.py` (ids, checks, thresholds) and `references/rubric.md` (what each check
means, examples, sources). Read rubric.md before judging anything.

## Prerequisites
- **Database:** `MEETINGS_DATABASE_URL` in the environment, or in `/Users/olegdeduchenko/Projects/oneaway-app/.env`.
- **Tools:** the Agent tool (three parallel reviewers) and the Artifact tool (publishing the page).
- **State:** `~/.claude/call-review/reps/<rep>.json` (focus, queue, streak, history) and `~/.claude/call-review/history.csv`.
- **Paths:**
  - Scripts: `/Users/olegdeduchenko/.claude/skills/call-review/scripts/` (called `$S` below).
  - Workdir per call: `/tmp/call-review/<first 8 chars of meeting id>/` (called `$W` below).

## Step 1: Find the call and the exec
- A link or id → use it (portal `meeting=<uuid>` or a Grain share link).
- A name → `node $S/fetch_call.mjs --search "<name>"`; "Mark's last call" → `node $S/fetch_call.mjs --recent 15`. Take the latest match and say which one you picked.
- Show each exec's current focus: `python3 $S/focus.py --show <rep>` (keys `mark`, `xavier`). A new exec gets a file shaped like the docstring in focus.py.

## Step 2: Fetch and measure
```bash
node $S/fetch_call.mjs <id|link> $W
python3 $S/grain_timing.py $W      # exact times from the Grain share page; falls back to estimates if missing
python3 $S/metrics.py $W
```
Metrics are signals. Check the flags against the text; `references/numbers.md` lists each number's blind spot.

## Step 3: Classify the call and name the prospect
- **Call type:** read the first ~15 lines and `meta.json`, then pick `discovery`, `proposal`, `negotiation` or `client` (definitions in `references/oneaway-context.md`).
- **First call or follow-up?** `node $S/fetch_call.mjs --search <their domain>` finds earlier calls with the same company.
- **Names:** add `"company": "<Company>"` and `"prospect": "<First Last, First Last>"` to `$W/meta.json`. The page's title and header use them, because Grain often lists one person twice ("J S.", "jamie").

## Step 4: Run the three reviewers
Read `references/reviewer-prompt.md` and spawn its three reviewers in ONE message, so they run in parallel. While
they run, read the whole transcript yourself; the judge step needs your own view.

## Step 5: Score, then judge
```bash
python3 $S/score.py $W <call_type>
```
- **What the script does:** fills the two measured checks, drops any quote it can't find, and scores each move (Good = every check that applied was met; Partly = some). It sets the score from the outcome's range (the claims check is advice and never changes it), builds the numbers panel, and writes one history row per exec.
- **Then judge:**
  - Confirm the outcome (interest + next step) against its quotes.
  - Read every "Work on" and "Partly" check against its quote; a check that did its job, even imperfectly, is met.
  - Name the root cause (what would have prevented the problem), not the trigger.
  - Fix any verdict that contradicts the transcript or rubric.md, including double-counted moments, then re-run score.py.
  - Make sure every rejected quote was either fixed or deliberately dropped.

## Step 6: Update each exec's focus
```bash
python3 $S/focus.py $W <rep>        # once per OneAway exec on the call
```
- **Attribution:** the focus result counts only the exec responsible for that check. On two-exec calls the check's `rep` field decides.
- **Picking a new focus:** no active focus, or it was just fixed and the queue is empty? Choose the costliest miss that is a trainable behaviour and repeats across this exec's calls (`history.csv`, `focus.py --show`). Point it at a check id or a metric, with `fixed_after: 3`.
- **Claims** are never a focus. They are advice on the page ("What we claimed"), at most three lines, and never change the score.

## Step 7: Write judge.json and render the page
Read `references/page.md`, which has the fields, word limits, tone and examples. Write `$W/judge.json`, then:
```bash
python3 $S/render_review.py $W
```
It prints the reading budget: skim ≤ 400 words (~2 min), skim + read ≤ 1,200 (~5 min). Exit code 3 means over
budget: tighten judge.json and re-render. Never cut a quote's precision to save words.

## Step 8: Publish and report
- **Publish:** `$W/review.html` with the Artifact tool, `icon: "chart"`, and a one-sentence description.
- **Record the link:** `python3 $S/focus.py --link <rep> <call_id> <url>`.
- **Chat reply:** give the link first, then 4–6 lines:
  - the score and band;
  - the costliest moment;
  - each exec's focus, HIT or MISS, and their streak;
  - the one line to say next time.
- **Recovery email:** only when the prospect was clearly put off, or a claim needs correcting (a "fix"); say it's on the page.
- **Sharing:** Claude can't change sharing (the Artifact tool publishes private). End the chat reply with the
  one-click step: open the page → Share → General access → "Anyone with the link" (view only). The user wants
  review pages link-shareable. Grain ▶ links still need a Grain login, so the recording itself stays private.
- **Weekly review:** suggest a 15-minute weekly human review of each focus. AI plus a human beats either alone (`references/coaching-research.md`).

## Rules
- One focus behaviour per exec until the numbers say it's fixed. Everything else is on the page, not in their head.
- Every verdict has a quote and a time. Every miss comes with the exact line to say instead.
- Every number comes from `scorecard.json`. Guides are ranges with sources, never pass marks.
- Open with one real strength, then say the score and the costliest moment plainly.
- When the user corrects a fact (offer, price, a claim, a habit), update `references/oneaway-context.md`.
- When changing the rubric, change `scripts/rubric.py` and `references/rubric.md` together. Never rename a check id (focus files point at them).
