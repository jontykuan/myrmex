import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bench-01" / "py"))
from src.scheduler import TaskItem, eval_rule, in_window, parse_task_input, schedule_next


def test_holdout_slice_01_eval_rule() -> None:
    assert eval_rule({"tier": "gold", "retries": 1}, {"field": "tier", "op": "eq", "value": "gold"}) is True
    assert eval_rule({"retries": 3}, {"field": "retries", "op": "lt", "value": 3}) is False
    assert eval_rule({}, {"field": "missing", "op": "eq", "value": None}) is False


def test_holdout_slice_02_schedule_next() -> None:
    assert schedule_next([]) is None
    t1 = TaskItem("a", 5, 2, 0, 10)
    t2 = TaskItem("b", 5, 1, 0, 10)
    t3 = TaskItem("c", 9, 5, 0, 10)
    assert schedule_next([t1, t2, t3]) == t3
    assert schedule_next([t1, t2]) == t2


def test_holdout_slice_03_parse_task_input() -> None:
    item = parse_task_input({"task_id": "x1", "priority": 2, "created_seq": 0, "window_start": 10, "window_end": 20})
    assert item.task_id == "x1"
    with pytest.raises(ValueError):
        parse_task_input({"task_id": "", "priority": "high"})


def test_holdout_slice_04_in_window_boundaries() -> None:
    assert in_window(10, 10, 20) is True
    assert in_window(20, 10, 20) is False
    assert in_window(9, 10, 20) is False
    assert in_window(10, 20, 10) is False
