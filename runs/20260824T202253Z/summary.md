## Aurum Future Branch QPU router

- Strict branch failure rate: **63.6%**
- QPU threshold: `50.0%`
- QPU eligible: **True**
- Model decision: `pre-run`
- Scope: branch ranking and preparation only

| Rank | Machine path | Weight | Boundary |
|---:|---|---:|---|
| 1 | `hopper-preexecution-recovery-pass-resolves` | 0.3000 | True |
| 2 | `terminal-unrepaired-pass-releases-current-tinyseed-boundary` | 0.2013 | True |
| 3 | `preexecution-receipt-missing-or-stale` | 0.1432 | False |
| 4 | `x86-physical-flash-readback-passes-after-explicit-authority` | 0.1214 | True |
| 5 | `media-identity-or-release-changes-before-authorized-write` | 0.0921 | False |
| 6 | `canonical-carrier-fails-while-direct-uefi-fallback-remains-virtually-proven` | 0.0773 | True |
| 7 | `healthy-regrow-arms-trial` | 0.0462 | True |
| 8 | `physical-success-unlocks-universal-carrier-and-arm64-canaries` | 0.0186 | True |

## QPU submission

- Backend: `ibm_kingston`
- Job: `da6agamsidac73adt97g`
- Initial status: `QUEUED`
- Shots: `256`

## QPU result

- Final status: `DONE`
- Winning preparation path: `hopper-preexecution-recovery-pass-resolves`
- Winning shots: `80 / 256`
- Valid declared-path shots: `256 / 256`
- Total-variation distance from the encoded model weights: `0.0748`
- Distribution usable: **True**
- Open Plan usage after completion: `6 / 600 seconds`
