"""VEC Phase 4 — canonicalise one batch's stored entity names in place.

Rewrites `scores_visibility.entities[*].entity` / `.brand` for the batch's active visibility-v3
scores to the confirmed game's name and brand, so the reporting views match them directly.
No aliases written, no new games/brands, no schema change.

Match order per extracted name (first hit wins; a cleaned-title hit must be unique):
  exact     normalize_company_name(name) == a confirmed game's normalized_entity_key
  alias     an active alias key for a confirmed game
  title     same cleaned title (vec_titles.title_l1 / title_l2a) as exactly one confirmed game
Unmatched names are grouped by cleaned title and rewritten to the group's most frequent spelling
(and brand) so variants report as one item.

Every rewritten item keeps its original wording in `raw_entity` / `raw_brand` and gets
`canonicalised = {rule, entity_id, at, by}`. Re-runs are idempotent (they start from raw_*).

Usage (from the brand_score_pipeline repo root, so .env / DATABASE_URL resolve):
    poetry run python <skill>/scripts/canonicalise_batch.py --batch-id <uuid>                 # dry run
    poetry run python <skill>/scripts/canonicalise_batch.py --batch-id <uuid> --apply --refresh \
        --backup-dir ~/Documents/dev/branded-llm/db_backup/<folder>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vec_titles import norm_key, title_l1, title_l2a  # noqa: E402

from dotenv import load_dotenv  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

load_dotenv(Path.cwd() / ".env")  # run from the brand_score_pipeline repo root
BY ="zebora-scoring-vec canonicaliser"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--apply", action="store_true", help="write the rewritten entities (default: dry run)")
    ap.add_argument("--refresh", action="store_true", help="run refresh_entity_metrics_v2(batch) after applying")
    ap.add_argument("--backup-dir", help="where to save the pre-rewrite entities JSON (required with --apply)")
    args = ap.parse_args()
    if args.apply and not args.backup_dir:
        ap.error("--apply needs --backup-dir")

    eng = create_engine(os.environ["DATABASE_URL"])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with eng.connect() as c:
        brand_id = c.execute(text("SELECT brand_id FROM batches WHERE id = :b"), {"b": args.batch_id}).scalar()
        ents = {r.id: r for r in c.execute(text(
            "SELECT ve.id, ve.name, ve.normalized_entity_key, b.name AS brand, b.is_target_brand, ve.is_target_entity "
            "FROM visibility_entities ve JOIN visibility_entity_brands b ON b.id = ve.entity_brand_id AND b.active "
            "WHERE ve.brand_id = :br AND ve.active"), {"br": brand_id})}
        aliases = {r.alias_key: r.visibility_entity_id for r in c.execute(text(
            "SELECT a.alias_key, a.visibility_entity_id FROM visibility_entity_aliases a "
            "JOIN visibility_entities ve ON ve.id = a.visibility_entity_id AND ve.active AND ve.brand_id = a.brand_id "
            "WHERE a.brand_id = :br AND a.active"), {"br": brand_id}) if r.visibility_entity_id in ents}
        scores = c.execute(text(
            "SELECT sv.id, sv.entities FROM scores_visibility sv JOIN prompts_outputs po ON po.id = sv.output_id AND po.active "
            "WHERE sv.batch_id = :b AND sv.active AND sv.scorer_model = 'visibility-v3' AND jsonb_typeof(sv.entities) = 'array'"),
            {"b": args.batch_id}).fetchall()

    by_key = {}
    for e in ents.values():
        by_key.setdefault(e.normalized_entity_key, e.id)
    by_title = defaultdict(set)
    for e in ents.values():
        for k in {title_l1(e.name), title_l2a(e.name)}:
            if k:
                by_title[k].add(e.id)

    def match(name: str):
        k = norm_key(name)
        if k in by_key:
            return by_key[k], "exact"
        if k in aliases:
            return aliases[k], "alias"
        for t in (title_l1(name), title_l2a(name)):
            ids = by_title.get(t)
            if ids and len(ids) == 1:
                return next(iter(ids)), "title"
        return None, None

    rows = {s.id: [dict(x) if isinstance(x, dict) else x for x in s.entities] for s in scores}
    groups = defaultdict(Counter)
    plan = []
    for sid, items in rows.items():
        for i, it in enumerate(items):
            if not isinstance(it, dict):
                continue
            raw_e = it.get("raw_entity", it.get("entity") or "")
            raw_b = it.get("raw_brand", it.get("brand") or "")
            eid, rule = match(raw_e)
            plan.append((sid, i, raw_e, raw_b, eid, rule))
            if not eid and raw_e:
                groups[title_l2a(raw_e) or norm_key(raw_e)][(raw_e, raw_b)] += 1
    canon_group = {}
    for g, cnt in groups.items():
        names, brands = Counter(), Counter()
        for (e, b), n in cnt.items():
            names[e] += n
            if b:
                brands[b] += n
        canon_group[g] = (names.most_common(1)[0][0], brands.most_common(1)[0][0] if brands else "", len(names))

    stats, changed = Counter(), set()
    for sid, i, raw_e, raw_b, eid, rule in plan:
        it = rows[sid][i]
        before = (it.get("entity"), it.get("brand"), it.get("target_brand"), it.get("target_entity"))
        if eid:
            e = ents[eid]
            new = (e.name, e.brand, bool(e.is_target_brand), bool(e.is_target_entity))
            stats[f"matched:{rule}"] += 1
        else:
            name, brand, n = canon_group.get(title_l2a(raw_e) or norm_key(raw_e), (raw_e, raw_b, 1))
            new = (name, brand, it.get("target_brand"), it.get("target_entity"))
            rule = "grouped" if n > 1 else None
            stats["unmatched:grouped" if n > 1 else "unmatched:single"] += 1
        if new == before:
            continue
        it.setdefault("raw_entity", raw_e)
        it.setdefault("raw_brand", raw_b)
        it["entity"], it["brand"], it["target_brand"], it["target_entity"] = new
        it["canonicalised"] = {"rule": rule, "entity_id": eid, "at": now, "by": BY}
        stats["items_rewritten"] += 1
        changed.add(sid)

    matched = sum(v for k, v in stats.items() if k.startswith("matched:"))
    total = matched + stats["unmatched:grouped"] + stats["unmatched:single"]
    print(f"batch {args.batch_id} · brand {brand_id} · {len(rows)} scores · {total} extracted items")
    for k in sorted(stats):
        print(f"  {k:22} {stats[k]:6}")
    print(f"  matched share        {100 * matched / max(total, 1):5.1f}%   scores to update: {len(changed)}")
    if not args.apply:
        print("dry run — nothing written (use --apply --backup-dir … to write)")
        return

    bdir = Path(os.path.expanduser(args.backup_dir))
    bdir.mkdir(parents=True, exist_ok=True)
    bfile = bdir / f"scores_visibility_entities_{args.batch_id[:8]}_before_canonicalise_{now[:19].replace(':', '')}.json"
    bfile.write_text(json.dumps({str(s.id): s.entities for s in scores if s.id in changed}, default=str))
    with eng.begin() as c:
        c.execute(text("SET LOCAL lock_timeout = '10s'"))
        for sid in changed:
            c.execute(text("UPDATE scores_visibility SET entities = CAST(:e AS jsonb) WHERE id = :id AND active"),
                      {"e": json.dumps(rows[sid], ensure_ascii=False, default=str), "id": sid})
    print(f"applied: {len(changed)} scores updated · backup {bfile}")
    if args.refresh:
        with eng.begin() as c:
            c.execute(text("SET LOCAL statement_timeout = '12min'"))
            c.execute(text("SET LOCAL lock_timeout = '10s'"))
            c.execute(text("SELECT public.refresh_entity_metrics_v2(CAST(:b AS uuid))"), {"b": args.batch_id})
        with eng.connect() as c:
            pct = c.execute(text(
                "SELECT round(100.0 * sum(mention_total) FILTER (WHERE entity_id IS NOT NULL) / nullif(sum(mention_total), 0), 2) "
                "FROM mv_visibility_entity_output_facts_brand_entity WHERE batch_id = :b AND mentioned = 1"), {"b": args.batch_id}).scalar()
        print(f"refreshed · mentions matched to a known game: {pct}%")


if __name__ == "__main__":
    main()
