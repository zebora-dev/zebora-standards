#!/usr/bin/env python3
"""
ai_tells_rubric@0.1.0 — deterministic AI-tell scoring for prose.

Counts the fifteen signals current detection research treats as meaningful and
returns a Human Read Score (0-100, higher reads more human) plus a per-signal
traffic light.

Stdlib only. Usage:

    score.py article.md
    score.py page.html --format html
    score.py data.ts --format ts --slug 4as-ai-brand-audit
    cat copy.txt | score.py -
    score.py article.md --json

The counting lives here so two runs of the same copy always produce the same
number. Judgement — which findings matter, how to rewrite them — stays with the
model. Never hand-adjust these counts in a scorecard.
"""

import argparse
import json
import math
import re
import statistics
import sys
from html.parser import HTMLParser

RUBRIC = "ai_tells_rubric@0.1.0"

# ─────────────────────────────────────────────────────────── watchlists

# Words that mark AI prose hard. Kept deliberately tight: each one is a word a
# careful human writer rarely reaches for unprompted. Do not pad this list with
# ordinary business vocabulary or every page scores red.
AI_VOCAB = [
    "delve", "leverage", "robust", "seamless", "tapestry", "testament",
    "harness", "unlock", "realm", "landscape of", "navigate the", "elevate",
    "empower", "holistic", "underscore", "pivotal", "multifaceted",
    "plethora", "myriad", "crucial", "vital role", "game-chang",
    "cutting-edge", "state-of-the-art", "ever-evolving", "fast-paced",
    "in today's", "it is important to note", "it's worth noting",
    "when it comes to", "a wide range of", "play a significant role",
]

# Adverbs that inflate a claim without adding information.
MAGIC_ADVERBS = [
    "genuinely", "fundamentally", "deeply", "remarkably", "notably",
    "noticeably", "essentially", "profoundly", "significantly", "truly",
    "incredibly", "vastly", "quietly", "simply put", "arguably",
]

# Grandiosity formulas.
STAKES = [
    r"is itself an? \w+ outcome", r"cannot be overstated",
    r"a (?:significant|major|profound|fundamental) (?:shift|outcome|change)",
    r"in its own right", r"more than just an?", r"nothing short of",
    r"a new era", r"paradigm shift", r"transform(?:s|ed|ing)? (?:the|how) \w+ entirely",
]

# Attribution with nobody behind it.
VAGUE_SOURCING = [
    r"\bexperts? (?:say|argue|suggest|agree|believe)",
    r"\bstudies (?:show|suggest|indicate|have shown)",
    r"\bresearch (?:shows|suggests|indicates)",
    r"\bit is widely (?:known|believed|accepted)",
    r"\bindustry reports? (?:suggest|show)",
    r"\bmany (?:believe|argue|would say)",
    r"\bsome (?:argue|say|would argue)",
]

# Staging a question in order to answer it.
STAGED_REFRAME = [
    r"shift(?:s|ed|ing)? the question from",
    r"move(?:s|d)? (?:past|beyond) [\"“']",
    r"the (?:real|useful|better) question (?:is|was|becomes)",
    r"start(?:s|ed)? asking",
    r"reframe(?:s|d)? the question",
    r"it'?s not (?:about|a question of) \w+[,.] (?:it'?s|but)",
]

NEGATION = (r"(?:isn['’]?t|wasn['’]?t|aren['’]?t|weren['’]?t|doesn['’]?t|didn['’]?t"
            r"|don['’]?t|not just|not only|not merely|more than just|no longer)")
# NB: it['’]s, never it'?s — the latter also matches the possessive "its" and
# turns every "wasn't measuring its presence" into a false positive.
PIVOT = (r"(?:it['’]s|it is|it was|they['’]re|so much as|rather than"
         r"|but rather|but|instead)")


# ─────────────────────────────────────────────────────────── extraction

