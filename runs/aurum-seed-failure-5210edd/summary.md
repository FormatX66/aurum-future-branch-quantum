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
- Job: `da6qf83sq5js73bj391g`
- Initial status: `QUEUED`
- Shots: `256`

## Live outcome

- Status: **DONE**
- Declared Aurum path shots: `256 / 256`
- Unexpected-state shots: `0`
- Total-variation distance: `0.043296`
- Full rank agreement: `1.0000` Spearman
- Top-path agreement: **True**
- Selected path observed mass: `0.242188` (expected `0.275753`)
- Maximum absolute path-weight delta: `0.033566`
- Execution gate changed: **False**
- Recommendation: `retain-top-probability-execution-selection`

## Injected failure tests

- Corrupted Aurum artifact hash: refused by the seed loader.
- Pruned path receives all shots: model review required; execution gate unchanged.
- Undeclared state receives all shots: no winning path, unusable result, execution gate unchanged.
- Failure probes passed: **3 / 3**
- Physical or destructive effects executed: **False**
