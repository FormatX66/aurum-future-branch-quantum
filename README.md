# Aurum Future Branch Quantum Gateway

Provider-neutral quantum test harness for Aurum's Future Branch. It compares
matched workloads across local reference computation, simulators, and QPUs,
while recording enough evidence to decide whether a problem should be routed
to quantum hardware at all.

## Continuous flow

GitHub runs the active Google and Microsoft formulation stacks every four
hours. Each provider executes nine rotating cases drawn from the same 45-case
catalog: Bell, three-qubit GHZ, and parameterized rotation workloads across
three shot counts, three Aurum-derived seed lanes, and three rotation angles.
Five runs cover every declared combination, then the field repeats with fresh
evidence.

Every run checks out the canonical BoxBrain `main` branch and binds the current
TinySeed handoff plus `Prompts/FutureBranchSeed.txt` into the experiment. The
combined fingerprint selects the catalog offset and mixes every simulator seed,
while the build state, artifact hashes, unresolved gates, and source commits are
recorded as evidence. Unknown seed schemas are refused instead of guessed.

Every provider run publishes JSON evidence and a readable GitHub summary for
30 days. The schedule uses credential-free Cirq and Microsoft QDK simulators.
The same schedule now runs the canonical Future Branch model against its live
branch state and calibration. It creates a QPU candidate only when the strict
partial-or-miss rate is at least 50%. Live submission remains separately gated
because a recurring workflow must not create unbounded cloud charges.

## High-failure Future Branch router

The router imports the actual `FutureBranch` priority and speculative
feasibility models from the current BoxBrain `main` branch. It scores the
current `likely_machine_outcomes`, retains only the ceiling of the highest 5%
by model probability, prunes every other path from execution, converts the
selected priority mass into a small amplitude-sampling circuit, and maps any
samples back to the named Aurum machine path.

The QPU's role is deliberately narrow: rank and prepare paths. A sampled path
never grants authority to flash media, boot hardware, use credentials, make a
destructive write, or cross any other real-world boundary. Those lanes remain
held for their existing proof or human authorization, while reversible
preparation can continue.

Every continuous run writes a version-controlled record under
`experiment-logs/` and a compact `experiment-logs/index.jsonl` entry. Records
include GitHub run identity, hypotheses, probability/confidence, hashed
evidence, failures, outcomes, selected and pruned branches, and the next branch
update. Provider artifacts remain available for 30 days; the summarized record
and evidence hashes remain durable in Git.

## Current live access

- IBM Quantum: control-plane verified; breadth smoke tests supported on every
  backend exposed by the configured instance.
- Google Quantum Engine and Microsoft Azure Quantum: accounts reported working;
  their local provider stacks are the active continuous-flow paths.
- Amazon Braket, Quantinuum, IonQ, Rigetti, QuEra, and Pasqal:
  live access and human approval gates are tracked in
  [`docs/provider-access-status.md`](docs/provider-access-status.md); no
  credentials are stored in this repository.

## Safety model

- Secrets are read at runtime from an external file or environment variable.
- Hardware submission requires the literal `--confirm-qpu` flag.
- Future Branch hardware routing requires a measured partial-or-miss rate of at
  least 50% and a positive speculative-feasibility decision.
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

Run one complete continuous-flow cycle locally:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[cirq,microsoft]"
$aurumRoot = "C:\path\to\BoxBrain"
$seedCommit = git -C $aurumRoot rev-parse HEAD
.\.venv\Scripts\python.exe scripts\run_continuous_sweep.py google --cycle 0 --aurum-build-manifest "$aurumRoot\Projects\Aurum\Release\latest-tinyseed-handoff.json" --future-branch-seed "$aurumRoot\Prompts\FutureBranchSeed.txt" --seed-source-commit $seedCommit --output evidence\google.json
.\.venv\Scripts\python.exe scripts\run_continuous_sweep.py microsoft --cycle 0 --aurum-build-manifest "$aurumRoot\Projects\Aurum\Release\latest-tinyseed-handoff.json" --future-branch-seed "$aurumRoot\Prompts\FutureBranchSeed.txt" --seed-source-commit $seedCommit --output evidence\microsoft.json
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

## Route a high-failure Aurum branch field

Create the candidate manifest without touching hardware:

```powershell
$aurumRoot = "C:\path\to\BoxBrain"
$seedCommit = git -C $aurumRoot rev-parse HEAD
.\.venv\Scripts\python.exe scripts\run_future_branch_qpu.py `
  --branch-state "$aurumRoot\Projects\Aurum\future-branches.json" `
  --calibration "$aurumRoot\Projects\Aurum\future-branch-calibration.json" `
  --experiments-dir "$aurumRoot\Projects\Aurum\Experiments" `
  --aurum-build-manifest "$aurumRoot\Projects\Aurum\Release\latest-tinyseed-handoff.json" `
  --future-branch-seed "$aurumRoot\Prompts\FutureBranchSeed.txt" `
  --seed-source-commit $seedCommit `
  --top-probability-fraction 0.05 `
  --output evidence\future-branch.json `
  --summary evidence\future-branch.md
```

Add `--confirm-qpu --shots 256` only for a separately authorized IBM hardware
run. If `--backend` is omitted, the tool selects the operational processor with
the shortest queue. The output contains hashes, branch weights, usage, backend,
and job ID, but never the API key.
