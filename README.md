# call-review

A [Claude Code](https://claude.com/claude-code) skill that reviews B2B agency sales calls and coaches the execs who
ran them. Built at OneAway for selling a 5–20k USD/month outbound retainer in two or three calls.

It pulls a call's transcript, measures it, has three AI reviewers judge it against a fixed rubric, and publishes a
branded review page: a 2-minute first screen, the exact lines to say next time, and receipts where every quote opens
the recording at that moment. Each exec gets **one** focus behaviour, tracked from call to call until it's fixed.

## What a call is judged on

**Outcome first.** Did the call move the deal? That sets the score band before anything else:

| Outcome | When | Score |
| --- | --- | --- |
| Moved forward | Interest, and a next step booked or specific | 7–10 |
| Left open | Interest, but the next step is vague or in their hands | 4–7 |
| Stalled | No real interest or no path forward | 1–4 |

**Then 8 parts of the call, 2 checks each** (key 70%, supporting 30%). Good = both done, Partly = one, Work on = neither.

| Part | Key check | Supporting check |
| --- | --- | --- |
| Opening | Who we are, why we're here and the plan | Asked what they want from the call (or answered it) |
| Their problem | Every problem they raised got a follow-up question | We know how they get meetings today |
| What a win is worth | What one new customer is worth to them | Meetings or deals needed versus today |
| Listening | Worries named back or explored, never brushed off | *Measured:* enough questions, mostly open, none re-asked |
| Showing expertise | One insight from across clients, and they engaged | *Measured:* longest answer under ~250 words |
| The offer | Said plainly what we'd do, what they get, how we start | Sized to them: enough market, pays back at their deal value |
| Price | Money as a plain number or range | No discount without a scope change |
| Next step | Booked on the call | The decider will be there; purpose agreed |

A soft **"What we claimed"** check shows at most three lines a prospect could check and find wrong. It's advice and
never changes the score. Sources for every check (Sandler, SPIN, Gap Selling, Voss, Challenger, Enns, Weiss,
Weinberg, Gong's call data) are in `references/rubric.md` and `references/techniques.md`.

## Layout

```
SKILL.md                 the workflow Claude follows (8 steps)
references/              rubric, company context, reviewer prompts, page template, numbers, techniques, research
scripts/                 fetch, Grain timings, metrics, scoring, focus tracking, page renderer, tests
assets/fonts.css         brand fonts, inlined into each page
```

## Install

```bash
git clone https://github.com/oleg042/call-review ~/.claude/skills/call-review
```

Needs:
- **Python 3** with `curl_cffi` (`python3 -m pip install --user curl_cffi`), used to read exact timings from Grain share pages.
- **Node** and a checkout of the app that holds the meetings database driver and `.env`
  (`~/Projects/oneaway-app` by default; set `ONEAWAY_APP_DIR` to change it).
- **`MEETINGS_DATABASE_URL`**: a read-only connection to the meetings database (Grain transcripts). Read from the
  environment or the app's `.env`; never stored in this repo.

Brand fonts are commercially licensed, so `assets/fonts.css` isn't in the repo; without it the page uses system
fonts. To brand it, add your own `@font-face` rules (inlined as base64) in `assets/fonts.css`.

State lives outside the repo, in `~/.claude/call-review/` (each exec's focus and history). Team notes on each exec's
habits live in `references/team.local.md`, which is git-ignored.

Then, in Claude Code: *"review Mark's last call"* or paste a Grain or portal meeting link.

## Tests

```bash
python3 scripts/test_questions.py   # question counting: 31 real cases
```
