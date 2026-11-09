#!/usr/bin/env python3
"""Phase 3: summarise a labels CSV. Reads the file only; touches no database.

Prints the round's headline numbers in the form used in context notes, for example
"20 outputs, 142 entities: 94% ok, 5 wrong-canon, 3 noise, 1 escalated",
then counts by label and by competitor_type, and every non-ok row grouped by label.

CSV columns: output_id, entity, brand, competitor_type, label, note
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict

LABELS = ["ok", "wrong-canon", "wrong-type", "wrong-context", "noise", "missing", "escalate"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("labels", nargs="+", help="one or more labels CSV files")
    a = ap.parse_args()

    rows = []
    for path in a.labels:
        with open(path, newline="") as fh:
            rows += [r for r in csv.DictReader(fh) if (r.get("label") or "").strip()]
    if not rows:
        sys.exit("no labelled rows")

    unknown = sorted({r["label"] for r in rows} - set(LABELS))
    if unknown:
        sys.exit(f"unknown labels {unknown}; use one of {LABELS}")

    labels = Counter(r["label"] for r in rows)
    outputs = {r["output_id"] for r in rows}
    extracted = [r for r in rows if r["label"] != "missing"]
    ok_rate = labels["ok"] / len(extracted) if extracted else 0.0
    rest = ", ".join(f"{labels[k]} {k}" for k in LABELS[1:] if labels[k])
    print(f"{len(outputs)} outputs, {len(extracted)} entities: {ok_rate:.0%} ok" + (f", {rest}" if rest else ""))
    print("(ok rate is over extracted entities; 'missing' rows are misses the scorer never produced)\n")

    by_type: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        by_type[r.get("competitor_type") or "-"][r["label"]] += 1
    print("by competitor_type:")
    for ctype, counts in sorted(by_type.items()):
        print(f"  {ctype:<10} " + ", ".join(f"{k} {counts[k]}" for k in LABELS if counts[k]))

    print("\nnon-ok rows:")
    for label in LABELS[1:]:
        hits = [r for r in rows if r["label"] == label]
        if hits:
            print(f"\n  [{label}] {len(hits)}")
            for r in hits:
                print(f"    {r['output_id']}  {r['brand']} / {r['entity']}  — {r.get('note', '')}")


if __name__ == "__main__":
    main()
