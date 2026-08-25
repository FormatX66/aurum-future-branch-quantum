from __future__ import annotations

import argparse
import json
from pathlib import Path

from aurum_quantum.experiment_log import build_experiment_log, write_experiment_log


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--provider-evidence", action="append", type=Path, default=[])
    parser.add_argument("--expected-provider", action="append", default=[])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument("--workflow-name", required=True)
    parser.add_argument("--workflow-url", required=True)
    parser.add_argument("--runner-commit", required=True)
    parser.add_argument("--router-outcome", required=True)
    parser.add_argument("--resumed-from-run-id")
    parser.add_argument("--recovered-failure")
    parser.add_argument("--log-dir", type=Path, default=Path("experiment-logs"))
    args = parser.parse_args()

    candidate = None
    candidate_path = None
    if args.candidate and args.candidate.exists():
        candidate_path = args.candidate
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    provider_evidence = []
    for path in args.provider_evidence:
        if path.exists():
            provider_evidence.append(
                (json.loads(path.read_text(encoding="utf-8")), path)
            )
    record = build_experiment_log(
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        workflow_name=args.workflow_name,
        workflow_url=args.workflow_url,
        runner_commit=args.runner_commit,
        router_outcome=args.router_outcome,
        candidate=candidate,
        candidate_path=candidate_path,
        provider_evidence=provider_evidence,
        expected_providers=args.expected_provider,
        resumed_from_run_id=args.resumed_from_run_id,
        recovered_failure=args.recovered_failure,
    )
    path = write_experiment_log(record, args.log_dir)
    print(json.dumps({"experiment_log": str(path), "overall": record["outcomes"]["overall"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
