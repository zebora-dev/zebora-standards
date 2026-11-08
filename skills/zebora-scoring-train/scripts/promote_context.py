#!/usr/bin/env python3
"""Make a trained draft the brand's active visibility_prompt_contexts version. Dry run unless --go.

The draft folder is the whole truth: category_rules, brand_profile and draft.json (target_brand,
visibility_brand_override, canonical_entity_mappings, brand_canonical_aliases, metadata) all go into the new row.
  - If the brand has an active 'default' context: writes version+1 (created_from_context_id = that row),
    deactivates the old row, in one transaction. metadata keys the draft does not set (e.g. vec_change_log)
    are kept; --notes is prepended to metadata.notes ("vN (date): ... | <previous notes>").
  - If it has none: writes v1.
The dry run prints a unified diff of every changed field.

  --with-primaries   also make draft.json "primaries" ([{name, url}]) the brand's primary tier
                     (competitors + competitors_primary, in draft order). Primaries in the DB but not in the
                     draft are listed, never deleted.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import db_engine, read_draft, resolve_batch  # noqa: E402

FIELDS_TEXT = ("category_rules", "brand_profile")
FIELDS_JSON = ("canonical_entity_mappings", "brand_canonical_aliases")
FIELDS_PLAIN = ("target_brand", "visibility_brand_override")


def show_diff(field: str, old: str, new: str) -> None:
    diff = list(difflib.unified_diff(old.splitlines(), new.splitlines(), f"{field} (active)", f"{field} (draft)",
                                     lineterm=""))
    print("\n".join(diff) if diff else f"{field}: unchanged")


def as_json_text(value) -> str:
    return json.dumps(value or {}, indent=2, sort_keys=True)


def sync_primaries(conn, brand_id: str, primaries: list[dict], go: bool) -> None:
    from sqlalchemy import text

    current = conn.execute(
        text("""SELECT c.id, c.name FROM competitors_primary cp JOIN competitors c ON c.id = cp.competitor_id
                WHERE cp.brand_id = :b ORDER BY cp."order" """),
        {"b": brand_id},
    ).mappings().all()
    names = [p["name"] for p in primaries]
    print(f"\nprimaries  DB: {[r['name'] for r in current]}\n        draft: {names}")
    extra = [r["name"] for r in current if r["name"] not in names]
    if extra:
        print(f"  in the DB but not the draft (NOT removed; remove by hand if intended): {extra}")
    if not go:
        return
    for order, p in enumerate(primaries, 1):
        cid = conn.execute(text("SELECT id FROM competitors WHERE brand_id = :b AND name = :n"),
                           {"b": brand_id, "n": p["name"]}).scalar()
        if cid is None:
            domain = (p.get("url") or "").split("//", 1)[-1].split("/", 1)[0] or None
            cid = conn.execute(
                text("INSERT INTO competitors (name, url, domain, brand_id) VALUES (:n, :u, :d, :b) RETURNING id"),
                {"n": p["name"], "u": p.get("url"), "d": domain, "b": brand_id},
            ).scalar()
        conn.execute(
            text("""INSERT INTO competitors_primary (brand_id, competitor_id, "order") VALUES (:b, :c, :o)
                    ON CONFLICT (brand_id, competitor_id) DO UPDATE SET "order" = EXCLUDED."order" """),
            {"b": brand_id, "c": cid, "o": order},
        )
    print(f"  primaries written: {names}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", required=True)
    ap.add_argument("--draft", required=True)
    ap.add_argument("--summary", required=True, help='e.g. "v4: scoring-train sets 1-4 -- <decisions>"')
    ap.add_argument("--notes", required=True, help="training record, prepended to metadata.notes")
    ap.add_argument("--with-primaries", action="store_true")
    ap.add_argument("--go", action="store_true")
    a = ap.parse_args()

    from sqlalchemy import text

    draft = read_draft(Path(a.draft))
    with db_engine().begin() as conn:
        brand_id = resolve_batch(conn, a.batch)["brand_id"]
        active = conn.execute(
            text("""SELECT * FROM visibility_prompt_contexts
                    WHERE brand_id = :b AND context_name = 'default' AND active FOR UPDATE"""),
            {"b": brand_id},
        ).mappings().all()
        if len(active) > 1:
            sys.exit(f"{len(active)} active default contexts for this brand; fix that first")
        cur = dict(active[0]) if active else None
        top = conn.execute(
            text("SELECT coalesce(max(version), 0) FROM visibility_prompt_contexts "
                 "WHERE brand_id = :b AND context_name = 'default'"),
            {"b": brand_id},
        ).scalar()
        version = top + 1

        meta = {**((cur or {}).get("metadata") or {}), **(draft.get("metadata") or {})}
        prev = meta.get("notes") or ""
        meta["notes"] = f"v{version} ({dt.date.today().isoformat()}): {a.notes}" + (f" | {prev}" if prev else "")
        meta["trained_from_draft"] = {"draft": Path(a.draft).name, "based_on": draft.get("based_on")}

        print(f"brand {brand_id}: " + (f"active v{cur['version']} (id {cur['id']})" if cur else "no context yet")
              + f" -> v{version}\n")
        for f in FIELDS_TEXT:
            show_diff(f, (cur or {}).get(f) or "", draft[f])
        for f in FIELDS_JSON:
            show_diff(f, as_json_text((cur or {}).get(f)), as_json_text(draft.get(f)))
        for f in FIELDS_PLAIN:
            old, new = (cur or {}).get(f), draft.get(f)
            print(f"{f}: {old!r}" + ("" if old == new else f" -> {new!r}"))
        print(f"\nchange_summary: {a.summary}\nmetadata.notes starts: {meta['notes'][:300]}")
        if a.with_primaries:
            sync_primaries(conn, brand_id, draft.get("primaries") or [], a.go)

        if not a.go:
            print("\ndry run: nothing written. Re-run with --go after the user approves this exact diff.")
            conn.rollback()
            return
        if cur:
            conn.execute(text("UPDATE visibility_prompt_contexts SET active = false, updated_at = now() WHERE id = :id"),
                         {"id": cur["id"]})
        new_id = conn.execute(
            text(
                """
                INSERT INTO visibility_prompt_contexts
                  (brand_id, context_name, version, target_brand, visibility_brand_override,
                   langfuse_prompt_id, langfuse_prompt_name, langfuse_prompt_version,
                   category_rules, brand_profile, canonical_entity_mappings, brand_canonical_aliases,
                   metadata, change_summary, created_from_context_id, active)
                VALUES
                  (:brand_id, 'default', :version, :target_brand, :override,
                   :lf_id, :lf_name, :lf_version,
                   :rules, :profile, CAST(:mappings AS jsonb), CAST(:aliases AS jsonb),
                   CAST(:metadata AS jsonb), :summary, :parent, true)
                RETURNING id
                """
            ),
            {
                "brand_id": brand_id, "version": version, "target_brand": draft.get("target_brand"),
                "override": draft.get("visibility_brand_override"),
                "lf_id": (cur or {}).get("langfuse_prompt_id"),
                "lf_name": (cur or {}).get("langfuse_prompt_name") or "visibility-v3",
                "lf_version": (cur or {}).get("langfuse_prompt_version"),
                "rules": draft["category_rules"], "profile": draft["brand_profile"],
                "mappings": json.dumps(draft.get("canonical_entity_mappings") or {}),
                "aliases": json.dumps(draft.get("brand_canonical_aliases") or {}),
                "metadata": json.dumps(meta, default=str), "summary": a.summary,
                "parent": (cur or {}).get("id"),
            },
        ).scalar()
        print(f"\nwritten: v{version} id {new_id} active" + (f"; v{cur['version']} id {cur['id']} deactivated" if cur else ""))


if __name__ == "__main__":
    main()
