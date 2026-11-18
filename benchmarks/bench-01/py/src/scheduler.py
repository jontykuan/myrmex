from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TaskItem:
    task_id: str
    priority: int
    created_seq: int
    window_start: int
    window_end: int


def eval_rule(facts: dict[str, Any], rule: dict[str, Any]) -> bool:
    """Slice 01 stub: evaluate typed rule against facts."""
    raise NotImplementedError("slice-01-core-eval")


def schedule_next(queue: list[TaskItem]) -> TaskItem | None:
    """Slice 02 stub: deterministic priority + FIFO tie-break."""
    raise NotImplementedError("slice-02-priority-queue")


def parse_task_input(raw: dict[str, Any]) -> TaskItem:
    """Slice 03 stub: strict schema validation & normalization."""
    raise NotImplementedError("slice-03-input-parser")


def in_window(ts: int, start: int, end: int) -> bool:
    """Slice 04 stub: half-open/closed window boundary check."""
    raise NotImplementedError("slice-04-window-bounds")
