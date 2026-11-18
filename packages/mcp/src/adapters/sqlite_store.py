import json
from pathlib import Path
import sqlite3
import threading
from typing import Any
import uuid
from packages.mcp.src.core.scope import find_scope_conflict

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS pheromones (
  id TEXT PRIMARY KEY,
  target_ref TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('task_seed','test_red','type_error','smell_refactor','conflict_hotspot','blocked_unknown')),
  intensity REAL NOT NULL,
  decay_rate REAL NOT NULL,
  payload TEXT,
  emitter_id TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  expires_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_pheromones_target ON pheromones(target_ref, kind);
CREATE INDEX IF NOT EXISTS idx_pheromones_expiry ON pheromones(expires_at);
CREATE TABLE IF NOT EXISTS leases (
  slice_id TEXT PRIMARY KEY,
  worker_id TEXT NOT NULL,
  worktree TEXT NOT NULL,
  file_scope TEXT NOT NULL,
  acquired_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_leases_expiry ON leases(expires_at);
CREATE TABLE IF NOT EXISTS gate_policies (
  gate_id TEXT PRIMARY KEY,
  tier INTEGER NOT NULL CHECK (tier IN (0, 1, 2)),
  command TEXT NOT NULL,
  active INTEGER NOT NULL CHECK (active IN (0, 1)),
  trigger_rule TEXT,
  last_triggered_at INTEGER
);
CREATE TABLE IF NOT EXISTS telemetry_events (
  event_id TEXT PRIMARY KEY,
  experiment_id TEXT,
  task_id TEXT,
  worker_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  slice_id TEXT,
  tokens_in INTEGER DEFAULT 0,
  tokens_out INTEGER DEFAULT 0,
  duration_ms INTEGER DEFAULT 0,
  outcome TEXT,
  metadata_json TEXT,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_telemetry_exp ON telemetry_events(experiment_id, task_id);
"""


class SqliteStateStore:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def list_pheromones(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM pheromones").fetchall()
        return [{**dict(r), "payload": json.loads(r["payload"]) if r["payload"] else None} for r in rows]

    def list_active_leases(self, now: int) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM leases WHERE expires_at > ?", (now,)).fetchall()
        return [{**dict(r), "file_scope": json.loads(r["file_scope"])} for r in rows]

    def get_lease(self, slice_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM leases WHERE slice_id = ?", (slice_id,)).fetchone()
        return {**dict(row), "file_scope": json.loads(row["file_scope"])} if row else None

    def acquire_lease(
        self, slice_id: str, worker_id: str, worktree: str, file_scope: list[str], now: int, ttl_sec: int
    ) -> dict[str, Any]:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                self._conn.execute("DELETE FROM leases WHERE expires_at <= ?", (now,))
                rows = self._conn.execute("SELECT slice_id, file_scope, expires_at FROM leases").fetchall()
                active = [{**dict(r), "file_scope": json.loads(r["file_scope"])} for r in rows]
                conflict = find_scope_conflict(file_scope, active, now)
                if conflict:
                    self._conn.execute("ROLLBACK")
                    return {"status": "CONFLICT_LEASED", "conflict_owner": conflict}
                exp = now + ttl_sec
                self._conn.execute(
                    "INSERT INTO leases (slice_id, worker_id, worktree, file_scope, acquired_at, expires_at) VALUES (?,?,?,?,?,?)",
                    (slice_id, worker_id, worktree, json.dumps(file_scope), now, exp),
                )
                self._conn.execute("COMMIT")
                return {"status": "CLAIMED", "expires_at": exp}
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def extend_lease(self, slice_id: str, worker_id: str, extend_sec: int, now: int) -> dict[str, Any]:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            row = self._conn.execute(
                "SELECT expires_at FROM leases WHERE slice_id = ? AND worker_id = ? AND expires_at > ?",
                (slice_id, worker_id, now),
            ).fetchone()
            if not row:
                self._conn.execute("ROLLBACK")
                return {"status": "LEASE_EXPIRED"}
            new_exp = int(row["expires_at"]) + extend_sec
            self._conn.execute("UPDATE leases SET expires_at = ? WHERE slice_id = ?", (new_exp, slice_id))
            self._conn.execute("COMMIT")
            return {"status": "EXTENDED", "expires_at": new_exp}

    def release_lease(self, slice_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM leases WHERE slice_id = ?", (slice_id,))

    def emit_pheromone(
        self,
        worker_id: str,
        target_ref: str,
        kind: str,
        intensity: float,
        decay_rate: float,
        ttl_sec: int | None,
        payload: dict[str, Any] | None,
        now: int,
        release_slice_id: str | None = None,
    ) -> dict[str, Any]:
        pid = str(uuid.uuid4())
        exp = (now + ttl_sec) if ttl_sec is not None else None
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            self._conn.execute(
                "INSERT INTO pheromones (id, target_ref, kind, intensity, decay_rate, payload, emitter_id, created_at, updated_at, expires_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (pid, target_ref, kind, intensity, decay_rate, json.dumps(payload) if payload else None, worker_id, now, now, exp),
            )
            if release_slice_id:
                self._conn.execute("DELETE FROM leases WHERE slice_id = ?", (release_slice_id,))
            self._conn.execute("COMMIT")
        return {"pheromone_id": pid, "updated_intensity": intensity}

    def clear_attractive_pheromones(self, target_ref: str) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM pheromones WHERE target_ref = ? AND kind IN ('task_seed','test_red','type_error','smell_refactor')",
                (target_ref,),
            )

    def log_telemetry(
        self,
        worker_id: str,
        event_type: str,
        now: int,
        slice_id: str | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        duration_ms: int = 0,
        outcome: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO telemetry_events (event_id, worker_id, event_type, slice_id, tokens_in, tokens_out, duration_ms, outcome, metadata_json, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), worker_id, event_type, slice_id, tokens_in, tokens_out, duration_ms, outcome, json.dumps(metadata) if metadata else None, now),
            )

    def list_gate_policies(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM gate_policies ORDER BY tier ASC").fetchall()
        return [dict(r) for r in rows]

    def upsert_gate_policy(self, gate_id: str, tier: int, command: str, active: int) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO gate_policies (gate_id, tier, command, active) VALUES (?,?,?,?) ON CONFLICT(gate_id) DO UPDATE SET tier=excluded.tier, command=excluded.command, active=excluded.active",
                (gate_id, tier, command, active),
            )

    def activate_gates(self, gate_ids: list[str], now: int) -> None:
        if not gate_ids:
            return
        with self._lock:
            for gid in gate_ids:
                self._conn.execute("UPDATE gate_policies SET active = 1, last_triggered_at = ? WHERE gate_id = ?", (now, gid))
