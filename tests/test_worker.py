"""工作线程队列行为测试（使用假管线，不占用 GPU）。"""

from types import SimpleNamespace

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from nex import worker as worker_mod
from nex.db import TaskRepository
from nex.task import TaskParams, TaskStatus, new_task


def test_worker_processes_task_and_updates_db(tmp_path, monkeypatch):
    repo = TaskRepository(tmp_path / "nex.db")
    task = new_task(TaskParams(input_path="input.mp4"))
    repo.add(task)

    events: list[tuple[str, str, str]] = []

    def fake_run(options, on_progress=None, cancel=None, on_log=None):
        assert options.task_id == task.id
        if on_log:
            on_log("00:00:01 [探测] 测试")
        if on_progress:
            on_progress("超分", 50.0, "一半")
            on_progress("合成", 100.0, "完成")
        return SimpleNamespace(
            output_path=tmp_path / "output.mp4",
            log_path=tmp_path / "task.log",
        )

    monkeypatch.setattr(worker_mod, "run_pipeline", fake_run)

    app = QCoreApplication.instance() or QCoreApplication([])
    worker = worker_mod.PipelineWorker(repo)
    loop = QEventLoop()
    worker.taskFinished.connect(
        lambda task_id, outcome, message: events.append(
            (task_id, outcome, message)
        )
    )
    worker.taskFinished.connect(lambda *_: loop.quit())
    QTimer.singleShot(5000, loop.quit)

    worker.enqueue(task.id)
    loop.exec()
    worker.stop()
    worker.wait(5000)

    assert events and events[0][0] == task.id
    assert events[0][1] == "done"
    stored = repo.get(task.id)
    assert stored.status == TaskStatus.DONE
    assert stored.progress == 100
    assert stored.output_path.endswith("output.mp4")
    assert stored.log_path.endswith("task.log")
