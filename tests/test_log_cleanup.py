"""日志保留天数清理测试。"""

import os
import time

from nex.logger import cleanup_old_logs


def test_cleanup_old_logs(tmp_path):
    old = tmp_path / "old.log"
    new = tmp_path / "new.log"
    old.write_text("old", encoding="utf-8")
    new.write_text("new", encoding="utf-8")

    old_time = time.time() - 10 * 86400
    os.utime(old, (old_time, old_time))

    assert cleanup_old_logs(7, tmp_path) == 1
    assert not old.exists()
    assert new.exists()
    assert cleanup_old_logs(0, tmp_path) == 0
