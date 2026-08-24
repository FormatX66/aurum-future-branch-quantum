from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from math import pi, sin, sqrt
from typing import Any, Callable

from .aurum_seed import AurumSeedBuild


SHOT_VALUES = (64, 256, 1024)
SEED_VALUES = (7, 23, 101)
ROTATION_QUARTERS = (1, 2, 3)
CASES_PER_PROVIDER_RUN = 9
SUPPORTED_FLOW_PROVIDERS = ("google", "microsoft")


@dataclass(frozen=True)
class SweepCase:
    workload: str
    shots: int
    seed: int
    angle_quarters: int | None = None

    @property
    def case_id(self) -> str:
        suffix = "" if self.angle_quarters is None else f"-q{self.angle_quarters}"
        return f"{self.workload}{suffix}-s{self.shots}-r{self.seed}"

    @property
    def qubits(self) -> int:
        return {"bell": 2, "ghz3": 3, "rotation": 1}[self.workload]


def build_case_catalog() -> tuple[SweepCase, ...]:
    cases: list[SweepCase] = []
    for workload in ("bell", "ghz3"):
        for shots in SHOT_VALUES:
            for seed in SEED_VALUES:
                cases.append(SweepCase(workload=workload, shots=shots, seed=seed))
    for angle_quarters in ROTATION_QUARTERS:
        for shots in SHOT_VALUES:
            for seed in SEED_VALUES:
                cases.append(
                    SweepCase(
                        workload="rotation",
                        shots=shots,
                        seed=seed,
                        angle_quarters=angle_quarters,
                    )
                )
    return tuple(cases)


CASE_CATALOG = build_case_catalog()


def select_cycle_cases(
    cycle: int, *, cases_per_run: int = CASES_PER_PROVIDER_RUN
) -> tuple[SweepCase, ...]:
    if cycle < 0:
        raise ValueError("cycle must not be negative")
    if not 1 <= cases_per_run <= len(CASE_CATALOG):
        raise ValueError(f"cases_per_run must be between 1 and {len(CASE_CATALOG)}")
    start = (cycle * cases_per_run) % len(CASE_CATALOG)
    return tuple(
        CASE_CATALOG[(start + offset) % len(CASE_CATALOG)]
        for offset in range(cases_per_run)
    )


def evaluate_counts(case: SweepCase, counts: dict[str, int]) -> dict[str, Any]:
    total = sum(counts.values())
    unexpected = sorted(
        outcome
        for outcome in counts
        if len(outcome) != case.qubits or set(outcome) - {"0", "1"}
    )
    base: dict[str, Any] = {
        "total_shots": total,
        "expected_shots": case.shots,
        "unexpected_outcomes": unexpected,
    }
    if total != case.shots or unexpected:
        return {**base, "passed": False, "reason": "invalid_measurement_shape"}

    if case.workload in {"bell", "ghz3"}:
        correlated = counts.get("0" * case.qubits, 0) + counts.get(
            "1" * case.qubits, 0
        )
        rate = correlated / total
        return {
            **base,
            "correlated_shots": correlated,
            "correlation_rate": rate,
            "minimum_correlation_rate": 0.9,
            "passed": rate >= 0.9,
        }

    if case.angle_quarters is None:
        raise ValueError("rotation cases require angle_quarters")
    expected_one_probability = sin(pi * case.angle_quarters / 8) ** 2
    observed_one_probability = counts.get("1", 0) / total
    standard_error = sqrt(
        expected_one_probability * (1 - expected_one_probability) / total
    )
    tolerance = max(0.08, 5 * standard_error)
    error = abs(observed_one_probability - expected_one_probability)
    return {
        **base,
        "expected_one_probability": expected_one_probability,
        "observed_one_probability": observed_one_probability,
        "absolute_error": error,
        "tolerance": tolerance,
        "passed": error <= tolerance,
    }


def _google_counts(case: SweepCase) -> dict[str, int]:
    import cirq

    qubits = cirq.LineQubit.range(case.qubits)
    circuit = cirq.Circuit()
    if case.workload == "bell":
        circuit.append((cirq.H(qubits[0]), cirq.CNOT(qubits[0], qubits[1])))
    elif case.workload == "ghz3":
        circuit.append(
            (
                cirq.H(qubits[0]),
                cirq.CNOT(qubits[0], qubits[1]),
                cirq.CNOT(qubits[1], qubits[2]),
            )
        )
    elif case.workload == "rotation" and case.angle_quarters is not None:
        circuit.append(cirq.rx(pi * case.angle_quarters / 4)(qubits[0]))
    else:
        raise ValueError(f"Unsupported Google sweep workload: {case.workload}")
    circuit.append(cirq.measure(*qubits, key="m"))
    histogram = cirq.Simulator(seed=case.seed).run(
        circuit, repetitions=case.shots
    ).histogram(key="m")
    return {
        format(outcome, f"0{case.qubits}b"): int(count)
        for outcome, count in histogram.items()
    }


