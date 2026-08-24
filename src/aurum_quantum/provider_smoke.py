from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isclose
from typing import Any, Callable

from qiskit.quantum_info import Statevector

from .circuits import bell_circuit, evaluate_bell_counts


@dataclass(frozen=True)
class ProviderSmokeResult:
    stack: str
    provider_targets: tuple[str, ...]
    modality: str
    execution: str
    passed: bool
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _statevector_evidence(state: Any) -> dict[str, Any]:
    probabilities = [float(abs(amplitude) ** 2) for amplitude in state]
    if len(probabilities) != 4:
        raise ValueError("Bell smoke statevector must contain exactly four amplitudes")
    correlated = probabilities[0] + probabilities[3]
    return {
        "basis_probabilities": {
            "00": probabilities[0],
            "01": probabilities[1],
            "10": probabilities[2],
            "11": probabilities[3],
        },
        "correlated_probability": correlated,
        "exact_bell_pass": isclose(correlated, 1.0, abs_tol=1e-9),
    }


def qiskit_smoke() -> ProviderSmokeResult:
    evidence = _statevector_evidence(
        Statevector.from_instruction(bell_circuit(measure=False)).data
    )
    return ProviderSmokeResult(
        stack="qiskit",
        provider_targets=("ibm_quantum",),
        modality="gate-model",
        execution="local-statevector",
        passed=bool(evidence["exact_bell_pass"]),
        evidence=evidence,
    )


def cirq_smoke(*, shots: int = 512) -> ProviderSmokeResult:
    import cirq

    qubits = cirq.LineQubit.range(2)
    circuit = cirq.Circuit(
        cirq.H(qubits[0]),
        cirq.CNOT(qubits[0], qubits[1]),
        cirq.measure(*qubits, key="m"),
    )
    histogram = cirq.Simulator(seed=7).run(circuit, repetitions=shots).histogram(key="m")
    counts = {format(value, "02b"): int(count) for value, count in histogram.items()}
    evidence = {"counts": counts, **evaluate_bell_counts(counts)}
    return ProviderSmokeResult(
        stack="cirq",
        provider_targets=("google_quantum_ai",),
        modality="gate-model",
        execution="local-simulator",
        passed=bool(evidence["bell_correlation_pass"]),
        evidence=evidence,
    )


def braket_smoke(*, shots: int = 512) -> ProviderSmokeResult:
    from braket.circuits import Circuit
    from braket.devices import LocalSimulator

    circuit = Circuit().h(0).cnot(0, 1)
    result = LocalSimulator("braket_sv").run(circuit, shots=shots).result()
    counts = {str(key): int(value) for key, value in result.measurement_counts.items()}
    evidence = {"counts": counts, **evaluate_bell_counts(counts)}
    return ProviderSmokeResult(
        stack="amazon-braket-sdk",
        provider_targets=("amazon_braket", "ionq", "iqm", "rigetti", "aqt"),
        modality="gate-model",
        execution="local-braket-sv",
        passed=bool(evidence["bell_correlation_pass"]),
        evidence=evidence,
    )


def quera_smoke(*, shots: int = 512) -> ProviderSmokeResult:
    from braket.ahs.analog_hamiltonian_simulation import AnalogHamiltonianSimulation
    from braket.ahs.atom_arrangement import AtomArrangement
    from braket.ahs.driving_field import DrivingField
    from braket.devices import LocalSimulator
    from braket.timings.time_series import TimeSeries

    spacing = 5.7e-6
    register = AtomArrangement()
    for coordinate in (
        (0.0, 0.0),
        (spacing, 0.0),
        (spacing, spacing),
        (0.0, spacing),
    ):
        register.add(coordinate)

    time_max = 4e-6
    time_ramp = 1e-7
    omega_max = 6_300_000.0
    omega = (
        TimeSeries()
        .put(0.0, 0.0)
        .put(time_ramp, omega_max)
        .put(time_max - time_ramp, omega_max)
        .put(time_max, 0.0)
    )
    delta = (
        TimeSeries()
        .put(0.0, -5 * omega_max)
        .put(time_ramp, -5 * omega_max)
        .put(time_max - time_ramp, 5 * omega_max)
        .put(time_max, 5 * omega_max)
    )
    phi = TimeSeries().put(0.0, 0.0).put(time_max, 0.0)
    program = AnalogHamiltonianSimulation(
        register=register,
        hamiltonian=DrivingField(amplitude=omega, phase=phi, detuning=delta),
    )
    result = LocalSimulator("braket_ahs").run(program, shots=shots).result()
    valid_measurements = sum(
        len(shot.pre_sequence) == 4 and len(shot.post_sequence) == 4
        for shot in result.measurements
    )
    evidence = {
        "atoms": 4,
        "shots": shots,
        "valid_measurements": valid_measurements,
        "program_duration_seconds": time_max,
    }
    return ProviderSmokeResult(
        stack="amazon-braket-sdk-ahs",
        provider_targets=("quera_aquila",),
        modality="neutral-atom-analog-hamiltonian",
        execution="local-braket-ahs",
        passed=valid_measurements == shots,
        evidence=evidence,
    )


