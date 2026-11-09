"""Shared helpers for the zebora-scoring-train scripts. Never prints secrets."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# zebora-standards/skills/zebora-scoring-train/scripts/_common.py -> four levels up is the workspace.
# resolve() follows the ~/.claude/skills symlink back into the checkout.
WORKSPACE = Path(os.environ.get("ZEBORA_WORKSPACE") or Path(__file__).resolve().parents[4])
TODAY = dt.date.today().isoformat()


def _default_pipeline() -> Path:
    for name in ("brand-score-pipeline", "brand_score_pipeline"):
        if (WORKSPACE / name).exists():
            return WORKSPACE / name
    return WORKSPACE / "brand-score-pipeline"


PIPELINE = Path(os.environ.get("ZEBORA_PIPELINE") or _default_pipeline())
OPS_VAULT = Path(os.environ.get("ZEBORA_OPS_VAULT") or WORKSPACE / "zebora-ops")

DRAFT_RULES = "category_rules.md"
DRAFT_PROFILE = "brand_profile.md"
DRAFT_META = "draft.json"


def db_engine():
    """SQLAlchemy engine on DATABASE_URL (env, else the pipeline's .env). Needs the pipeline venv."""
    from sqlalchemy import create_engine

    url = os.environ.get("DATABASE_URL")
    env_file = PIPELINE / ".env"
    if not url and env_file.exists():
        from dotenv import dotenv_values

        url = dotenv_values(env_file).get("DATABASE_URL")
    if not url:
        sys.exit(f"DATABASE_URL not found (env or {env_file})")
    return create_engine(url)


def resolve_batch(conn, batch_id: str) -> dict:
    from sqlalchemy import text

    row = conn.execute(
        text(
            """
            SELECT b.id::text AS batch_id, b.name AS batch_name, b.brand_id::text AS brand_id,
                   br.name AS brand_name, br.slug AS brand_slug, br.category AS brand_category
            FROM batches b JOIN brands br ON br.id = b.brand_id
            WHERE b.id = :batch_id
            """
        ),
        {"batch_id": batch_id},
    ).mappings().first()
    if not row:
        sys.exit(f"no batch {batch_id!r}")
    return dict(row)


def train_dir(brand_name: str) -> Path:
    """Default home for one training run: the ops vault, so the work survives the machine."""
    override = os.environ.get("ZEBORA_TRAIN_DIR")
    if override:
        return Path(override)
    return OPS_VAULT / "Clients" / brand_name / "Research" / "Scoring train" / TODAY


def clean_response(response_text: str) -> str:
    """Strip markdown images and (url) fragments so names are judged in prose, not in links."""
    response_text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", response_text)
    return re.sub(r"\((?:https?://|www\.)[^)]*\)", "", response_text)


def read_draft(draft_dir: Path) -> dict[str, Any]:
    meta = json.loads((draft_dir / DRAFT_META).read_text())
    meta["category_rules"] = (draft_dir / DRAFT_RULES).read_text()
    meta["brand_profile"] = (draft_dir / DRAFT_PROFILE).read_text()
    return meta


def write_draft(draft_dir: Path, rules: str, profile: str, meta: dict[str, Any]) -> None:
    draft_dir.mkdir(parents=True, exist_ok=True)
    (draft_dir / DRAFT_RULES).write_text(rules)
    (draft_dir / DRAFT_PROFILE).write_text(profile)
    (draft_dir / DRAFT_META).write_text(json.dumps(meta, indent=2, default=str) + "\n")


def load_set(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def render_output(r: dict[str, Any]) -> str:
    """One output as markdown: prompt, cleaned response, entity table (with QA verdicts if present)."""
    qa = r.get("entity_qa") or {}
    head = f"## Output {r['output_id']} · {r.get('llm_model')}"
    if r.get("context_label"):
        head += f" · {r['context_label']}"
    if qa:
        head += f" · QA {qa.get('overall_status')} {float(qa.get('overall_score') or 0):.2f}"
    lines = [
        head,
        "",
        f"**Prompt:** {r.get('prompt_text')}",
        "",
        "<details><summary>Response (images and link URLs stripped)</summary>",
        "",
        clean_response(r.get("response") or "").strip(),
        "",
        "</details>",
        "",
    ]
    if r.get("entities") is None:
        return "\n".join(lines) + "\n"
    lines += [
        "| # | brand | entity | type | competitor_type | pos | source_text | QA |",
        "|---|---|---|---|---|---|---|---|",
    ]
    reviews = {(rv.get("brand"), rv.get("entity")): rv for rv in qa.get("entity_reviews", [])}
    for i, e in enumerate(r["entities"], 1):
        rv = reviews.get((e.get("brand"), e.get("entity")), {})
        note = rv.get("status", "") + (f": {rv['issue']}" if rv.get("issue") else "")
        src = " / ".join(e.get("source_text") or [])[:160]
        cells = [
            str(i), e.get("brand"), e.get("entity"), e.get("entity_type"), e.get("competitor_type"),
            e.get("position"), src, note,
        ]
        lines.append("| " + " | ".join(str(c or "").replace("|", "/") for c in cells) + " |")
    for rv in reviews.values():
        if rv.get("status") == "missing":
            lines.append(f"| - | {rv.get('brand')} | {rv.get('entity')} | | | | | QA says missing: {rv.get('issue', '')} |")
    return "\n".join(lines) + "\n"
