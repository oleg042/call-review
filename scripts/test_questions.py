"""Question counting: real questions from reviewed calls. Run: python3 test_questions.py (exit 1 on any failure).

Each case was a miscount on a published review (2026-09-29): open questions marked closed because they didn't start
with what/how, and small talk, agenda checks and verbal tics counted as questions.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from metrics import SMALLTALK_Q, TAG_Q, is_open  # noqa: E402

OPEN = {
    "And then number two is, what has already been What's— oh my God, what's already been done in terms of outreach?": True,
    "Yes, I would love if you can, and it's okay if you don't have the exact numbers, but roughly, uh, how many meetings are being booked": True,
    "Where do you feel like you can improve your numbers?": True,
    "Like, why hasn't it worked to your standard?": True,
    "So would you be able to tell me a little more, like, what you're looking for, for on the CRM side?": True,
    "Um, what are you trying to get the— like, how many booked meetings per month is, is a good target?": True,
    "So, uh, with respect to the agency that you've hired, like, how long ago was this and what happened with it?": True,
    "Can you walk me through how you book meetings today?": True,
    "What is the annual contract value for you guys?": True,
    "So how many AEs do you have?": True,
    "Can I just know, um, how much in, in boxes do you guys have?": True,
    "And, uh, you said how many emails did they send with that?": True,
    "Can I ask you something about your budget?": False,
    "Interested leads, or those people that book a meeting with you?": False,
    "Does your team know if I use Google or Microsoft?": False,
    "Yeah, so it, it depends on, um, what you're looking for, but it sounds like you're looking for like 20,000 contacts?": False,
    "Would that be useful to you?": False,
    "Do you have a goal in mind?": False,
}
NOT_COUNTED = [  # small talk, logistics, agenda checks and tics: not discovery questions
    "Hey, how you doing?", "Which time zone are you in?", "Are you able to drop the meeting link here in the chat?",
    "Are we expecting, uh, your colleague to join as well?", "It starts on Monday, right, Priya?", "Is your last name?",
    "Does that sound fair?", "You know what I mean?", "Which name do you want me to use?",
    "Like, how can I ask, how old are your kids now?", "I'm not even gonna try, just remind me, how do you say it?",
]
COUNTED = ["Where are you at right now?", "How many deals do you close a month?"]

fails = [f"open={is_open(q)} expected {want}: {q}" for q, want in OPEN.items() if is_open(q) != want]
skipped = lambda q: bool(SMALLTALK_Q.search(q) or TAG_Q.search(q.strip()))  # noqa: E731
fails += [f"should not count: {q}" for q in NOT_COUNTED if not skipped(q)]
fails += [f"should count: {q}" for q in COUNTED if skipped(q)]
print("\n".join(fails) or f"all {len(OPEN) + len(NOT_COUNTED) + len(COUNTED)} cases pass")
sys.exit(1 if fails else 0)
