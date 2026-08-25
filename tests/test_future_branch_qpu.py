from __future__ import annotations

import pytest
from qiskit.quantum_info import Statevector

from aurum_quantum.future_branch_qpu import (
    build_branch_sampling_circuit,
    evaluate_branch_counts,
    select_top_probability_paths,
)


def _analysis() -> dict:
    return {
        "qpu_eligible": True,
        "ranked_machine_paths": [
            {
                "name": "recover",
                "qpu_amplitude_weight": 0.5,
                "selected_for_execution": True,
                "execution_weight": 1.0,
                "real_boundary": False,
                "disposition": "prepare-now",
            },
            {
                "name": "hold",
                "qpu_amplitude_weight": 0.3,
                "selected_for_execution": False,
                "execution_weight": 0.0,
                "real_boundary": True,
                "disposition": "wait-boundary",
            },
            {
                "name": "fallback",
                "qpu_amplitude_weight": 0.2,
                "selected_for_execution": False,
                "execution_weight": 0.0,
                "real_boundary": False,
                "disposition": "prepare-now",
            },
        ],
    }


def test_branch_sampling_circuit_matches_future_branch_weights() -> None:
    circuit, reference = build_branch_sampling_circuit(_analysis())
    state = Statevector.from_instruction(circuit.remove_final_measurements(inplace=False))
    probabilities = state.probabilities_dict()

    assert circuit.num_qubits == 2
    assert reference["padding_states"] == ["11"]
    assert probabilities["00"] == pytest.approx(0.5)
    assert probabilities["01"] == pytest.approx(0.3)
    assert probabilities["10"] == pytest.approx(0.2)
    assert probabilities.get("11", 0.0) == pytest.approx(0.0)


def test_branch_counts_are_mapped_back_to_preparation_paths() -> None:
    _, reference = build_branch_sampling_circuit(_analysis())
    evaluation = evaluate_branch_counts(
        {"00": 50, "01": 30, "10": 20}, reference
    )

    assert evaluation["winning_path"] == "recover"
    assert evaluation["winning_path_selected_for_execution"] is True
    assert evaluation["execution_selection_agreement"] is True
    assert evaluation["padding_shots"] == 0
    assert evaluation["total_variation_distance"] == pytest.approx(0.0)
    assert evaluation["distribution_usable"] is True
    assert evaluation["learning"]["full_field_weighted"] is True
    assert evaluation["learning"]["recommendation"] == "retain-top-probability-execution-selection"
    assert evaluation["path_distribution"][0]["observed_probability"] == pytest.approx(0.5)


def test_ineligible_field_refuses_circuit() -> None:
    analysis = _analysis()
    analysis["qpu_eligible"] = False
    with pytest.raises(RuntimeError, match="not eligible"):
        build_branch_sampling_circuit(analysis)


def test_top_five_percent_keeps_only_highest_probability_path() -> None:
    paths = [
        {"name": f"branch-{index}", "probability": index / 100, "priority": index}
        for index in range(1, 21)
    ]
    selected, pruned = select_top_probability_paths(paths, fraction=0.05)

    assert [item["name"] for item in selected] == ["branch-20"]
    assert len(pruned) == 19
    assert selected[0]["execution_weight"] == pytest.approx(1.0)
    assert all(item["execution_weight"] == 0.0 for item in pruned)


def test_single_execution_path_does_not_collapse_qpu_weighting_field() -> None:
    analysis = _analysis()
    analysis["selected_machine_paths"] = [analysis["ranked_machine_paths"][0]]

    circuit, reference = build_branch_sampling_circuit(analysis)
    state = Statevector.from_instruction(circuit.remove_final_measurements(inplace=False))

    assert circuit.num_qubits == 2
    assert reference["paths"] == 3
    assert reference["padding_states"] == ["11"]
    assert reference["weighting_stage"] == "before-top-probability-execution-pruning"
    assert reference["execution_selected_paths"] == ["recover"]
    assert state.probabilities_dict()["00"] == pytest.approx(0.5)
    assert state.probabilities_dict()["01"] == pytest.approx(0.3)
    assert state.probabilities_dict()["10"] == pytest.approx(0.2)
