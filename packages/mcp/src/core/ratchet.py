from typing import Any


def evaluate_ratchet(
    policies: list[dict[str, Any]],
    telemetry: dict[str, Any],
) -> list[str]:
    inactive = {p["gate_id"] for p in policies if not p["active"]}
    tier1_active = any(p["tier"] == 1 and p["active"] for p in policies)
    escalate: list[str] = []

    rules = {
        "diff_must_add_tests": telemetry.get("recent_regressions", 0) >= 2,
        "strict_typecheck": telemetry.get("type_error_count", 0) >= 3,
        "slice_loc_cap": telemetry.get("max_file_conflicts", 0) >= 3,
        "ast_complexity_cap": tier1_active
        and telemetry.get("tier1_attempts", 0) >= 8
        and telemetry.get("tier1_first_pass_rate", 1.0) < 0.5,
        "mutation_test": tier1_active and telemetry.get("recent_regressions", 0) >= 2,
    }
    for gate_id, triggered in rules.items():
        if gate_id in inactive and triggered:
            escalate.append(gate_id)
    return escalate
