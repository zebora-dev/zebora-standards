#!/usr/bin/env python3
"""Phase 3: primary competitors (competitors + competitors_primary) and visibility context v1, rendered from the
base templates plus a per-brand config JSON. Dry run unless --go. Refuses if a context already exists.

Config keys (see examples/twinkl_context.json):
  brand_slug, target_brand, market, category_label, category_description, entity_types (list),
  extractable (list of bullet lines), exclusions (list of bullet lines), standalone_exclusions (string),
  collapse (list of [surface names, canonical brand]), canonical_names (list), examples (list of lines),
  target_aliases (list), about_target (string), primary (list of {name, url}), notes (string)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import TODAY, brand_by_slug, supabase  # noqa: E402

TEMPLATES = Path(__file__).parent.parent / "templates"


def render(text: str, values: dict[str, str]) -> str:
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    assert "{{" not in text, "unfilled placeholder: " + text[text.index("{{") :][:40]
    return text


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--config", required=True)
    ap.add_argument("--go", action="store_true")
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    target = cfg["target_brand"]

    collapse = "\n".join(
        f"  {', '.join(names) if isinstance(names, list) else names}  -> brand {brand}, entity {brand}"
        for names, brand in cfg["collapse"]
    )
    rules = render(
        (TEMPLATES / "category_rules_base.md").read_text(),
        {
            "CATEGORY_DESCRIPTION": cfg["category_description"],
            "ENTITY_TYPES": ", ".join(cfg["entity_types"]),
            "EXTRACTABLE": "\n".join(f"- {x}" for x in cfg["extractable"]),
            "EXCLUSIONS": "\n".join(f"- {x}" for x in cfg["exclusions"]),
            "STANDALONE_EXCLUSIONS": cfg["standalone_exclusions"],
            "COLLAPSE_LINES": collapse,
            "CANONICAL_NAMES": ", ".join(cfg["canonical_names"]),
            "EXAMPLES": "\n".join(cfg["examples"]),
        },
    )
    profile = render(
        (TEMPLATES / "brand_profile_base.md").read_text(),
        {
            "TARGET": target,
            "MARKET": cfg["market"],
            "ABOUT": cfg["about_target"],
            "TARGET_ALIASES": ", ".join(cfg["target_aliases"]),
        },
    )
    primary = cfg["primary"]
    notes = (
        f"v1 ({TODAY}): built from the zebora-onboard-preview-brand base template. PROVISIONAL primary tier: "
        + ", ".join(p["name"] for p in primary)
        + ". "
        + cfg.get("notes", "")
    )
    print(
        f"target {target} | primaries {len(primary)} | rules {len(rules)} chars | profile {len(profile)} chars"
    )
    sb = supabase()
    brand = brand_by_slug(sb, cfg["brand_slug"])
    brand_id = brand["id"]
    if (
        sb.table("visibility_prompt_contexts")
        .select("id")
        .eq("brand_id", brand_id)
        .execute()
        .data
    ):
        print(
            "a context already exists for this brand: nothing to create (this script only writes v1)"
        )
        return
    if not a.go:
        print("dry run: pass --go to write")
        return
    for i, p in enumerate(primary, 1):
        dom = p["url"].split("//", 1)[-1].split("/", 1)[0]
        ex = (
            sb.table("competitors")
            .select("id")
            .eq("brand_id", brand_id)
            .eq("name", p["name"])
            .execute()
            .data
        )
        cid = (
            ex[0]["id"]
            if ex
            else sb.table("competitors")
            .insert(
                {
                    "name": p["name"],
                    "url": p["url"],
                    "domain": dom,
                    "brand_id": brand_id,
                }
            )
            .execute()
            .data[0]["id"]
        )
        sb.table("competitors_primary").upsert(
            {"brand_id": brand_id, "competitor_id": cid, "order": i},
            on_conflict="brand_id,competitor_id",
        ).execute()
        print(f"  primary #{i}: {p['name']} -> competitor {cid}")
    ctx = (
        sb.table("visibility_prompt_contexts")
        .insert(
            {
                "brand_id": brand_id,
                "context_name": "default",
                "target_brand": target,
                "version": 1,
                "active": True,
                "category_rules": rules,
                "brand_profile": profile,
                "canonical_entity_mappings": {},
                "brand_canonical_aliases": {n: target for n in cfg["target_aliases"]},
                "metadata": {
                    "notes": notes,
                    "market": cfg["market"],
                    "category": cfg["category_label"],
                    "seed_source": "onboard_preview_brand_template",
                    "entity_suffix_strips": [
                        "ltd",
                        "limited",
                        "inc",
                        "plc",
                        "uk",
                        "group",
                    ],
                },
                "change_summary": "v1: initial context from the preview-brand base template.",
            }
        )
        .execute()
        .data[0]
    )
    print("context v1 id", ctx["id"])


if __name__ == "__main__":
    main()
