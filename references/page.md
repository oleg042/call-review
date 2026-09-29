# The review page: the template

The page is a fixed template, built by `scripts/render_review.py`. The code owns its structure: the order,
the sections, the numbers and the links. Per call, only the prose fields in `judge.json` are written, and each has
a word limit. The renderer refuses to build a page that is over its reading budget (exit 3), or whose own lines
invent claims about OneAway (exit 4).

## The template, top to bottom
```
<oneaway> // call review                                   ▶ Recording
CALL WITH  Company  domain.com ↗          ONEAWAY  Exec name      ← from participant emails; bots dropped
           Their people, full names                 (domain = most common non-OneAway, non-Gmail email domain;
           their@emails                              no emails → company only, never a guessed domain)
Date · Call type · Length

LEFT OPEN · 4.6/10                        ← outcome + score, said once
Headline: the main line, ≤ 8 words       ← judge.headline
Verdict, ≤ 30 words                       ← judge.verdict
┃ Your one change, Mark: <focus> ↓        ← from the rep's focus file

PART 1 · HOW THE CALL WENT                (feedback only: what happened, no advice)
  What worked        1–2 strengths with ▶ time (recoveries count)      ← judge.worked
  Each part of the call  GOOD / PARTLY / WORK ON · part · what happened · ⌄   ← judge.items
                     every row expands IN PLACE to its evidence (key + supporting check: done or not,
                     who, ▶ moment, quote, note) and, when the script has a step for it, an explicit
                     "What to say next time ↓" link. No row ever jumps elsewhere silently.
                     What we claimed: CLEAN / TIGHTEN / FIX · advice only, ≤3 lines + better wording
  The numbers        two talk lanes (us / them), first question, longest answer
                     4 rows: status word · plain sentence · aim         ← metrics
PART 2 · WHAT TO DO NEXT                  (recommendations only)
  Your one change    behaviour · streak in words · Why ▶ · the line to say · drill   ← judge.focus
  Next call script   Open → Ask → Listen → Offer → Price → Close; each: cue ▶ last time's moment,
                     then the words to say                               ← judge.script
  Recovery email     only when the call damaged trust (needs recovery_reason)
PART 3 · THE EVIDENCE                     (open by default, same weight as Parts 1 and 2)
  Problems they raised and whether each got a follow-up (per-part evidence lives in the Part 1 rows)
  "All the numbers and how the score works" (the one collapsed block)
```

## Rules the template enforces
- **Feedback and recommendations never mix.** Part 1 describes what happened. Part 2 says what to do. The hero only summarises: one headline and one pointer to the change.
- **Status is always a word:** Good, Partly, Work on (What we claimed: Clean, Tighten, Fix). No symbols that need a legend.
- **Budgets:** the first screen (hero + Part 1 + the one change) ≤ 400 words, about 2 minutes. Add the script and it's ≤ 1,200 words, about 5 minutes. The evidence (Part 3) isn't counted.
- **Times:** with exact Grain timings (`timing.json`), every time is a ▶ link that opens the recording 2 seconds before the words. Without them, times show as `~07:54` with no link, and the receipts say why.
- **Claims lint:** every figure, and every sweeping claim ("we only", "we aim at", "clients like you", "what we usually see", "guarantee") in the lines we write for execs must appear in the transcript or in `oneaway-context.md`. Anything else fails the build. When a fact is missing, ask it as a question.

## Writing judge.json
- **Coach, not grader.** Name what worked. Be plain about the gap, and never judge the person.
- **Names, not pronouns.** Refer to people by name, never he/she.
- **Plain style.** Short sentences, no softeners.
- **One main line.** The headline, the one change and the script's first step tell the same story.
- **Script steps** go in call order. Each step has:
  - a cue that points to last time's moment: `line` + `quote`, rendered as ▶;
  - the words to say: a sentence, or a list of 1–3 questions.
- **Facts about OneAway** come only from `oneaway-context.md`. That covers what we can deliver and the pilot with its $500 deposit. Offer lines in the script reuse what the exec offered on this call, reshaped as their problem → what we'd do → why us; never a canned package. About $6.2k a month is the usual starting point, never a price list: execs quote individually on the call.

## Publishing
- **Publish:** publish `<WORKDIR>/review.html` with the Artifact tool, `icon: "chart"`, and a one-sentence description. Re-publishing the same path keeps the link.
- **Record the link:** run `focus.py --link <rep> <call_id> <url>`.
- **Sharing:** the page is private until the user shares it from the Share menu.
- **Brand:**
  - Tokens come from the portal and oneaway.io. Paper `#F5F0E8`, ink `#1F1F1F`; in dark mode `#0D0D0D`.
  - Orange is used only for our side's voice (our talk lane, the quote marks, the focus rule). Cobalt is theirs.
  - Fonts: Geist Pixel Square, PP Telegraf and Geist Mono, inlined from `assets/fonts.css`.
