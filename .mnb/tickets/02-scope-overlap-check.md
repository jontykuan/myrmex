# 02: File Scope Overlap Detection

**What to build:** Pure predicate checking whether a requested `file_scope` glob list conflicts with any non-expired active lease.
**Blocked by:** None (frontier)
**Target files:** `packages/mcp/src/core/scope.py`, `packages/mcp/tests/core/test_scope.py`
**Size budget:** <= 20 LOC

## Acceptance Criteria (Deterministic Contracts)
- [ ] Given active lease `{slice_id: "s1", file_scope: ["src/auth/**"], expires_at: 200}` at `t = 150`, When checking candidate scope `["src/auth/login.ts"]`, Then overlap returns `true` with `conflict_owner: "s1"`.
- [ ] Given active lease `{slice_id: "s1", file_scope: ["src/auth/**"], expires_at: 150}` at `t = 150`, When checking candidate scope `["src/auth/login.ts"]`, Then overlap returns `false`.
- [ ] Given active lease `{slice_id: "s1", file_scope: ["src/auth/**"], expires_at: 200}` at `t = 150`, When checking candidate scope `["src/billing/pay.ts"]`, Then overlap returns `false`.

## Deterministic Verification
- Unit test path: `packages/mcp/tests/core/test_scope.py`
- Mutation target: `packages/mcp/src/core/scope.py`
- Mutants to kill:
  - Changing `expires_at <= t` expiry check to `expires_at < t` must turn tests red.
  - Returning `false` on directory-glob vs file-path match must turn tests red.
