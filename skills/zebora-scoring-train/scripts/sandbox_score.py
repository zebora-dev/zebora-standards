#!/usr/bin/env python3
"""Score a set of outputs with a DRAFT context, exactly as production would, and save nothing.

Uses the pipeline's own VisibilityV3Scorer and VisibilityV3QAScorer. The only difference from production is
that the active-context lookup returns the draft, and nothing is written: no scores_visibility row, no
entity-discovery capture, no change to visibility_prompt_contexts. Results go to runs/<set>__<draft>.json
and a labelling pack runs/<set>__<draft>.md. LLM calls are made (and traced in Langfuse as usual).

  --set FILE            sets/set-<k>.json from pick_set.py
  --draft DIR           drafts/<name>/ from draft_context.py
  --repeat N            score each output N times (default 1). With 2, the pack lists entities that differ
                        between runs: that is scorer noise, not a rule effect.
  --no-qa               skip the QA pass (faster; QA verdicts are only a hint anyway)
  --concurrency N       parallel outputs (default 5)

Run with the pipeline venv:  $PIPE/.venv/bin/python sandbox_score.py ...
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import PIPELINE, TODAY, load_set, read_draft, render_output  # noqa: E402


class DraftContextRepo:
    """Stands in for VisibilityPromptContextRepo: every lookup returns the draft."""

    def __init__(self, row: dict):
        self.row = row

    def get_active_context(self, *, brand_id, context_name: str = "default"):
        return self.row


def draft_row(draft: dict, name: str) -> dict:
    return {
        "id": None,
        "context_name": "default",
        "version": 0,
        "target_brand": draft.get("target_brand"),
        "visibility_brand_override": draft.get("visibility_brand_override"),
        "langfuse_prompt_name": "visibility-v3",
        "created_from_context_id": (draft.get("based_on") or {}).get("context_id"),
        "change_summary": f"sandbox draft {name}",
        "category_rules": draft["category_rules"],
        "brand_profile": draft["brand_profile"],
        "canonical_entity_mappings": draft.get("canonical_entity_mappings") or {},
        "brand_canonical_aliases": draft.get("brand_canonical_aliases") or {},
        "metadata": {**(draft.get("metadata") or {}), "sandbox_draft": name},
    }


def import_pipeline():
    os.chdir(PIPELINE)
    sys.path.insert(0, str(PIPELINE))
    from dotenv import load_dotenv

    load_dotenv(PIPELINE / ".env", override=False)
    from scorer.models.visibility_v3_qa_scorer import VisibilityV3QAScorer
    from scorer.models.visibility_v3_scorer import VisibilityV3Scorer

    return VisibilityV3Scorer, VisibilityV3QAScorer


async def score_all(st: dict, draft: dict, name: str, repeat: int, qa: bool, concurrency: int) -> list[dict]:
    VisibilityV3Scorer, VisibilityV3QAScorer = import_pipeline()
    scorer = VisibilityV3Scorer()
    scorer.visibility_context_repo = DraftContextRepo(draft_row(draft, name))
    scorer._load_and_set_visibility_v3_brand_config(st["batch_id"])
    if draft.get("target_brand"):
        scorer.target_brand = draft["target_brand"]
    primaries = [p["name"] if isinstance(p, dict) else p for p in draft.get("primaries") or []]
    if primaries:
        scorer.primary_competitors = primaries
    print(f"target {scorer.target_brand!r} | primaries {scorer.primary_competitors}")

    qa_scorer = VisibilityV3QAScorer() if qa else None
    client = scorer._create_async_client()
    gate = asyncio.Semaphore(concurrency)
    # One scorer instance holds per-call state (visibility_prompt_context); the draft is identical for every
    # call, so sharing it across concurrent calls is safe here.

    async def one(out: dict, run: int) -> dict:
        async with gate:
            res = {**out, "run": run, "context_label": f"draft {name}", "entities": [], "entity_qa": None}
            try:
                result = await scorer._assign_scores(
                    prompt_output=out["response"], batch_id=st["batch_id"], brand_id=st["brand_id"], client=client
                )
                res["entities"] = result.entities
                if qa_scorer:
                    verdict = await qa_scorer.evaluate(
                        target_brand=result.target_brand,
                        primary_competitors=result.primary_competitors,
                        response_text=out["response"],
                        extraction_output=result.entities,
                        category_rules=draft["category_rules"],
                        brand_profile=draft["brand_profile"],
                        batch_id=st["batch_id"],
                        brand_id=st["brand_id"],
                    )
                    res["entity_qa"] = verdict.model_dump()
            except Exception as e:  # report per output, keep the rest of the set going
                res["error"] = f"{type(e).__name__}: {e}"
            print(f"  {out['output_id']} run {run}: {len(res['entities'])} entities"
                  + (f" ERROR {res['error'][:120]}" if res.get("error") else ""))
            return res

    jobs = [one(o, run) for run in range(1, repeat + 1) for o in st["outputs"]]
    return await asyncio.gather(*jobs)


def variance_section(results: list[dict]) -> str:
    """Entities, or their type / role, that differ between runs of the same output: scorer noise."""
    by_out: dict[int, dict[int, dict]] = {}
    for r in results:
        by_out.setdefault(r["output_id"], {})[r["run"]] = {
            (e["brand"], e["entity"]): (e.get("entity_type"), e.get("competitor_type")) for e in r["entities"]
        }
    lines = ["# Run-to-run variance (same draft, same output)", ""]
    for oid, runs in by_out.items():
        keys = [set(v) for v in runs.values()]
        union, common = set().union(*keys), set.intersection(*keys)
        notes = [f"{b}/{e} only in some runs" for b, e in sorted(union - common)]
        for k in sorted(common):
            roles = {v[k] for v in runs.values()}
            if len(roles) > 1:
                notes.append(f"{k[0]}/{k[1]} type/role varies: " + " vs ".join(f"{t}/{c}" for t, c in sorted(roles, key=str)))
        if notes:
            lines.append(f"- {oid}: " + "; ".join(notes))
    if len(lines) == 2:
        lines.append("None: every run produced the same entities with the same types and roles.")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", required=True)
    ap.add_argument("--draft", required=True)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--no-qa", action="store_true")
    ap.add_argument("--concurrency", type=int, default=5)
    a = ap.parse_args()

    set_path, draft_dir = Path(a.set).resolve(), Path(a.draft).resolve()
    st, draft = load_set(set_path), read_draft(draft_dir)
    name = draft_dir.name
    results = asyncio.run(score_all(st, draft, name, a.repeat, not a.no_qa, a.concurrency))

    runs = set_path.parent.parent / "runs"
    runs.mkdir(exist_ok=True)
    stem = f"set-{st['set']}__{name}"
    payload = {"set": st["set"], "draft": name, "created": TODAY, "repeat": a.repeat,
               "batch_id": st["batch_id"], "brand_name": st["brand_name"], "results": results}
    (runs / f"{stem}.json").write_text(json.dumps(payload, indent=2, default=str))
    first = [r for r in results if r["run"] == 1]
    pack = f"# Set {st['set']} scored with draft {name} · {st['brand_name']}\n\n"
    pack += f"{len(first)} outputs, {sum(len(r['entities']) for r in first)} entities (run 1).\n\n"
    if a.repeat > 1:
        pack += variance_section(results) + "\n"
    pack += "\n".join(render_output(r) for r in first)
    (runs / f"{stem}.md").write_text(pack)
    errors = sum(1 for r in results if r.get("error"))
    print(f"\n{len(first)} outputs, {sum(len(r['entities']) for r in first)} entities, {errors} errors")
    print(f"run:  {runs / (stem + '.json')}\npack: {runs / (stem + '.md')}")


if __name__ == "__main__":
    main()
