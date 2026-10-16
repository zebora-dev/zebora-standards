#!/usr/bin/env python3
"""Phase 6: correct STORED scores_visibility.entities for a batch instead of re-scoring (the scorer is non-deterministic,
drops items from long lists and ignores exclusion rules). Dry run unless --go. Idempotent: a second run reports 0 changes.

  --find-candidates   print numbered / bold / "Name :" items in each response that were NOT extracted (review by hand) and
                      write candidates.json next to the backup. Writes nothing to the database.
  --spec FILE         apply a corrections spec (see examples/twinkl_corrections.json)

Spec keys:
  include_context_mappings (default true)  also apply the active context's canonical_entity_mappings
  mappings        {alias: canonical brand}   rename: brand AND entity become the canonical brand (raw_* kept)
  remove          [names]                    drop entities whose brand or entity equals one of these (case-insensitive)
  remove_prefix   [prefixes]
  remove_by_output {output_id: [names]}      per-output removals
  merge_by_output  {output_id: {alias: brand}}   per-output renames
  type_fix        {"unknown": "resource_provider"}
  add             [{output_id, brand, entity_type, variants?[]}]   add a missed provider found in the response text
Every changed row records metadata.manual_edits and each touched entity carries canonicalised.rule.
A full backup of the batch's score rows is written to db_backup/<slug>_<date>/ before the first write.
"""
from __future__ import annotations

