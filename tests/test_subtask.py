"""tests/test_subtask.py - 测试 skills/subtask.py

测试方法:
  - cmd_add_subtask()     → 向父任务追加子任务
  - cmd_resplit_task()    → 将原任务拆分为多个子任务

使用:
  pytest tests/test_subtask.py -v

预期输出:
  test_add_subtask_success ......... PASSED
  test_add_subtask_not_found ....... PASSED
  test_resplit_task_success ........ PASSED
  test_resplit_completed_task ...... PASSED
  test_resplit_empty_list .......... PASSED
  test_resplit_invalid_json ........ PASSED
  test_missing_session_id .......... PASSED
"""
import json
import pytest

from skills.subtask import cmd_add_subtask, cmd_resplit_task
from tests.conftest import TEST_AGENT, TEST_SID, SAMPLE_TASK, SAMPLE_COMPLETED_TASK, create_task_file


def make_args(**kwargs):
    from argparse import Namespace
    defaults = {"session_id": TEST_SID}
    defaults.update(kwargs)
    return Namespace(**defaults)


class TestCmdAddSubtask:
    """测试 cmd_add_subtask()"""

    def test_add_subtask_success(self, mock_tasks_dir, capsys, fixed_uuid, fixed_now):
        """验证成功向父任务追加子任务"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(parent_id=SAMPLE_TASK["id"],
                         name="实现 JWT 签发",
                         desc="实现 JWT token 的签发逻辑")
        cmd_add_subtask(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert "subtasks" in task
        assert len(task["subtasks"]) == 1
        assert task["subtasks"][0]["name"] == "实现 JWT 签发"
        assert task["subtasks"][0]["parentId"] == SAMPLE_TASK["id"]
        captured = capsys.readouterr()
        assert "已向任务" in captured.out
        assert "追加子任务" in captured.out

    def test_add_subtask_not_found(self, mock_tasks_dir, capsys):
        """验证找不到父任务时退出"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[])
        args = make_args(parent_id="nonexistent", name="子任务", desc="描述")
        with pytest.raises(SystemExit):
            cmd_add_subtask(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "找不到父任务" in captured.out


class TestCmdResplitTask:
    """测试 cmd_resplit_task()"""

    RESPLIT_JSON = json.dumps([
        {"name": "子任务1", "description": "子任务1描述",
         "implementationGuide": "指南1", "verificationCriteria": "标准1",
         "relatedFiles": [], "dependencies": []},
        {"name": "子任务2", "description": "子任务2描述",
         "implementationGuide": "指南2", "verificationCriteria": "标准2",
         "relatedFiles": [], "dependencies": []},
    ])

    def test_resplit_success(self, mock_tasks_dir, capsys, fixed_uuid, fixed_now):
        """验证成功将原任务拆分为多个子任务"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"], tasks=self.RESPLIT_JSON)
        cmd_resplit_task(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        assert len(data["tasks"]) == 2  # 原任务删除，创建 2 个新任务
        for t in data["tasks"]:
            assert t["parentTaskId"] == SAMPLE_TASK["id"]
            assert t["status"] == "pending"
        captured = capsys.readouterr()
        assert "已删除" in captured.out
        assert "创建了 2 个新子任务" in captured.out

    def test_resplit_completed_task(self, mock_tasks_dir, capsys):
        """验证已完成的任务不允许拆分"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_COMPLETED_TASK])
        args = make_args(id=SAMPLE_COMPLETED_TASK["id"], tasks=self.RESPLIT_JSON)
        with pytest.raises(SystemExit):
            cmd_resplit_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "已完成" in captured.out
        assert "不允许二次拆分" in captured.out

    def test_resplit_empty_list(self, mock_tasks_dir, capsys):
        """验证空任务列表时退出"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"], tasks="[]")
        with pytest.raises(SystemExit):
            cmd_resplit_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "不能为空" in captured.out

    def test_resplit_invalid_json(self, mock_tasks_dir, capsys):
        """验证 JSON 解析失败时退出"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"], tasks="不是JSON")
        with pytest.raises(SystemExit):
            cmd_resplit_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "JSON 解析失败" in captured.out

    def test_resplit_not_found(self, mock_tasks_dir, capsys):
        """验证找不到原任务时退出"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[])
        args = make_args(id="nonexistent", tasks="[]")
        with pytest.raises(SystemExit):
            cmd_resplit_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "找不到任务" in captured.out


class TestMissingSessionId:
    """测试缺少 session_id 的场景"""

    def test_add_subtask_missing_sid(self, capsys):
        args = make_args(session_id=None, parent_id="p", name="n", desc="d")
        with pytest.raises(SystemExit):
            cmd_add_subtask(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 --session-id" in captured.out

    def test_resplit_missing_sid(self, capsys):
        args = make_args(session_id=None, id="t", tasks="[]")
        with pytest.raises(SystemExit):
            cmd_resplit_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 --session-id" in captured.out
