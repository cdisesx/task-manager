"""tests/test_block.py - 测试 skills/block.py

测试方法:
  - cmd_block_task()     → 以 question 类型阻塞任务
  - cmd_block_queue()    → 以 queue 类型阻塞任务
  - cmd_unblock_task()   → 解除阻塞任务

使用:
  pytest tests/test_block.py -v

预期输出:
  test_block_task_success ......... PASSED
  test_block_task_completed ...... PASSED
  test_block_task_not_found ...... PASSED
  test_block_queue_success ....... PASSED
  test_unblock_task_success ...... PASSED
  test_unblock_not_blocked ....... PASSED
  test_missing_session_id ........ PASSED
"""
import json
import pytest

from skills.block import cmd_block_task, cmd_block_queue, cmd_unblock_task
from tests.conftest import TEST_AGENT, TEST_SID, SAMPLE_TASK, SAMPLE_COMPLETED_TASK, create_task_file


def make_args(**kwargs):
    from argparse import Namespace
    defaults = {"session_id": TEST_SID}
    defaults.update(kwargs)
    return Namespace(**defaults)


class TestCmdBlockTask:
    """测试 cmd_block_task() - question 类型阻塞"""

    def test_block_task_success(self, mock_tasks_dir, capsys, fixed_now):
        """验证成功将任务阻塞为 question 类型"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"], reason="需要确认技术方案",
                         question="使用 JWT 还是 OAuth？")
        cmd_block_task(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert task["status"] == "blocked"
        assert task["blockInfo"]["blockType"] == "question"
        assert task["blockInfo"]["question"] == "使用 JWT 还是 OAuth？"
        captured = capsys.readouterr()
        assert "[BLOCKED]" in captured.out

    def test_block_task_completed(self, mock_tasks_dir, capsys):
        """验证已完成的任务不可阻塞"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_COMPLETED_TASK])
        args = make_args(id=SAMPLE_COMPLETED_TASK["id"], reason="test", question="test")
        with pytest.raises(SystemExit):
            cmd_block_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "已完成的任务不可阻塞" in captured.out

    def test_block_task_not_found(self, mock_tasks_dir, capsys):
        """验证找不到任务时退出"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[])
        args = make_args(id="nonexistent", reason="test", question="test")
        with pytest.raises(SystemExit):
            cmd_block_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "找不到任务" in captured.out


class TestCmdBlockQueue:
    """测试 cmd_block_queue() - queue 类型阻塞"""

    def test_block_queue_success(self, mock_tasks_dir, capsys, fixed_now):
        """验证成功将任务阻塞为 queue 类型"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"], reason="等待上游完成",
                         waiting_for="数据库迁移任务完成")
        cmd_block_queue(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert task["status"] == "blocked"
        assert task["blockInfo"]["blockType"] == "queue"
        assert task["blockInfo"]["waitingFor"] == "数据库迁移任务完成"
        captured = capsys.readouterr()
        assert "[BLOCKED/QUEUE]" in captured.out


class TestCmdUnblockTask:
    """测试 cmd_unblock_task()"""

    def test_unblock_success(self, mock_tasks_dir, capsys, fixed_now):
        """验证成功解除阻塞"""
        tmp_path, tasks_dir = mock_tasks_dir
        blocked_task = dict(SAMPLE_TASK, status="blocked",
                            blockInfo={"blockType": "question",
                                       "reason": "需要确认",
                                       "question": "使用 JWT？",
                                       "blockedAt": "2026-05-09T10:00:00",
                                       "unblockAnswer": None,
                                       "unblockedAt": None})
        create_task_file(tasks_dir, TEST_SID, tasks=[blocked_task])
        args = make_args(id=SAMPLE_TASK["id"], answer="使用 JWT")
        cmd_unblock_task(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert task["status"] == "in_progress"
        assert task["blockInfo"]["unblockAnswer"] == "使用 JWT"
        assert task["blockInfo"]["unblockedAt"] is not None
        captured = capsys.readouterr()
        assert "[UNBLOCKED]" in captured.out

    def test_unblock_not_blocked(self, mock_tasks_dir, capsys):
        """验证非 blocked 状态的任务无法解除阻塞"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"], answer="test")
        with pytest.raises(SystemExit):
            cmd_unblock_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "只有 blocked 任务可以解除阻塞" in captured.out


class TestBlockMissingSessionId:
    """测试缺少 session_id 的场景"""

    def test_block_task_missing_sid(self, capsys):
        args = make_args(session_id=None, id="test", reason="test", question="test")
        with pytest.raises(SystemExit):
            cmd_block_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 --session-id" in captured.out

    def test_block_queue_missing_sid(self, capsys):
        args = make_args(session_id=None, id="test", reason="test", waiting_for="test")
        with pytest.raises(SystemExit):
            cmd_block_queue(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 --session-id" in captured.out

    def test_unblock_missing_sid(self, capsys):
        args = make_args(session_id=None, id="test", answer="test")
        with pytest.raises(SystemExit):
            cmd_unblock_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 --session-id" in captured.out
