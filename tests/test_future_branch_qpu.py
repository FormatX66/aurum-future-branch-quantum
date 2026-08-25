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
                "real_boundary": False,
                "disposition": "prepare-now",
            },
            {
                "name": "hold",
                "qpu_amplitude_weight": 0.3,
                "real_boundary": True,
                "disposition": "wait-boundary",
            },
            {
                "name": "fallback",
                "qpu_amplitude_weight": 0.2,
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
    assert evaluation["padding_shots"] == 0
    assert evaluation["total_variation_distance"] == pytest.approx(0.0)
    assert evaluation["distribution_usable"] is True


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
    assert selected[0]["qpu_amplitude_weight"] == pytest.approx(1.0)
    assert all(item["qpu_amplitude_weight"] == 0.0 for item in pruned)


def test_single_selected_path_uses_one_qubit_with_padding() -> None:
    analysis = _analysis()
    analysis["selected_machine_paths"] = [analysis["ranked_machine_paths"][0]]
    analysis["selected_machine_paths"][0]["qpu_amplitude_weight"] = 1.0

    circuit, reference = build_branch_sampling_circuit(analysis)
    state = Statevector.from_instruction(circuit.remove_final_measurements(inplace=False))

    assert circuit.num_qubits == 1
    assert reference["paths"] == 1
    assert reference["padding_states"] == ["1"]
    assert state.probabilities_dict()["0"] == pytest.approx(1.0)
