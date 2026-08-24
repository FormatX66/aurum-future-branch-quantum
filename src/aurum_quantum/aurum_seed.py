from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


AURUM_SEED_REPOSITORY = "https://github.com/FormatX66/BoxBrain"
AURUM_BUILD_SCHEMA = "aurum-tinyseed-handoff-v1"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class AurumSeedBuild:
    source_repository: str
    authority_commit: str
    build_source_commit: str
    build_state: str
    next_gate: str
    gates: dict[str, str]
    unresolved_gates: tuple[str, ...]
    artifact_hashes: dict[str, str]
    manifest_sha256: str
    future_branch_seed_sha256: str
    combined_fingerprint: str
    deterministic_seed: int

    def mix_case_seed(self, base_seed: int, *, cycle: int = 0) -> int:
        if cycle < 0:
            raise ValueError("cycle must not be negative")
        mixed = (
            self.deterministic_seed
            ^ (base_seed * 0x45D9F3B)
            ^ (cycle * 0x27D4EB2D)
            ^ int(self.combined_fingerprint[16:24], 16)
        ) % (2**31 - 1)
        return mixed or 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_sha256(value: Any, *, field: str) -> str:
    normalized = str(value).lower()
    if not _SHA256_PATTERN.fullmatch(normalized):
        raise ValueError(f"{field} must be a 64-character SHA-256 value")
    return normalized


def load_aurum_seed_build(
    manifest_path: Path,
    future_branch_seed_path: Path,
    *,
    authority_commit: str,
) -> AurumSeedBuild:
    authority_commit = authority_commit.lower()
    if not _COMMIT_PATTERN.fullmatch(authority_commit):
        raise ValueError("authority_commit must be a 40-character Git commit")

    manifest_bytes = manifest_path.read_bytes()
    future_branch_seed_bytes = future_branch_seed_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict):
        raise ValueError("Aurum seed manifest must be a JSON object")
    if manifest.get("schema") != AURUM_BUILD_SCHEMA:
        raise ValueError(
            f"Unsupported Aurum seed schema: {manifest.get('schema')!r}"
        )

    build_source_commit = str(manifest.get("source_commit", "")).lower()
    if not _COMMIT_PATTERN.fullmatch(build_source_commit):
        raise ValueError("Aurum build source_commit must be a 40-character commit")
    build_state = str(manifest.get("state", "")).strip()
    next_gate = str(manifest.get("next_gate", "")).strip()
    if not build_state or not next_gate:
        raise ValueError("Aurum seed manifest requires state and next_gate")

    gates_value = manifest.get("gates")
    if not isinstance(gates_value, dict) or not gates_value:
        raise ValueError("Aurum seed manifest requires a nonempty gates object")
    gates = {str(name): str(status) for name, status in sorted(gates_value.items())}
    unresolved_gates = tuple(
        name for name, status in gates.items() if status.lower() != "passed"
    )

    artifacts_value = manifest.get("artifacts")
    if not isinstance(artifacts_value, dict) or not artifacts_value:
        raise ValueError("Aurum seed manifest requires a nonempty artifacts object")
    artifact_hashes: dict[str, str] = {}
    for platform, artifact in sorted(artifacts_value.items()):
        if not isinstance(artifact, dict):
            raise ValueError(f"Aurum artifact {platform!r} must be an object")
        artifact_hashes[str(platform)] = _require_sha256(
            artifact.get("sha256"), field=f"artifacts.{platform}.sha256"
        )

    manifest_sha256 = _sha256(manifest_bytes)
    future_branch_seed_sha256 = _sha256(future_branch_seed_bytes)
    combined_fingerprint = _sha256(
        bytes.fromhex(manifest_sha256) + bytes.fromhex(future_branch_seed_sha256)
    )
    deterministic_seed = int(combined_fingerprint[:16], 16) % (2**31 - 1)
    if deterministic_seed == 0:
        deterministic_seed = 1

    return AurumSeedBuild(
        source_repository=AURUM_SEED_REPOSITORY,
        authority_commit=authority_commit,
        build_source_commit=build_source_commit,
        build_state=build_state,
        next_gate=next_gate,
        gates=gates,
        unresolved_gates=unresolved_gates,
        artifact_hashes=artifact_hashes,
        manifest_sha256=manifest_sha256,
        future_branch_seed_sha256=future_branch_seed_sha256,
        combined_fingerprint=combined_fingerprint,
        deterministic_seed=deterministic_seed,
    )
