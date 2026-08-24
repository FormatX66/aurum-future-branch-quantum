from __future__ import annotations

import pytest

from aurum_quantum.provider_smoke import SMOKE_RUNNERS, qiskit_smoke, run_provider_smoke


def test_qiskit_smoke_is_exact_and_secret_free() -> None:
    result = qiskit_smoke().to_dict()
    assert result["passed"] is True
    assert result["evidence"]["correlated_probability"] == pytest.approx(1.0)
    assert "token" not in str(result).lower()
    assert "api_key" not in str(result).lower()


def test_provider_registry_is_bounded_and_explicit() -> None:
    assert set(SMOKE_RUNNERS) == {
        "qiskit",
        "cirq",
        "braket",
        "quera",
        "rigetti",
        "quantinuum",
        "pasqal",
    }
    with pytest.raises(ValueError, match="Unknown provider"):
        run_provider_smoke("not-a-provider")
