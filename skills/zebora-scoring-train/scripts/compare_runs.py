#!/usr/bin/env python3
"""Compare two sandbox runs of the SAME set (e.g. draft d0 vs d1). Reads files only.

For each output: entities only in the old run, only in the new run, and entities whose type / competitor_type /
target flags changed. With --labels (the CSV labelled on the OLD run) it also scores the change:
  fixed      a non-ok row (noise, wrong-*) that is gone or corrected in the new run, or a 'missing' now present
  regressed  an 'ok' row that disappeared or changed in the new run
  still      a non-ok row that is unchanged
Expect some churn from scorer noise; check the run-to-run variance section of the pack before blaming a rule.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


def norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def key(e: dict) -> tuple[str, str]:
    return norm(e.get("brand")), norm(e.get("entity"))


ROLE = ("entity_type", "competitor_type", "target_brand", "target_entity", "primary_competitor")


def by_output(path: str) -> dict[int, dict]:
    data = json.loads(Path(path).read_text())
    return {r["output_id"]: {key(e): e for e in r["entities"]} for r in data["results"] if r["run"] == 1}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--labels", help="labels CSV for the old run")
    a = ap.parse_args()
    old, new = by_output(a.old), by_output(a.new)

    print(f"entities: {sum(map(len, old.values()))} -> {sum(map(len, new.values()))}\n")
    for oid in sorted(set(old) | set(new)):
        o, n = old.get(oid, {}), new.get(oid, {})
        gone, added = sorted(set(o) - set(n)), sorted(set(n) - set(o))
        changed = [k for k in set(o) & set(n) if any(o[k].get(f) != n[k].get(f) for f in ROLE)]
        if not (gone or added or changed):
            continue
        print(f"{oid}")
        for k in gone:
            print(f"   - {o[k]['brand']} / {o[k]['entity']}")
        for k in added:
            print(f"   + {n[k]['brand']} / {n[k]['entity']}")
        for k in changed:
            diffs = ", ".join(f"{f} {o[k].get(f)}->{n[k].get(f)}" for f in ROLE if o[k].get(f) != n[k].get(f))
            print(f"   ~ {n[k]['brand']} / {n[k]['entity']}: {diffs}")

    if not a.labels:
        return
    with open(a.labels, newline="") as fh:
        labels = [r for r in csv.DictReader(fh) if (r.get("label") or "").strip()]
    fixed, regressed, still = [], [], []
    for r in labels:
        oid, k = int(r["output_id"]), (norm(r["brand"]), norm(r["entity"]))
        in_new = k in new.get(oid, {}) or any(norm(r["entity"]) == ek[1] for ek in new.get(oid, {}))
        role_same = k in new.get(oid, {}) and new[oid][k].get("competitor_type") == r.get("competitor_type")
        if r["label"] == "ok":
            if not (in_new and role_same):
                regressed.append(r)
        elif r["label"] == "missing":
            (fixed if in_new else still).append(r)
        elif r["label"] == "escalate":
            continue
        elif r["label"] == "wrong-type":
            (fixed if in_new and not role_same else still).append(r)
        else:  # noise, wrong-canon, wrong-context: fixed when that exact row is gone
            (fixed if k not in new.get(oid, {}) else still).append(r)
    print(f"\nagainst labels: {len(fixed)} fixed, {len(regressed)} regressed, {len(still)} still wrong")
    for title, rows in (("regressed", regressed), ("still wrong", still), ("fixed", fixed)):
        for r in rows:
            print(f"  [{title}] {r['output_id']} {r['brand']} / {r['entity']} ({r['label']}) {r.get('note', '')}")
    print("\nwrong-canon rows count as fixed when the old spelling is gone; check the new spelling is right.")


if __name__ == "__main__":
    main()
