from __future__ import annotations

from qiskit import QuantumCircuit

MIN_BELL_CORRELATION_RATE = 0.90


def bell_circuit(*, measure: bool = True) -> QuantumCircuit:
    """Return a minimal entanglement circuit with an exact local reference."""
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    if measure:
        circuit.measure_all()
    return circuit


def evaluate_bell_counts(counts: dict[str, int]) -> dict[str, object]:
    """Evaluate correlated outcomes while allowing realistic hardware noise."""
    total = sum(counts.values())
    correlated = counts.get("00", 0) + counts.get("11", 0)
    rate = correlated / total if total else 0.0
    return {
        "total_shots": total,
        "correlated_shots": correlated,
        "bell_correlation_rate": rate,
        "minimum_correlation_rate": MIN_BELL_CORRELATION_RATE,
        "bell_correlation_pass": rate >= MIN_BELL_CORRELATION_RATE,
        "unexpected_outcomes": sorted(set(counts) - {"00", "11"}),
    }
