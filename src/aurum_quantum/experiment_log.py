from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


LOG_SCHEMA = "aurum-future-branch-experiment-log-v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _provider_result(document: dict[str, Any], path: Path) -> dict[str, Any]:
    failed_cases = [
        item["case"]["case_id"]
        for item in document.get("results", [])
        if not item.get("evaluation", {}).get("passed", False)
    ]
    return {
        "provider": str(document.get("provider", "unknown")),
        "passed": bool(document.get("passed", False)),
        "cycle": document.get("cycle"),
        "effective_cycle": document.get("effective_cycle"),
        "cases_executed": len(document.get("results", [])),
        "failed_cases": failed_cases,
        "evidence_sha256": _sha256(path),
    }


def build_experiment_log(
    *,
    run_id: str,
    run_attempt: int,
    workflow_name: str,
    workflow_url: str,
    runner_commit: str,
    router_outcome: str,
    candidate: dict[str, Any] | None,
    candidate_path: Path | None,
    provider_evidence: Iterable[tuple[dict[str, Any], Path]],
    expected_providers: Iterable[str],
    resumed_from_run_id: str | None = None,
    recovered_failure: str | None = None,
) -> dict[str, Any]:
    providers = sorted(
        (_provider_result(document, path) for document, path in provider_evidence),
        key=lambda item: item["provider"],
    )
    expected = sorted(set(expected_providers))
    observed = {item["provider"] for item in providers}
    missing = sorted(set(expected) - observed)
    failures: list[dict[str, Any]] = []
    if router_outcome != "success" or candidate is None:
        failures.append(
            {
                "kind": "router",
                "status": "failed",
                "detail": "Future Branch router did not produce candidate evidence.",
            }
        )
    for provider in providers:
        if not provider["passed"]:
            failures.append(
                {
                    "kind": "provider-sweep",
                    "status": "failed",
                    "provider": provider["provider"],
                    "failed_cases": provider["failed_cases"],
                }
            )
    for provider in missing:
        failures.append(
            {
                "kind": "provider-evidence",
                "status": "missing",
                "provider": provider,
            }
        )
    if resumed_from_run_id and recovered_failure:
        failures.append(
            {
                "kind": "recovered-predecessor",
                "status": "recovered",
                "run_id": resumed_from_run_id,
                "detail": recovered_failure,
            }
        )

    analysis = (candidate or {}).get("analysis", {})
    selection = analysis.get("selection", {})
    selected = analysis.get("selected_machine_paths", [])
    pruned = analysis.get("pruned_machine_paths", [])
    leading = selected[0] if selected else None
    failure_analysis = analysis.get("failure", {})
    provider_pass_count = sum(1 for provider in providers if provider["passed"])
    provider_confidence = provider_pass_count / len(expected) if expected else 0.0
    expected_selected = (
        max(1, math.ceil(int(selection.get("population_size", 0)) * float(selection.get("top_probability_fraction", 0))))
        if selection
        else 0
    )

    hypotheses: list[dict[str, Any]] = []
    if leading:
        hypotheses.append(
            {
                "id": "top-five-percent-probability-selection",
                "hypothesis": "The live highest-probability Future Branch path is the only path retained from the top 5% field.",
                "probability": float(leading["probability"]),
                "confidence_basis": "Canonical Future Branch model probability derived from the live upstream rank.",
                "evidence": [
                    f"selected_count={selection.get('selected_count')}",
                    f"population_size={selection.get('population_size')}",
                    f"selected_path={leading['name']}",
                ],
                "outcome": (
                    "supported"
                    if selection.get("selected_count") == expected_selected
                    else "refuted"
                ),
            }
        )
    if failure_analysis:
        hypotheses.append(
            {
                "id": "high-failure-routing-gate",
                "hypothesis": "The calibrated partial-or-miss rate remains high enough to justify branch-ranking preparation.",
                "probability": float(failure_analysis["strict_failure_rate"]),
                "confidence_basis": "Observed partial plus miss predictions divided by calibration events.",
                "evidence": [
                    f"events={failure_analysis['events']}",
                    f"partial={failure_analysis['partial']}",
                    f"miss={failure_analysis['miss']}",
                    f"threshold={failure_analysis['high_failure_threshold']}",
                ],
                "outcome": "supported" if analysis.get("qpu_eligible") else "refuted",
            }
        )
    hypotheses.append(
        {
            "id": "provider-stack-reproducibility",
            "hypothesis": "Every active credential-free provider sweep completes its selected seeded cases.",
            "confidence": provider_confidence,
            "confidence_basis": "Observed passing-provider fraction in this workflow run.",
            "evidence": [
                f"{item['provider']}:{'pass' if item['passed'] else 'fail'}:{item['cases_executed']}-cases"
                for item in providers
            ]
            + [f"{provider}:missing" for provider in missing],
            "outcome": "supported" if provider_confidence == 1.0 else "refuted",
        }
    )

    active_failures = [item for item in failures if item["status"] != "recovered"]
    overall = "success" if not active_failures else "failure"
    branch_status = None
    if leading:
        branch_status = (
            "held-at-real-boundary"
            if leading.get("real_boundary")
            else "safe-preparation-selected"
        )
    evidence: dict[str, Any] = {
        "candidate": None,
        "providers": providers,
        "branch_state_sha256": analysis.get("branch_state_sha256"),
        "calibration_sha256": analysis.get("calibration_sha256"),
        "aurum_seed_build": analysis.get("aurum_seed_build"),
    }
    if candidate is not None and candidate_path is not None:
        evidence["candidate"] = {
            "sha256": _sha256(candidate_path),
            "schema": candidate.get("schema"),
        }

    next_updates: list[dict[str, Any]] = []
    if leading:
        next_updates.append(
            {
                "path": leading["name"],
                "probability": leading["probability"],
                "disposition": leading["disposition"],
                "status": branch_status,
                "next": leading.get("next"),
            }
        )
        next_updates.append(
            {
                "pruned_count": len(pruned),
                "pruned_paths": [item["name"] for item in pruned],
                "reconsider_when": "branch state, evidence, dependency, hypothesis, or authority changes",
            }
        )
    if resumed_from_run_id:
        next_updates.append(
            {
                "recovered_run_id": resumed_from_run_id,
                "update": "Schema compatibility advanced to accept the live v11 branch state.",
            }
        )

    experiment_id = f"gha-{run_id}-attempt-{run_attempt}"
    return {
        "schema": LOG_SCHEMA,
        "experiment_id": experiment_id,
        "recorded_at": datetime.now(UTC).isoformat(),
        "run": {
            "run_id": run_id,
            "run_attempt": run_attempt,
            "workflow": workflow_name,
            "url": workflow_url,
            "runner_commit": runner_commit,
            "resumed_from_run_id": resumed_from_run_id,
        },
        "hypotheses": hypotheses,
        "selection": selection or None,
        "evidence": evidence,
        "failures": failures,
        "outcomes": {
            "overall": overall,
            "router": router_outcome,
            "provider_sweeps": providers,
            "selected_branch": (
                {
                    "path": leading["name"],
                    "probability": leading["probability"],
                    "status": branch_status,
                    "physical_or_destructive_effect_executed": False,
                }
                if leading
                else None
            ),
            "hardware_submission": bool((candidate or {}).get("submission")),
        },
        "next_branch_updates": next_updates,
    }


def write_experiment_log(record: dict[str, Any], log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    record_path = log_dir / f"{record['experiment_id']}.json"
    record_path.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    index_path = log_dir / "index.jsonl"
    entries: list[dict[str, Any]] = []
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                if entry.get("experiment_id") != record["experiment_id"]:
                    entries.append(entry)
    selected = record["outcomes"].get("selected_branch") or {}
    entries.append(
        {
            "experiment_id": record["experiment_id"],
            "run_id": record["run"]["run_id"],
            "recorded_at": record["recorded_at"],
            "overall": record["outcomes"]["overall"],
            "selected_path": selected.get("path"),
            "selected_probability": selected.get("probability"),
            "record": record_path.name,
        }
    )
    index_path.write_text(
        "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in entries),
        encoding="utf-8",
    )
    return record_path