class _Text(HTMLParser):
    """Pulls readable text out of HTML, remembering headings and bold spans."""

    SKIP = {"script", "style", "nav", "footer", "noscript", "svg", "head"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.headings, self.stack = [], [], []
        self.bold = 0

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)
        if tag in ("strong", "b"):
            self.bold += 1
        if tag in ("p", "div", "li", "br") or tag.startswith("h"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.stack:
            self.stack.reverse()
            self.stack.remove(tag)
            self.stack.reverse()
        if tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
            self.parts.append("\n")

    def handle_data(self, data):
        if any(t in self.SKIP for t in self.stack):
            return
        self.parts.append(data)
        for t in self.stack:
            if t.startswith("h") and len(t) == 2 and t[1].isdigit():
                clean = data.strip()
                if clean:
                    self.headings.append(clean)
                break

    def text(self):
        return re.sub(r"\n{2,}", "\n\n", "".join(self.parts))


def from_html(raw):
    p = _Text()
    p.feed(raw)
    return p.text(), p.headings, p.bold


def from_ts(raw, slug=None):
    """Extract prose from the in-repo case-study data file.

    Prose fields are arrays of double-quoted paragraph strings. If a slug is
    given, narrow to that study's object first.
    """
    if slug:
        anchor = raw.find(f'slug: "{slug}"')
        if anchor == -1:
            anchor = raw.find(slug)
        if anchor == -1:
            sys.exit(f"slug not found: {slug}")
        start = raw.rfind("\n  {", 0, anchor)
        nxt = raw.find("\n  {", anchor)
        end = nxt if nxt != -1 else len(raw)
        raw = raw[start if start != -1 else 0:end]

    # Section headings are scored for Wh-word monotony. FAQ questions are NOT:
    # question-shaped FAQs are correct for AEO and must never be penalised.
    headings = [m.group(1) for m in
                re.finditer(r'\w+Heading:\s*\n?\s*"((?:[^"\\]|\\.)*)"', raw)]
    faqs = [m.group(1) for m in
            re.finditer(r'question:\s*\n?\s*"((?:[^"\\]|\\.)*)"', raw)]
    titles = [m.group(1) for m in
              re.finditer(r'\btitle:\s*\n?\s*"((?:[^"\\]|\\.)*)"', raw)]
    seen_headings = {h.strip() for h in headings + faqs + titles}

    strings = re.findall(r'"((?:[^"\\]|\\.)*)"', raw)
    prose = []
    for s in strings:
        s = s.replace('\\"', '"').replace("\\n", " ").strip()
        # Headings are scored as headings. Leaving them in the prose stream makes
        # every "Section: subtitle" heading read as a colon gloss.
        if s in seen_headings:
            continue
        if len(s) > 55 and " " in s and not s.startswith(("/", "http", "#")):
            prose.append(s)

    text = "\n\n".join(prose)
    return text, headings, len(re.findall(r"\*\*[^*]+\*\*", text))


def from_text(raw):
    headings = re.findall(r"^#{1,6}\s+(.+)$", raw, re.M)
    bold = len(re.findall(r"\*\*[^*]+\*\*", raw))
    body = re.sub(r"^#{1,6}\s+.+$", "", raw, flags=re.M)
    body = re.sub(r"```.*?```", " ", body, flags=re.S)
    return body, headings, bold


def extract(raw, fmt, slug):
    if fmt == "auto":
        head = raw.lstrip()[:400].lower()
        if "<html" in head or "<!doctype" in head or "<body" in head:
            fmt = "html"
        elif "caseStudies" in raw or re.search(r"^import .*from", raw, re.M):
            fmt = "ts"
        else:
            fmt = "text"
    if fmt == "html":
        return from_html(raw)
    if fmt == "ts":
        return from_ts(raw, slug)
    return from_text(raw)


# ─────────────────────────────────────────────────────────── counting

def sentences(text):
    flat = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z“\"'])", flat)
    return [s for s in parts if len(s.split()) >= 2]


