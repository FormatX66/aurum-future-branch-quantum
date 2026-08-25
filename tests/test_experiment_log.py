from __future__ import annotations

import json
from pathlib import Path

from aurum_quantum.experiment_log import build_experiment_log, write_experiment_log


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_log_preserves_hypotheses_failures_outcomes_and_next_branches(tmp_path: Path) -> None:
    candidate_path = _write_json(tmp_path / "candidate.json", {"schema": "candidate"})
    candidate = {
        "schema": "candidate",
        "submission": None,
        "analysis": {
            "qpu_eligible": True,
            "branch_state_sha256": "a" * 64,
            "calibration_sha256": "b" * 64,
            "aurum_seed_build": {"authority_commit": "c" * 40},
            "failure": {
                "events": 12,
                "partial": 5,
                "miss": 3,
                "strict_failure_rate": 8 / 12,
                "high_failure_threshold": 0.5,
            },
            "selection": {
                "top_probability_fraction": 0.05,
                "population_size": 8,
                "selected_count": 1,
                "pruned_count": 7,
            },
            "selected_machine_paths": [
                {
                    "name": "leader",
                    "probability": 8 / 9,
                    "disposition": "wait-boundary",
                    "real_boundary": True,
                    "next": "wait for explicit authority",
                }
            ],
            "pruned_machine_paths": [
                {"name": f"pruned-{index}"} for index in range(7)
            ],
        },
    }
    provider_path = _write_json(
        tmp_path / "google.json",
        {
            "provider": "google",
            "passed": True,
            "cycle": 1,
            "effective_cycle": 2,
            "results": [{"case": {"case_id": "bell"}, "evaluation": {"passed": True}}],
        },
    )
    record = build_experiment_log(
        run_id="123",
        run_attempt=1,
        workflow_name="continuous-variable-flow",
        workflow_url="https://example.test/runs/123",
        runner_commit="d" * 40,
        router_outcome="success",
        candidate=candidate,
        candidate_path=candidate_path,
        provider_evidence=[(json.loads(provider_path.read_text()), provider_path)],
        expected_providers=["google", "microsoft"],
        resumed_from_run_id="122",
        recovered_failure="schema v11 was rejected",
    )

    assert record["hypotheses"][0]["probability"] == 8 / 9
    assert record["outcomes"]["selected_branch"]["status"] == "held-at-real-boundary"
    assert record["outcomes"]["overall"] == "failure"
    assert {item["status"] for item in record["failures"]} == {"missing", "recovered"}
    assert record["next_branch_updates"][0]["next"] == "wait for explicit authority"

    path = write_experiment_log(record, tmp_path / "logs")
    assert path.exists()
    assert json.loads((tmp_path / "logs" / "index.jsonl").read_text())["run_id"] == "123"
