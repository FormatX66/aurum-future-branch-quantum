from __future__ import annotations

import pytest

from aurum_quantum.continuous_sweep import (
    CASE_CATALOG,
    SHOT_VALUES,
    SweepCase,
    evaluate_counts,
    select_cycle_cases,
)


def test_catalog_covers_every_declared_variable_combination() -> None:
    assert len(CASE_CATALOG) == 45
    assert {case.workload for case in CASE_CATALOG} == {"bell", "ghz3", "rotation"}
    assert {case.shots for case in CASE_CATALOG} == set(SHOT_VALUES)
    assert {case.seed for case in CASE_CATALOG} == {7, 23, 101}
    assert {case.angle_quarters for case in CASE_CATALOG if case.workload == "rotation"} == {
        1,
        2,
        3,
    }
    assert len({case.case_id for case in CASE_CATALOG}) == len(CASE_CATALOG)


def test_five_cycles_cover_the_catalog_without_gaps() -> None:
    selected = [case for cycle in range(5) for case in select_cycle_cases(cycle)]
    assert selected == list(CASE_CATALOG)


def test_cycle_wraps_deterministically() -> None:
    assert select_cycle_cases(5) == select_cycle_cases(0)
    with pytest.raises(ValueError, match="cycle"):
        select_cycle_cases(-1)


def test_correlated_and_rotation_evaluations() -> None:
    bell = SweepCase("bell", shots=64, seed=7)
    assert evaluate_counts(bell, {"00": 31, "11": 32, "01": 1})["passed"] is True

    rotation = SweepCase("rotation", shots=64, seed=7, angle_quarters=2)
    assert evaluate_counts(rotation, {"0": 32, "1": 32})["passed"] is True
    assert evaluate_counts(rotation, {"00": 64})["passed"] is False
