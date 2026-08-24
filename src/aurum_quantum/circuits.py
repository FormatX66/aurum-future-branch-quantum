from __future__ import annotations

from qiskit import QuantumCircuit


def bell_circuit(*, measure: bool = True) -> QuantumCircuit:
    """Return a minimal entanglement circuit with an exact local reference."""
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    if measure:
        circuit.measure_all()
    return circuit

