from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

from .circuits import bell_circuit
from .models import JobEnvelope

MAX_SMOKE_SHOTS = 1024


def load_api_key() -> str:
    key_file = os.environ.get("IQP_API_KEY_FILE")
    if key_file:
        with Path(key_file).open(encoding="utf-8") as handle:
            value = json.load(handle).get("apikey")
        if value:
            return value

    value = os.environ.get("IQP_API_TOKEN")
    if value:
        return value
    raise RuntimeError("Set IQP_API_KEY_FILE or inject IQP_API_TOKEN securely.")


def _iam_bearer_token(api_key: str) -> str:
    body = urllib.parse.urlencode(
        {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": api_key,
        }
    ).encode()
    request = urllib.request.Request(
        "https://iam.cloud.ibm.com/identity/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)["access_token"]


def discover_quantum_crn(api_key: str) -> str:
    configured = os.environ.get("IBM_QUANTUM_CRN")
    if configured:
        return configured

    request = urllib.request.Request(
        "https://resource-controller.cloud.ibm.com/v2/resource_instances?limit=100",
        headers={"Authorization": f"Bearer {_iam_bearer_token(api_key)}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        resources = json.load(response).get("resources", [])

    matches = [
        resource
        for resource in resources
        if "quantum" in f"{resource.get('name', '')} {resource.get('crn', '')}".lower()
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one accessible Quantum instance; found {len(matches)}."
        )
    return matches[0]["crn"]


def service() -> QiskitRuntimeService:
    api_key = load_api_key()
    return QiskitRuntimeService(
        channel="ibm_quantum_platform",
        token=api_key,
        instance=discover_quantum_crn(api_key),
    )


def safe_usage(runtime: QiskitRuntimeService) -> dict[str, Any]:
    usage = runtime.usage()
    return {
        "usage_consumed_seconds": usage.get("usage_consumed_seconds"),
        "usage_remaining_seconds": usage.get("usage_remaining_seconds"),
        "usage_limit_seconds": usage.get("usage_limit_seconds"),
        "usage_limit_reached": usage.get("usage_limit_reached"),
        "usage_period": usage.get("usage_period"),
    }


def submit_bell_job(
    runtime: QiskitRuntimeService,
    *,
    backend_name: str,
    shots: int,
    confirmed: bool,
) -> dict[str, Any]:
    if not confirmed:
        raise RuntimeError("Hardware submission requires explicit confirmation.")
    if shots < 1 or shots > MAX_SMOKE_SHOTS:
        raise ValueError(f"shots must be between 1 and {MAX_SMOKE_SHOTS}")

    usage = safe_usage(runtime)
    if usage["usage_limit_reached"]:
        raise RuntimeError("IBM usage limit is already reached.")
    remaining = usage.get("usage_remaining_seconds")
    if remaining is not None and remaining <= 0:
        raise RuntimeError("IBM reports no QPU time remaining.")

    backend = runtime.backend(backend_name)
    status = backend.status()
    if not status.operational:
        raise RuntimeError(f"{backend_name} is not operational: {status.status_msg}")

    original = bell_circuit(measure=True)
    pass_manager = generate_preset_pass_manager(
        backend=backend,
        optimization_level=3,
    )
    isa_circuit = pass_manager.run(original)
    sampler = SamplerV2(mode=backend)
    job = sampler.run([isa_circuit], shots=shots)

    envelope = JobEnvelope(
        workload_id="bell-state-v1",
        problem_class="sampling-validation",
        formulation="two-qubit-bell-correlation",
        provider="ibm_quantum",
        backend=backend_name,
        shots=shots,
        qpu_approved=True,
    )
    return {
        "envelope": envelope.to_dict(),
        "job_id": job.job_id(),
        "initial_status": str(job.status()),
        "backend_operational": status.operational,
        "backend_pending_jobs_at_submit": status.pending_jobs,
        "transpiled_depth": isa_circuit.depth(),
        "transpiled_two_qubit_ops": sum(
            count
            for instruction, count in isa_circuit.count_ops().items()
            if instruction in {"cx", "cz", "ecr"}
        ),
    }


def submit_sampling_circuit(
    runtime: QiskitRuntimeService,
    *,
    backend_name: str,
    circuit: QuantumCircuit,
    shots: int,
    confirmed: bool,
    workload_id: str,
    problem_class: str,
    formulation: str,
) -> dict[str, Any]:
    """Submit one bounded sampling circuit after the same live-QPU safeguards."""
    if not confirmed:
        raise RuntimeError("Hardware submission requires explicit confirmation.")
    if shots < 1 or shots > MAX_SMOKE_SHOTS:
        raise ValueError(f"shots must be between 1 and {MAX_SMOKE_SHOTS}")

    usage = safe_usage(runtime)
    if usage["usage_limit_reached"]:
        raise RuntimeError("IBM usage limit is already reached.")
    remaining = usage.get("usage_remaining_seconds")
    if remaining is not None and remaining <= 0:
        raise RuntimeError("IBM reports no QPU time remaining.")

    backend = runtime.backend(backend_name)
    status = backend.status()
    if not status.operational:
        raise RuntimeError(f"{backend_name} is not operational: {status.status_msg}")
    if circuit.num_qubits > backend.num_qubits:
        raise RuntimeError(
            f"{backend_name} has {backend.num_qubits} qubits; "
            f"the circuit needs {circuit.num_qubits}."
        )

    pass_manager = generate_preset_pass_manager(
        backend=backend,
        optimization_level=3,
    )
    isa_circuit = pass_manager.run(circuit)
    sampler = SamplerV2(mode=backend)
    job = sampler.run([isa_circuit], shots=shots)

    envelope = JobEnvelope(
        workload_id=workload_id,
        problem_class=problem_class,
        formulation=formulation,
        provider="ibm_quantum",
        backend=backend_name,
        shots=shots,
        qpu_approved=True,
    )
    return {
        "envelope": envelope.to_dict(),
        "job_id": job.job_id(),
        "initial_status": str(job.status()),
        "backend_operational": status.operational,
        "backend_pending_jobs_at_submit": status.pending_jobs,
        "logical_qubits": circuit.num_qubits,
        "transpiled_depth": isa_circuit.depth(),
        "transpiled_two_qubit_ops": sum(
            count
            for instruction, count in isa_circuit.count_ops().items()
            if instruction in {"cx", "cz", "ecr"}
        ),
    }


def result_counts(job: Any) -> dict[str, int]:
    result = job.result()
    pub_result = result[0]
    for register_name in pub_result.data.keys():
        register = getattr(pub_result.data, register_name)
        if hasattr(register, "get_counts"):
            return dict(register.get_counts())
    raise RuntimeError("IBM result contains no classical register counts.")
