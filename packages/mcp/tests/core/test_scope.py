from packages.mcp.src.core.scope import find_scope_conflict


def test_detects_glob_overlap_with_active_lease() -> None:
    leases = [{"slice_id": "s1", "file_scope": ["src/auth/**"], "expires_at": 200}]
    assert find_scope_conflict(["src/auth/login.ts"], leases, now=150) == "s1"


def test_ignores_expired_lease_at_exact_expiry() -> None:
    leases = [{"slice_id": "s1", "file_scope": ["src/auth/**"], "expires_at": 150}]
    assert find_scope_conflict(["src/auth/login.ts"], leases, now=150) is None


def test_allows_disjoint_scope() -> None:
    leases = [{"slice_id": "s1", "file_scope": ["src/auth/**"], "expires_at": 200}]
    assert find_scope_conflict(["src/billing/pay.ts"], leases, now=150) is None
