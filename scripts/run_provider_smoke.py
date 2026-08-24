from __future__ import annotations

import argparse
import json

from aurum_quantum.provider_smoke import SMOKE_RUNNERS, run_provider_smoke


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("provider", choices=sorted(SMOKE_RUNNERS))
    parser.add_argument("--shots", type=int, default=512)
    args = parser.parse_args()
    if not 1 <= args.shots <= 4096:
        parser.error("shots must be between 1 and 4096")
    result = run_provider_smoke(args.provider, shots=args.shots)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