import argparse
import collections
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import TODAY, backup_dir, clean_response, fetch_all, supabase  # noqa: E402


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def find_candidates(rows, outs, out_path: Path):
    res = {}
    for r in rows:
        oid = str(r["output_id"])
        resp = clean_response(outs[oid])
        have = {norm(e["brand"]) for e in r["entities"]} | {
            norm(e["entity"]) for e in r["entities"]
        }
        names = []
        for line in resp.splitlines():
            names += re.findall(r"\*\*([^*\n]{3,60})\*\*", line)
            h = re.match(r"^\s*#{1,4}\s*(?:\d+\\?[\.\)]\s*)?(.+)$", line)
            if h:
                names.append(h.group(1))
            n2 = re.match(r"^\s*\d+\\?[\.\)]\s*\**([^*\n:\u2014\u2013]{3,60})", line)
            if n2:
                names.append(n2.group(1))
            names += re.findall(
                r"(?:(?<=[\.\n!?])|^)\s*([A-Z][A-Za-z0-9’'&\.\+\- ]{2,45}?)\s:\s", line
            )
        got = []
        for n in dict.fromkeys(re.sub(r"[\\*#]", "", x).strip(" :") for x in names):
            n = re.split(r"\s[\u2014\u2013-]\s|\s\(|:", n)[0].strip()
            nn = norm(n)
            if (
                len(nn) < 4
                or len(n) > 55
                or any(nn in h or (len(h) > 4 and h in nn) for h in have)
            ):
                continue
            if re.match(
                r"^(Best|Why|Cost|Free|Tip|Look|Watch|Good|Try|Key|Note|Pros|Cons|Verdict|What|Which|How|One|Step|My |The best|Main|Quick|Your|Check|Ask|Use|If |Can |Let me)",
                n,
            ):
                continue
            got.append(n)
        if got:
            res[oid] = got
    out_path.write_text(json.dumps(res, indent=1))
    print(f"{len(res)} outputs with candidate misses -> {out_path}")
    for k, v in sorted(res.items()):
        print(k, "|", "; ".join(v)[:300])


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--batch", required=True)
    ap.add_argument("--spec")
    ap.add_argument("--find-candidates", action="store_true")
    ap.add_argument("--go", action="store_true")
    a = ap.parse_args()
    if not (a.spec or a.find_candidates):
        sys.exit("pass --spec FILE and/or --find-candidates")

    sb = supabase()
    batch = (
        sb.table("batches").select("id,brand_id").eq("id", a.batch).execute().data[0]
    )
    brand = (
        sb.table("brands")
        .select("id,name,slug")
        .eq("id", batch["brand_id"])
        .execute()
        .data[0]
    )
    bdir = backup_dir(brand["slug"])
    rows = fetch_all(sb, "scores_visibility", "*", batch_id=a.batch, active=True)
    outs = {
        str(o["id"]): o["response"]
        for o in fetch_all(
            sb, "prompts_outputs", "id,response", batch_id=a.batch, active=True
        )
    }
    print(
        f"brand {brand['name']} | {len(rows)} active score rows | {len(outs)} active outputs"
    )
    if a.find_candidates:
        find_candidates(rows, outs, bdir / "candidates.json")
    if not a.spec:
        return

    spec = json.loads(Path(a.spec).read_text())
    target = brand["name"]
    prim = (
        sb.table("competitors_primary")
        .select("competitors(name)")
        .eq("brand_id", brand["id"])
        .execute()
        .data
    )
    PRIMARY = {p["competitors"]["name"] for p in prim if p.get("competitors")}
    maps = {}
    if spec.get("include_context_mappings", True):
        ctx = (
            sb.table("visibility_prompt_contexts")
            .select("canonical_entity_mappings")
            .eq("brand_id", brand["id"])
            .eq("active", True)
            .execute()
            .data
        )
        if ctx:
            maps.update(
                {
                    k.lower(): v["brand"]
                    for k, v in (ctx[0]["canonical_entity_mappings"] or {}).items()
                }
            )
    maps.update({k.lower(): v for k, v in spec.get("mappings", {}).items()})
    REMOVE = {n.lower() for n in spec.get("remove", [])}
    PREFIX = tuple(p.lower() for p in spec.get("remove_prefix", []))
    RM_OUT = {
        str(k): {n.lower() for n in v}
        for k, v in spec.get("remove_by_output", {}).items()
    }
    MERGE_OUT = {
        str(k): {n.lower(): b for n, b in v.items()}
        for k, v in spec.get("merge_by_output", {}).items()
    }
    TYPE_FIX = spec.get("type_fix", {"unknown": "resource_provider"})
    ADD = [
        (
            str(x["output_id"]),
            x["brand"],
            x.get("entity_type", "resource_provider"),
            x.get("variants") or [x["brand"]],
        )
        for x in spec.get("add", [])
    ]

    def flags(brand_name):
        if brand_name == target:
            return dict(
                competitor_type="target", target_brand=True, primary_competitor=False
            )
        return dict(
            competitor_type="primary" if brand_name in PRIMARY else "active",
            target_brand=False,
            primary_competitor=brand_name in PRIMARY,
        )

    note = lambda rule: {
        "rule": rule,
        "by": "Claude (user-approved decisions)",
        "date": TODAY,
    }
    changes, totals = [], collections.Counter()
    for r in rows:
        oid = str(r["output_id"])
        resp = clean_response(outs[oid])
        L = collections.defaultdict(list)
        keep = []
        for e in copy.deepcopy(r["entities"]):
            names = {e["brand"].lower(), e["entity"].lower()}
            if (
                names & REMOVE
                or any(n.startswith(PREFIX) for n in names)
                or names & RM_OUT.get(oid, set())
            ):
                L["removed"].append(f'{e["brand"]}/{e["entity"]}')
                continue
            new_b = (
                MERGE_OUT.get(oid, {}).get(e["brand"].lower())
                or maps.get(e["entity"].lower())
                or maps.get(e["brand"].lower())
            )
            if new_b and (e["brand"] != new_b or e["entity"] != new_b):
                L["renamed"].append(f'{e["brand"]}/{e["entity"]} -> {new_b}')
                e["raw_brand"], e["raw_entity"] = e.get("raw_brand", e["brand"]), e.get(
                    "raw_entity", e["entity"]
                )
                e["brand"] = e["entity"] = new_b
                e.update(flags(new_b))
                e["canonicalised"] = note("manual_mapping")
            if e.get("entity_type") in TYPE_FIX:
                L["type_fixed"].append(e["brand"])
                e["entity_type"] = TYPE_FIX[e["entity_type"]]
            if e["brand"] == target and e.get("entity_type") != "brand":
                e["entity_type"] = "brand"
            keep.append(e)
        merged = []
        for e in sorted(keep, key=lambda x: x["position"]):
            d = next(
                (
                    m
                    for m in merged
                    if m["brand"] == e["brand"] and m["entity"] == e["entity"]
                ),
                None,
            )
            if d:
                d["mention_count"] = d.get("mention_count", 1) + e.get(
                    "mention_count", 1
                )
                d["source_text"] = list(
                    dict.fromkeys(
                        (d.get("source_text") or []) + (e.get("source_text") or [])
                    )
                )[:6]
                L["merged"].append(e["brand"])
            else:
                merged.append(e)
        have = {m["brand"].lower() for m in merged}
        for a_oid, b, etype, variants in ADD:
            if a_oid != oid or b.lower() in have:
                continue
            hits = sorted(
                (m.start(), m.group(0))
                for v in variants
                for m in re.finditer(re.escape(v), resp)
            )
            if not hits:
                L["add_failed"].append(b)
                continue
            srcs = []
            for pos, _ in hits[:2]:
                s = resp.rfind("\n", 0, pos) + 1
                e_ = resp.find("\n", pos)
                srcs.append(resp[s : (len(resp) if e_ < 0 else e_)].strip()[:300])
            merged.append(
                dict(
                    brand=b,
                    entity=b,
                    position=0,
                    visibility=1,
                    entity_type=etype,
                    source_text=list(dict.fromkeys(srcs)),
                    target_entity=False,
                    mention_count=len(hits),
                    canonicalised=note("manual_addition"),
                    **flags(b),
                )
            )
            have.add(b.lower())
            L["added"].append(b)
        for i, m in enumerate(
            merged, 1
        ):  # keep existing order, additions appended, then renumber
            m["position"] = i
        if L:
            changes.append((r["id"], oid, merged, dict(L), r["metadata"]))
            for k, v in L.items():
                totals[k] += len(v)
    print(f"rows touched {len(changes)} of {len(rows)} | {dict(totals)}")
    for _, oid, _, L, _ in changes:
        print(oid, " | ".join(f"{k}: {'; '.join(v)}" for k, v in L.items())[:500])
    if not a.go:
        print("dry run: pass --go to write")
        return
    if changes:
        bk = bdir / "scores_visibility_before_edit.json"
        if not bk.exists():
            bk.write_text(
                json.dumps(
                    fetch_all(sb, "scores_visibility", "*", batch_id=a.batch),
                    default=str,
                )
            )
            print("backup written:", bk)
        for rid, oid, merged, L, meta in changes:
            meta = dict(meta or {})
            meta["manual_edits"] = {
                "date": TODAY,
                "by": "Claude (user-approved decisions; stored-row edit instead of re-score)",
                **L,
                "backup": str(bk),
            }
            sb.table("scores_visibility").update(
                {"entities": merged, "metadata": meta}
            ).eq("id", rid).execute()
    print(f"WROTE {len(changes)} rows")


if __name__ == "__main__":
    main()
