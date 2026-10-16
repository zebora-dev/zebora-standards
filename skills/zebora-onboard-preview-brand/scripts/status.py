#!/usr/bin/env python3
"""Read-only onboarding status for a preview brand: setup, scoring, QA, duplicates, dimensions, website coverage,
view row counts (compared with a reference brand) and headline numbers. Safe to run at any time.

  python scripts/status.py --slug twinkl        # also: --batch <id>, --like transunion
Use the pipeline venv (psycopg2): brand_score_pipeline/.venv/bin/python scripts/status.py --slug twinkl
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import db_engine  # noqa: E402

VIEWS = [
    "mv_visibility_entity_output_facts_brand_entity",
    "mv_entity_metrics_overall_llm_brand_v2",
    "mv_entity_metrics_overall_llm_brand_entity_v2",
    "mv_entity_metrics_tag_llm_brand_v2",
    "mv_entity_metrics_category_llm_brand_v2",
    "mv_entity_metrics_tag_by_llm_brand_entity_v2",
    "mv_entity_metrics_category_by_llm_brand_entity_v2",
    "mv_entity_metrics_overall_by_llm_brand_entity_v2",
    "mv_url_scores_enriched_v3",
]


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--slug")
    ap.add_argument("--batch")
    ap.add_argument("--like", default="transunion")
    a = ap.parse_args()
    if not (a.slug or a.batch):
        sys.exit("pass --slug or --batch")
    from sqlalchemy import text

    eng = db_engine()
    with eng.connect() as c:
        q = lambda sql, **p: c.execute(text(sql), p).fetchall()
        if a.batch:
            row = q(
                "select b.id, b.brand_id from batches b where b.id = cast(:b as uuid)",
                b=a.batch,
            )
        else:
            row = q(
                "select b.id, b.brand_id from batches b join brands br on br.id=b.brand_id where br.slug=:s order by b.date desc limit 1",
                s=a.slug,
            )
        if not row:
            sys.exit(
                "no batch found" + (" (brand may not exist yet)" if a.slug else "")
            )
        batch, brand = str(row[0][0]), str(row[0][1])
        b = q(
            "select name, slug, status, is_demo, visibility_pool_enabled, tenant_id from brands where id=cast(:i as uuid)",
            i=brand,
        )[0]
        print(
            f"brand {b[0]} ({b[1]}) status={b[2]} demo={b[3]} in_weekly_pool={b[4]} tenant={b[5]} | brand_id={brand} | batch_id={batch}"
        )
        ctxs = q(
            "select version, id, active from visibility_prompt_contexts where brand_id=cast(:i as uuid) order by version",
            i=brand,
        )
        print(
            "context versions:",
            ", ".join(f"v{v}(id {i}{', ACTIVE' if act else ''})" for v, i, act in ctxs)
            or "none",
        )
        print(
            "primary competitors:",
            [
                r[0]
                for r in q(
                    'select c.name from competitors_primary cp join competitors c on c.id=cp.competitor_id where cp.brand_id=cast(:i as uuid) order by cp."order"',
                    i=brand,
                )
            ],
        )
        print(
            "weightings: categories",
            q(
                "select count(*), round(sum(weighting)::numeric,6) from scores_weightings_categories where batch_id=cast(:b as uuid)",
                b=batch,
            )[0],
            "| tags",
            q(
                "select count(*) from scores_weightings_tags where batch_id=cast(:b as uuid)",
                b=batch,
            )[0][0],
            "| llm",
            q(
                "select provider_key, weight from llm_model_weightings where batch_id=cast(:b as uuid)",
                b=batch,
            ),
        )
        act = q(
            "select count(*) from prompts_outputs po join prompts p on p.id=po.prompt_id where po.batch_id=cast(:b as uuid) and po.active and p.active",
            b=batch,
        )[0][0]
        tot = q(
            "select count(*) from prompts_outputs where batch_id=cast(:b as uuid)",
            b=batch,
        )[0][0]
        sc = q(
            "select count(*), count(distinct output_id) from scores_visibility where batch_id=cast(:b as uuid) and active",
            b=batch,
        )[0]
        unscored = q(
            "select po.id from prompts_outputs po join prompts p on p.id=po.prompt_id where po.batch_id=cast(:b as uuid) and po.active and p.active "
            "and not exists (select 1 from scores_visibility s where s.batch_id=po.batch_id and s.active and s.output_id=po.id) order by po.id",
            b=batch,
        )
        dups = q(
            "select output_id, count(*) from scores_visibility where batch_id=cast(:b as uuid) and active group by 1 having count(*)>1",
            b=batch,
        )
        print(
            f"outputs: {act} active of {tot} | active score rows {sc[0]} over {sc[1]} outputs | unscored {[r[0] for r in unscored][:15] or 'none'} | DUPLICATE active rows {[tuple(r) for r in dups] or 'none'}"
        )
        print(
            "QA:",
            dict(
                q(
                    "select metadata->'entity_qa'->>'overall_status', count(*) from scores_visibility where batch_id=cast(:b as uuid) and active group by 1",
                    b=batch,
                )
            ),
        )
        print(
            "edited rows (manual_edits):",
            q(
                "select count(*) from scores_visibility where batch_id=cast(:b as uuid) and active and metadata ? 'manual_edits'",
                b=batch,
            )[0][0],
        )
        d = q(
            "select (select count(*) from visibility_entity_brands where brand_id=cast(:i as uuid)), (select count(*) from visibility_entity_brands where brand_id=cast(:i as uuid) and website is not null), "
            "(select count(*) from visibility_entities where brand_id=cast(:i as uuid)), (select count(*) from visibility_entity_aliases where brand_id=cast(:i as uuid))",
            i=brand,
        )[0]
        print(
            f"dimensions: brands {d[0]} (with website {d[1]}) | entities {d[2]} | aliases {d[3]}"
        )
        print(
            "url_scores active:",
            q(
                "select count(*) from url_scores where batch_id=cast(:b as uuid) and active",
                b=batch,
            )[0][0],
            "| classified domains:",
            q(
                "select count(distinct lower(us.domain)) filter (where exists (select 1 from url_classification uc where uc.type='domain' and lower(uc.url)=lower(us.domain))), count(distinct lower(us.domain)) from url_scores us where us.batch_id=cast(:b as uuid) and us.active and us.domain is not null",
                b=batch,
            )[0],
        )
        ref = q(
            "select b.id from batches b join brands br on br.id=b.brand_id where br.slug=:s order by b.date desc limit 1",
            s=a.like,
        )
        refb = str(ref[0][0]) if ref else None
        print(f"\nview rows for this batch vs reference ({a.like}):")
        for v in VIEWS:
            n = q(f"select count(*) from {v} where batch_id=cast(:b as uuid)", b=batch)[
                0
            ][0]
            r = (
                q(f"select count(*) from {v} where batch_id=cast(:b as uuid)", b=refb)[
                    0
                ][0]
                if refb
                else "-"
            )
            print(f"  {v:58s} {n:>6}  ({r})" + ("   <-- EMPTY" if n == 0 else ""))
        print("\nheadline (overall, weighted):")
        for r in q(
            "select entity_brand_name, target_brand, primary_competitor, round((visibility_weighted*100)::numeric,1), round(avg_rank_weighted::numeric,1), (website is not null) "
            "from mv_entity_metrics_overall_llm_brand_v2 where batch_id=cast(:b as uuid) order by visibility_weighted desc limit 8",
            b=batch,
        ):
            print(
                f"  {r[0]:34s} vis {r[3]:>5}%  rank {r[4]}  {'TARGET' if r[1] else ('primary' if r[2] else '')}  {'site' if r[5] else 'no-site'}"
            )


if __name__ == "__main__":
    main()