def count_patterns(text, patterns, flags=re.I):
    """Match every pattern, then drop overlaps.

    Several formulas in a list deliberately overlap ("a significant outcome" sits
    inside "is itself a significant outcome"). Without span dedup one phrase
    scores three times and a clean page reads red.
    """
    spans = []
    for pat in patterns:
        for m in re.finditer(pat, text, flags):
            spans.append((m.start(), m.end(), m.group(0).strip()))
    spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))
    kept, last_end = [], -1
    for start, end, frag in spans:
        if start >= last_end:
            kept.append(frag)
            last_end = end
    return kept


def count_words(text, words):
    hits = []
    for w in words:
        pat = r"\b" + re.escape(w) if w[-1].isalpha() else re.escape(w)
        for m in re.finditer(pat, text, re.I):
            hits.append(m.group(0))
    return hits


def negative_parallelism(text):
    """Negation followed by a contrastive pivot inside ~120 characters.

    The two-stage match separates a real 'not X, it's Y' construction from
    ordinary negation like 'the figure was not available'. One sentence boundary
    is allowed, because the canonical form in the research is written as two
    sentences: "It isn't X. It's Y."
    """
    hits = []
    for m in re.finditer(NEGATION, text, re.I):
        window = text[m.end():m.end() + 120]
        # at most one [.!?] may sit between the negation and the pivot
        if re.search(r"^[^.!?]{0,110}?\b" + PIVOT + r"\b", window, re.I) or \
           re.search(r"^[^.!?]{0,80}[.!?]\s+[^.!?]{0,40}?\b" + PIVOT + r"\b", window, re.I):
            frag = text[m.start():m.end() + 90].strip()
            hits.append(re.sub(r"\s+", " ", frag))
    return hits


def colon_glosses(text):
    """Mid-sentence colon introducing a restatement of the clause before it.

    Excludes the two legitimate uses that otherwise flood the count: a short
    label introducing a definition ("AI visibility: how often it appears"),
    which is a glossary entry rather than a prose tic, and a coordinated list
    after the colon.
    """
    out = []
    for m in re.finditer(r"[a-z\)\]][:：] +[a-z]", text):
        tail = text[m.end():m.end() + 90]
        if re.match(r"^[^.;]{0,15},[^.;]{0,25},", tail):        # a list, not a gloss
            continue
        # how many words since the last sentence break? <=3 means it is a label.
        head = text[max(0, m.start() - 120):m.start() + 1]
        segment = re.split(r"[.!?;]\s+", head)[-1]
        if len(segment.split()) <= 3:
            continue
        out.append(re.sub(r"\s+", " ", text[max(0, m.start() - 25):m.end() + 55]))
    return out


def cascades(text):
    """Lists of four or more coordinated items."""
    pat = r"\b(?:[a-z][\w'-]*(?:\s[a-z][\w'-]*){0,2}, ){3,}(?:and |or )?[a-z][\w'-]*"
    return [re.sub(r"\s+", " ", m.group(0)) for m in re.finditer(pat, text)]


def self_echo(text, n=6):
    words = re.findall(r"[a-z0-9'’%/#-]+", text.lower())
    seen, rep = {}, []
    for i in range(len(words) - n + 1):
        g = " ".join(words[i:i + n])
        seen[g] = seen.get(g, 0) + 1
    for g, c in seen.items():
        if c > 1:
            rep.append((g, c))
    return sorted(rep, key=lambda x: -x[1])


def scare_quotes(text):
    return [m.group(0) for m in re.finditer(r"[“\"]([a-z][^”\"]{3,70})[”\"]", text)]


def wh_headings(headings):
    return [h for h in headings if re.match(r"^\s*(why|what|how|where|when|who)\b", h, re.I)]


# ─────────────────────────────────────────────────────────── scoring

