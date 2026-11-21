"""任务数据库测试。"""

from nex.db import TaskRepository
from nex.task import TaskParams, TaskStatus, new_task


def test_add_get_update_delete(tmp_path):
    repo = TaskRepository(tmp_path / "nex.db")
    task = new_task(
        TaskParams(
            input_path=r"D:\视频\测试 视频.mp4",
            output_dir=r"D:\输出",
        )
    )
    repo.add(task)

    got = repo.get(task.id)
    assert got is not None
    assert got.file_name == "测试 视频.mp4"
    assert got.params.summary() == "2x / 2x"
    assert [t.id for t in repo.list_all()] == [task.id]

    got.status = TaskStatus.DONE
    got.progress = 100
    got.output_path = r"D:\输出\测试 视频_NEX.mp4"
    repo.update(got)

    again = repo.get(task.id)
    assert again.status == TaskStatus.DONE
    assert again.progress == 100
    assert again.output_path.endswith("_NEX.mp4")

    repo.delete(task.id)
    assert repo.get(task.id) is None
    assert repo.list_all() == []


def test_recover_running_resets_task(tmp_path):
    repo = TaskRepository(tmp_path / "nex.db")
    task = new_task(TaskParams(input_path="a.mp4"))
    task.status = TaskStatus.RUNNING
    task.progress = 42
    task.stage = "超分"
    repo.add(task)

    assert repo.recover_running() == 1
    got = repo.get(task.id)
    assert got.status == TaskStatus.PENDING
    assert got.progress == 0
    assert got.stage == ""


def test_list_pending_only(tmp_path):
    repo = TaskRepository(tmp_path / "nex.db")
    pending = new_task(TaskParams(input_path="pending.mp4"))
    done = new_task(TaskParams(input_path="done.mp4"))
    done.status = TaskStatus.DONE
    repo.add(pending)
    repo.add(done)

    result = repo.list_pending()
    assert [task.id for task in result] == [pending.id]
