from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from aurum_quantum.ibm_runtime import result_counts, safe_usage, service


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    runtime = service()
    checks = []
    for submission in manifest["submissions"]:
        if "job_id" not in submission:
            checks.append(submission)
            continue
        job = runtime.job(submission["job_id"])
        status = str(job.status())
        check = {
            "backend": submission["envelope"]["backend"],
            "job_id": submission["job_id"],
            "status": status,
        }
        if job.done() and "DONE" in status.upper():
            counts = result_counts(job)
            unexpected = sorted(set(counts) - {"00", "11"})
            check.update(
                {
                    "counts": counts,
                    "unexpected_outcomes": unexpected,
                    "bell_correlation_pass": not unexpected,
                }
            )
        checks.append(check)
        print(json.dumps(check, indent=2))

    status_document = {
        "schema_version": 1,
        "checked_at": datetime.now(UTC).isoformat(),
        "run_id": manifest["run_id"],
        "usage": safe_usage(runtime),
        "jobs": checks,
    }
    status_path = args.manifest.with_name("status.json")
    status_path.write_text(
        json.dumps(status_document, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Status: {status_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

