"""tests/test_todo.py - 测试 skills/todo.py

测试方法:
  - cmd_create_todo()      → 创建 todo 记录
  - cmd_plan_from_todo()   → 从 todo 生成任务计划
  - cmd_assign_task()      → 指派任务给目标 agent
  - cmd_list_todos()       → 列出所有 todo

使用:
  pytest tests/test_todo.py -v

预期输出:
  全部 PASSED
"""
import json
import pytest
from unittest.mock import patch

from skills.todo import cmd_create_todo, cmd_plan_from_todo, cmd_assign_task, cmd_list_todos
from tests.conftest import TEST_AGENT, TEST_SID, create_task_file


def make_args(**kwargs):
    from argparse import Namespace
    defaults = {"session_id": TEST_SID}
    defaults.update(kwargs)
    return Namespace(**defaults)


class TestCmdCreateTodo:
    """测试 cmd_create_todo()"""

    def test_create_todo_success(self, mock_tasks_dir, capsys, fixed_now, fixed_session_id):
        """验证成功创建 todo 文件"""
        tmp_path, tasks_dir = mock_tasks_dir
        args = make_args(session_id=None, description="user login feature",
                         creator=None)
        cmd_create_todo(TEST_AGENT, args)
        todo_path = tasks_dir / f"todo-{TEST_SID}.json"
        assert todo_path.exists()
        data = json.loads(todo_path.read_text(encoding="utf-8"))
        assert data["description"] == "user login feature"
        assert data["status"] == "pending"
        assert data["creator"] == TEST_AGENT
        captured = capsys.readouterr()
        assert "Todo" in captured.out


