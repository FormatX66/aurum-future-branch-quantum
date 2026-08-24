from __future__ import annotations

import pytest

from aurum_quantum.progression import (
    LaneProgress,
    LaneState,
    WorkflowDisposition,
    evaluate_workflow_progress,
)


def test_human_boundary_does_not_stall_independent_provider_lanes() -> None:
    progress = evaluate_workflow_progress(
        (
            LaneProgress("quantinuum-login", LaneState.HUMAN_BOUNDARY),
            LaneProgress("azure-subscription", LaneState.HUMAN_BOUNDARY),
            LaneProgress("provider-simulators", LaneState.RUNNING),
            LaneProgress("rigetti-fallback", LaneState.READY),
        )
    )

    assert progress.disposition is WorkflowDisposition.PROGRESSING
    assert progress.ask_human_now is False
    assert progress.continue_lanes == ("provider-simulators", "rigetti-fallback")
    assert progress.human_boundary_lanes == (
        "quantinuum-login",
        "azure-subscription",
    )


def test_refused_cost_lane_can_still_prepare_safe_artifacts() -> None:
    progress = evaluate_workflow_progress(
        (
            LaneProgress("aws-sign-in", LaneState.HUMAN_BOUNDARY),
            LaneProgress(
                "braket-cost-manifest",
                LaneState.REFUSED,
                safe_preparation_ready=True,
            ),
        )
    )

    assert progress.disposition is WorkflowDisposition.PROGRESSING
    assert progress.ask_human_now is False
    assert progress.continue_lanes == ("braket-cost-manifest",)


def test_human_is_asked_only_when_no_machine_route_remains() -> None:
    progress = evaluate_workflow_progress(
        (
            LaneProgress("ionq-password", LaneState.HUMAN_BOUNDARY),
            LaneProgress("pasqal-verification", LaneState.HUMAN_BOUNDARY),
        )
    )

    assert progress.disposition is WorkflowDisposition.AWAITING_HUMAN
    assert progress.ask_human_now is True


def test_external_observation_precedes_human_handoff() -> None:
    progress = evaluate_workflow_progress(
        (
            LaneProgress("ibm-marrakesh", LaneState.WAITING_EXTERNAL),
            LaneProgress("aws-sign-in", LaneState.HUMAN_BOUNDARY),
        )
    )

    assert progress.disposition is WorkflowDisposition.OBSERVING
    assert progress.ask_human_now is False


def test_progression_rejects_empty_or_duplicate_lanes() -> None:
    with pytest.raises(ValueError, match="At least one"):
        evaluate_workflow_progress(())
    with pytest.raises(ValueError, match="unique"):
        evaluate_workflow_progress(
            (
                LaneProgress("same", LaneState.READY),
                LaneProgress("same", LaneState.RUNNING),
            )
        )
