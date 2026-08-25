from __future__ import annotations

import argparse
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aurum_quantum.aurum_seed import load_aurum_seed_build
from aurum_quantum.future_branch_qpu import evaluate_branch_counts


def _corrupted_seed_probe(
    manifest_path: Path,
    seed_path: Path,
    authority_commit: str,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact_name = sorted(manifest["artifacts"])[0]
    manifest["artifacts"][artifact_name]["sha256"] = "corrupted"
    observed_error = None
    with tempfile.TemporaryDirectory(prefix="aurum-seed-failure-") as root:
        corrupted_path = Path(root) / "corrupted-handoff.json"
        corrupted_path.write_text(json.dumps(manifest), encoding="utf-8")
        try:
            load_aurum_seed_build(
                corrupted_path,
                seed_path,
                authority_commit=authority_commit,
            )
        except ValueError as error:
            observed_error = str(error)
    return {
        "id": "corrupted-seed-artifact-hash",
        "injection": f"artifacts.{artifact_name}.sha256=corrupted",
        "expected": "seed loader refuses the manifest",
        "observed_error": observed_error,
        "passed": bool(
            observed_error
            and f"artifacts.{artifact_name}.sha256" in observed_error
        ),
        "physical_or_destructive_effect_executed": False,
    }


def _pruned_winner_probe(reference: dict[str, Any], shots: int) -> dict[str, Any]:
    pruned_state, pruned_item = next(
        (state, item)
        for state, item in reference["basis_map"].items()
        if not item["selected_for_execution"]
    )
    evaluation = evaluate_branch_counts({pruned_state: shots}, reference)
    passed = (
        evaluation["winning_path"] == pruned_item["path"]
        and not evaluation["execution_selection_agreement"]
        and not evaluation["learning"]["execution_gate_changed"]
        and evaluation["learning"]["recommendation"]
        == "review-model-qpu-divergence-before-execution"
    )
    return {
        "id": "pruned-branch-wins-all-shots",
        "injection": {pruned_state: shots},
        "expected": "review is required and the execution gate remains unchanged",
        "winning_path": evaluation["winning_path"],
        "execution_selection_agreement": evaluation[
            "execution_selection_agreement"
        ],
        "execution_gate_changed": evaluation["learning"]["execution_gate_changed"],
        "recommendation": evaluation["learning"]["recommendation"],
        "passed": passed,
        "physical_or_destructive_effect_executed": False,
    }


def _undeclared_winner_probe(reference: dict[str, Any], shots: int) -> dict[str, Any]:
    undeclared_state = "1" * (int(reference["qubits"]) + 1)
    evaluation = evaluate_branch_counts({undeclared_state: shots}, reference)
    passed = (
        not evaluation["winning_state_declared"]
        and evaluation["winning_path"] is None
        and not evaluation["winning_path_selected_for_execution"]
        and not evaluation["distribution_usable"]
        and not evaluation["learning"]["execution_gate_changed"]
        and evaluation["learning"]["recommendation"]
        == "review-model-qpu-divergence-before-execution"
    )
    return {
        "id": "undeclared-state-wins-all-shots",
        "injection": {undeclared_state: shots},
        "expected": "result is unusable and fails closed without a selected path",
        "winning_state_declared": evaluation["winning_state_declared"],
        "winning_path": evaluation["winning_path"],
        "winning_path_selected_for_execution": evaluation[
            "winning_path_selected_for_execution"
        ],
        "distribution_usable": evaluation["distribution_usable"],
        "execution_gate_changed": evaluation["learning"]["execution_gate_changed"],
        "recommendation": evaluation["learning"]["recommendation"],
        "passed": passed,
        "physical_or_destructive_effect_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--aurum-build-manifest", type=Path, required=True)
    parser.add_argument("--future-branch-seed", type=Path, required=True)
    parser.add_argument("--seed-source-commit", required=True)
    parser.add_argument("--shots", type=int, default=256)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    reference = candidate.get("circuit")
    if not isinstance(reference, dict):
        raise RuntimeError("Candidate does not contain a QPU circuit reference")

    probes = [
        _corrupted_seed_probe(
            args.aurum_build_manifest,
            args.future_branch_seed,
            args.seed_source_commit,
        ),
        _pruned_winner_probe(reference, args.shots),
        _undeclared_winner_probe(reference, args.shots),
    ]
    document = {
        "schema": "aurum-future-branch-failure-probes-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "seed_source_commit": args.seed_source_commit,
        "candidate": str(args.candidate.as_posix()),
        "hypothesis": (
            "Corrupt provenance or anomalous QPU winners must fail closed without "
            "changing the top-5% execution gate."
        ),
        "probes": probes,
        "passed": all(probe["passed"] for probe in probes),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(document, indent=2, sort_keys=True))
    return 0 if document["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
