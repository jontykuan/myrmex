from fnmatch import fnmatch
from typing import Any


def _patterns_overlap(a: str, b: str) -> bool:
    if fnmatch(a, b) or fnmatch(b, a):
        return True
    pa, pb = a.rstrip("/*"), b.rstrip("/*")
    return bool(pa and pb and (a.startswith(pb + "/") or b.startswith(pa + "/")))


def find_scope_conflict(
    requested_scope: list[str],
    leases: list[dict[str, Any]],
    now: int,
) -> str | None:
    for lease in leases:
        if int(lease["expires_at"]) <= now:
            continue
        for req in requested_scope:
            if any(_patterns_overlap(req, held) for held in lease["file_scope"]):
                return str(lease["slice_id"])
    return None
