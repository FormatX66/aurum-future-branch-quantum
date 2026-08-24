from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class LaneState(StrEnum):
    READY = "ready"
    RUNNING = "running"
    WAITING_EXTERNAL = "waiting_external"
    HUMAN_BOUNDARY = "human_boundary"
    SUCCESS = "success"
    NO_CHANGE = "no_change"
    REFUSED = "refused"
    FAILED = "failed"


class WorkflowDisposition(StrEnum):
    PROGRESSING = "progressing"
    OBSERVING = "observing"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass(frozen=True)
class LaneProgress:
    name: str
    state: LaneState
    safe_preparation_ready: bool = False


@dataclass(frozen=True)
class WorkflowProgress:
    disposition: WorkflowDisposition
    ask_human_now: bool
    continue_lanes: tuple[str, ...]
    human_boundary_lanes: tuple[str, ...]


def evaluate_workflow_progress(lanes: Iterable[LaneProgress]) -> WorkflowProgress:
    """Keep independent work moving when one lane reaches a human boundary.

    A human-only gate is scoped to its lane. It becomes a workflow-wide request
    only after no safe ready/running/preparable lane and no external observation
    remains. This prevents account, identity, or approval gates from turning a
    broad Future Branch field into a stagnant handoff list.
    """

    values = tuple(lanes)
    if not values:
        raise ValueError("At least one workflow lane is required")
    if any(not lane.name.strip() for lane in values):
        raise ValueError("Workflow lane names must not be empty")
    names = tuple(lane.name for lane in values)
    if len(set(names)) != len(names):
        raise ValueError("Workflow lane names must be unique")

    human_boundary_lanes = tuple(
        lane.name for lane in values if lane.state is LaneState.HUMAN_BOUNDARY
    )
    continue_lanes = tuple(
        lane.name
        for lane in values
        if lane.state in {LaneState.READY, LaneState.RUNNING}
        or lane.safe_preparation_ready
    )
    observing_lanes = tuple(
        lane.name for lane in values if lane.state is LaneState.WAITING_EXTERNAL
    )

    if continue_lanes:
        disposition = WorkflowDisposition.PROGRESSING
        ask_human_now = False
    elif observing_lanes:
        disposition = WorkflowDisposition.OBSERVING
        ask_human_now = False
    elif human_boundary_lanes:
        disposition = WorkflowDisposition.AWAITING_HUMAN
        ask_human_now = True
    elif all(lane.state in {LaneState.SUCCESS, LaneState.NO_CHANGE} for lane in values):
        disposition = WorkflowDisposition.COMPLETE
        ask_human_now = False
    else:
        disposition = WorkflowDisposition.FAILED
        ask_human_now = False

    return WorkflowProgress(
        disposition=disposition,
        ask_human_now=ask_human_now,
        continue_lanes=continue_lanes,
        human_boundary_lanes=human_boundary_lanes,
    )
