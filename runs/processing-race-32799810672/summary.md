## Aurum Future Branch QPU router

- Strict branch failure rate: **66.7%**
- QPU threshold: `50.0%`
- QPU eligible: **True**
- Model decision: `pre-run`
- Scope: branch ranking and preparation only
- Probability field retained: **5.0%**
- Selected paths: `1 / 8`
- Pruned paths: `7`

| Rank | Machine path | Probability | Execution weight | Selected | Boundary |
|---:|---|---:|---:|---|---|
| 1 | `fresh-authority-triggers-live-reproof-and-guarded-preflight` | 0.8889 | 1.0000 | True | True |
| 2 | `x86-physical-flash-readback-passes-after-explicit-authority` | 0.6667 | 0.0000 | False | True |
| 3 | `media-identity-release-or-protection-state-changes-before-write` | 0.7778 | 0.0000 | False | True |
| 4 | `guarded-flash-refuses-or-readback-mismatches` | 0.5556 | 0.0000 | False | True |
| 5 | `physical-boot-success-with-possible-network-or-regrow-defer` | 0.4444 | 0.0000 | False | True |
| 6 | `canonical-carrier-fails-while-direct-uefi-fallback-remains-virtually-proven` | 0.3333 | 0.0000 | False | True |
| 7 | `healthy-regrow-arms-trial` | 0.2222 | 0.0000 | False | True |
| 8 | `physical-success-unlocks-universal-carrier-and-arm64-canaries` | 0.1111 | 0.0000 | False | True |

## QPU submission

- Backend: `ibm_kingston`
- Job: `da6g1qjsq5js73bimkg0`
- Initial status: `QUEUED`
- Shots: `256`

## QPU result

- Final status: `DONE`
- Completed check: `2026-08-25T02:42:21.584135Z`
- Winning path: `fresh-authority-triggers-live-reproof-and-guarded-preflight`
- Counts: `0 = 256 / 256`
- Padding shots: `0`
- Total-variation distance: `0.0`
- Distribution usable: **True**
- IBM Open Plan usage: `10 / 600 seconds` (`2` seconds added by this test)

## Processing-run comparison

- BoxBrain workflow: `32799810672` (`Aurum Hopper Live Status`)
- Bound BoxBrain commit: `9ffc2b4563b4f5801c9e1733604cf16615f7055c`
- Comparison state at QPU submission: `queued`
- Comparison state after QPU completion: `queued`
- QPU elapsed time from manifest creation to result check: `46.565273 seconds`

## Assessment

- Timing-path hypothesis: **supported**. The QPU completed while the self-hosted
  workflow remained queued.
- Weighting-advantage hypothesis: **refuted for this field**. Top-5% pruning
  retained only one branch, so the QPU sampled a deterministic distribution and
  did not improve the branch choice.
- Useful routing rule: use QPU weighting only when pruning retains at least two
  materially competitive paths; use deterministic selection for a one-path
  field.
