from __future__ import annotations

import json

from aurum_quantum.interaction_frontier import (
    build_interaction_frontier,
    persist_interaction_frontier,
    render_interaction_frontier,
)


def _candidate() -> dict:
    return {
        "aurum_seed_build": {
            "build_state": "READY_TO_FLASH",
            "next_gate": "physical-flash-and-boot-proof",
            "unresolved_gates": ["guardian_forced_rollback", "physical_boot"],
            "future_branch_seed_sha256": "seed-hash",
            "combined_fingerprint": "fingerprint",
        },
        "branch_state_sha256": "branch-hash",
        "calibration_sha256": "calibration-hash",
        "selected_machine_paths": [
            {
                "name": "fresh-authority-triggers-live-reproof-and-guarded-preflight",
                "probability": 0.8888888889,
                "disposition": "wait-boundary",
                "next": "write only after fresh proof",
                "real_boundary": True,
            }
        ],
    }


def _providers() -> list[dict]:
    return [
        {
            "provider": "google",
            "passed": True,
            "cases_per_run": 9,
            "results": [{"evaluation": {"passed": True}} for _ in range(9)],
        },
        {
            "provider": "microsoft",
            "passed": True,
            "cases_per_run": 9,
            "results": [{"evaluation": {"passed": True}} for _ in range(9)],
        },
    ]


def test_frontier_is_prepared_but_never_scheduled() -> None:
    frontier = build_interaction_frontier(
        candidate=_candidate(),
        provider_evidence=_providers(),
        run={"run_id": "123", "run_attempt": "1"},
        recorded_at="2026-08-25T10:00:00+00:00",
    )
    assert frontier["activation"] == "next-user-interaction"
    assert frontier["scheduled_delivery"] is False
    assert frontier["notification"] is False
    assert frontier["selected_interaction_branch"] == "status-handoff"
    assert frontier["handoff"]["status"] == "ready"
    assert frontier["handoff"]["provider_sweeps"][0]["cases_executed"] == 9
    assert frontier["handoff"]["selected_machine_path"]["probability"] > 0.88


def test_missing_evidence_degrades_instead_of_fabricating_readiness() -> None:
    frontier = build_interaction_frontier(candidate=None, run={"run_id": "124"})
    assert frontier["handoff"]["status"] == "degraded"
    assert "future-branch-candidate" in frontier["handoff"]["missing_evidence"]
    assert frontier["handoff"]["build_state"] == "unknown"
    assert frontier["handoff"]["selected_machine_path"] is None


def test_persist_writes_render_ready_latest_and_history(tmp_path) -> None:
    frontier = build_interaction_frontier(
        candidate=_candidate(),
        provider_evidence=_providers(),
        run={"run_id": "125", "run_attempt": "2"},
        recorded_at="2026-08-25T10:05:00+00:00",
    )
    latest_json, latest_md, history = persist_interaction_frontier(frontier, tmp_path)
    assert latest_json.exists()
    assert latest_md.exists()
    assert history.name == "gha-125-attempt-2.json"
    assert json.loads(latest_json.read_text())["scheduled_delivery"] is False
    rendered = render_interaction_frontier(frontier)
    assert "not a scheduled delivery" in rendered
    assert "physical-flash-and-boot-proof" in rendered
