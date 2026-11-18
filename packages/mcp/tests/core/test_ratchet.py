from packages.mcp.src.core.ratchet import evaluate_ratchet


def test_escalates_strict_typecheck_at_three_type_errors() -> None:
    policies = [
        {"gate_id": "strict_typecheck", "tier": 1, "active": 0},
        {"gate_id": "diff_must_add_tests", "tier": 1, "active": 0},
    ]
    telemetry = {"type_error_count": 3, "recent_regressions": 0, "max_file_conflicts": 0, "tier1_first_pass_rate": 1.0, "tier1_attempts": 0}
    assert evaluate_ratchet(policies, telemetry) == ["strict_typecheck"]


def test_escalates_diff_must_add_tests_on_two_regressions() -> None:
    policies = [{"gate_id": "diff_must_add_tests", "tier": 1, "active": 0}]
    telemetry = {"type_error_count": 0, "recent_regressions": 2, "max_file_conflicts": 0, "tier1_first_pass_rate": 1.0, "tier1_attempts": 0}
    assert evaluate_ratchet(policies, telemetry) == ["diff_must_add_tests"]


def test_escalates_ast_complexity_when_tier1_active_and_low_pass_rate() -> None:
    policies = [
        {"gate_id": "strict_typecheck", "tier": 1, "active": 1},
        {"gate_id": "ast_complexity_cap", "tier": 2, "active": 0},
    ]
    telemetry = {"type_error_count": 0, "recent_regressions": 0, "max_file_conflicts": 0, "tier1_first_pass_rate": 0.4, "tier1_attempts": 8}
    assert evaluate_ratchet(policies, telemetry) == ["ast_complexity_cap"]


def test_does_not_escalate_tier2_when_tier1_inactive_or_rate_at_half() -> None:
    policies = [{"gate_id": "ast_complexity_cap", "tier": 2, "active": 0}]
    telemetry = {"type_error_count": 0, "recent_regressions": 0, "max_file_conflicts": 0, "tier1_first_pass_rate": 0.5, "tier1_attempts": 8}
    assert evaluate_ratchet(policies, telemetry) == []
