from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from qiskit import QuantumCircuit
from qiskit.circuit.library import StatePreparation

from .aurum_seed import AurumSeedBuild


BRANCH_SCHEMAS = {
    "aurum-future-branch-state-v10",
    "aurum-future-branch-state-v11",
}
CALIBRATION_SCHEMA = "aurum-future-branch-calibration-v2"
DEFAULT_HIGH_FAILURE_THRESHOLD = 0.50
DEFAULT_TOP_PROBABILITY_FRACTION = 0.05


def _load_module(path: Path, label: str) -> ModuleType:
    name = f"aurum_external_{label}_{hashlib.sha256(str(path).encode()).hexdigest()[:12]}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load Future Branch model: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_json(
    path: Path, *, schema: str | set[str]
) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"Unsupported JSON document in {path}")
    allowed = {schema} if isinstance(schema, str) else schema
    if value.get("schema") not in allowed:
        raise ValueError(f"Unsupported schema in {path}: {value.get('schema')!r}")
    return value, hashlib.sha256(raw).hexdigest()


def select_top_probability_paths(
    paths: list[dict[str, Any]], *, fraction: float = DEFAULT_TOP_PROBABILITY_FRACTION
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep the ceiling of the highest-probability fraction and prune the rest."""
    if not 0 < fraction <= 1:
        raise ValueError("top probability fraction must be greater than 0 and at most 1")
    if not paths:
        raise ValueError("at least one Future Branch path is required")
    selected_count = max(1, math.ceil(len(paths) * fraction))
    ordered = sorted(
        paths,
        key=lambda item: (
            -float(item["probability"]),
            -float(item["priority"]),
            str(item["name"]),
        ),
    )
    selected = ordered[:selected_count]
    pruned = ordered[selected_count:]
    selected_priority = sum(max(float(item["priority"]), 0.0) for item in selected)
    if selected_priority <= 0:
        raise ValueError("selected Future Branch paths have no positive priority")
    for item in selected:
        item["selected_for_execution"] = True
        item["execution_weight"] = max(float(item["priority"]), 0.0) / selected_priority
    for item in pruned:
        item["selected_for_execution"] = False
        item["execution_weight"] = 0.0
    return selected, pruned


def _boundary_flags(text: str) -> dict[str, bool]:
    lowered = text.lower()
    return {
        "physical_boundary": any(
            token in lowered for token in ("physical", "flash", "usb", "boot", "reboot")
        ),
        "destructive_boundary": any(
            token in lowered for token in ("destructive", "disk write", "raw readback")
        ),
        "credential_boundary": any(
            token in lowered for token in ("credential", "secret", "ssh authorization")
        ),
        "preference_boundary": "preference" in lowered,
        "irreversible_boundary": "irreversible" in lowered,
    }


def analyze_future_branch_field(
    *,
    branch_state_path: Path,
    calibration_path: Path,
    experiments_dir: Path,
    aurum_seed: AurumSeedBuild,
    high_failure_threshold: float = DEFAULT_HIGH_FAILURE_THRESHOLD,
    top_probability_fraction: float = DEFAULT_TOP_PROBABILITY_FRACTION,
) -> dict[str, Any]:
    if not 0 <= high_failure_threshold <= 1:
        raise ValueError("high_failure_threshold must be between 0 and 1")
    branch_state, branch_sha = _load_json(branch_state_path, schema=BRANCH_SCHEMAS)
    calibration, calibration_sha = _load_json(
        calibration_path, schema=CALIBRATION_SCHEMA
    )
    future_branch = _load_module(experiments_dir / "future_branch.py", "branch")
    feasibility = _load_module(
        experiments_dir / "speculative_feasibility.py", "feasibility"
    )

    metrics = calibration.get("metrics", {})
    events = int(metrics.get("events", 0))
    exact = int(metrics.get("exact_predictions", 0))
    partial = int(metrics.get("partial_predictions", 0))
    misses = int(metrics.get("miss_predictions", 0))
    if events < 1 or exact + partial + misses != events:
        raise ValueError("Future Branch calibration prediction counts are inconsistent")
    strict_failure_rate = (partial + misses) / events

    outcomes = branch_state.get("likely_machine_outcomes")
    if not isinstance(outcomes, list) or not 2 <= len(outcomes) <= 8:
        raise ValueError("QPU branch field requires between two and eight machine outcomes")

    model_inputs: list[Any] = []
    upstream: dict[str, dict[str, Any]] = {}
    count = len(outcomes)
    for raw in outcomes:
        if not isinstance(raw, dict):
            raise ValueError("Future Branch machine outcomes must be objects")
        state = str(raw.get("state", "")).strip()
        rank = int(raw.get("rank", 0))
        if not state or not 1 <= rank <= count:
            raise ValueError("Future Branch machine outcomes require valid state and rank")
        prepared = raw.get("prepared", [])
        if not isinstance(prepared, list):
            raise ValueError(f"Future Branch prepared field must be a list: {state}")
        next_action = str(raw.get("next", ""))
        boundary = _boundary_flags(f"{state} {next_action} {' '.join(map(str, prepared))}")
        probability = (count - rank + 1) / (count + 1)
        item = future_branch.FutureBranch(
            name=state,
            probability=probability,
            impact=1.0,
            user_time_saved=1.0 + min(len(prepared), 5) / 5,
            preparation_leverage=1.0 + min(len(prepared), 10) / 10,
            cost=1.0 + rank / (2 * count),
            safe_reversible_action=not any(boundary.values()),
            dependencies_satisfied=False,
            linearity=0.75 if next_action else 0.5,
            **boundary,
        )
        model_inputs.append(item)
        upstream[state] = {
            "upstream_rank": rank,
            "prepared": prepared,
            "next": next_action,
            "model_probability_from_rank": probability,
            "boundary_flags": boundary,
        }

    ranked = future_branch.rank_branches(model_inputs, limit=count)
    positive_priorities = [max(float(item["priority"]), 0.0) for item in ranked]
    total_priority = sum(positive_priorities)
    if total_priority <= 0:
        raise ValueError("Future Branch model returned no positive branch priority")
    for item, priority in zip(ranked, positive_priorities, strict=True):
        item.update(upstream[item["name"]])
        item["population_amplitude_weight"] = priority / total_priority
        item["qpu_amplitude_weight"] = priority / total_priority
        item["qpu_role"] = "full-field-weighting-before-execution-pruning"
    selected, pruned = select_top_probability_paths(
        ranked, fraction=top_probability_fraction
    )

    probe = feasibility.FeasibilityProbe(
        name="aurum-future-branch-qpu-ranking",
        success_probability=exact / events,
        success_value=2.0,
        failure_learning_value=4.0 * strict_failure_rate,
        downstream_cost_avoided_if_failure=2.0 * strict_failure_rate,
        run_cost=0.25,
        risk_exposure=0.05,
        resource_headroom=1.0,
        reversible=True,
        external_side_effects=False,
    )
    information_value = feasibility.expected_information_value(probe)
    prerun_decision = feasibility.decide_prerun(probe).value
    qpu_eligible = (
        strict_failure_rate >= high_failure_threshold and prerun_decision == "pre-run"
    )
    return {
        "schema": "aurum-future-branch-qpu-analysis-v1",
        "aurum_seed_build": aurum_seed.to_dict(),
        "branch_state_sha256": branch_sha,
        "calibration_sha256": calibration_sha,
        "future_branch_model": {
            "schema": branch_state["schema"],
            "current_program": branch_state.get("current_program"),
            "calibration_schema": calibration["schema"],
        },
        "failure": {
            "events": events,
            "exact": exact,
            "partial": partial,
            "miss": misses,
            "strict_failure_rate": strict_failure_rate,
            "high_failure_threshold": high_failure_threshold,
            "high_failure": strict_failure_rate >= high_failure_threshold,
        },
        "speculative_feasibility": {
            "decision": prerun_decision,
            **information_value,
        },
        "qpu_eligible": qpu_eligible,
        "qpu_scope": "full-field-weighting-before-top-probability-execution-pruning",
        "selection": {
            "rule": "highest-model-probability-ceiling",
            "top_probability_fraction": top_probability_fraction,
            "population_size": len(ranked),
            "selected_count": len(selected),
            "pruned_count": len(pruned),
            "probability_cutoff": min(float(item["probability"]) for item in selected),
        },
        "ranked_machine_paths": ranked,
        "selected_machine_paths": selected,
        "pruned_machine_paths": pruned,
    }


def build_branch_sampling_circuit(analysis: dict[str, Any]) -> tuple[QuantumCircuit, dict[str, Any]]:
    if not analysis.get("qpu_eligible"):
        raise RuntimeError("Future Branch field is not eligible for QPU escalation")
    paths = analysis["ranked_machine_paths"]
    qubits = max(1, math.ceil(math.log2(len(paths))))
    dimensions = 2**qubits
    amplitudes = [0.0] * dimensions
    basis_map: dict[str, Any] = {}
    for index, path in enumerate(paths):
        weight = float(path["qpu_amplitude_weight"])
        amplitudes[index] = math.sqrt(weight)
        basis_map[format(index, f"0{qubits}b")] = {
            "path": path["name"],
            "weight": weight,
            "model_probability": path.get("probability"),
            "selected_for_execution": path.get("selected_for_execution", True),
            "execution_weight": path.get("execution_weight", weight),
            "real_boundary": path["real_boundary"],
            "disposition": path["disposition"],
        }

    circuit = QuantumCircuit(qubits, qubits, name="aurum_future_branch")
    circuit.append(StatePreparation(amplitudes, normalize=True), range(qubits))
    circuit.measure(range(qubits), range(qubits))
    reference = {
        "qubits": qubits,
        "paths": len(paths),
        "basis_map": basis_map,
        "padding_states": [
            format(index, f"0{qubits}b") for index in range(len(paths), dimensions)
        ],
        "weighting_stage": "before-top-probability-execution-pruning",
        "execution_selected_paths": [
            path["name"] for path in paths if path.get("selected_for_execution", True)
        ],
        "interpretation": (
            "weight the full ranked field, then execute only the separately gated "
            "top-probability paths; never execute physical effects"
        ),
    }
    return circuit, reference


def evaluate_branch_counts(
    counts: dict[str, int], reference: dict[str, Any]
) -> dict[str, Any]:
    total = sum(counts.values())
    if total < 1:
        raise ValueError("QPU result counts must not be empty")
    basis_map = reference["basis_map"]
    padding = set(reference["padding_states"])
    observed = {state: count / total for state, count in counts.items()}
    expected = {state: float(item["weight"]) for state, item in basis_map.items()}
    states = set(observed) | set(expected) | padding
    total_variation_distance = 0.5 * sum(
        abs(observed.get(state, 0.0) - expected.get(state, 0.0)) for state in states
    )
    winning_state = max(counts, key=counts.get)
    path_distribution = []
    for state, item in basis_map.items():
        count = int(counts.get(state, 0))
        observed_probability = count / total
        path_distribution.append(
            {
                "state": state,
                "path": item["path"],
                "shots": count,
                "observed_probability": observed_probability,
                "expected_weight": float(item["weight"]),
                "weight_delta": observed_probability - float(item["weight"]),
                "model_probability": item.get("model_probability"),
                "selected_for_execution": item.get("selected_for_execution", True),
            }
        )
    path_distribution.sort(
        key=lambda item: (-item["shots"], -item["expected_weight"], item["path"])
    )
    winning_path = basis_map.get(winning_state, {}).get("path")
    winning_path_selected = bool(
        basis_map.get(winning_state, {}).get("selected_for_execution", True)
    )
    distribution_usable = total_variation_distance <= 0.50
    return {
        "shots": total,
        "total_variation_distance": total_variation_distance,
        "padding_shots": sum(counts.get(state, 0) for state in padding),
        "winning_state": winning_state,
        "winning_path": winning_path,
        "winning_path_selected_for_execution": winning_path_selected,
        "execution_selection_agreement": winning_path_selected,
        "distribution_usable": distribution_usable,
        "path_distribution": path_distribution,
        "learning": {
            "full_field_weighted": len(basis_map) > 1,
            "execution_gate_changed": False,
            "recommendation": (
                "retain-top-probability-execution-selection"
                if distribution_usable and winning_path_selected
                else "review-model-qpu-divergence-before-execution"
            ),
        },
    }


def render_qpu_analysis_summary(analysis: dict[str, Any]) -> str:
    failure = analysis["failure"]
    lines = [
        "## Aurum Future Branch QPU router",
        "",
        f"- Strict branch failure rate: **{failure['strict_failure_rate']:.1%}**",
        f"- QPU threshold: `{failure['high_failure_threshold']:.1%}`",
        f"- QPU eligible: **{analysis['qpu_eligible']}**",
        f"- Model decision: `{analysis['speculative_feasibility']['decision']}`",
        "- QPU weighting: full ranked field before execution pruning",
        f"- Probability field retained: **{analysis['selection']['top_probability_fraction']:.1%}**",
        f"- Selected paths: `{analysis['selection']['selected_count']} / {analysis['selection']['population_size']}`",
        f"- Pruned paths: `{analysis['selection']['pruned_count']}`",
        "",
        "| Rank | Machine path | Probability | QPU weight | Execution weight | Selected | Boundary |",
        "|---:|---|---:|---:|---:|---|---|",
    ]
    for rank, path in enumerate(analysis["ranked_machine_paths"], start=1):
        lines.append(
            f"| {rank} | `{path['name']}` | {path['probability']:.4f} | "
            f"{path['qpu_amplitude_weight']:.4f} | {path['execution_weight']:.4f} | "
            f"{path['selected_for_execution']} | "
            f"{path['real_boundary']} |"
        )
    return "\n".join(lines) + "\n"
