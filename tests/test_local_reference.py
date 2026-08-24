from __future__ import annotations

from math import isclose

from qiskit.quantum_info import Statevector

from aurum_quantum import JobEnvelope, bell_circuit
from aurum_quantum.circuits import evaluate_bell_counts


def test_bell_state_exact_reference() -> None:
    probabilities = Statevector.from_instruction(
        bell_circuit(measure=False)
    ).probabilities_dict()
    assert set(probabilities) == {"00", "11"}
    assert isclose(probabilities["00"], 0.5, abs_tol=1e-12)
    assert isclose(probabilities["11"], 0.5, abs_tol=1e-12)


def test_job_envelope_is_secret_free() -> None:
    envelope = JobEnvelope(
        workload_id="bell-state-v1",
        problem_class="sampling-validation",
        formulation="two-qubit-bell-correlation",
        provider="local",
        backend="statevector",
        shots=0,
        qpu_approved=False,
    )
    data = envelope.to_dict()
    assert "token" not in data
    assert "api_key" not in data
    assert data["qpu_approved"] is False


def test_bell_hardware_noise_gate() -> None:
    metrics = evaluate_bell_counts({"00": 143, "11": 110, "01": 1, "10": 2})
    assert metrics["total_shots"] == 256
    assert metrics["correlated_shots"] == 253
    assert metrics["bell_correlation_pass"] is True
