from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aurum_quantum.aurum_seed import load_aurum_seed_build
from aurum_quantum.future_branch_qpu import (
    DEFAULT_HIGH_FAILURE_THRESHOLD,
    analyze_future_branch_field,
    build_branch_sampling_circuit,
    render_qpu_analysis_summary,
)
from aurum_quantum.ibm_runtime import (
    safe_usage,
    service,
    submit_sampling_circuit,
)


def _select_backend(runtime: Any, required_qubits: int) -> tuple[str, list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    for backend in runtime.backends():
        status = backend.status()
        if status.operational and backend.num_qubits >= required_qubits:
            candidates.append(
                {
                    "name": backend.name,
                    "pending_jobs": status.pending_jobs,
                    "qubits": backend.num_qubits,
                }
            )
    if not candidates:
        raise RuntimeError("No operational IBM QPU can run this branch circuit.")
    candidates.sort(key=lambda item: (item["pending_jobs"], item["name"]))
    return str(candidates[0]["name"]), candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch-state", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--experiments-dir", type=Path, required=True)
    parser.add_argument("--aurum-build-manifest", type=Path, required=True)
    parser.add_argument("--future-branch-seed", type=Path, required=True)
    parser.add_argument("--seed-source-commit", required=True)
    parser.add_argument("--high-failure-threshold", type=float, default=DEFAULT_HIGH_FAILURE_THRESHOLD)
    parser.add_argument("--backend")
    parser.add_argument("--shots", type=int, default=256)
    parser.add_argument("--confirm-qpu", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    aurum_seed = load_aurum_seed_build(
        args.aurum_build_manifest,
        args.future_branch_seed,
        authority_commit=args.seed_source_commit,
    )
    analysis = analyze_future_branch_field(
        branch_state_path=args.branch_state,
        calibration_path=args.calibration,
        experiments_dir=args.experiments_dir,
        aurum_seed=aurum_seed,
        high_failure_threshold=args.high_failure_threshold,
    )
    circuit = None
    reference = None
    if analysis["qpu_eligible"]:
        circuit, reference = build_branch_sampling_circuit(analysis)
    document: dict[str, Any] = {
        "schema": "aurum-future-branch-qpu-candidate-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "analysis": analysis,
        "circuit": reference,
        "submission": None,
    }

    if args.confirm_qpu:
        if circuit is None:
            raise RuntimeError("Future Branch field is below the QPU escalation gate.")
        runtime = service()
        usage_before = safe_usage(runtime)
        if args.backend:
            backend_name = args.backend
            candidates = None
        else:
            backend_name, candidates = _select_backend(runtime, circuit.num_qubits)
        submission = submit_sampling_circuit(
            runtime,
            backend_name=backend_name,
            circuit=circuit,
            shots=args.shots,
            confirmed=True,
            workload_id="aurum-future-branch-high-failure-v1",
            problem_class="ranked-machine-path-preparation",
            formulation="ranked-branch-amplitude-sampling",
        )
        document["submission"] = {
            **submission,
            "usage_before": usage_before,
            "usage_after_submit": safe_usage(runtime),
            "automatic_backend_candidates": candidates,
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        summary = render_qpu_analysis_summary(analysis)
        if document["submission"]:
            submission = document["submission"]
            summary += (
                "\n## QPU submission\n\n"
                f"- Backend: `{submission['envelope']['backend']}`\n"
                f"- Job: `{submission['job_id']}`\n"
                f"- Initial status: `{submission['initial_status']}`\n"
                f"- Shots: `{submission['envelope']['shots']}`\n"
            )
        else:
            summary += "\n- Hardware submission: not requested in this run\n"
        args.summary.write_text(summary, encoding="utf-8")
    print(
        json.dumps(
            {
                "qpu_eligible": analysis["qpu_eligible"],
                "strict_failure_rate": analysis["failure"]["strict_failure_rate"],
                "job_id": (document["submission"] or {}).get("job_id"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
