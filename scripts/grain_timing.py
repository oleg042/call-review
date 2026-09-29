#!/usr/bin/env python3
"""Exact timings from Grain, so every quote on the review page can open the recording at that moment.

Usage: python3 grain_timing.py <workdir>
Reads  <workdir>/meta.json (grainUrl) and transcript.txt. Writes <workdir>/timing.json, or prints why not.

Source: the recording's share page embeds Grain's transcript with word-level times in milliseconds
(`"transcript":{"data":{"results":[[start_ms, word, end_ms], …], "speakerRanges":[{startIndex, endIndex, startMs,
endMs, speakerId}], "speakers":[…], "speakerStatistics":[…]}}`). One speaker range = one line of transcript.txt.
Grain deep links take the same clock: <share url>?t=<ms> (verified 2026-09-28: clicking 7:41 in Grain → ?t=461967).
This is an undocumented page payload: when it's missing or doesn't line up, the page falls back to estimated
times (marked "~") and says so. The official lane is the API's JSON transcript (start/end ms per section),
which needs the meetings app to store it.

Library use (render_review.py): load(workdir) → timing or None; moment(timing, line, quote) → ms.
"""
import html as H
import json
import re
import sys
from pathlib import Path


def _norm(w):
    return re.sub(r"[^a-z0-9$%']+", "", w.lower())


def _extract(page: str):
    t = H.unescape(page)
    i = t.find('"transcript":{"data":')
    if i < 0:
        return None
    j = i + len('"transcript":')
    depth = 0
    for k in range(j, len(t)):
        if t[k] == "{":
            depth += 1
        elif t[k] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(t[j:k + 1]).get("data")
    return None


def build(workdir: Path):
    meta = json.loads((workdir / "meta.json").read_text())
    url = (meta.get("grainUrl") or "").split("?")[0]
    if not url:
        return None, "no Grain share URL in meta.json"
    from curl_cffi import requests
    r = requests.get(url, impersonate="chrome", timeout=30)
    if r.status_code != 200:
        return None, f"share page HTTP {r.status_code}"
    data = _extract(r.text)
    dm = re.search(r'"state":"PROCESSED","title":.{0,400}?"duration":(\d+)', H.unescape(r.text))
    if not data or not data.get("results") or not data.get("speakerRanges"):
        return None, "no embedded transcript on the share page (Grain changed it, or the link isn't shared)"
    words, ranges = data["results"], data["speakerRanges"]
    names = {s["id"]: s["name"] for s in data.get("speakers", [])}
    lines = [l for l in (workdir / "transcript.txt").read_text().splitlines()]
    if len(ranges) != len(lines):
        return None, f"{len(ranges)} Grain speaker turns vs {len(lines)} transcript lines: not aligned, using estimates"
    out = {}
    for n, (line, rg) in enumerate(zip(lines, ranges), 1):
        speaker = line.split(":", 1)[0].strip()
        first = [_norm(w) for w in line.split(":", 1)[-1].split()[:3]]
        got = [_norm(w[1]) for w in words[rg["startIndex"]:rg["startIndex"] + 3]]
        g_name = names.get(rg["speakerId"], speaker)
        same_person = g_name == speaker or g_name.lower().split()[0] == speaker.lower().split()[0] or speaker.lower() in g_name.lower()
        if not same_person or (first and got and first[0] != got[0]):
            return None, f"line {n} doesn't match Grain's turn {n} ({speaker!r} vs {names.get(rg['speakerId'])!r}): using estimates"
        out[str(n)] = {"start_ms": rg["startMs"], "end_ms": rg["endMs"], "w0": rg["startIndex"], "w1": rg["endIndex"],
                       "speaker": speaker}
    talk = {}
    for rg in ranges:
        nm = names.get(rg["speakerId"], "?")
        talk[nm] = talk.get(nm, 0) + (rg["endMs"] - rg["startMs"])
    duration = int(dm.group(1)) if dm else max(rg["endMs"] for rg in ranges)
    return {"source": "grain share page", "url": url, "duration_ms": duration, "lines": out, "talk_ms": talk,
            "words": [[w[0], w[1]] for w in words]}, None


def load(workdir):
    p = Path(workdir) / "timing.json"
    return json.loads(p.read_text()) if p.exists() else None


def moment(timing, line, quote=None):
    """Recording time (ms) where `quote` starts inside transcript line `line`; the line's start if not found."""
    if not timing or not line or str(line) not in timing["lines"]:
        return None
    L = timing["lines"][str(line)]
    if quote:
        q = [_norm(w) for w in quote.split() if _norm(w)]
        ws = timing["words"][L["w0"]:L["w1"] + 1]
        normed = [_norm(w[1]) for w in ws]
        for i in range(len(normed)):
            if q and normed[i:i + min(3, len(q))] == q[:min(3, len(q))]:
                return ws[i][0]
    return L["start_ms"]


def link(timing, line, quote=None, lead_ms=2000):
    """Grain deep link a couple of seconds before the moment, so the listener hears the lead-in."""
    ms = moment(timing, line, quote)
    return None if ms is None else f"{timing['url']}?t={max(0, ms - lead_ms)}"


if __name__ == "__main__":
    wd = Path(sys.argv[1])
    timing, why = build(wd)
    if timing is None:
        (wd / "timing.json").unlink(missing_ok=True)
        print(f"no exact timings: {why}")
        sys.exit(0)
    (wd / "timing.json").write_text(json.dumps(timing))
    total = sum(timing["talk_ms"].values()) or 1
    print(f"exact timings for {len(timing['lines'])} lines from {timing['source']}; talk time: "
          + ", ".join(f"{k} {v / 1000:.0f}s ({100 * v / total:.0f}%)" for k, v in timing["talk_ms"].items()))