def rigetti_smoke() -> ProviderSmokeResult:
    from pyquil import Program
    from pyquil.gates import CNOT, H
    from pyquil.pyqvm import PyQVM

    program = Program(H(0), CNOT(0, 1))
    simulator = PyQVM(n_qubits=2, seed=7).execute(program)
    evidence = {
        "quil": program.out().strip().splitlines(),
        **_statevector_evidence(simulator.wf_simulator.wf.reshape(-1)),
    }
    return ProviderSmokeResult(
        stack="pyquil",
        provider_targets=("rigetti_qcs",),
        modality="gate-model",
        execution="in-process-pyqvm",
        passed=bool(evidence["exact_bell_pass"]),
        evidence=evidence,
    )


def quantinuum_smoke() -> ProviderSmokeResult:
    from pytket import Circuit

    circuit = Circuit(2).H(0).CX(0, 1)
    evidence = {
        "commands": [str(command) for command in circuit.get_commands()],
        "depth": circuit.depth(),
        **_statevector_evidence(circuit.get_statevector()),
    }
    return ProviderSmokeResult(
        stack="pytket",
        provider_targets=("quantinuum",),
        modality="gate-model",
        execution="local-tket-statevector",
        passed=bool(evidence["exact_bell_pass"]),
        evidence=evidence,
    )


def pasqal_smoke() -> ProviderSmokeResult:
    from pulser import Pulse, Register, Sequence
    from pulser.devices import MockDevice
    from pulser_simulation import QutipEmulator

    register = Register.from_coordinates(((0.0, 0.0), (8.0, 0.0)), prefix="q")
    sequence = Sequence(register, MockDevice)
    sequence.declare_channel("drive", "rydberg_global")
    sequence.add(Pulse.ConstantPulse(100, 1.0, 0.0, 0.0), "drive")
    result = QutipEmulator.from_sequence(sequence).run()
    final_state = result.get_final_state()
    norm = float(final_state.norm())
    evidence = {
        "qubits": len(register.qubit_ids),
        "duration_ns": sequence.get_duration(),
        "final_state_norm": norm,
        "sequence_abstract_repr_bytes": len(sequence.to_abstract_repr().encode("utf-8")),
    }
    return ProviderSmokeResult(
        stack="pulser",
        provider_targets=("pasqal",),
        modality="neutral-atom-pulse",
        execution="local-qutip-emulator",
        passed=isclose(norm, 1.0, abs_tol=1e-7),
        evidence=evidence,
    )


SMOKE_RUNNERS: dict[str, Callable[..., ProviderSmokeResult]] = {
    "qiskit": qiskit_smoke,
    "cirq": cirq_smoke,
    "braket": braket_smoke,
    "quera": quera_smoke,
    "rigetti": rigetti_smoke,
    "quantinuum": quantinuum_smoke,
    "pasqal": pasqal_smoke,
}


def run_provider_smoke(provider: str, *, shots: int = 512) -> ProviderSmokeResult:
    try:
        runner = SMOKE_RUNNERS[provider]
    except KeyError as error:
        raise ValueError(f"Unknown provider smoke stack: {provider}") from error
    if provider in {"cirq", "braket", "quera"}:
        return runner(shots=shots)
    return runner()
