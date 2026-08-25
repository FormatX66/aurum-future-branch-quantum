from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "aurum-future-branch-interaction-frontier-v1"
DEFAULT_PRIORS = (
    ("status-handoff", 0.60, "Summarize what changed, what is ready, what is blocked, and the proof."),
    ("what-next", 0.25, "State the highest-value next action and whether it is machine-safe or a real human boundary."),
    ("proof-check", 0.15, "Answer whether Future Branch actually worked from durable run evidence, not activity alone."),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _selected_machine_path(candidate: dict[str, Any]) -> dict[str, Any] | None:
    selected = candidate.get("selected_machine_paths")
    if isinstance(selected, list) and selected:
        first = selected[0]
        return first if isinstance(first, dict) else None
    ranked = candidate.get("ranked_machine_paths")
    if isinstance(ranked, list):
        for item in ranked:
            if isinstance(item, dict) and item.get("selected_for_execution"):
                return item
    return None


def _provider_rows(provider_evidence: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in provider_evidence:
        if not isinstance(raw, dict):
            continue
        provider = str(raw.get("provider", raw.get("name", "unknown")))
        passed = bool(raw.get("passed", raw.get("success", False)))
        cases = raw.get("cases_executed", raw.get("cases", 0))
        failures = raw.get("failed_cases", raw.get("failures", []))
        rows.append(
            {
                "provider": provider,
                "passed": passed,
                "cases_executed": int(cases or 0),
                "failed_cases": list(failures) if isinstance(failures, list) else [str(failures)],
            }
        )
    rows.sort(key=lambda item: item["provider"])
    return rows


def build_interaction_frontier(
    *,
    candidate: dict[str, Any] | None,
    provider_evidence: Iterable[dict[str, Any]] = (),
    run: dict[str, Any] | None = None,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    """Materialize likely next human interactions without scheduling delivery.

    The packet is refreshed as a side effect of normal Future Branch work. It is not
    a reminder, notification, timer, or morning task. Nothing is delivered until a
    real user interaction asks for it.
    """
    candidate = candidate or {}
    run = run or {}
    recorded_at = recorded_at or _utc_now()
    machine = _selected_machine_path(candidate)
    seed = candidate.get("aurum_seed_build")
    seed = seed if isinstance(seed, dict) else {}
    providers = _provider_rows(provider_evidence)

    interaction_branches = []
    for name, probability, purpose in DEFAULT_PRIORS:
        interaction_branches.append(
            {
                "name": name,
                "prior_probability": probability,
                "purpose": purpose,
                "prepared": True,
                "delivery": "on-user-interaction-only",
            }
        )

    missing: list[str] = []
    if not candidate:
        missing.append("future-branch-candidate")
    if machine is None:
        missing.append("selected-machine-path")
    if not providers:
        missing.append("provider-evidence")

    handoff = {
        "status": "degraded" if missing else "ready",
        "build_state": seed.get("build_state", "unknown"),
        "next_gate": seed.get("next_gate", "unknown"),
        "unresolved_gates": seed.get("unresolved_gates", []),
        "selected_machine_path": (
            {
                "path": machine.get("name"),
                "probability": machine.get("probability"),
                "disposition": machine.get("disposition"),
                "next": machine.get("next"),
                "real_boundary": machine.get("real_boundary"),
            }
            if machine
            else None
        ),
        "provider_sweeps": providers,
        "missing_evidence": missing,
        "proof": {
            "branch_state_sha256": candidate.get("branch_state_sha256"),
            "calibration_sha256": candidate.get("calibration_sha256"),
            "future_branch_seed_sha256": seed.get("future_branch_seed_sha256"),
            "combined_fingerprint": seed.get("combined_fingerprint"),
        },
        "render_contract": {
            "use_prepared_packet_first": True,
            "fetch_only_newer_deltas_when_possible": True,
            "never_claim_delivery_before_user_interaction": True,
            "never_promote_unverified_physical_state": True,
        },
    }

    packet_source = json.dumps(
        {"candidate": candidate, "providers": providers, "run": run},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return {
        "schema": SCHEMA,
        "recorded_at": recorded_at,
        "activation": "next-user-interaction",
        "scheduled_delivery": False,
        "notification": False,
        "interaction_branches": interaction_branches,
        "selected_interaction_branch": "status-handoff",
        "handoff": handoff,
        "run": run,
        "source_sha256": hashlib.sha256(packet_source).hexdigest(),
    }


def render_interaction_frontier(frontier: dict[str, Any]) -> str:
    handoff = frontier["handoff"]
    machine = handoff.get("selected_machine_path") or {}
    lines = [
        "# Future Branch ready handoff",
        "",
        f"Recorded: `{frontier['recorded_at']}`",
        "",
        "This is a prepared next-interaction packet. It is not a scheduled delivery.",
        "",
        f"- Handoff state: **{handoff['status']}**",
        f"- Aurum build state: `{handoff['build_state']}`",
        f"- Next gate: `{handoff['next_gate']}`",
    ]
    if machine:
        lines.extend(
            [
                f"- Leading machine path: `{machine.get('path')}`",
                f"- Model probability: `{machine.get('probability')}`",
                f"- Disposition: `{machine.get('disposition')}`",
            ]
        )
    providers = handoff.get("provider_sweeps", [])
    if providers:
        lines.append("- Provider evidence: " + ", ".join(
            f"{item['provider']}={'pass' if item['passed'] else 'fail'}({item['cases_executed']})"
            for item in providers
        ))
    if handoff.get("unresolved_gates"):
        lines.append("- Unresolved gates: " + ", ".join(map(str, handoff["unresolved_gates"])))
    if handoff.get("missing_evidence"):
        lines.append("- Missing evidence: " + ", ".join(handoff["missing_evidence"]))
    lines.extend(
        [
            "",
            "Prepared for likely next questions: status/what is ready, what next, and proof that Future Branch worked.",
            "Render this packet when the user asks; do not create a timer or proactive morning notification.",
        ]
    )
    return "\n".join(lines) + "\n"


def persist_interaction_frontier(frontier: dict[str, Any], output_dir: Path) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    history_dir = output_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    run_id = str(frontier.get("run", {}).get("run_id", "unknown"))
    attempt = str(frontier.get("run", {}).get("run_attempt", "1"))
    history_path = history_dir / f"gha-{run_id}-attempt-{attempt}.json"
    latest_path = output_dir / "latest.json"
    latest_md_path = output_dir / "latest.md"
    payload = json.dumps(frontier, indent=2, sort_keys=True) + "\n"
    history_path.write_text(payload, encoding="utf-8")
    latest_path.write_text(payload, encoding="utf-8")
    latest_md_path.write_text(render_interaction_frontier(frontier), encoding="utf-8")
    return latest_path, latest_md_path, history_path
