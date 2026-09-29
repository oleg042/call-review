# The rubric: outcome first, eight moves, two checks each

Built for OneAway's selling: a B2B agency selling a $5–20k/month retainer in two or three calls (discovery →
proposal → sometimes negotiation). The execs running these calls are not trained salespeople. The review has to
feel like a good coach, not a grader: what did the call achieve, what one or two things would make the next one
better, and what exactly to say. Ids match `scripts/rubric.py`; change both together.

## 1. Outcome: what the call achieved (the headline)
| Outcome | When | Score range |
| --- | --- | --- |
| **Moved forward** | They showed interest, and a specific next step was agreed or a next call scheduled | 7–10 |
| **Left open** | They showed interest, but the next step is vague or in their hands ("I'll send my Calendly", "drop me some options") | 4–7 |
| **Stalled** | No real interest, or no path forward | 1–4 |

- **Interest** can be `clear` ("let's do it", asks about starting), `some` ("we can do that on the next call", asks for the offer) or `none`.
- **The next step** is one of:
  - `scheduled`: a date and time agreed, or an invite sent on the call;
  - `specific`: a concrete action with an owner and a time;
  - `vague`;
  - `prospect_owned`;
  - `none`.
- **The score** is the outcome's range, with the eight moves placing the call inside it. In each move the key check is worth 70% and the supporting check 30%, so a Good move with its supporting check missed still dents the score a little.
  - A booked call with average moves lands around 8.
  - A call left open with weak moves lands around 5.
  - A perfect call that stalls still can't pass 4, because the job is to move the deal.
- **No caps.** The claims check is advice, not a penalty: it never changes the score.

## 2. The eight moves
Each move has a **key check** (the thing that matters most for an agency deal) and one **supporting check**.
- **Good:** both checks happened (or the one that applied).
- **Partly:** one of the two happened. The key check still counts for more in the score (70/30).
- **Work on:** neither happened.

A check is **met** when it did its job, even if imperfect or late. A clean recovery is named as a strength.

| Move | Key check | Supporting check |
| --- | --- | --- |
| **Open** (first minute) | **open.purpose**: opened with who we are, why we're here and the plan | open.their_goals: asked what they want out of the call, or answered what they asked for |
| **Discover** (their problem) | **discover.followup**: problems they raised got a follow-up question before we answered | discover.setup: we know how they get meetings today (channels, tools, who, volume, results) |
| **Quantify** (the number) | **quantify.deal_value**: we know what one new customer is worth to them | quantify.goal_vs_now: we know how many meetings or deals they need versus get today |
| **Listen** (whole call) | **listen.concerns**: their worries were named back or explored, never brushed off | listen.questions *(measured)*: at least ~5 questions per 30 minutes, at least half open, none re-asked |
| **Teach** (when we explain) | **teach.insight**: one insight from what we see across clients that they engaged with | teach.short *(measured)*: longest answer under ~250 words (~90 s) |
| **Offer** (what we'd do) | **offer.stated**: said plainly what we do, what they get, how we start | offer.fits: sized to them; enough market for the plan, and it pays back at their deal value |
| **Price** (money) | **price.plain**: money came up as a plain number or range, never "it depends" | price.held: no discount for nothing; price moved only if scope moved (n/a if no pushback). A price built on the call for the scope described is a quote, not a discount |
| **Close** (last 5 min) | **close.booked**: next step booked on the call, a date and time or a specific agreed action | close.right_people: the person who decides will be there, and the purpose is agreed |

### What good sounds like (one line each)
- **Open:** "I'm Mark, I run campaign strategy. You replied about finding a new lead partner. I'll ask how you win clients today and what went wrong before, then tell you exactly what we'd do. Sound good?"
- **Discover:** "You said the last agencies sent fake leads. What did that look like?"
- **Quantify:** "What's a typical new customer worth to you in year one? And how many would make next year a good year?"
- **Listen:** "Sounds like you've been burned by agencies before."
- **Teach:** "What we usually see: when one agency worked and the next didn't, the difference was who was on the list, not the channel."
- **Offer** (a shape, not a script: the offer itself is built on the call): their problem in their words → what we'd do
  about it, in a line or two → why us, the mechanism rather than a meeting count. "You said [their problem]. What we'd
  do is [the offer that fits]. What's different is [how we get there]." (Weinberg's sales story.)
