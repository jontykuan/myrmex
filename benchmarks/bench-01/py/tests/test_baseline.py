import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.scheduler import TaskItem


def test_task_item_dataclass_exists() -> None:
    item = TaskItem("t1", 1, 0, 10, 20)
    assert item.task_id == "t1"
