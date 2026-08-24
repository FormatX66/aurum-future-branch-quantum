from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class JobEnvelope:
    workload_id: str
    problem_class: str
    formulation: str
    provider: str
    backend: str
    shots: int
    qpu_approved: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

