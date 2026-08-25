# Provider access status

Status: 2026-08-25 06:35 America/New_York

This document records access state without credentials. A provider can be
configured before it is enabled; hardware execution stays disabled until the
account, pricing, and job are explicitly approved.

| Access path | State | Next gate |
|---|---|---|
| IBM Quantum | Live Open Plan; Fez, Kingston, and Marrakesh Bell tests passed; full-field Future Branch weighting passed on Kingston | Accumulate only changed-state full-field evidence; do not replay the same branch field |
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
- `ibm_marrakesh`: 251/256 correlated Bell outcomes, 98.05%, pass.
- `ibm_kingston` Future Branch: job `da6agamsidac73adt97g`, 256 shots,
  eight current Aurum machine paths, completed. All shots mapped to declared
  paths; total-variation distance was 0.0748; the sampled winner was
  `hopper-preexecution-recovery-pass-resolves` with 80 shots.
- `ibm_kingston` top-5%-only comparison: job `da6g1qjsq5js73bimkg0`,
  256/256 shots on the sole retained path. This verified execution but added no
  weighting information because pruning happened before sampling.
- `ibm_kingston` full-field learning: job `da6mta46l22c73dmhqig`, eight paths,
  256 shots, zero padding, total-variation distance 0.0374, full-order Spearman
  agreement 1.0, and the top sampled path matched the top-5% execution gate.
- IBM Open Plan usage after the completed jobs: 12 of 600 seconds.

No paid provider account, subscription, workspace, or API key was created. The
Future Branch jobs use the existing IBM Open Plan and did not require a charge
acceptance.
