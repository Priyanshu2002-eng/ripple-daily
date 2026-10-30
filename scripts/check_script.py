#!/usr/bin/env python3
"""Guard rails for a Ripple Daily script. Usage: check_script.py <episode.json> [<ripple days/DATE.json>]
Fails (exit 1) on: bad speakers, word count, missing disclaimer, buy/sell language, [CHECK] tags,
non-English script, or (with the days doc) any number not traceable to the Ripple Feed."""
import json, re, sys

DISCLAIMER = "not investment advice"
BANNED = re.compile(r"\b(buy|sell|accumulate|target price|stop[- ]loss|go long|go short)\b", re.I)
NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")

def nums(text):
    out = []
    for m in NUM.findall(text):
        try: out.append(float(m.replace(",", "")))
        except ValueError: pass
    return out

def strings(o):
    if isinstance(o, str): yield o
    elif isinstance(o, dict):
        for v in o.values(): yield from strings(v)
    elif isinstance(o, list):
        for v in o: yield from strings(v)

def traceable(x, src):
    if x <= 12 or 1990 <= x <= 2035: return True          # counts ("ten stories", "two"), years
    for y in src:
        if x == y: return True
        d = len(str(x).split(".")[1]) if "." in str(x) and not str(x).endswith(".0") else 0
        if round(y, d) == x: return True                    # rounding: 1.38 -> 1.4
        if y and abs(x - y) / abs(y) <= 0.03: return True  # "about" within 3%
        if y and abs(x - abs(y)) / abs(y) <= 0.03: return True
    return False

def main():
    ep = json.load(open(sys.argv[1])); errs, warns = [], []
    lines = ep.get("lines") or []
    if not lines: errs.append("no lines")
    for i, l in enumerate(lines):
        if l.get("speaker") not in ("SU", "PRI"): errs.append(f"line {i}: speaker {l.get('speaker')!r}")
        t = l.get("text", "")
        if "[CHECK]" in t: errs.append(f"line {i}: unresolved [CHECK]")
        if BANNED.search(t): errs.append(f"line {i}: advice word {BANNED.search(t).group(0)!r}")
        if re.search(r"[ऀ-ॿ]", t): errs.append(f"line {i}: non-English script")
        lim = 32 if l.get("speaker") == "SU" else 22
        if len(t.split()) > lim: warns.append(f"line {i}: {len(t.split())} words (> {lim})")
    words = sum(len(l.get("text", "").split()) for l in lines)
    if words > 1300: errs.append(f"{words} words > 1,300 hard cap")
    if words < 650: errs.append(f"{words} words < 650: episode would be too short")
    if DISCLAIMER not in " ".join(l.get("text", "") for l in lines[-3:]).lower():
        errs.append("disclaimer missing from the last lines")
    for k in ("date", "title", "description"):
        if not ep.get(k): errs.append(f"missing {k}")
    if len(sys.argv) > 2:
        day = json.load(open(sys.argv[2]))
        src = [n for s in strings(day) for n in nums(s)]
        for i, l in enumerate(lines):
            for x in nums(l.get("text", "")):
                if not traceable(x, src): errs.append(f"line {i}: number {x:g} not found in the Ripple Feed")
    est = words / 140 * 60
    print(json.dumps({"ok": not errs, "words": words, "est_minutes": round(est / 60, 1), "errors": errs, "warnings": warns}, indent=1))
    sys.exit(1 if errs else 0)

if __name__ == "__main__": main()
