#!/usr/bin/env python3
"""Phase 2: one-off DataForSEO extraction for a preview batch (GPT + Google AI Overview), no workers, no webhook.

Submits to the Standard queue WITHOUT a pingback, then collects locally with reconcile_pending until nothing is pending.
Needs an UP-TO-DATE automated-extraction checkout (main) for the dataforseo modules, and DataForSEO credentials
(ZEBORA_DATAFORSEO_ENV, default <workspace>/prompt-extractor/.env; the automated-extraction .env copy is stale).
Needs the Supabase env too. --repo defaults to ZEBORA_EXTRACTION_REPO.
"""
from __future__ import annotations

import argparse
import collections
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import DATAFORSEO_ENV as DFS_ENV  # noqa: E402
from _common import EXTRACTION_REPO  # noqa: E402


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("batch_id")
    ap.add_argument(
        "--repo",
        default=EXTRACTION_REPO or os.environ.get("REPO"),
        help="up-to-date automated-extraction checkout (main)",
    )
    ap.add_argument("--region", default="uk")
    ap.add_argument("--max-minutes", type=int, default=40)
    a = ap.parse_args()
    if not a.repo or not Path(a.repo, "automated_extraction").is_dir():
        sys.exit(
            "--repo must point at an automated-extraction checkout containing automated_extraction/ (use main, not an old worktree)"
        )

    if DFS_ENV.exists():  # load credentials into this process only; never printed
        from dotenv import dotenv_values

        for k, v in dotenv_values(DFS_ENV).items():
            if k.upper().startswith("DATAFORSEO") and v:
                os.environ[k] = v
    os.environ.pop("WEBHOOK_BASE_URL", None)  # no pingback: we collect ourselves
    sys.path.insert(0, a.repo)
    from automated_extraction import dataforseo_async as dfa
    from automated_extraction.dataforseo_extraction import (
        run_dataforseo_ai_overview_submit,
    )

    t0 = time.time()
    print("submitting gpt ...", flush=True)
    r1 = dfa.run_dataforseo_llm_submit(
        a.batch_id, provider="gpt", region=a.region, measurements_filter="Visibility"
    )
    print(
        {
            k: r1.get(k)
            for k in ("status", "prompts", "submitted", "errors", "submit_cost_usd")
        },
        flush=True,
    )
    print("submitting google-ai-overview ...", flush=True)
    r2 = run_dataforseo_ai_overview_submit(
        a.batch_id, region=a.region, measurements_filter="Visibility"
    )
    print(
        {
            k: r2.get(k)
            for k in ("status", "prompts", "submitted", "errors", "submit_cost_usd")
        },
        flush=True,
    )

    sb = dfa._sb()
    while time.time() - t0 < a.max_minutes * 60:
        res = dfa.reconcile_pending(
            batch_id=a.batch_id, older_than_minutes=0, limit=500
        )
        rows = (
            sb.table("dataforseo_tasks")
            .select("provider,status")
            .eq("batch_id", a.batch_id)
            .execute()
            .data
        )
        c = collections.Counter((r["provider"], r["status"]) for r in rows)
        print(
            f"[{int(time.time() - t0)}s] sweep={ {k: res[k] for k in ('checked', 'ingested', 'failed', 'still_pending', 'errors') if k in res} } tasks={dict(c)}",
            flush=True,
        )
        if not any(r["status"] == "pending" for r in rows):
            break
        time.sleep(20)
    print("extraction finished", flush=True)


if __name__ == "__main__":
    main()
