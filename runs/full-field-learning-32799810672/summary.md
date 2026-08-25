## Aurum Future Branch QPU router

- Strict branch failure rate: **66.7%**
- QPU threshold: `50.0%`
- QPU eligible: **True**
- Model decision: `pre-run`
- QPU weighting: full ranked field before execution pruning
- Probability field retained: **5.0%**
- Selected paths: `1 / 8`
- Pruned paths: `7`

| Rank | Machine path | Probability | QPU weight | Execution weight | Selected | Boundary |
|---:|---|---:|---:|---:|---|---|
| 1 | `fresh-authority-triggers-live-reproof-and-guarded-preflight` | 0.8889 | 0.2758 | 1.0000 | True | True |
| 2 | `x86-physical-flash-readback-passes-after-explicit-authority` | 0.6667 | 0.1742 | 0.0000 | False | True |
| 3 | `media-identity-release-or-protection-state-changes-before-write` | 0.7778 | 0.1689 | 0.0000 | False | True |
| 4 | `guarded-flash-refuses-or-readback-mismatches` | 0.5556 | 0.1379 | 0.0000 | False | True |
| 5 | `physical-boot-success-with-possible-network-or-regrow-defer` | 0.4444 | 0.1050 | 0.0000 | False | True |
| 6 | `canonical-carrier-fails-while-direct-uefi-fallback-remains-virtually-proven` | 0.3333 | 0.0752 | 0.0000 | False | True |
| 7 | `healthy-regrow-arms-trial` | 0.2222 | 0.0450 | 0.0000 | False | True |
| 8 | `physical-success-unlocks-universal-carrier-and-arm64-canaries` | 0.1111 | 0.0181 | 0.0000 | False | True |

## QPU submission

- Backend: `ibm_kingston`
- Job: `da6mta46l22c73dmhqig`
- Initial status: `QUEUED`
- Shots: `256`

## QPU result

- Final status: `DONE`
- First observed completion: `2026-08-25T10:30:46.090676Z`
- Elapsed to first observed result: `59.374770 seconds`
- Counts across declared paths: `256 / 256`
- Padding shots: `0`
- Winning path: `fresh-authority-triggers-live-reproof-and-guarded-preflight`
- Winning shots: `76 / 256` (`29.6875%`)
- Expected winning weight: `27.5753%`
- Total-variation distance: `0.037443`
- Full-order Spearman agreement: `1.0`
- Selected execution mass: expected `27.5753%`, observed `29.6875%`, delta `+2.1122 pp`
- Maximum absolute per-path weight delta: `2.1122 pp`
- Distribution usable: **True**
- IBM Open Plan usage after result: `12 / 600 seconds`

## Learning outcome

- Full-field weighting hypothesis: **supported**. All eight paths received
  nonzero samples and their complete observed ordering matched the expected
  ordering.
- Execution-gate hypothesis: **supported**. The sampled winner is the same path
  retained by the top-5% probability gate.
- Gate update: **none**. Continue to retain the current top-probability path and
  hold it at the physical authorization boundary.
- Divergence rule: if a usable future result disagrees on the leading path or
  selects a pruned path, pause promotion and review the model before execution.
