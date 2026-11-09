#!/usr/bin/env python3
"""Build or copy a DRAFT context into drafts/<name>/ (category_rules.md, brand_profile.md, draft.json).
Read-only on the database: a draft only reaches visibility_prompt_contexts through promote_context.py.

  --list                    every brand's active context: category, market, version, size, last change.
                            Use it to find the nearest existing context to learn from.
  --from-active             start from this brand's own active context (retraining a live brand)
  --from-brand SLUG|NAME    start from another brand's active context (closest category); adapt it after
  --template CONFIG         render the onboarding base templates from a brand config JSON
                            (format: zebora-onboard-preview-brand/examples/twinkl_context.json)
  --copy FROM               copy drafts/FROM to drafts/--name (the next iteration), keeping the lineage

  --batch ID                the batch being trained (names the brand and the default folder)
  --name NAME               draft name (default d0)
  --dir DIR                 training folder (default: ops vault Clients/<Brand>/Research/Scoring train/<date>)

draft.json holds what the scorer needs besides the two texts: target_brand, visibility_brand_override,
primaries ([{name, url}], provisional until promoted), canonical_entity_mappings, brand_canonical_aliases,
metadata, based_on, notes.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import (  # noqa: E402
    DRAFT_META, TODAY, db_engine, read_draft, resolve_batch, train_dir, write_draft,
)

ONBOARD_TEMPLATES = Path(__file__).resolve().parents[2] / "zebora-onboard-preview-brand" / "templates"


def list_contexts(conn) -> None:
    from sqlalchemy import text

    rows = conn.execute(
        text(
            """
            SELECT br.name, br.slug, coalesce(v.metadata->>'category', br.category) AS category,
                   v.metadata->>'market' AS market, v.version, length(v.category_rules) AS rules_chars,
                   length(v.brand_profile) AS profile_chars, v.updated_at::date AS updated,
                   left(coalesce(v.change_summary, ''), 110) AS last_change
            FROM visibility_prompt_contexts v JOIN brands br ON br.id = v.brand_id
            WHERE v.active AND v.context_name = 'default'
            ORDER BY v.updated_at DESC
            """
        )
    ).mappings()
    for r in rows:
        print(f"{r['name']} ({r['slug']}) · {r['category'] or '-'} · {r['market'] or '-'} · v{r['version']} · "
              f"rules {r['rules_chars']} / profile {r['profile_chars']} chars · {r['updated']}\n"
              f"    {r['last_change']}")


def active_context(conn, brand_ref: str) -> dict:
    from sqlalchemy import text

    row = conn.execute(
        text(
            """
            SELECT v.*, br.name AS brand_name FROM visibility_prompt_contexts v JOIN brands br ON br.id = v.brand_id
            WHERE v.active AND v.context_name = 'default'
              AND (br.id::text = :ref OR br.slug = :ref OR lower(br.name) = lower(:ref))
            ORDER BY v.version DESC LIMIT 1
            """
        ),
        {"ref": brand_ref},
    ).mappings().first()
    if not row:
        sys.exit(f"no active default context for {brand_ref!r}")
    return dict(row)


def primaries_for(conn, brand_id: str) -> list[dict]:
    from sqlalchemy import text

    rows = conn.execute(
        text(
            """
            SELECT c.name, c.url FROM competitors_primary cp JOIN competitors c ON c.id = cp.competitor_id
            WHERE cp.brand_id = :b ORDER BY cp."order"
            """
        ),
        {"b": brand_id},
    ).mappings()
    return [dict(r) for r in rows]


def from_row(row: dict, primaries: list[dict], note: str) -> tuple[str, str, dict]:
    meta = {
        "target_brand": row["target_brand"],
        "visibility_brand_override": row.get("visibility_brand_override"),
        "primaries": primaries,
        "canonical_entity_mappings": row["canonical_entity_mappings"] or {},
        "brand_canonical_aliases": row["brand_canonical_aliases"] or {},
        "metadata": {k: v for k, v in (row["metadata"] or {}).items() if k not in ("notes", "vec_change_log")},
        "based_on": {"brand": row["brand_name"], "context_id": row["id"], "version": row["version"]},
        "notes": note,
    }
    return row["category_rules"], row["brand_profile"], meta


def from_template(cfg: dict) -> tuple[str, str, dict]:
    def render(name: str, values: dict[str, str]) -> str:
        out = (ONBOARD_TEMPLATES / name).read_text()
        for k, v in values.items():
            out = out.replace("{{" + k + "}}", v)
        if "{{" in out:
            sys.exit(f"unfilled placeholder in {name}: {out[out.index('{{'):][:40]}")
        return out

    collapse = "\n".join(
        f"  {', '.join(n) if isinstance(n, list) else n}  -> brand {b}, entity {b}" for n, b in cfg["collapse"]
    )
    rules = render("category_rules_base.md", {
        "CATEGORY_DESCRIPTION": cfg["category_description"],
        "ENTITY_TYPES": ", ".join(cfg["entity_types"]),
        "EXTRACTABLE": "\n".join(f"- {x}" for x in cfg["extractable"]),
        "EXCLUSIONS": "\n".join(f"- {x}" for x in cfg["exclusions"]),
        "STANDALONE_EXCLUSIONS": cfg["standalone_exclusions"],
        "COLLAPSE_LINES": collapse,
        "CANONICAL_NAMES": ", ".join(cfg["canonical_names"]),
        "EXAMPLES": "\n".join(cfg["examples"]),
    })
    profile = render("brand_profile_base.md", {
        "TARGET": cfg["target_brand"], "MARKET": cfg["market"], "ABOUT": cfg["about_target"],
        "TARGET_ALIASES": ", ".join(cfg["target_aliases"]),
    })
    meta = {
        "target_brand": cfg["target_brand"],
        "visibility_brand_override": None,
        "primaries": cfg["primary"],
        "canonical_entity_mappings": {},
        "brand_canonical_aliases": {n: cfg["target_brand"] for n in cfg["target_aliases"]},
        "metadata": {"market": cfg["market"], "category": cfg["category_label"],
                     "seed_source": "zebora-scoring-train template draft",
                     "entity_suffix_strips": ["ltd", "limited", "inc", "plc", "uk", "group"]},
        "based_on": {"template": "zebora-onboard-preview-brand/templates"},
        "notes": cfg.get("notes", ""),
    }
    return rules, profile, meta


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--list", action="store_true")
    src.add_argument("--from-active", action="store_true")
    src.add_argument("--from-brand")
    src.add_argument("--template")
    src.add_argument("--copy")
    ap.add_argument("--batch")
    ap.add_argument("--name", default="d0")
    ap.add_argument("--dir")
    a = ap.parse_args()

    from sqlalchemy import text

    with db_engine().connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        if a.list:
            list_contexts(conn)
            return
        if not a.batch:
            sys.exit("--batch is required")
        batch = resolve_batch(conn, a.batch)
        folder = Path(a.dir) if a.dir else train_dir(batch["brand_name"])
        target = folder / "drafts" / a.name
        if target.exists():
            sys.exit(f"{target} already exists; pick another --name")

        if a.copy:
            src_dir = folder / "drafts" / a.copy
            shutil.copytree(src_dir, target)
            meta = json.loads((target / DRAFT_META).read_text())
            meta["parent_draft"] = a.copy
            (target / DRAFT_META).write_text(json.dumps(meta, indent=2, default=str) + "\n")
            print(f"copied draft {a.copy} -> {a.name}: edit {target}")
            return
        if a.from_active or a.from_brand:
            row = active_context(conn, batch["brand_id"] if a.from_active else a.from_brand)
            same = str(row["brand_id"]) == batch["brand_id"]
            prims = primaries_for(conn, batch["brand_id"]) if same else []
            note = (f"{TODAY}: from {row['brand_name']} v{row['version']}"
                    + ("" if same else " — ANOTHER BRAND: replace target names, primaries, aliases, examples"))
            rules, profile, meta = from_row(row, prims, note)
            if not same:
                meta["target_brand"] = batch["brand_name"]
                meta["brand_canonical_aliases"] = {}
                meta["canonical_entity_mappings"] = {}
        else:
            rules, profile, meta = from_template(json.loads(Path(a.template).read_text()))

    write_draft(target, rules, profile, meta)
    draft = read_draft(target)
    print(f"draft {a.name}: target {draft['target_brand']!r}, {len(draft['primaries'] or [])} primaries, "
          f"rules {len(rules)} / profile {len(profile)} chars")
    print(f"edit: {target}")


if __name__ == "__main__":
    main()
