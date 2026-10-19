#!/usr/bin/env python3
"""Phase 7: seed entity dimensions for a brand, modelled on TransUnion: one visibility_entity_brands row and one
visibility_entities row per canonical provider in the STORED entities, aliases on entities (from raw_* names and the
active context mappings), target / primary flags from the brand and competitors_primary. Dry run unless --go.
Refuses if the brand already has dimension rows. Keys come from the SQL function normalize_company_name.

READ the printed brand list for near-duplicates ("Widgit" / "Widgit Resources") before --go.
"""
from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import (  # noqa: E402
    batch_for_brand,
    brand_by_slug,
    fetch_all,
    normalize_key,
    supabase,
)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--slug", required=True)
    ap.add_argument("--go", action="store_true")
    a = ap.parse_args()
    sb = supabase()
    brand = brand_by_slug(sb, a.slug)
    bid = brand["id"]
    batch = batch_for_brand(sb, bid)
    for t in (
        "visibility_entity_brands",
        "visibility_entities",
        "visibility_entity_aliases",
    ):
        if sb.table(t).select("id").eq("brand_id", bid).limit(1).execute().data:
            sys.exit(f"{t} already has rows for {a.slug}: refusing to seed twice")
    prim = (
        sb.table("competitors_primary")
        .select("competitors(name)")
        .eq("brand_id", bid)
        .execute()
        .data
    )
    PRIMARY = {p["competitors"]["name"] for p in prim if p.get("competitors")}
    # the answers name the brand by its canonical name ("Twinkl"), not the display name ("Twinkl (US)")
    target = brand.get("name_canonical") or brand["name"]
    rows = fetch_all(
        sb, "scores_visibility", "entities", batch_id=batch["id"], active=True
    )
    ctx = (
        sb.table("visibility_prompt_contexts")
        .select("canonical_entity_mappings")
        .eq("brand_id", bid)
        .eq("active", True)
        .execute()
        .data
    )
    pairs, raws = collections.Counter(), collections.defaultdict(set)
    for r in rows:
        for e in r["entities"]:
            pairs[(e["brand"], e["entity"])] += 1
            for k in ("raw_entity", "raw_brand"):
                if e.get(k) and e[k] not in (e["brand"], e["entity"]):
                    raws[(e["brand"], e["entity"])].add(e[k])
    for alias, v in (
        (ctx[0]["canonical_entity_mappings"] if ctx else {}) or {}
    ).items():
        if alias != v["entity"]:
            raws[(v["brand"], v["entity"])].add(alias)
    cache: dict = {}
    key = lambda n: normalize_key(sb, n, cache)
    brands = {}
    for b, _ in pairs:
        brands.setdefault(key(b), b)
    bclash = collections.defaultdict(set)
    eclash = collections.defaultdict(set)
    for b, e in pairs:
        bclash[key(b)].add(b)
        eclash[key(e)].add((b, e))
    alias_rows = {}
    for pair, names in raws.items():
        if pair not in pairs:
            continue
        for n in names:
            k = key(n)
            if k and k != key(pair[1]) and k not in alias_rows:
                alias_rows[k] = (n, pair)
    print(
        f"{len(rows)} stored rows | brands {len(brands)} | entities {len(pairs)} | aliases {len(alias_rows)} | primaries {sorted(PRIMARY)}"
    )
    print(
        "brand-key clashes:", {k: v for k, v in bclash.items() if len(v) > 1} or "none"
    )
    print(
        "entity-key clashes:", {k: v for k, v in eclash.items() if len(v) > 1} or "none"
    )
    print("brands:", "; ".join(sorted(brands.values())))
    if not a.go:
        print(
            "dry run: pass --go to write (after reading the brand list for near-duplicates)"
        )
        return
    brow = [
        {
            "brand_id": bid,
            "name": n,
            "normalized_brand_key": k,
            "is_target_brand": n == target,
            "is_primary_competitor": n in PRIMARY,
            "active": True,
            "metadata": {},
        }
        for k, n in brands.items()
    ]
    bins = {
        r["normalized_brand_key"]: r["id"]
        for r in sb.table("visibility_entity_brands").insert(brow).execute().data
    }
    seen, erow = set(), []
    for b, e in pairs:
        k = key(e)
        if k in seen:
            continue
        seen.add(k)
        erow.append(
            {
                "brand_id": bid,
                "entity_brand_id": bins[key(b)],
                "name": e,
                "normalized_entity_key": k,
                "is_target_entity": e == target and b == target,
                "active": True,
                "metadata": {},
            }
        )
    eins = {
        r["normalized_entity_key"]: r["id"]
        for r in sb.table("visibility_entities").insert(erow).execute().data
    }
    arow = [
        {
            "brand_id": bid,
            "visibility_entity_id": eins[key(p[1])],
            "alias_name": n,
            "alias_key": k,
            "active": True,
        }
        for k, (n, p) in alias_rows.items()
        if key(p[1]) in eins
    ]
    if arow:
        sb.table("visibility_entity_aliases").insert(arow).execute()
    print(f"WROTE brands {len(brow)} entities {len(erow)} aliases {len(arow)}")


if __name__ == "__main__":
    main()
