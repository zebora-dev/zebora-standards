#!/usr/bin/env python3
"""Pick the next set of outputs to train on and save it as set-<k>.json. Read-only on the database.

Works on unscored outputs too: training happens before the batch is scored for real.
Outputs already in any set-*.json in --dir are never picked again, so every set is fresh.

  --n N                 outputs in the set (default 10)
  --mode spread         round-robin across LLMs, one output per prompt before any prompt repeats (default)
  --mode long-lists     the outputs with the most numbered / bulleted lines (where the scorer drops items)
  --mode flagged        scored outputs whose stored QA status is review or fail (pool brands, worst first)
  --dir DIR             the training folder (default: the ops vault, Clients/<Brand>/Research/Scoring train/<date>)
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import TODAY, db_engine, render_output, resolve_batch, train_dir  # noqa: E402

LIST_LINE = re.compile(r"^\s*(?:\d+\\?[\.\)]|[-*•])\s+", re.MULTILINE)


def load_outputs(conn, batch_id: str) -> list[dict]:
    from sqlalchemy import text

    rows = conn.execute(
        text(
            """
            SELECT po.id AS output_id, po.llm_model, po.prompt_id::text AS prompt_id, p.text AS prompt_text,
                   po.response, sv.metadata->'entity_qa' AS entity_qa
            FROM prompts_outputs po
            LEFT JOIN prompts p ON p.id = po.prompt_id
            LEFT JOIN scores_visibility sv ON sv.output_id = po.id AND sv.active
                 AND sv.scorer_model = 'visibility-v3'
            WHERE po.batch_id = :batch_id AND po.active AND coalesce(p.active, true)
              AND coalesce(po.response, '') <> ''
            """
        ),
        {"batch_id": batch_id},
    ).mappings()
    return [dict(r) for r in rows]


def used_ids(folder: Path) -> tuple[set[int], int]:
    ids, count = set(), 0
    for f in sorted(folder.glob("sets/set-*.json")):
        ids |= {o["output_id"] for o in json.loads(f.read_text())["outputs"]}
        count += 1
    return ids, count


def pick_spread(rows: list[dict], n: int, rng: random.Random) -> list[dict]:
    rows = rows[:]
    rng.shuffle(rows)
    by_llm: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_llm[r["llm_model"] or "unknown"].append(r)
    for llm, bucket in by_llm.items():
        seen: set[str] = set()
        first = [r for r in bucket if not (r["prompt_id"] in seen or seen.add(r["prompt_id"]))]
        first_ids = {id(r) for r in first}
        by_llm[llm] = first + [r for r in bucket if id(r) not in first_ids]
    picked: list[dict] = []
    while len(picked) < n and any(by_llm.values()):
        for bucket in by_llm.values():
            if bucket and len(picked) < n:
                picked.append(bucket.pop(0))
    return picked


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", required=True)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--mode", choices=["spread", "long-lists", "flagged"], default="spread")
    ap.add_argument("--dir")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    from sqlalchemy import text

    with db_engine().connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        batch = resolve_batch(conn, a.batch)
        rows = load_outputs(conn, a.batch)

    folder = Path(a.dir) if a.dir else train_dir(batch["brand_name"])
    used, n_sets = used_ids(folder)
    pool = [r for r in rows if r["output_id"] not in used]
    if a.mode == "flagged":
        pool = [r for r in pool if (r["entity_qa"] or {}).get("overall_status") in ("review", "fail")]
        picked = sorted(pool, key=lambda r: float((r["entity_qa"] or {}).get("overall_score") or 0))[: a.n]
    elif a.mode == "long-lists":
        picked = sorted(pool, key=lambda r: -len(LIST_LINE.findall(r["response"])))[: a.n]
    else:
        picked = pick_spread(pool, a.n, random.Random(a.seed + n_sets))
    if not picked:
        sys.exit(f"nothing left to pick ({len(rows)} outputs, {len(used)} already used)")

    k = n_sets + 1
    (folder / "sets").mkdir(parents=True, exist_ok=True)
    payload = {
        "set": k, "mode": a.mode, "created": TODAY, **batch,
        "outputs": [{k2: r[k2] for k2 in ("output_id", "llm_model", "prompt_id", "prompt_text", "response")}
                    for r in picked],
    }
    path = folder / "sets" / f"set-{k}.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    md = folder / "sets" / f"set-{k}.md"
    md.write_text(
        f"# Set {k} · {batch['brand_name']} · {a.mode} · {len(picked)} outputs\n\n"
        + "\n".join(render_output({**r, "entities": None, "entity_qa": None}) for r in picked)
    )
    llms = defaultdict(int)
    for r in picked:
        llms[r["llm_model"]] += 1
    print(f"{batch['brand_name']}: set {k} = {len(picked)} outputs ({dict(llms)}); "
          f"{len(pool) - len(picked)} unused outputs left")
    print(f"set:  {path}\nread: {md}")


if __name__ == "__main__":
    main()
