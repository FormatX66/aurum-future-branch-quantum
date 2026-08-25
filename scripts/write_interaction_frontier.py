from __future__ import annotations

import argparse
import json
from pathlib import Path

from aurum_quantum.interaction_frontier import (
    build_interaction_frontier,
    persist_interaction_frontier,
)


def _load(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize the Future Branch next-user interaction frontier."
    )
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--provider-evidence", action="append", default=[], type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--workflow-name", required=True)
    parser.add_argument("--workflow-url", required=True)
    parser.add_argument("--runner-commit", required=True)
    parser.add_argument("--router-outcome", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    providers = [_load(path) for path in args.provider_evidence if path.exists()]
    frontier = build_interaction_frontier(
        candidate=_load(args.candidate),
        provider_evidence=providers,
        run={
            "run_id": args.run_id,
            "run_attempt": args.run_attempt,
            "workflow": args.workflow_name,
            "workflow_url": args.workflow_url,
            "runner_commit": args.runner_commit,
            "router_outcome": args.router_outcome,
        },
    )
    latest_json, latest_md, history = persist_interaction_frontier(
        frontier, args.output_dir
    )
    print(latest_json)
    print(latest_md)
    print(history)


if __name__ == "__main__":
    main()
