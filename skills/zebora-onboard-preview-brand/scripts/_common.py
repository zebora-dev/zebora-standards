"""Shared helpers for the zebora-onboard-preview-brand scripts. Never prints secrets."""

from __future__ import annotations

import datetime as dt
import os
import re
import sys
from pathlib import Path

# Where the sibling checkouts live. By default the folder that holds zebora-standards
# (this file is zebora-standards/skills/<skill>/scripts/_common.py, so four levels up; resolve()
# follows the ~/.claude/skills symlink). Each path can be overridden with an environment variable.
WORKSPACE = Path(os.environ.get("ZEBORA_WORKSPACE") or Path(__file__).resolve().parents[4])
PIPELINE = Path(os.environ.get("ZEBORA_PIPELINE") or WORKSPACE / "brand_score_pipeline")
PIPELINE_ENV = PIPELINE / ".env"
BACKUP_ROOT = Path(os.environ.get("ZEBORA_BACKUP_ROOT") or WORKSPACE / "db_backup")
# DataForSEO credentials (prompt-extractor's .env; the automated-extraction copy is stale).
DATAFORSEO_ENV = Path(
    os.environ.get("ZEBORA_DATAFORSEO_ENV") or WORKSPACE / "prompt-extractor" / ".env"
)
# The automated-extraction (zebora-dev/prompt-extractor) checkout on main: DataForSEO code and the
# Supabase service key. No default: it lives outside the workspace on some machines.
EXTRACTION_REPO = os.environ.get("ZEBORA_EXTRACTION_REPO")
TODAY = dt.date.today().isoformat()


def load_supabase_env() -> None:
    """Load the BRANDSIGHT_SUPABASE_* keys from the extraction checkout's .env into this process
    when they are not already set. Values are never printed."""
    if os.environ.get("BRANDSIGHT_SUPABASE_SERVICE_KEY") or not EXTRACTION_REPO:
        return
    env = Path(EXTRACTION_REPO) / ".env"
    if env.exists():
        from dotenv import dotenv_values

        for k, v in dotenv_values(env).items():
            if k.startswith("BRANDSIGHT_SUPABASE_") and v and not os.environ.get(k):
                os.environ[k] = v


def supabase():
    """supabase-py client using the service key (env, else ZEBORA_EXTRACTION_REPO/.env)."""
    from supabase import create_client

    load_supabase_env()
    url, key = os.environ.get("BRANDSIGHT_SUPABASE_URL"), os.environ.get(
        "BRANDSIGHT_SUPABASE_SERVICE_KEY"
    )
    if not url or not key:
        sys.exit(
            "BRANDSIGHT_SUPABASE_URL / BRANDSIGHT_SUPABASE_SERVICE_KEY not set. "
            "Set ZEBORA_EXTRACTION_REPO to the automated-extraction checkout, or "
            "run: set -a; source <automated-extraction>/.env; set +a"
        )
    return create_client(url, key)


def db_engine():
    """SQLAlchemy engine on DATABASE_URL (env, else brand_score_pipeline/.env). Needs psycopg2 (use the pipeline venv)."""
    from sqlalchemy import create_engine

    url = os.environ.get("DATABASE_URL")
    if not url and PIPELINE_ENV.exists():
        from dotenv import dotenv_values

        url = dotenv_values(PIPELINE_ENV).get("DATABASE_URL")
    if not url:
        sys.exit(f"DATABASE_URL not found (env or {PIPELINE_ENV})")
    return create_engine(url)


def brand_by_slug(sb, slug: str) -> dict:
    rows = sb.table("brands").select("*").eq("slug", slug).execute().data
    if not rows:
        sys.exit(f"no brand with slug {slug!r}")
    return rows[0]


def batch_for_brand(sb, brand_id: str) -> dict:
    rows = sb.table("batches").select("*").eq("brand_id", brand_id).execute().data
    if not rows:
        sys.exit("brand has no batch yet")
    return rows[0]


def normalize_key(sb, name: str, cache: dict) -> str:
    """Key via the SQL function public.normalize_company_name (never compute these by hand)."""
    if name not in cache:
        cache[name] = sb.rpc("normalize_company_name", {"name": name}).execute().data
    return cache[name]


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def clean_response(text: str) -> str:
    """Strip markdown images and (url) fragments so names are only matched in prose."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    return re.sub(r"\((?:https?://|www\.)[^)]*\)", "", text)


def backup_dir(slug: str) -> Path:
    d = BACKUP_ROOT / f"{slug}_{TODAY}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def fetch_all(sb, table: str, select: str, **eq):
    """Page through a table (PostgREST caps at 1000 rows)."""
    out, off = [], 0
    while True:
        q = sb.table(table).select(select)
        for k, v in eq.items():
            q = q.eq(k, v)
        page = q.range(off, off + 999).execute().data
        out += page
        if len(page) < 1000:
            return out
        off += 1000
