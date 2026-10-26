#!/usr/bin/env python3
"""RateMyPrompts house-rules check.

Counts the mechanical breaches of the RateMyPrompts tone of voice and house
rules (references/tone-of-voice.md), so the same copy always gets the same
result. Judgement on tone, humour and argument stays with the reviewer.

Usage:
  check.py <file|->            text report
  check.py <file|-> --json     machine-readable
Exit code: 0 clean, 1 if any "must fix" finding.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html import unescape

# (rule id, severity, pattern, why). Severity "must" = breaks a house rule;
# "check" = usually wrong, but a reader should decide.
RULES: list[tuple[str, str, str, str]] = [
    # Mechanics
    ("em-dash", "must", r"—", "No em dashes. Use a full stop, comma, colon or brackets."),
    ("double-exclamation", "must", r"!{2,}", "Never two exclamation marks together."),
    ("emoji", "must",
     r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]",
     "No emoji in product copy, emails or community posts."),
    # Section 7: generic SaaS language the tone of voice names
    ("saas-word", "must",
     r"\b(unlock(?:s|ed|ing)?|supercharg(?:e|es|ed|ing)|revolutionis(?:e|es|ed|ing)|"
     r"revolutioniz(?:e|es|ed|ing)|leverag(?:e|es|ed|ing)|cutting[- ]edge)\b",
     "Named in the tone of voice as generic SaaS language."),
    # Same family; the tone of voice says "such as", so these are flagged for a look
    ("saas-family", "check",
     r"\b(game[- ]chang(?:er|ing)|seamless(?:ly)?|empower(?:s|ed|ing)?|harness(?:es|ed|ing)?|"
     r"elevat(?:e|es|ed|ing)|actionable insights?|best[- ]in[- ]class|next[- ]gen(?:eration)?|"
     r"world[- ]class|robust solution|in today's|ever[- ]evolving|landscape|delve|"
     r"transform(?:s|ed|ing|ative)?|comprehensive)\b",
     "Same family as the SaaS words the tone of voice bans. Keep only if it is the plainest word."),
    ("ai-hype", "check",
     r"\b(AI[- ]powered|powered by AI|the future of|game changer|"
     r"scientifically proven|independently certified|guaranteed?)\b",
     "AI hype or an unsubstantiated claim (section 7)."),
    # British English
    ("us-spelling", "must",
     r"\b(optimiz\w*|analyz\w*|prioritiz\w*|organiz\w*|recogniz\w*|categoriz\w*|"
     r"standardiz\w*|summariz\w*|personaliz\w*|customiz\w*|"
     r"behavior\w*|color\w*|favor\w*|center(?:s|ed)?|licens(?=e\b)|program(?=s?\b)(?!matic))",
     "British English spelling (optimise, analyse, behaviour, colour, centre). "
     "'program' is fine for software."),
    # Count rule
    ("count-rule", "must",
     r"\b(\d+\s*(?:of|/)\s*50\b|\d+\s+(?:founding\s+)?places?\s+(?:left|remaining|taken|gone)|"
     r"only\s+\d+\s+(?:founding\s+)?places?|(?:places?|spots?|slots?)\s+(?:left|remaining)|"
     r"nearly\s+(?:full|gone)|almost\s+(?:full|gone)|filling\s+(?:up\s+)?fast|"
     r"(?:last|final)\s+(?:few\s+)?(?:founding\s+)?places?|"
     r"(?:you(?:'re| are)|your)\s+(?:position|place)\s+in\s+(?:the\s+)?(?:queue|line)|"
     r"number\s+\d+\s+in\s+(?:the\s+)?queue)",
     "Count rule: say '50 founding places', never how many are taken or left, never a queue position."),
    ("place-words", "check", r"\b(slots?|spots?|seats?)\b",
     "We say 'founding places', not slots, spots or seats."),
    ("queue-word", "check", r"\bqueue\b", "Customer copy says 'the waitlist', not 'the queue'."),
    # Product vocabulary
    ("grade-word", "check", r"\b(grade[ds]?|grading|letter grade)\b",
     "User-facing copy says 'overall score', 'scores and assessment' or 'scorecard'."),
    # Scoring not yet final
    ("rubric-number", "check",
     r"(\bweighted at \d+%|\b\d{1,3}\s*/\s*100\b|\bthreshold of \d+|\bscores? (?:of )?\d+ out of 10\b)",
     "Rubric weightings, thresholds and score bands stay out of public copy until scoring is confirmed."),
    # Figures need a source
    ("unsourced-figure", "check",
     r"\b\d+(?:\.\d+)?\s?(?:%|x|×|times)(?=\W)",
     "A figure: is the source and sample named in the same passage?"),
]


# A figure is treated as sourced when one of these appears within SOURCE_WINDOW
# characters: a named study, our own panels, or the sampling arithmetic.
SOURCE_CUES = re.compile(
    r"(\bZebora\b|\bpanels?\b|\bstudy\b|\bsurvey\b|\bpaper\b|\bresearch\b|\bfound\b|"
    r"\bmeasured\b|\baccording to\b|\bsource\b|\bdata\b|\bsample\b|\bmargin\b|"
    r"\binterval\b|\bconfidence\b|\bmention rate\b|\bper cent\b|\[[^\]]+\]\(https?://)",
    re.I,
)
SOURCE_WINDOW = 300


def strip_markup(text: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return unescape(text)


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def check(text: str) -> list[dict]:
    findings = []
    for rule, severity, pattern, why in RULES:
        flags = 0 if rule in {"em-dash", "emoji", "double-exclamation"} else re.I
        for m in re.finditer(pattern, text, flags):
            if rule == "unsourced-figure":
                window = text[max(0, m.start() - SOURCE_WINDOW) : m.end() + SOURCE_WINDOW]
                if SOURCE_CUES.search(window):
                    continue
            start = max(0, m.start() - 40)
            context = text[start : m.end() + 40].replace("\n", " ").strip()
            findings.append(
                {
                    "rule": rule,
                    "severity": severity,
                    "line": line_of(text, m.start()),
                    "match": m.group(0),
                    "context": context,
                    "why": why,
                }
            )
    findings.sort(key=lambda f: (f["severity"] != "must", f["line"]))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", help="file to check, or - for stdin")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--html", action="store_true", help="strip HTML tags first")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.path == "-" else open(args.path, encoding="utf-8").read()
    text = strip_markup(raw) if args.html or args.path.endswith((".html", ".htm")) else raw
    findings = check(text)
    must = [f for f in findings if f["severity"] == "must"]

    if args.json:
        print(json.dumps({"must_fix": len(must), "to_check": len(findings) - len(must),
                          "findings": findings}, ensure_ascii=False, indent=2))
    else:
        print(f"RateMyPrompts house rules: {len(must)} must fix, {len(findings) - len(must)} to check")
        for f in findings:
            tag = "MUST " if f["severity"] == "must" else "check"
            print(f"  [{tag}] line {f['line']:>4} {f['rule']:<17} '{f['match']}'  ...{f['context']}...")
        if findings:
            print("\nWhy:")
            for rule in dict.fromkeys(f["rule"] for f in findings):
                why = next(f["why"] for f in findings if f["rule"] == rule)
                print(f"  {rule}: {why}")
    return 1 if must else 0


if __name__ == "__main__":
    sys.exit(main())
