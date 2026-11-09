#!/usr/bin/env python3
"""Discovery: what do the responses in a set actually contain? Read-only. Run BEFORE scoring a draft.

Writes sets/set-<k>__discovery.md with:
  - candidate names: bold text, numbered items, headings, "Name:" leads, link text, "(brand)" attributions,
    with how many outputs each appears in and how it appeared
  - for each name: whether the draft context already mentions it, and whether the brand's alias tables know it
  - cited domains (citations are not recommendations, but they show who the LLMs lean on)
  - structure per output: list lines, tables, images, shopping-widget style lines
It is a reading aid for spotting themes, not an extraction: read the responses too.

  --set FILE      sets/set-<k>.json
  --draft DIR     optional: the current draft, to mark which names it already covers
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))
from _common import clean_response, db_engine, load_set, read_draft  # noqa: E402

PATTERNS = {
    "bold": re.compile(r"\*\*([^*\n]{2,60})\*\*"),
    "numbered": re.compile(r"^\s*\d+\\?[\.\)]\s*\**([^*\n:\u2014\u2013|]{2,60})", re.MULTILINE),
    "heading": re.compile(r"^\s*#{1,4}\s*(?:\d+\\?[\.\)]\s*)?([^\n]{2,60})$", re.MULTILINE),
    "lead": re.compile(r"^\s*(?:[-*•]\s*)?\**([A-Z][A-Za-z0-9’'&\.\+\- ]{1,45}?)\**\s*[:\u2014\u2013]\s", re.MULTILINE),
    "link": re.compile(r"(?<!!)\[([^\]]{2,60})\]\((?:https?://)[^)]+\)"),
    "attribution": re.compile(r"\(([A-Za-z0-9+&\.\- ]{2,30})\)"),
}
URL = re.compile(r"https?://[^\s)\]]+")
NOISE = re.compile(r"^(step|tip|note|why|best|pros?|cons?|summary|overview|key|example|option|bottom line|"
                   r"verdict|price|cost|features?|my|the|a|an|for|if|how|what|when|which|who)\b", re.I)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def alias_keys(brand_id: str) -> set[str]:
    from sqlalchemy import text

    with db_engine().connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        keys = conn.execute(
            text(
                """
                SELECT alias_key FROM visibility_entity_aliases WHERE brand_id = :b AND active
                UNION SELECT alias_key FROM visibility_entity_brand_aliases WHERE brand_id = :b AND active
                """
            ),
            {"b": brand_id},
        ).scalars().all()
    return {norm(k) for k in keys if k}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", required=True)
    ap.add_argument("--draft")
    a = ap.parse_args()
    set_path = Path(a.set)
    st = load_set(set_path)
    draft_text = ""
    if a.draft:
        d = read_draft(Path(a.draft))
        draft_text = norm(d["category_rules"] + d["brand_profile"] + str(d.get("canonical_entity_mappings")))
    try:
        known_aliases = alias_keys(st["brand_id"])
    except Exception as e:  # alias tables are a hint; discovery still works without them
        print(f"alias lookup skipped: {e}")
        known_aliases = set()

    seen_in: dict[str, set[int]] = defaultdict(set)
    how: dict[str, Counter] = defaultdict(Counter)
    display: dict[str, str] = {}
    domains: Counter = Counter()
    structure = []
    for out in st["outputs"]:
        raw = out["response"] or ""
        text_ = clean_response(raw)
        for kind, pat in PATTERNS.items():
            for m in pat.findall(raw if kind == "link" else text_):
                name = re.sub(r"\]\([^)]*\)", "", html.unescape(m))
                name = re.sub(r"[\\*#`\[\]]", "", name).strip(" :.-")
                name = re.sub(r"^\d+[\.\)]\s*", "", name)
                if len(name) < 2 or NOISE.match(name) or len(name.split()) > 6:
                    continue
                k = norm(name)
                if not k:
                    continue
                seen_in[k].add(out["output_id"])
                how[k][kind] += 1
                display.setdefault(k, name)
        domains.update({urlparse(u).netloc.removeprefix("www.") for u in URL.findall(raw)})
        structure.append(
            (out["output_id"], out["llm_model"],
             len(re.findall(r"^\s*(?:\d+\\?[\.\)]|[-*•])\s+", raw, re.MULTILINE)),
             raw.count("\n|"), len(re.findall(r"!\[", raw)), len(PATTERNS["attribution"].findall(text_)))
        )

    ranked = sorted(seen_in, key=lambda k: (-len(seen_in[k]), display[k].lower()))
    lines = [f"# Discovery · set {st['set']} · {st['brand_name']} · {len(st['outputs'])} outputs", ""]
    lines += ["## Candidate names", "",
              "In = outputs it appears in. Draft / Alias = already covered by the draft text / the alias tables.", "",
              "| Name | In | How it appeared | Draft | Alias |", "|---|---|---|---|---|"]
    for k in ranked:
        hows = ", ".join(f"{h} {c}" for h, c in how[k].most_common())
        lines.append(f"| {display[k]} | {len(seen_in[k])} | {hows} | {'yes' if draft_text and k in draft_text else ''} | "
                     f"{'yes' if k in known_aliases else ''} |")
    lines += ["", "## Cited domains", "", ", ".join(f"{d} ({c})" for d, c in domains.most_common(40)) or "None", ""]
    lines += ["## Structure", "", "| Output | LLM | list lines | table rows | images | (attributions) |",
              "|---|---|---|---|---|---|"]
    lines += [f"| {o} | {m} | {li} | {t} | {im} | {at} |" for o, m, li, t, im, at in structure]
    path = set_path.with_name(f"{set_path.stem}__discovery.md")
    path.write_text("\n".join(lines) + "\n")
    multi = sum(1 for k in ranked if len(seen_in[k]) > 1)
    print(f"{len(ranked)} candidate names ({multi} in 2+ outputs), {len(domains)} cited domains")
    print(f"report: {path}")


if __name__ == "__main__":
    main()