def band_score(value, green, red, higher_is_better=False):
    """Map a measurement onto 0-10, linear between the green and red thresholds."""
    if higher_is_better:
        if value >= green:
            return 10.0
        if value <= red:
            return 0.0
        return round(10 * (value - red) / (green - red), 1)
    if value <= green:
        return 10.0
    if value >= red:
        return 0.0
    return round(10 * (red - value) / (red - green), 1)


def light(score):
    if score >= 7.5:
        return "green", "Keep"
    if score >= 4.0:
        return "amber", "Tighten"
    return "red", "Fix now"


# name, weight, measured value, unit, green threshold, red threshold, higher_better
def build(text, headings, bold_n):
    sents = sentences(text)
    lens = [len(s.split()) for s in sents]
    words = len(text.split())
    k = max(words, 1) / 1000.0

    em = text.count("—")
    neg = negative_parallelism(text)
    col = colon_glosses(text)
    elaboration = em + len(col) + len(neg)
    per_move = words / elaboration if elaboration else 999.0

    vocab = count_words(text, AI_VOCAB)
    adverbs = count_words(text, MAGIC_ADVERBS)
    stakes = count_patterns(text, STAKES)
    vague = count_patterns(text, VAGUE_SOURCING)
    reframe = count_patterns(text, STAGED_REFRAME)
    casc = cascades(text)
    sq = scare_quotes(text)
    wh = wh_headings(headings)
    wh_ratio = len(wh) / len(headings) if headings else 0.0
    echo = [e for e in self_echo(text) if e[1] > 1]
    sigma = statistics.pstdev(lens) if len(lens) > 1 else 0.0

    rows = [
        # id, label, weight, value, display, green, red, higher_better, evidence
        ("elaboration", "Appositive elaboration", 20, per_move,
         f"1 : {per_move:.0f}", 80, 45, True,
         f"{elaboration} moves ({em} dash, {len(col)} colon, {len(neg)} negative)"),
        ("negparallel", "Negative parallelism", 15, len(neg) / k,
         f"{len(neg)}", 1.0, 3.5, False, "; ".join(neg[:3])),
        ("emdash", "Em-dash density", 10, em / k,
         f"{em / k:.1f}/1k", 5.0, 11.0, False, f"{em} in {words} words"),
        ("colon", "Colon glosses", 5, len(col) / k,
         f"{len(col)}", 3.0, 8.0, False, "; ".join(c[:60] for c in col[:2])),
        ("vocab", "AI vocabulary", 8, len(vocab) / k,
         f"{len(vocab)}", 0.4, 3.0, False, ", ".join(sorted(set(vocab))[:6]) or "none"),
        ("burstiness", "Sentence burstiness", 6, sigma,
         f"σ {sigma:.1f}", 10.0, 6.0, True,
         f"mean {statistics.mean(lens):.0f}w, range {min(lens)}-{max(lens)}" if lens else "n/a"),
        ("bold", "Bold-scatter", 5, bold_n / k,
         f"{bold_n}", 4.0, 9.0, False, f"{bold_n} spans"),
        ("scarequote", "Scare-quoted phrases", 5, len(sq),
         f"{len(sq)}", 1, 5, False, "; ".join(sq[:3])),
        ("stakes", "Stakes inflation", 5, len(stakes),
         f"{len(stakes)}", 0, 3, False, "; ".join(stakes[:3]) or "none"),
        ("adverbs", "Magic adverbs", 5, len(adverbs) / k,
         f"{len(adverbs)}", 1.5, 6.0, False, ", ".join(sorted(set(adverbs))[:6]) or "none"),
        ("reframe", "Staged reframing", 4, len(reframe),
         f"{len(reframe)}", 0, 3, False, "; ".join(reframe[:2]) or "none"),
        ("whhead", "Wh-word headings", 4, wh_ratio,
         f"{len(wh)}/{len(headings)}" if headings else "n/a", 0.40, 1.00, False,
         "; ".join(wh[:3]) or "none"),
        ("cascade", "Long cascades", 3, len(casc),
         f"{len(casc)}", 3, 9, False, "; ".join(c[:55] for c in casc[:2]) or "none"),
        ("sourcing", "Vague sourcing", 3, len(vague),
         f"{len(vague)}", 0, 3, False, "; ".join(vague[:3]) or "none"),
        ("echo", "Self-echo", 2, len(echo),
         f"{len(echo)}", 25, 70, False,
         "; ".join(f"{g} ×{c}" for g, c in echo[:2]) or "none"),
    ]

    signals, total_w, acc = [], 0, 0.0
    for sid, label, w, val, disp, green, red, hib, ev in rows:
        s = band_score(val, green, red, hib)
        lt, verdict = light(s)
        acc += s * w
        total_w += w
        signals.append({
            "id": sid, "label": label, "weight": w, "score": s,
            "light": lt, "verdict": verdict, "measured": disp, "evidence": ev,
        })

    overall = int(round(10 * acc / total_w))
    if overall >= 80:
        oband, olight = "Passes as human", "green"
    elif overall >= 60:
        oband, olight = "Reads AI on a careful read", "amber"
    else:
        oband, olight = "Reads AI immediately", "red"

    return {
        "rubric": RUBRIC,
        "words": words,
        "sentences": len(sents),
        "human_read_score": overall,
        "band": oband,
        "light": olight,
        "signals": signals,
        "detail": {
            "negative_parallelism": neg,
            "colon_glosses": col[:20],
            "scare_quotes": sq,
            "cascades": casc[:10],
            "ai_vocab": sorted(set(vocab)),
            "magic_adverbs": sorted(set(adverbs)),
            "stakes": stakes,
            "vague_sourcing": vague,
            "staged_reframes": reframe,
            "wh_headings": wh,
            "self_echo": [f"{g} ×{c}" for g, c in echo[:15]],
        },
    }


