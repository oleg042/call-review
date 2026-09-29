# The numbers panel

Eight measures shown on every review, computed by scripts (`metrics.py` → `score.py`) or counted from the reviewers'
evidence lists, never estimated by the model. Guides are ranges, not pass marks. Most outside benchmarks come from
Gong's analyses of B2B tech sales calls, not agencies, and they show correlation, not cause. Show the guide, never
fail a call on one number.

| Measure (panel key) | How it's computed | Guide | Source | Blind spot |
| --- | --- | --- | --- | --- |
| **Talk share, us vs them** (`talk`) | Share of speaking time from Grain's exact timings (share of words when timings are missing); split per exec on shared calls | Us ≤55% discovery, ≤60% proposal | Gong 2025: won deals 57%, lost 62% ([link](https://www.gong.io/blog/talk-to-listen-conversion-ratio)); Gong calls the gap small, so it's a number to glance at, not a check | Grain can mislabel speakers |
| **Longest answer** (`longest`) | Longest single turn of ours, in words; ~150 words per minute | ≤250 words (~90 s) | OneAway line, kept at 250 on purpose (2026-09-29): explaining the service plainly takes room, and Gong's own data allows ~2 min for the "about us" part before win rates drop ([link](https://www.gong.io/blog/winning-sales-conversations)). Gong's stricter 76 s is uninterrupted pitching in software demos ([link](https://www.gong.io/blog/sales-demos)). Sandler, Rackham, Khalsa and Weinberg all favour short answers but give no number | An "mm-hm" from them splits one monologue into two |
| **Talk before the first real question** (`pitch`) | Our words before the first question they answered | ≤300 words (~2 min); proposal ≤450 for the recap | Gong: win rates fall after ~2 min of company overview ([link](https://www.gong.io/blog/winning-sales-conversations)) | A scripted proposal recap inflates it (hence the higher guide) |
| **Questions they answered** (`questions`) | Our questions at the end of a turn that they then answered; tag questions ("…, right?"), small talk and "what was that?" excluded; % open = a clause starts with how/what/which/where/when/who/why/tell me/walk me after fillers ("And then, what…", "Yes, roughly, how many…"), or "can you walk me through…"; name questions and "does that sound fair?" checks are left out | 11–14 per 30 min (scaled to call length), at least half open; fewer with C-suite buyers | Gong, 519K discovery calls ([link](https://www.gong.io/resources/labs/deal-closing-discovery-call/)) | A real question mid-monologue is dropped; "What do you think of our…" counts as open |
| **Problems they raised, dug into first** (`pains`) | Reviewer 2 lists every problem they volunteered and whether a follow-up question came before our answer | All of them | Sandler pain funnel; SPIN | Depends on the reviewer's list; the list is shown in the receipts |
| **Questions about what the problem costs them** (`cost_qs`) | Reviewer 2 lists our questions about consequences or payoff (implication and need-payoff questions) | At least 2 | OneAway line; Rackham: these questions predict success in bigger sales | Same as above |
| **Price first raised** (`price_at`) | First line with price/budget words, skipping their own deal-size talk; by whom; before or after value (from `price.after_value`) | On call 1, after the value, ~¾ of the way in | Gong, 11,331 deals ([link](https://www.gong.io/blog/data-reveals-the-best-time-to-talk-price-and-budget)); Enns proclamation 9 | Keyword-based; the reviewer confirms |
| **Questions re-asked** (`repeats`) | Our questions that repeat ≥50% of an earlier one's content words | 0 | Voss / basic listening | Deliberate clarifying re-asks look the same |

Also computed and used by the checks, not shown as rows: label and mirror candidates (the reviewer confirms or
rejects each), "why" questions, questions by quarter of the call, speaker switches per minute, minute marks for
every line (shown as `~mm:ss`, approximate, by word position), and the talk map (one block per turn, in call order).

The "Your last 3" column (single-exec calls) reads `~/.claude/call-review/history.csv`, one row per exec per call.
