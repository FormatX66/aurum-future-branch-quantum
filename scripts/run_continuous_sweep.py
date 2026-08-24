from __future__ import annotations

import argparse
import json
from pathlib import Path

from aurum_quantum.aurum_seed import load_aurum_seed_build
from aurum_quantum.continuous_sweep import (
    CASES_PER_PROVIDER_RUN,
    SUPPORTED_FLOW_PROVIDERS,
    render_sweep_summary,
    run_continuous_sweep,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("provider", choices=SUPPORTED_FLOW_PROVIDERS)
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument("--cases-per-run", type=int, default=CASES_PER_PROVIDER_RUN)
    parser.add_argument("--aurum-build-manifest", type=Path, required=True)
    parser.add_argument("--future-branch-seed", type=Path, required=True)
    parser.add_argument("--seed-source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    aurum_seed = load_aurum_seed_build(
        args.aurum_build_manifest,
        args.future_branch_seed,
        authority_commit=args.seed_source_commit,
    )
    result = run_continuous_sweep(
        args.provider,
        cycle=args.cycle,
        aurum_seed=aurum_seed,
        cases_per_run=args.cases_per_run,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(render_sweep_summary(result), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("provider", "cycle", "passed")}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