LIGHTS = {"green": "🟢", "amber": "🟠", "red": "🔴"}


def render(r):
    out = []
    out.append(f"# AI tells — Human Read Score {r['human_read_score']}/100")
    out.append("")
    out.append(f"{LIGHTS[r['light']]} **{r['band']}** · {r['words']:,} prose words · "
               f"{r['sentences']} sentences · `{r['rubric']}`")
    out.append("")
    out.append("> Higher reads more human. The score measures surface tells, "
               "not whether the copy is true, useful or well argued.")
    out.append("")
    out.append("| | Signal | Measured | Weight | Verdict | Evidence |")
    out.append("| --- | --- | ---: | ---: | --- | --- |")
    for s in sorted(r["signals"], key=lambda x: (x["score"], -x["weight"])):
        ev = (s["evidence"] or "")[:90]
        out.append(f"| {LIGHTS[s['light']]} | {s['label']} | `{s['measured']}` | "
                   f"{s['weight']}% | {s['verdict']} | {ev} |")
    out.append("")
    reds = [s for s in r["signals"] if s["light"] == "red"]
    ambers = [s for s in r["signals"] if s["light"] == "amber"]
    greens = [s for s in r["signals"] if s["light"] == "green"]
    out.append(f"**{len(reds)} fix now · {len(ambers)} tighten · {len(greens)} keep**")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Score prose for AI tells.")
    ap.add_argument("path", help="file to score, or - for stdin")
    ap.add_argument("--format", default="auto", choices=["auto", "text", "html", "ts"])
    ap.add_argument("--slug", help="case-study slug when --format ts")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    a = ap.parse_args()

    raw = sys.stdin.read() if a.path == "-" else open(a.path, encoding="utf-8").read()
    text, headings, bold = extract(raw, a.format, a.slug)

    if len(text.split()) < 120:
        sys.exit("under 120 words of prose found — rates are not meaningful at this "
                 "length. Check --format, or score a longer passage.")

    result = build(text, headings, bold)
    print(json.dumps(result, indent=2) if a.json else render(result))


if __name__ == "__main__":
    main()