- **Price:** "After the pilot, the retainer starts at about $6.2k a month for email outbound. How does that compare with what one new customer is worth to you?"
- **Close:** "Tuesday at 10 with our founder? I'll send the invite now."

### Which moves apply
| Move | Discovery | Proposal | Negotiation | Client call |
| --- | --- | --- | --- | --- |
| Open, Listen, Close | ✓ | ✓ | ✓ | ✓ |
| Discover, Quantify, Teach | ✓ | ✓ (played back and confirmed counts) | n/a | n/a |
| Offer, Price | ✓ (headline offer and a range) | ✓ | ✓ | n/a |

The fit math for offer.fits (deals needed per year = 12 × retainer ÷ deal value, ideally ≤ 1; months of market
runway ≥ 3) is always written in the review, inputs marked KNOWN or ASSUMED (defaults in oneaway-context.md).

## 3. What we claimed (advice, not a penalty)
The reviewer checks what the OneAway side said against the claims policy in oneaway-context.md and plain fact, and
shows at most three lines worth improving, each with a better wording. It never changes the score.
- **Clean:** nothing worth changing.
- **Tighten:** a line that over-promises or can't be backed up.
- **Fix:** a line a prospect could check and find wrong (e.g. "MX records show who uses Anthropic").
Standard parts of the service are never flagged, however candidly they're described. That includes LinkedIn avatar
accounts rented or sourced from real account holders and run through Aimfox or HeyReach.

## 4. What the page coaches
- **Worked:** one or two real strengths, including recoveries.
- **The one focus behaviour,** tracked across calls.
- **At most one more fix, the root cause.** The root cause is what would have prevented the problem, not the moment it showed.
- **A single "line to try" for every other move marked Work on.** Everything else stays in the receipts.

## 5. Going further (tips, not scored)
These techniques still matter. They are left out of the score because they make less difference to an agency deal
than the sixteen checks above, or because they are covered by the outcome. Use them as coaching tips once the basics hold.
- **Opening:** confirm the time; say "if it's not a fit, we'll tell you, and that's fine" (Sandler up-front contract).
- **Discovery:** find the root cause and test their own diagnosis (Keenan; Enns "diagnose before prescribing").
  Keep going down the pain funnel: example, how long, what they tried, what it cost.
- **Numbers:** play the gap back in money and get a yes ("so you're ~$1M short this year, right?"). Ask what
  happens if nothing changes (SPICED critical event; SPIN implication and need-payoff questions).
- **Listening:** ask every person on the call about their own stake. Label and mirror (Voss).
- **Teaching:** tie every explanation to something they said. Ask a question before any pitch.
- **Offer and price:** offer two or three options, whatever the offer is, on proposal calls. Name the price after the value
  number. Ask how it sits with them (Enns, Weiss).
- **Close:** know how they decide and when they want to start. Test the commitment: "what could get in the way?"

## Sources
- **Open:** Sandler up-front contract.
- **Discover:** Sandler pain funnel; SPIN problem questions; Keenan current state.
- **Quantify:** SPICED Impact; Weiss conceptual agreement.
- **Listen:** Voss labels and calibrated questions; Gong talk-ratio and question data.
- **Teach:** Challenger commercial insight; Baker unapplied insight; Gong monologue data.
- **Offer:** Weinberg's sales story (*New Sales. Simplified.*): their problem, then what we do, then why us; Enns (*Win Without Pitching*); OneAway's own fit math.
- **Price:** Enns proclamation 9 ("address issues of money early"); Weiss (price moves with scope); Gong price timing.
- **Close:** Rackham (advance vs continuation).
- **Trust:** Maister's trust equation.
