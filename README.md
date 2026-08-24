# Aurum Future Branch Quantum Gateway

Provider-neutral quantum test harness for Aurum's Future Branch. It compares
matched workloads across local reference computation, simulators, and QPUs,
while recording enough evidence to decide whether a problem should be routed
to quantum hardware at all.

## Current live access

- IBM Quantum: control-plane verified; breadth smoke tests supported on every
  backend exposed by the configured instance.
- Google Quantum Engine: dedicated Cloud project prepared; external sponsor or
  program approval is still required.
- Amazon Braket, Quantinuum, Azure Quantum, IonQ, Rigetti, QuEra, and Pasqal:
  live access and human approval gates are tracked in
  [`docs/provider-access-status.md`](docs/provider-access-status.md); no
  credentials are stored in this repository.

## Safety model

- Secrets are read at runtime from an external file or environment variable.
- Hardware submission requires the literal `--confirm-qpu` flag.
- Smoke jobs are capped at 1,024 shots.
- IBM usage is checked before submission and a reached quota blocks the run.
- One small, reproducible Bell-state circuit is submitted per selected QPU.
- Local reference validation and provenance manifests are mandatory.
- GitHub Actions runs local tests only. It never receives a QPU credential and
  never submits hardware jobs.
- A tested progression gate scopes each human-only boundary to its own lane;
  other safe work continues, including preparation and external observation.
- Provider account gates do not stop independent work: CI fans out across local
  Cirq, Amazon Braket, QuEra AHS, PyQuil, pytket, and Pulser execution lanes in
  parallel.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
```

Set only a reference to the IBM key file; do not copy its value into the
repository:

```powershell
$env:IQP_API_KEY_FILE = "C:\path\outside\the\repo\apikey.json"
```

## Test locally

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run the full credential-free provider simulator field with the optional SDKs:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test,provider-simulators]"
.\.venv\Scripts\python.exe scripts\run_provider_smoke.py cirq
.\.venv\Scripts\python.exe scripts\run_provider_smoke.py braket
.\.venv\Scripts\python.exe scripts\run_provider_smoke.py quera
.\.venv\Scripts\python.exe scripts\run_provider_smoke.py rigetti
.\.venv\Scripts\python.exe scripts\run_provider_smoke.py quantinuum
.\.venv\Scripts\python.exe scripts\run_provider_smoke.py pasqal
```

These runs validate local formulation/execution readiness; they are not claims
of provider account access or QPU execution.

## Submit an IBM breadth smoke test

```powershell
.\.venv\Scripts\python.exe scripts\submit_ibm_breadth.py `
  --backend ibm_fez `
  --backend ibm_kingston `
  --backend ibm_marrakesh `
  --shots 256 `
  --confirm-qpu
```

The command writes a secret-free submission manifest under `runs/`. Check the
jobs later with:

```powershell
.\.venv\Scripts\python.exe scripts\check_ibm_jobs.py runs\RUN_ID\submission.json
```

QPU queue time can be much longer than execution time. A submitted job is not
treated as scientific evidence until its result passes the Bell correlation
check and is compared with the exact local reference.
