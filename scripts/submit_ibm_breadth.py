from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from aurum_quantum.ibm_runtime import safe_usage, service, submit_bell_job


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", action="append", required=True)
    parser.add_argument("--shots", type=int, default=256)
    parser.add_argument("--confirm-qpu", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.confirm_qpu:
        raise SystemExit("Refusing QPU submission without --confirm-qpu")

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path("runs") / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    runtime = service()
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "purpose": "maximum-breadth minimal-cost QPU smoke test",
        "classical_reference": {"allowed_outcomes": ["00", "11"]},
        "usage_before": safe_usage(runtime),
        "submissions": [],
    }

    for backend_name in dict.fromkeys(args.backend):
        try:
            submission = submit_bell_job(
                runtime,
                backend_name=backend_name,
                shots=args.shots,
                confirmed=True,
            )
        except Exception as exc:  # Continue breadth run if one provider rejects.
            submission = {"backend": backend_name, "error": str(exc)}
        manifest["submissions"].append(submission)
        print(json.dumps(submission, indent=2))

    manifest["usage_after_submit"] = safe_usage(runtime)
    manifest_path = run_dir / "submission.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

