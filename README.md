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
  adapter and access work is tracked in the setup report; no credentials are
  stored in this repository.

## Safety model

- Secrets are read at runtime from an external file or environment variable.
- Hardware submission requires the literal `--confirm-qpu` flag.
- Smoke jobs are capped at 1,024 shots.
- IBM usage is checked before submission and a reached quota blocks the run.
- One small, reproducible Bell-state circuit is submitted per selected QPU.
- Local reference validation and provenance manifests are mandatory.
- GitHub Actions runs local tests only. It never receives a QPU credential and
  never submits hardware jobs.

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