class TestCmdPlanFromTodo:
    """测试 cmd_plan_from_todo()"""

    def test_plan_from_todo_success(self, mock_tasks_dir, capsys, fixed_now, fixed_session_id):
        """验证成功从 todo 生成任务计划"""
        tmp_path, tasks_dir = mock_tasks_dir
        todo_path = tasks_dir / f"todo-{TEST_SID}.json"
        todo_data = {
            "sessionId": TEST_SID,
            "description": "user login",
            "creator": TEST_AGENT,
            "createdAt": "2026-05-09T10:00:00",
            "status": "pending",
            "linkedTaskFile": None,
        }
        todo_path.write_text(json.dumps(todo_data, ensure_ascii=False, indent=2),
                             encoding="utf-8")

        args = make_args(session_id=None, todo_session_id=TEST_SID)
        new_task_sid = "new-task-sid-001"
        with patch("skills.todo.resolve_session_id", return_value=new_task_sid):
            cmd_plan_from_todo(TEST_AGENT, args)

        task_path = tasks_dir / f"tasks-{new_task_sid}.json"
        assert task_path.exists()
        task_data = json.loads(task_path.read_text(encoding="utf-8"))
        assert task_data["userRequirement"] == "user login"
        assert task_data["status"] == "unassigned"
        assert task_data["createdFrom"] == f"todo-{TEST_SID}.json"

        todo_updated = json.loads(todo_path.read_text(encoding="utf-8"))
        assert todo_updated["status"] == "planned"
        assert todo_updated["linkedTaskSessionId"] == new_task_sid

    def test_plan_from_todo_not_found(self, mock_tasks_dir, capsys):
        """验证找不到 todo 文件时退出"""
        tmp_path, tasks_dir = mock_tasks_dir
        args = make_args(session_id=None, todo_session_id="nonexistent")
        with pytest.raises(SystemExit):
            cmd_plan_from_todo(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "todo" in captured.out.lower()


class TestCmdAssignTask:
    """测试 cmd_assign_task()"""

    def test_assign_task_success(self, mock_tasks_dir, capsys, fixed_now):
        """验证成功指派任务给目标 agent"""
        tmp_path, tasks_dir = mock_tasks_dir
        todo_path = tasks_dir / f"todo-{TEST_SID}.json"
        todo_data = {
            "sessionId": TEST_SID,
            "description": "user login",
            "creator": TEST_AGENT,
            "createdAt": "2026-05-09T10:00:00",
            "status": "planned",
            "linkedTaskFile": f"tasks-{TEST_SID}.json",
        }
        todo_path.write_text(json.dumps(todo_data, ensure_ascii=False, indent=2),
                             encoding="utf-8")

        task_data = {
            "userRequirement": "user login",
            "tasks": [],
            "ownerSession": TEST_SID,
            "sessionHistory": [],
            "status": "unassigned",
        }
        task_path = tasks_dir / f"tasks-{TEST_SID}.json"
        task_path.write_text(json.dumps(task_data, ensure_ascii=False, indent=2),
                             encoding="utf-8")

        args = make_args(session_id=None, todo_session_id=TEST_SID,
                         target_agent="target-agent",
                         target_session_id="target-sid-001")

        cmd_assign_task(TEST_AGENT, args)

        # 目标 agent 的 task 文件应在 target-agent 的工作区中
        target_tasks_dir = tmp_path / "workspace" / "target-agent" / "tasks"
        target_task_path = target_tasks_dir / "tasks-target-sid-001.json"
        assert target_task_path.exists()
        target_data = json.loads(target_task_path.read_text(encoding="utf-8"))
        assert target_data["assignedTo"] == "target-agent"
        assert target_data["status"] == "assigned"

        todo_updated = json.loads(todo_path.read_text(encoding="utf-8"))
        assert todo_updated["status"] == "assigned"

    def test_assign_no_linked_task(self, mock_tasks_dir, capsys):
        """验证 todo 未关联 task 文件时退出"""
        tmp_path, tasks_dir = mock_tasks_dir
        todo_path = tasks_dir / f"todo-{TEST_SID}.json"
        todo_data = {
            "sessionId": TEST_SID,
            "description": "test",
            "status": "pending",
            "linkedTaskFile": None,
        }
        todo_path.write_text(json.dumps(todo_data, ensure_ascii=False, indent=2),
                             encoding="utf-8")

        args = make_args(session_id=None, todo_session_id=TEST_SID,
                         target_agent="ta", target_session_id="ts")
        with pytest.raises(SystemExit):
            cmd_assign_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "plan_from_todo" in captured.out

    def test_assign_todo_not_found(self, mock_tasks_dir, capsys):
        """验证找不到 todo 文件时退出"""
        tmp_path, tasks_dir = mock_tasks_dir
        args = make_args(session_id=None, todo_session_id="nonexistent",
                         target_agent="ta", target_session_id="ts")
        with pytest.raises(SystemExit):
            cmd_assign_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "todo" in captured.out.lower()


class TestCmdListTodos:
    """测试 cmd_list_todos()"""

    def test_list_todos_empty(self, mock_tasks_dir, capsys):
        """验证无 todo 时输出提示"""
        tmp_path, tasks_dir = mock_tasks_dir
        args = make_args(status="all")
        cmd_list_todos(TEST_AGENT, args)
        captured = capsys.readouterr()
        # 避免 Windows 终端中文字符编码问题，使用 ASCII 文本断言
        assert "todo" in captured.out.lower()

    def test_list_todos_with_data(self, mock_tasks_dir, capsys):
        """验证列出所有 todo"""
        tmp_path, tasks_dir = mock_tasks_dir
        for sid, desc, status in [("todo-1", "desc-A", "pending"),
                                   ("todo-2", "desc-B", "planned")]:
            todo_path = tasks_dir / f"todo-{sid}.json"
            todo_path.write_text(json.dumps({
                "sessionId": sid, "description": desc,
                "status": status, "creator": TEST_AGENT,
            }, ensure_ascii=False, indent=2), encoding="utf-8")

        args = make_args(status="all")
        cmd_list_todos(TEST_AGENT, args)
        captured = capsys.readouterr()
        # 文件被正确读取时应有这些 ASCII 文本
        assert "desc-A" in captured.out
        assert "desc-B" in captured.out

    def test_list_todos_filtered(self, mock_tasks_dir, capsys):
        """验证按状态筛选 todo"""
        tmp_path, tasks_dir = mock_tasks_dir
        for sid, desc, status in [("todo-1", "desc-A", "pending"),
                                   ("todo-2", "desc-B", "planned")]:
            todo_path = tasks_dir / f"todo-{sid}.json"
            todo_path.write_text(json.dumps({
                "sessionId": sid, "description": desc,
                "status": status, "creator": TEST_AGENT,
            }, ensure_ascii=False, indent=2), encoding="utf-8")

        args = make_args(status="pending")
        cmd_list_todos(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "desc-A" in captured.out
        assert "desc-B" not in captured.out
