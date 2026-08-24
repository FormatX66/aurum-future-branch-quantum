from __future__ import annotations

import json
from pathlib import Path

import pytest

from aurum_quantum.aurum_seed import load_aurum_seed_build


def _write_seed_fixture(root: Path, *, schema: str = "aurum-tinyseed-handoff-v1") -> tuple[Path, Path]:
    manifest_path = root / "handoff.json"
    seed_path = root / "FutureBranchSeed.txt"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": schema,
                "source_commit": "1" * 40,
                "state": "READY_TO_FLASH",
                "next_gate": "physical-flash-and-boot-proof",
                "gates": {"build": "passed", "physical_boot": "pending"},
                "artifacts": {
                    "x86": {"sha256": "a" * 64},
                    "pi": {"sha256": "b" * 64},
                },
            }
        ),
        encoding="utf-8",
    )
    seed_path.write_text("Human chooses direction; machine clears the field.\n", encoding="utf-8")
    return manifest_path, seed_path


def test_seed_build_is_deterministic_and_preserves_unresolved_gates(tmp_path: Path) -> None:
    manifest_path, seed_path = _write_seed_fixture(tmp_path)
    seed = load_aurum_seed_build(
        manifest_path,
        seed_path,
        authority_commit="2" * 40,
    )

    assert seed.build_state == "READY_TO_FLASH"
    assert seed.next_gate == "physical-flash-and-boot-proof"
    assert seed.unresolved_gates == ("physical_boot",)
    assert seed.artifact_hashes == {"pi": "b" * 64, "x86": "a" * 64}
    assert seed.deterministic_seed == load_aurum_seed_build(
        manifest_path, seed_path, authority_commit="2" * 40
    ).deterministic_seed
    assert seed.mix_case_seed(7, cycle=3) == seed.mix_case_seed(7, cycle=3)
    assert seed.mix_case_seed(7) != seed.mix_case_seed(23)
    assert seed.mix_case_seed(7, cycle=1) != seed.mix_case_seed(7, cycle=2)


def test_seed_build_refuses_unknown_schema(tmp_path: Path) -> None:
    manifest_path, seed_path = _write_seed_fixture(tmp_path, schema="unknown-v9")
    with pytest.raises(ValueError, match="Unsupported Aurum seed schema"):
        load_aurum_seed_build(
            manifest_path,
            seed_path,
            authority_commit="2" * 40,
        )
