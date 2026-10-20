#!/usr/bin/env python3
"""Phase 9b: make the target brand's own sites right before the release chain. Dry run unless --go.

1. Target website (and any primary competitor with no website, taken from its competitor record). Website enrichment looks the brand up by name, so a brand with sites in several
   countries can get the wrong one (Twinkl US got https://www.twinkl.co.uk/). This sets the website
   on the target's visibility_entity_brands / visibility_entities rows and the company record to the
   brand's PRIMARY url from brands.urls (the --url given at setup).
2. Owned domains. A cited URL counts as the brand's own only when its domain (or a subdomain) is in
   brands.urls. Lists the cited domains for the batch that contain the brand's name but are not owned
   (help centres, other-country sites: twinkl.zendesk.com, twinkl.com.br, twinkl.fr). With
   --add-owned, adds them to brands.urls (primary stays primary) and marks those url_scores rows
   owned. Review the list first: a domain containing the name is not always the brand's.

Run after Phase 9 (URL classification), before the release chain, which rebuilds the views.

    $PY_DB brand_sites.py --slug twinkl-us                     # report
    $PY_DB brand_sites.py --slug twinkl-us --go                # fix the target website
    $PY_DB brand_sites.py --slug twinkl-us --go --add-owned    # also add the listed domains as owned
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import db_engine  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--slug", required=True)
    ap.add_argument("--go", action="store_true")
    ap.add_argument(
        "--add-owned",
        action="store_true",
        help="with --go: add the listed brand-named domains to brands.urls and mark their citations owned",
    )
    a = ap.parse_args()
    from sqlalchemy import text

    e = db_engine()
    with e.connect() as c:
        b = (
            c.execute(
                text(
                    "SELECT id::text, name, coalesce(name_canonical, name) AS target, urls, company_entity, batch_id::text "
                    "FROM brands WHERE slug = :s"
                ),
                {"s": a.slug},
            )
            .mappings()
            .first()
        )
        if not b:
            sys.exit(f"no brand with slug {a.slug!r}")
        urls = b["urls"] or []
        primary = next((u["url"] for u in urls if u.get("primary")), None) or (urls[0]["url"] if urls else None)
        if not primary:
            sys.exit("brands.urls has no url: set the primary site first")
        dims = c.execute(
            text(
                "SELECT 'brand' AS kind, name, website FROM visibility_entity_brands WHERE brand_id = CAST(:b AS uuid) AND is_target_brand "
                "UNION ALL SELECT 'entity', name, website FROM visibility_entities WHERE brand_id = CAST(:b AS uuid) AND is_target_entity"
            ),
            {"b": b["id"]},
        ).all()
        token = re.sub(r"[^a-z0-9]", "", b["target"].lower())
        owned_hosts = {re.sub(r"^https?://", "", u["url"]).split("/", 1)[0].lower() for u in urls}
        cited = c.execute(
            text(
                "SELECT lower(domain) AS d, bool_or(coalesce(is_brand_owned, false)) AS owned, count(*) AS n "
                "FROM url_scores WHERE batch_id = CAST(:bt AS uuid) AND active GROUP BY 1"
            ),
            {"bt": b["batch_id"]},
        ).all()
    candidates = [
        r for r in cited if token and token in re.sub(r"[^a-z0-9]", "", r.d) and not r.owned
    ]

    print(f"brand {b['name']} (target {b['target']}) | primary site {primary}")
    wrong = [r for r in dims if (r.website or "").rstrip("/").lower() != primary.rstrip("/").lower()]
    for r in dims:
        print(f"  target {r.kind:6s} {r.name}: website {r.website or '(none)'}")
    print(f"  {len(wrong)} target row(s) to set to {primary}" if wrong else "  target website already right")
    print(f"owned domains in brands.urls: {sorted(owned_hosts)}")
    if candidates:
        print("cited domains containing the brand name but NOT owned (review before --add-owned):")
        for r in candidates:
            print(f"  {r.d}  ({r.n} citations)")
    else:
        print("no unowned cited domains contain the brand name")
    if not a.go:
        print("dry run: pass --go")
        return

    with e.begin() as c:
        # only rows that really differ: a trailing slash is not a different site, and the views copy
        # the website, so a cosmetic rewrite would show up only after the next refresh
        same = "rtrim(lower(coalesce(website, '')), '/') = rtrim(lower(:u), '/')"
        c.execute(
            text(f"UPDATE visibility_entity_brands SET website = :u WHERE brand_id = CAST(:b AS uuid) AND is_target_brand AND NOT {same}"),
            {"u": primary, "b": b["id"]},
        )
        c.execute(
            text(f"UPDATE visibility_entities SET website = :u WHERE brand_id = CAST(:b AS uuid) AND is_target_entity AND NOT {same}"),
            {"u": primary, "b": b["id"]},
        )
        if b["company_entity"]:
            c.execute(
                text("UPDATE competitors SET url = :u WHERE id = :i AND rtrim(lower(coalesce(url, '')), '/') <> rtrim(lower(:u), '/')"),
                {"u": primary, "i": b["company_entity"]},
            )
        print(f"target website: {len(wrong)} row(s) set to {primary}" if wrong else "target website already right")
        # primaries enrichment missed: take the url from their competitor record (Twinkl US, Lavazza)
        filled = c.execute(
            text(
                "UPDATE visibility_entity_brands v SET website = comp.url FROM competitors comp, competitors_primary cp "
                "WHERE v.brand_id = CAST(:b AS uuid) AND comp.brand_id = v.brand_id AND comp.name = v.name "
                "AND cp.competitor_id = comp.id AND cp.brand_id = v.brand_id AND coalesce(v.website, '') = '' AND comp.url IS NOT NULL "
                "RETURNING v.name"
            ),
            {"b": b["id"]},
        ).scalars().all()
        if filled:
            print(f"primary websites filled from competitor records: {', '.join(filled)}")
        if a.add_owned and candidates:
            new = urls + [{"url": f"https://{r.d}/", "primary": False} for r in candidates if r.d not in owned_hosts]
            c.execute(
                text("UPDATE brands SET urls = CAST(:u AS jsonb) WHERE id = CAST(:b AS uuid)"),
                {"u": json.dumps(new), "b": b["id"]},
            )
            n = c.execute(
                text(
                    "UPDATE url_scores SET is_brand_owned = true WHERE batch_id = CAST(:bt AS uuid) AND active "
                    "AND lower(domain) = ANY(:ds) AND NOT coalesce(is_brand_owned, false)"
                ),
                {"bt": b["batch_id"], "ds": [r.d for r in candidates]},
            ).rowcount
            print(f"added {len(candidates)} owned domain(s) to brands.urls; {n} citation(s) marked owned")
    print("now run the release chain (it rebuilds the views that copy the website and ownership)")


if __name__ == "__main__":
    main()
