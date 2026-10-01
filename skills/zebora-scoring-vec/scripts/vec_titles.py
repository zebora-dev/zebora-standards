"""Title cleaning used by the VEC canonicaliser (Phase 4).

norm_key()  — Python twin of public.normalize_company_name(): the key the reporting views match on.
title_l1()  — same title once case, punctuation, accents, '&', a leading 'the', number words and
              "game" / "card game" / "board game" / "party game" style suffixes are ignored.
title_l2a() — additionally ignores edition / format / packaging words ("2nd Edition", "Travel",
              "Mini", "Deluxe", "UK", "(2025 Edition)" …), retailer/publisher tails ("… by X",
              "… - John Lewis") and word order. Colon subtitles, sequel numbers and
              junior/kids/family/after-dark words are deliberately NOT stripped: those are often
              different products and need a judgement call.
"""
from __future__ import annotations

import re
import unicodedata


def _asc(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower().replace("’", "'").replace("‘", "'")


def norm_key(s: str) -> str:
    s = re.sub(r"^the ", "", _asc(s))
    s = s.replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "", s)


_NUM = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7",
        "eight": "8", "nine": "9", "ten": "10", "second": "2nd", "third": "3rd", "fourth": "4th"}
_TYPE_SUFFIX = re.compile(
    r"(\s*[-–—:]?\s*(the\s+)?((board|card|party|dice|tile|word|drinking|trivia|quiz|family|bluffing|guessing|"
    r"strategy|tabletop|social|deduction|memory|music|musical|cooperative|co-op|team|group|adult|adults|kids')\s+)*"
    r"(game|games))\s*$")
_QUAL_WORDS = (r"travel|mini|pocket|tin|deluxe|classic|refresh|refreshed|revised|anniversary|collector'?s?|"
               r"uk|us|usa|english|nordic|big box|original|retro|exclusive|amazon exclusive|new|updated|official")
_QUAL = re.compile(r"\b(" + _QUAL_WORDS + r")\b(\s+(edition|version|pack|set))?")
_EDITION = re.compile(r"\b((19|20)\d\d|\d+(st|nd|rd|th)|second|third|fourth)\s+edition\b|\b(edition|version)\b")
_PAREN_QUAL = re.compile(r"[\(\[]\s*[^\)\]]*\b(edition|version|(19|20)\d\d|uk|travel|mini|pocket|deluxe|refresh|classic|"
                         r"english|nordic|exclusive|new)\b[^\)\]]*[\)\]]")


def _words(s: str) -> list[str]:
    s = _asc(s).replace("&", " and ")
    return [_NUM.get(t, t) for t in re.findall(r"[a-z0-9]+", s)]


def title_l1(s: str) -> str:
    s = _TYPE_SUFFIX.sub("", _asc(s).replace("&", " and "))
    t = _words(s)
    if t and t[0] == "the":
        t = t[1:]
    return "".join(t)


def title_l2a(s: str) -> str:
    s = _asc(s).replace("&", " and ")
    s = _PAREN_QUAL.sub(" ", s)
    s = re.sub(r"\s+(by|from)\s+[a-z0-9 .'-]+$", " ", s)
    s = re.sub(r"\s+[-–—|]\s+[a-z0-9 .'&-]+$", " ", s)
    s = _EDITION.sub(" ", s)
    s = _QUAL.sub(" ", s)
    s = _TYPE_SUFFIX.sub("", s.strip())
    t = _words(s)
    if t and t[0] == "the":
        t = t[1:]
    return " ".join(sorted(t))
