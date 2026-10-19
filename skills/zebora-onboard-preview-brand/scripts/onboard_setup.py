#!/usr/bin/env python3
"""Phase 1: create a preview brand, modelled field for field on a reference brand (default: transunion).

Creates: target competitors row -> brands row -> batch -> prompts -> category + tag weightings -> llm_model_weightings.
Dry run unless --go. Idempotent with --resume (re-uses the brand / competitor / batch / prompts that already exist).

Prompts file: JSON list of {"prompt", "category", "label"} or a CSV with headers
"Prompt", "Prompt Category", "Prompt Reporting Label".
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import TODAY, slugify, supabase  # noqa: E402

NOW = dt.datetime.now(dt.timezone.utc).isoformat()


def load_prompts(path: str) -> list[tuple[str, str, str]]:
    p = Path(path)
    if p.suffix.lower() == ".json":
        rows = [
            (r["prompt"].strip(), r["category"].strip(), r["label"].strip())
            for r in json.loads(p.read_text())
        ]
    else:
        with p.open(newline="") as f:
            rows = [
                (
                    r["Prompt"].strip(),
                    r["Prompt Category"].strip(),
                    r["Prompt Reporting Label"].strip(),
                )
                for r in csv.DictReader(f)
            ]
    assert rows, "no prompts"
    assert len({r[0] for r in rows}) == len(rows), "duplicate prompt text"
    return rows


def weights(rows):
    cats = list(dict.fromkeys(c for _, c, _ in rows))
    cat_w = [round(1 / len(cats), 6)] * len(cats)
    cat_w[-1] = round(
        1 - sum(cat_w[:-1]), 6
    )  # last absorbs rounding so the sum is exactly 1.0
    tags = []
    for c in cats:
        labels = list(dict.fromkeys(l for _, cc, l in rows if cc == c))
        base = round(1 / len(labels), 6)
        for i, l in enumerate(labels):
            tags.append(
                (
                    c,
                    l,
                    (
                        base
                        if i < len(labels) - 1
                        else round(1 - base * (len(labels) - 1), 6)
                    ),
                )
            )
    return cats, cat_w, tags


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--name", required=True)
    ap.add_argument(
        "--url", required=True, help="primary site, e.g. https://www.twinkl.co.uk"
    )
    ap.add_argument(
        "--target-name",
        help="the brand as the answers name it (default: --name without a trailing market tag, "
        "so 'Twinkl (US)' -> 'Twinkl'). Used for name_canonical, config.target_brand and the "
        "company record, which the scorer, corrections and dimension seeding match on.",
    )
    ap.add_argument("--slug")
    ap.add_argument(
        "--category",
        required=True,
        help="short category label, e.g. 'Teaching resources'",
    )
    ap.add_argument("--market", default="UK")
    ap.add_argument("--region", default="uk", help="batch region: uk | us")
    ap.add_argument("--localization", default="UK English")
    ap.add_argument(
        "--system-intro",
        required=True,
        help="e.g. 'response about UK teaching resources for primary schools.'",
    )
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--sheet-id", default="")
    ap.add_argument(
        "--tenant-id",
        type=int,
        default=1,
        help="1 = Zebora/app (TransUnion, Twinkl). Smart Energy GB used a different tenant: confirm.",
    )
    ap.add_argument(
        "--like",
        default="transunion",
        help="reference brand slug to copy batch creator from",
    )
    ap.add_argument("--batch-name", help="default '<Mon> - <YYYY>'")
    ap.add_argument("--llm-weights", default="gpt=0.6,google=0.4")
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    target_name = a.target_name or re.sub(r"\s*\([A-Z]{2,3}\)$", "", a.name).strip()

    slug = a.slug or slugify(a.name)
    rows = load_prompts(a.prompts)
    cats, cat_w, tag_rows = weights(rows)
    assert abs(sum(cat_w) - 1.0) < 1e-9, sum(cat_w)
    today = dt.date.today()
    batch_name = a.batch_name or today.strftime("%b - %Y")
    report_month = (
        (today.replace(day=1) + dt.timedelta(days=32)).replace(day=1).isoformat()
    )

    print(
        f"brand {a.name} (target name {target_name}) slug={slug} tenant={a.tenant_id} region={a.region}"
    )
    print(
        f"prompts {len(rows)} | categories {len(cats)} | tag weightings {len(tag_rows)} | category weights sum {sum(cat_w):.6f}"
    )
    for c in cats:
        n = [r for r in rows if r[1] == c]
        print(f"   {c}: {len(n)} prompts, {len({r[2] for r in n})} labels")
    sb = supabase()
    existing = sb.table("brands").select("*").eq("slug", slug).execute().data
    if existing and not a.resume:
        sys.exit(
            f"brand {slug!r} already exists. Pass --resume to continue the remaining steps"
        )
    ref = sb.table("brands").select("id").eq("slug", a.like).execute().data
    ref_batch = (
        sb.table("batches")
        .select("created_by,llm_models")
        .eq("brand_id", ref[0]["id"])
        .limit(1)
        .execute()
        .data
        if ref
        else []
    )
    created_by = ref_batch[0]["created_by"] if ref_batch else None
    if not a.go:
        print("dry run: pass --go to write")
        return

    brand = {
        "name": a.name,
        "description": f"{a.name} - preview brand ({a.category}, {a.market})",
        "logo_url": f"https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url={a.url}&size=256",
        "is_active": True,
        "category": a.category,
        "urls": [{"url": a.url, "primary": True}],
        "config": {
            "market": a.market,
            "release": {
                "engagement": {
                    "note": "Preview, not an ongoing brief.",
                    "status": "one_off",
                    "capture": "none",
                    "release": "dashboard_only",
                },
                "updated_at": NOW,
                "updated_by": f"{os.getenv('USER', 'unknown')} (via Claude)",
            },
            "category": a.category,
            "brand_values": [{"title": "-", "description": "-"}],
            "localization": a.localization,
            "system_intro": a.system_intro,
            "target_brand": target_name,
            "hideSubBrandView": True,
            "dashboardLimitedView": False,
        },
        "is_demo": True,
        "status": "onboarding",
        "name_canonical": target_name,
        "slug": slug,
        "reporting_type": "brand",
        "reporting_version": "v2",
        "visibility_pool_enabled": False,
        "tenant_id": a.tenant_id,
    }
    b = existing[0] if existing else sb.table("brands").insert(brand).execute().data[0]
    brand_id = b["id"]
    print("brand", brand_id, "(existing)" if existing else "(created)")

    domain = a.url.split("//", 1)[-1].split("/", 1)[0]
    comp = (
        sb.table("competitors")
        .select("*")
        .eq("brand_id", brand_id)
        .eq("name", target_name)
        .execute()
        .data
        or [None]
    )[0]
    if not comp:  # never insert normalized_name: it is a generated column
        comp = (
            sb.table("competitors")
            .insert(
                {"name": target_name, "url": a.url, "domain": domain, "brand_id": brand_id}
            )
            .execute()
            .data[0]
        )
    sb.table("brands").update({"company_entity": comp["id"]}).eq(
        "id", brand_id
    ).execute()
    print("company_entity", comp["id"])

    batch = (
        sb.table("batches").select("*").eq("brand_id", brand_id).execute().data
        or [None]
    )[0] or sb.table("batches").insert(
        {
            "name": batch_name,
            "batch_type": "prompt_execution",
            "status": "paused",
            "config": {
                "brand": brand_id,
                "brand_id": brand_id,
                "report_date": today.strftime("%B"),
            },
            "started_at": NOW,
            "created_by": created_by,
            "brand_id": brand_id,
            "is_active": True,
            "date": today.replace(day=1).isoformat() + "T00:00:00",
            "multi_llm": True,
            "dashboard_version": "v2",
            "dashboard_type": "preview",
            "llm_models": {
                "gpt": True,
                "claude": False,
                "gemini": False,
                "perplexity": False,
                "required_models": ["gpt-5-5"],
                "google-ai-overview": True,
            },
            "reporting_version": "v2",
            "region": a.region,
            "report_month": report_month,
        }
    ).execute().data[
        0
    ]
    batch_id = batch["id"]
    sb.table("brands").update(
        {"batch_id": batch_id, "visibility_pool_batch_id": batch_id}
    ).eq("id", brand_id).execute()
    print("batch", batch_id)

    if (
        not sb.table("prompts")
        .select("id")
        .eq("brand_id", brand_id)
        .limit(1)
        .execute()
        .data
    ):
        sb.table("prompts").insert(
            [
                {
                    "text": t,
                    "category": c,
                    "tags": [l],
                    "measurements": ["Visibility"],
                    "approved": True,
                    "active": True,
                    "flag": False,
                    "brand_id": brand_id,
                    "metadata": {
                        "source": "google_sheets_import",
                        "reporting_label": l,
                        "source_category": c,
                        "scoring_category": "Visibility",
                        "source_spreadsheet_id": a.sheet_id,
                        "variable_weighting": "33.3",
                    },
                }
                for t, c, l in rows
            ]
        ).execute()
    print("prompts", len(rows))

    if (
        sb.table("scores_weightings_categories")
        .select("id")
        .eq("batch_id", batch_id)
        .limit(1)
        .execute()
        .data
    ):
        sys.exit(
            "weightings already exist for this batch: stopping before duplicating them"
        )
    sb.table("scores_weightings_categories").insert(
        [
            {
                "brand_id": brand_id,
                "batch_id": batch_id,
                "category": c,
                "weighting": w,
                "source": f"Equal weights across categories ({TODAY})",
                "measurement_type": "visibility",
            }
            for c, w in zip(cats, cat_w)
        ]
    ).execute()
    sb.table("scores_weightings_tags").insert(
        [
            {
                "brand_id": brand_id,
                "batch_id": batch_id,
                "category": c,
                "tag": l,
                "weighting": w,
                "source": f"Equal weights across nodes ({TODAY})",
            }
            for c, l, w in tag_rows
        ]
    ).execute()
    sb.table("llm_model_weightings").insert(
        [
            {"batch_id": batch_id, "provider_key": k, "weight": float(v)}
            for k, v in (kv.split("=") for kv in a.llm_weights.split(","))
        ]
    ).execute()
    print(f"DONE brand_id={brand_id} batch_id={batch_id} company_entity={comp['id']}")


if __name__ == "__main__":
    main()
