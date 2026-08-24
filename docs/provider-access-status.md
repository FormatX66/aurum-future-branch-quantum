# Provider access status

Status: 2026-08-24 15:51 America/New_York

This document records access state without credentials. A provider can be
configured before it is enabled; hardware execution stays disabled until the
account, pricing, and job are explicitly approved.

| Access path | State | Next gate |
|---|---|---|
| IBM Quantum | Live Open Plan; Fez and Kingston smoke tests passed; Marrakesh queued | Poll the existing Marrakesh job; do not resubmit |
| Amazon Braket | Braket console open at AWS sign-in | AWS account/root or IAM sign-in; then budgets, S3 results location, and QPU allowlist |
| Quantinuum | Q-Net and 48-question Guppy/H2 application prefilled; two-page proposal prepared | User facts, Q-Net conduct acknowledgement, proposal attachment, and explicit submissions by 2026-09-07 |
| Azure Quantum | Account reported working by Bruce; Microsoft QDK local stack active | GitHub workload identity is not configured; live jobs remain off |
| IonQ direct | Free simulator account prefilled | User-created password, terms review, and final account creation |
| Rigetti direct | QCS inquiry prefilled for secure API research access | Truthful role/organization type, reCAPTCHA, and explicit submit |
| QuEra direct | Premium Aquila inquiry prefilled | Review and explicit send; Braket remains the standard comparison path |
| Pasqal direct | Account awaiting email verification | Verify mailbox link, log in, and start with Explorer emulation |
| Google Quantum Engine | Account and project `aurum-future-branch-quantum` reported working; Cirq local stack active | GitHub workload identity is not configured; live jobs remain off |

## Hardware evidence

- `ibm_kingston`: 253/256 correlated Bell outcomes, 98.83%, pass.
- `ibm_fez`: 249/256 correlated Bell outcomes, 97.27%, pass.
- `ibm_marrakesh`: submitted once and queued.
- IBM Open Plan usage after the completed jobs: 4 of 600 seconds.

No paid provider account, subscription, workspace, API key, or additional QPU
job was created during access preparation.
