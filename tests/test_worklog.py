"""tests/test_worklog.py - 测试 skills/worklog.py

测试方法:
  - cmd_add_work_log()    → 向任务追加工作记录
  - cmd_cancel_task()     → 取消任务（含子任务取消）

使用:
  pytest tests/test_worklog.py -v

预期输出:
  test_add_work_log_success ............ PASSED
  test_add_work_log_with_files ........ PASSED
  test_add_work_log_not_found ......... PASSED
  test_cancel_task_success ............ PASSED
  test_cancel_subtask_success ......... PASSED
  test_cancel_completed_task .......... PASSED
  test_cancel_not_found ............... PASSED
  test_missing_session_id ............. PASSED
"""
import json
import pytest

from skills.worklog import cmd_add_work_log, cmd_cancel_task
from tests.conftest import TEST_AGENT, TEST_SID, SAMPLE_TASK, SAMPLE_COMPLETED_TASK, create_task_file


def make_args(**kwargs):
    from argparse import Namespace
    defaults = {"session_id": TEST_SID}
    defaults.update(kwargs)
    return Namespace(**defaults)


class TestCmdAddWorkLog:
    """测试 cmd_add_work_log()"""

    def test_add_work_log_success(self, mock_tasks_dir, capsys, fixed_now):
        """验证成功追加工作记录"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"], type="code_change",
                         content="实现了 JWT 签发逻辑",
                         files=None, line_range=None)
        cmd_add_work_log(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        logs = data["tasks"][0]["workLog"]
        assert len(logs) == 1
        assert logs[0]["type"] == "code_change"
        assert logs[0]["content"] == "实现了 JWT 签发逻辑"
        captured = capsys.readouterr()
        assert "已向任务" in captured.out
        assert "追加工作记录" in captured.out

    def test_add_work_log_with_files_json(self, mock_tasks_dir, capsys, fixed_now):
        """验证工作记录中的 files 字段（JSON 格式）"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"], type="code_change",
                         content="修改文件", files='["a.py","b.py"]',
                         line_range="10-20")
        cmd_add_work_log(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        log = data["tasks"][0]["workLog"][0]
        assert log["files"] == ["a.py", "b.py"]
        assert log["lineRange"] == "10-20"

    def test_add_work_log_files_csv_fallback(self, mock_tasks_dir, capsys, fixed_now):
        """验证 files 不是 JSON 时的 CSV 降级解析"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"], type="other",
                         content="调研", files="a.py, b.py",
                         line_range=None)
        cmd_add_work_log(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        log = data["tasks"][0]["workLog"][0]
        assert "a.py" in log["files"]
        assert "b.py" in log["files"]

    def test_add_work_log_not_found(self, mock_tasks_dir, capsys):
        """验证找不到任务时退出"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[])
        args = make_args(id="nonexistent", type="other", content="test",
                         files=None, line_range=None)
        with pytest.raises(SystemExit):
            cmd_add_work_log(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "找不到任务" in captured.out


class TestCmdCancelTask:
    """测试 cmd_cancel_task()"""

    def test_cancel_task_success(self, mock_tasks_dir, capsys, fixed_now):
        """验证成功取消任务"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"], reason="需求变更")
        cmd_cancel_task(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert task["status"] == "cancelled"
        assert task["cancelReason"] == "需求变更"
        captured = capsys.readouterr()
        assert "任务已取消" in captured.out

    def test_cancel_subtask_success(self, mock_tasks_dir, capsys, fixed_now):
        """验证成功取消子任务"""
        tmp_path, tasks_dir = mock_tasks_dir
        subtask = {"id": "sub-1234", "name": "子任务", "status": "todo"}
        parent = dict(SAMPLE_TASK, subtasks=[subtask])
        create_task_file(tasks_dir, TEST_SID, tasks=[parent])
        args = make_args(id="sub-1234", reason="子任务不再需要")
        cmd_cancel_task(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        assert data["tasks"][0]["subtasks"][0]["status"] == "cancelled"
        captured = capsys.readouterr()
        assert "子任务已取消" in captured.out

    def test_cancel_completed_task(self, mock_tasks_dir, capsys):
        """验证已完成的任务不可取消"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_COMPLETED_TASK])
        args = make_args(id=SAMPLE_COMPLETED_TASK["id"], reason="test")
        with pytest.raises(SystemExit):
            cmd_cancel_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "已完成的任务不可取消" in captured.out

    def test_cancel_not_found(self, mock_tasks_dir, capsys):
        """验证找不到任务或子任务时退出"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id="nonexistent", reason="test")
        with pytest.raises(SystemExit):
            cmd_cancel_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "找不到任务或子任务" in captured.out


class TestMissingSessionId:
    """测试缺少 session_id 的场景"""

    def test_add_work_log_missing_sid(self, capsys):
        args = make_args(session_id=None, id="t", type="other", content="c",
                         files=None, line_range=None)
        with pytest.raises(SystemExit):
            cmd_add_work_log(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 --session-id" in captured.out

    def test_cancel_missing_sid(self, capsys):
        args = make_args(session_id=None, id="t", reason="r")
        with pytest.raises(SystemExit):
            cmd_cancel_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 --session-id" in captured.out
