from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from aurum_quantum.future_branch_qpu import evaluate_branch_counts
from aurum_quantum.ibm_runtime import result_counts, safe_usage, service


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    document = json.loads(args.manifest.read_text(encoding="utf-8"))
    submission = document.get("submission")
    if not submission or not submission.get("job_id"):
        raise SystemExit("Manifest does not contain a QPU submission.")

    runtime = service()
    job = runtime.job(submission["job_id"])
    status = str(job.status())
    check = {
        "schema": "aurum-future-branch-qpu-result-v1",
        "checked_at": datetime.now(UTC).isoformat(),
        "backend": submission["envelope"]["backend"],
        "job_id": submission["job_id"],
        "status": status,
        "usage": safe_usage(runtime),
    }
    if job.done() and "DONE" in status.upper():
        counts = result_counts(job)
        check["counts"] = counts
        check["evaluation"] = evaluate_branch_counts(counts, document["circuit"])

    status_path = args.manifest.with_name("qpu-status.json")
    status_path.write_text(json.dumps(check, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(check, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
