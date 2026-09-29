# OneAway context pack

What the reviewers need to judge a OneAway sales call: how we sell, what we sell, what we may claim. Update this file when the offer, pricing or
approved claims change — the lenses are only as right as this page.

## What OneAway can deliver (a menu, not a fixed package)
- **The offer is built on the call.** Execs, Xavier especially, reshape it to what the client needs: a different
  mix, a mechanism instead of a meeting count, CRM management or another service entirely. That is fine and is never
  marked down or flagged. Judge only whether it was said plainly, tied to their problem and sized to them
  (offer.stated, offer.fits). A promised meeting count is what every agency sells; explaining the mechanism, how we
  get there, is what sets us apart (Oleg, 2026-09-29). The list below is what we can deliver, used to check facts.
- Done-for-you B2B outbound: cold email (primary, the intro offer) + LinkedIn campaigns; add-ons are
  appointment setting / SDRs calling leads, CRM integration and automation.
- We build the list (signal-based, scored against the client's ICP), write the copy, run the
  campaigns, and book meetings on the client's calendar. The client attends the meetings.
- Delivery runs on our own portal and AI agents; private sending infrastructure (custom domains,
  mixed Google / Outlook / SMTP mailboxes, warm-up, private sequencer).

## How we sell (the motion the rubric is built for)
- B2B agency selling, small-service-business dynamics: a **$5–20k/month retainer**, usually started with a pilot.
- Two or three calls over a few weeks: **discovery** (Mark or another exec, 20–30 min) → **proposal** (founder call
  with Xavier, 30–45 min) → sometimes **negotiation**. Buyers: founders, CEOs, VPs of sales/growth, CROs at SMB to
  mid-market, sometimes enterprise; one to three people on the call; the decision-maker is usually reachable.
- Not transactional (one call, one card) and not a nine-month enterprise cycle (no procurement maps, no champions
  programme). What wins: being treated as the expert, a number that makes the retainer look small, a concrete
  right-sized offer, money discussed early and plainly, and a booked next step.

## Commercial terms (as stated on calls, Sep 2026)
- Free pilot campaign first, then a flat monthly retainer, typically $5–20k/month; about **$6.2k/month** is the
  usual starting point for email outbound. It scales with contact volume and channels.
- **Pricing is individual, not a price sheet.** Execs often build a price on the call for the scope they've just
  described. That is a quote, not a claim: never compare it with the usual starting point, never flag it as
  misleading, and never rewrite it into a list price (confirmed by Oleg, 2026-09-29). Coach only on whether money
  came up plainly and whether it held without a scope change (price.plain, price.held).
- Options on a proposal call (a tip, not scored): two or three versions of whatever offer fits them, fullest first.
- A **$500 refundable deposit** is asked before the pilot. Never call the pilot "free" without
  naming the deposit in the same breath.
- Pricing is volume-based (contacts reached), not per meeting. A "guarantee" can only ever be about
  activity (contacts reached), never leads, meetings or revenue — say "contacts", not "leads".
- Rough planning ratio used on calls: ~1 interested lead per 100–300 contacts. It is an estimate.

## Who is a good fit for a ~$6k/month retainer
- The client's first-year contract value makes a handful of meetings worth far more than the
  retainer (enterprise or mid-market deal sizes).
- The target market is big enough for the planned volume. A small TAM (a few hundred accounts)
  needs an account-based approach with several contacts per account, not 20k sends a month.
- Someone on their side can take the meetings, and a decision-maker is reachable.
- Poor fits: low-ACV self-serve products ($1–$100 items), buyers whose whole marketing budget is
  below the retainer, "trial only" buyers with no path to paying.

## Claims policy
The claims check is advice, not a penalty: it never lowers the score. Flag only lines a prospect could check and
find wrong, or that promise more than we can show, at most three per call, with a better wording.

| Claim | Status | Correct version |
| --- | --- | --- |
| MX records show whether a company uses a given AI vendor (Anthropic, OpenAI) | FALSE | MX records show who hosts their email (Google, Microsoft, Mimecast). Use hiring/job-post signals for AI adoption. |
| Outreach / Salesloft are "public" or "low-grade" sequencers that share sender reputation | FALSE | They send from the customer's own mailboxes. Our point is private infra for high-volume cold sending. |
| Secure email gateways make enterprise mail "bounce back" | SALES COLOUR: not flagged on its own | SEGs filter and quarantine more aggressively; deliverability to enterprise is harder, not impossible. It is "Secure Email Gateway". |
| LinkedIn avatar accounts: rented or sourced from real account holders, run through Aimfox or HeyReach, branded to the client | OK: PART OF THE SERVICE | Industry-standard practice (confirmed by Oleg, 2026-09-29). Explaining how it works is fine and is never flagged. |
| Personal email addresses for enterprise execs | WORTH A NOTE | Mention only if asked; in regulated industries (pharma, finance, health) say the client decides whether to use them. |
| "Best sequencer in the world", "better deliverability than any other tool" | UNPROVABLE | Name a real client or case study, or drop it. |
| "Guaranteed leads/meetings" | FALSE | Guarantee contacts reached, if anything. |
| "Free pilot" with no mention of the deposit anywhere on the call | MISLEADING | "Free pilot with a $500 refundable deposit." Fine if the deposit is named elsewhere on the call. |
| An offer built on the call (a different mix, a mechanism, CRM work, anything outside the usual package) | OK: BUILT ON THE CALL | See "The offer is built on the call" above. |
| A price quoted on the call for the scope described | OK: A QUOTE, NOT A CLAIM | See "Pricing is individual" above. |
| Tone and ego lines ("I don't need to beg for your business") | NOT A CLAIM | Leave out of the claims check. |

## Reps and their known habits
Kept in `references/team.local.md` (local only, not in the repo). Reviewers read it when it exists.

## Call types (classify before scoring; the id goes to score.py)
- **discovery**: the first conversation after a positive reply. Goal: understand the problem and its number,
  check fit, state the headline offer and a price range, and book the proposal call with the decision-maker.
- **proposal**: the founder call. Goal: play back their problem and numbers, propose out loud (options, success
  metric, price), and book the start or the decision.
- **negotiation**: price, objections, terms, contract.
- **client**: an existing client (check-ins, weekly calls). Only Open, Listen, Close and Trust apply.

## Fit math defaults (offer.fits): use when a number wasn't said on the call, and mark it ASSUMED
| Input | Default |
| --- | --- |
| Retainer | $6,200/month email only; +$2–4k with LinkedIn |
| Their close rate, qualified meeting → deal | 20% |
| Interested leads per contacts reached | 1 per 200 (range 100–300) |
| Interested lead → held meeting | 50% |
Math: deals needed per year = 12 × retainer ÷ deal value (healthy ≤1, acceptable ≤3). Months of runway = reachable
contacts (accounts × contacts per account) ÷ monthly contacts (under 3 means the volume pitch burns the market;
switch to account-based). Example (a biotech prospect): $74k/yr ÷ $200k deal value = 0.4 deals, which is healthy; 200
accounts × ~100 people = 20k contacts ÷ 20k/month = 1 month of runway, so the volume plan was wrong.