def _microsoft_qasm(case: SweepCase) -> str:
    operations: list[str]
    if case.workload == "bell":
        operations = ["h q[0];", "cx q[0], q[1];"]
    elif case.workload == "ghz3":
        operations = ["h q[0];", "cx q[0], q[1];", "cx q[1], q[2];"]
    elif case.workload == "rotation" and case.angle_quarters is not None:
        operations = [f"rx({case.angle_quarters} * pi / 4) q[0];"]
    else:
        raise ValueError(f"Unsupported Microsoft sweep workload: {case.workload}")
    lines = [
        "OPENQASM 3.0;",
        'include "stdgates.inc";',
        f"qubit[{case.qubits}] q;",
        f"bit[{case.qubits}] c;",
        *operations,
        "c = measure q;",
    ]
    return "\n".join(lines)


def _microsoft_counts(case: SweepCase) -> dict[str, int]:
    from qdk import set_classical_seed, set_quantum_seed
    from qdk.openqasm import run

    set_quantum_seed(case.seed)
    set_classical_seed(case.seed)
    outcomes = run(
        _microsoft_qasm(case),
        shots=case.shots,
        as_bitstring=True,
    )
    if not isinstance(outcomes, list):
        raise TypeError("Microsoft QDK sweep did not return a shot list")
    return dict(Counter(str(outcome) for outcome in outcomes))


COUNT_RUNNERS: dict[str, Callable[[SweepCase], dict[str, int]]] = {
    "google": _google_counts,
    "microsoft": _microsoft_counts,
}


def run_continuous_sweep(
    provider: str,
    *,
    cycle: int,
    aurum_seed: AurumSeedBuild,
    cases_per_run: int = CASES_PER_PROVIDER_RUN,
) -> dict[str, Any]:
    try:
        runner = COUNT_RUNNERS[provider]
    except KeyError as error:
        raise ValueError(f"Unknown continuous-flow provider: {provider}") from error

    started_at = datetime.now(timezone.utc)
    case_results: list[dict[str, Any]] = []
    coverage_runs = (len(CASE_CATALOG) + cases_per_run - 1) // cases_per_run
    effective_cycle = cycle + aurum_seed.deterministic_seed % coverage_runs
    for case in select_cycle_cases(effective_cycle, cases_per_run=cases_per_run):
        effective_seed = aurum_seed.mix_case_seed(case.seed, cycle=cycle)
        execution_case = replace(case, seed=effective_seed)
        counts = runner(execution_case)
        evaluation = evaluate_counts(case, counts)
        case_results.append(
            {
                "case": {
                    **asdict(case),
                    "case_id": case.case_id,
                    "qubits": case.qubits,
                    "base_seed": case.seed,
                    "aurum_effective_seed": effective_seed,
                },
                "counts": counts,
                "evaluation": evaluation,
            }
        )
    finished_at = datetime.now(timezone.utc)
    return {
        "schema_version": 1,
        "provider": provider,
        "execution": "credential-free-local-provider-stack",
        "cycle": cycle,
        "effective_cycle": effective_cycle,
        "catalog_size": len(CASE_CATALOG),
        "cases_per_run": cases_per_run,
        "full_catalog_coverage_runs": coverage_runs,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "aurum_seed_build": aurum_seed.to_dict(),
        "passed": all(result["evaluation"]["passed"] for result in case_results),
        "results": case_results,
    }


def render_sweep_summary(result: dict[str, Any]) -> str:
    status = "PASS" if result["passed"] else "FAIL"
    lines = [
        f"## Aurum continuous quantum flow — {result['provider']}",
        "",
        f"- Status: **{status}**",
        f"- Cycle: `{result['cycle']}`",
        f"- Aurum-derived cycle: `{result['effective_cycle']}`",
        f"- Cases this run: `{result['cases_per_run']}`",
        f"- Full variable coverage: `{result['full_catalog_coverage_runs']}` runs",
        "- Execution: credential-free local provider stack",
        f"- Aurum build state: `{result['aurum_seed_build']['build_state']}`",
        f"- Aurum next gate: `{result['aurum_seed_build']['next_gate']}`",
        f"- Aurum fingerprint: `{result['aurum_seed_build']['combined_fingerprint']}`",
        "",
        "| Case | Shots | Aurum seed | Result |",
        "|---|---:|---:|---|",
    ]
    for item in result["results"]:
        case = item["case"]
        case_status = "pass" if item["evaluation"]["passed"] else "fail"
        lines.append(
            f"| `{case['case_id']}` | {case['shots']} | "
            f"{case['aurum_effective_seed']} | {case_status} |"
        )
    return "\n".join(lines) + "\n"
