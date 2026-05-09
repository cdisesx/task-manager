"""tests/test_task_crud.py - 测试 core/task_crud.py（核心 CRUD 操作）

测试方法（共 25+ 个测试用例）:
  cmd_get_session_id()     → 打印 session ID
  cmd_plan_task()          → 设置用户需求
  cmd_split_tasks()        → 按不同 mode 创建/更新任务
  cmd_list_tasks()         → 按状态筛选列出任务
  cmd_get_task_detail()    → 查看任务详情
  cmd_execute_task()       → 执行任务（含依赖检查）
  cmd_verify_task()        → 验证任务（含 work_log 解析）
  cmd_complete_task()      → 完成任务（含 memory hook 调用）
  cmd_update_task()        → 更新任务字段
  cmd_delete_task()        → 删除任务（含依赖检查）
  cmd_query_task()         → 搜索任务
  cmd_archive()            → 归档 session
  cmd_complete_session()   → 批量完成
  cmd_claim_task()         → 认领任务文件

使用:
  pytest tests/test_task_crud.py -v

预期输出:
  全部 PASSED
"""
import json
import sys
from unittest.mock import patch, MagicMock
from argparse import Namespace

import pytest

from core.task_crud import (
    cmd_get_session_id, cmd_plan_task, cmd_split_tasks, cmd_list_tasks,
    cmd_get_task_detail, cmd_execute_task, cmd_verify_task, cmd_complete_task,
    cmd_update_task, cmd_delete_task, cmd_query_task, cmd_archive,
    cmd_complete_session, cmd_claim_task,
)

from tests.conftest import (
    TEST_AGENT, TEST_SID, TEST_SID_2,
    SAMPLE_TASK, SAMPLE_TASK_2, SAMPLE_COMPLETED_TASK,
    create_task_file,
)


# ── 辅助函数 ───────────────────────────────────────────────────────────────────

def make_args(**kwargs):
    """创建一个模拟的 argparse.Namespace 对象"""
    defaults = {
        "session_id": TEST_SID,
        "agent": TEST_AGENT,
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


# ══════════════════════════════════════════════════════════════════════════════
# cmd_get_session_id
# ══════════════════════════════════════════════════════════════════════════════

class TestCmdGetSessionId:
    """测试 cmd_get_session_id()"""

    def test_print_session_id(self, capsys):
        """验证打印 resolve_session_id() 的结果"""
        with patch("core.task_crud.resolve_session_id", return_value="mock-sid-123"):
            cmd_get_session_id(TEST_AGENT, make_args())
        captured = capsys.readouterr()
        assert captured.out.strip() == "mock-sid-123"


# ══════════════════════════════════════════════════════════════════════════════
# cmd_plan_task
# ══════════════════════════════════════════════════════════════════════════════

class TestCmdPlanTask:
    """测试 cmd_plan_task()"""

    def test_plan_task_sets_requirement(self, mock_tasks_dir, capsys):
        """验证 plan_task 设置用户需求并归档旧需求"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_COMPLETED_TASK],
                         requirement="旧需求")
        args = make_args(description="新需求", requirements=None)
        with patch("core.task_crud.render_prompt", return_value="[rendered]"):
            cmd_plan_task(TEST_AGENT, args)
        # 验证已归档旧需求
        data_file = tasks_dir / f"tasks-{TEST_SID}.json"
        data = json.loads(data_file.read_text(encoding="utf-8"))
        assert data["userRequirement"].startswith("新需求")
        assert len(data["history"]) == 1
        assert data["history"][0]["description"] == "旧需求"

    def test_plan_task_with_requirements(self, mock_tasks_dir, capsys):
        """验证 plan_task 附加技术要求"""
        tmp_path, tasks_dir = mock_tasks_dir
        args = make_args(description="实现登录", requirements="使用 JWT")
        with patch("core.task_crud.render_prompt", return_value="[rendered]"):
            cmd_plan_task(TEST_AGENT, args)
        data_file = tasks_dir / f"tasks-{TEST_SID}.json"
        data = json.loads(data_file.read_text(encoding="utf-8"))
        assert "技术要求" in data["userRequirement"]
        assert "JWT" in data["userRequirement"]

    def test_plan_task_missing_session_id(self, capsys):
        """验证缺少 session_id 时退出"""
        args = make_args(session_id=None, description="test")
        with pytest.raises(SystemExit):
            cmd_plan_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 --session-id" in captured.out


# ══════════════════════════════════════════════════════════════════════════════
# cmd_split_tasks
# ══════════════════════════════════════════════════════════════════════════════

class TestCmdSplitTasks:
    """测试 cmd_split_tasks()"""

    NEW_TASKS_JSON = json.dumps([
        {"name": "任务A", "description": "描述A",
         "implementationGuide": "指南A", "verificationCriteria": "标准A",
         "relatedFiles": [], "dependencies": []},
        {"name": "任务B", "description": "描述B",
         "implementationGuide": "指南B", "verificationCriteria": "标准B",
         "relatedFiles": [], "dependencies": []},
    ])

    def test_split_append(self, mock_tasks_dir, capsys, fixed_uuid, fixed_now):
        """验证 append 模式：保留所有已有任务并追加新任务"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK], requirement="需求")
        args = make_args(mode="append", tasks=self.NEW_TASKS_JSON,
                         user_requirement=None, analysis=None)
        with patch("core.task_crud.render_prompt", return_value=""):
            cmd_split_tasks(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        # 原有 1 个 + 新 2 个 = 3 个
        assert len(data["tasks"]) == 3

    def test_split_overwrite(self, mock_tasks_dir, capsys, fixed_uuid, fixed_now):
        """验证 overwrite 模式：只保留已完成任务"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID,
                         tasks=[SAMPLE_COMPLETED_TASK, SAMPLE_TASK])
        args = make_args(mode="overwrite", tasks=self.NEW_TASKS_JSON,
                         user_requirement=None, analysis=None)
        with patch("core.task_crud.render_prompt", return_value=""):
            cmd_split_tasks(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        # 保留已完成(1) + 新创建的(2) = 3
        assert len(data["tasks"]) == 3

    def test_split_selective(self, mock_tasks_dir, capsys, fixed_uuid, fixed_now):
        """验证 selective 模式：更新已有任务并添加新任务"""
        tmp_path, tasks_dir = mock_tasks_dir
        existing_task = dict(SAMPLE_TASK, status="pending")
        create_task_file(tasks_dir, TEST_SID, tasks=[existing_task])
        update_json = json.dumps([
            {"name": "实现用户登录功能", "description": "更新后的描述",
             "implementationGuide": "新指南", "verificationCriteria": "新标准",
             "relatedFiles": [], "dependencies": []},
        ])
        args = make_args(mode="selective", tasks=update_json,
                         user_requirement=None, analysis="新分析结果")
        with patch("core.task_crud.render_prompt", return_value=""):
            cmd_split_tasks(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["description"] == "更新后的描述"
        assert data["tasks"][0]["analysisResult"] == "新分析结果"

    def test_split_clearAllTasks(self, mock_tasks_dir, capsys, fixed_uuid, fixed_now):
        """验证 clearAllTasks 模式：清空并备份已完成任务"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID,
                         tasks=[SAMPLE_COMPLETED_TASK, SAMPLE_TASK])
        args = make_args(mode="clearAllTasks", tasks="[]",
                         user_requirement=None, analysis=None)
        with patch("core.task_crud.render_prompt", return_value=""):
            cmd_split_tasks(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        assert len(data["tasks"]) == 0
        # 验证备份文件
        memory_dir = tasks_dir / "memory"
        backup_files = list(memory_dir.glob("*.json"))
        assert len(backup_files) == 1

    def test_split_invalid_json(self, capsys):
        """验证 --tasks 参数 JSON 格式错误时退出"""
        args = make_args(mode="append", tasks="不是JSON", user_requirement=None, analysis=None)
        with pytest.raises(SystemExit):
            cmd_split_tasks(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "JSON 解析失败" in captured.out
        assert '"name"' in captured.out  # 包含示例 JSON 提示

    def test_split_not_a_list(self, capsys):
        """验证 --tasks 不是数组时退出"""
        args = make_args(mode="append", tasks='"just a string"',
                         user_requirement=None, analysis=None)
        with pytest.raises(SystemExit):
            cmd_split_tasks(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "必须是一个 JSON 数组" in captured.out

    def test_split_item_not_a_dict(self, capsys):
        """验证 --tasks 中的元素不是对象时退出（如 ["123"]）"""
        args = make_args(mode="append", tasks='["123"]',
                         user_requirement=None, analysis=None)
        with pytest.raises(SystemExit):
            cmd_split_tasks(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "第 1 项不是任务对象" in captured.out
        assert '["123"]' in captured.out

    def test_split_item_missing_name(self, capsys):
        """验证 --tasks 中的对象缺少 name 字段时退出"""
        args = make_args(mode="append",
                         tasks='[{"description": "没有name字段"}]',
                         user_requirement=None, analysis=None)
        with pytest.raises(SystemExit):
            cmd_split_tasks(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 name 字段" in captured.out

    def test_split_missing_session_id(self, capsys):
        """验证缺少 session_id 时退出"""
        args = make_args(session_id=None, mode="append", tasks="[]",
                         user_requirement=None, analysis=None)
        with pytest.raises(SystemExit):
            cmd_split_tasks(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 --session-id" in captured.out


# ══════════════════════════════════════════════════════════════════════════════
# cmd_list_tasks
# ══════════════════════════════════════════════════════════════════════════════

class TestCmdListTasks:
    """测试 cmd_list_tasks()"""

    def test_list_tasks_empty(self, mock_tasks_dir, capsys):
        """验证无任务时输出空提示并列出可认领的任务文件"""
        tmp_path, tasks_dir = mock_tasks_dir
        # 创建另一个 session 的任务文件
        create_task_file(tasks_dir, "other-sid", tasks=[SAMPLE_TASK],
                         owner_session="other-sid")
        args = make_args(status="all")
        cmd_list_tasks(TEST_AGENT, args)
        captured = capsys.readouterr()
        # 使用 ASCII 文本断言避免 Windows 终端编码问题
        assert "claim_task" in captured.out
        assert "ownerSession" in captured.out

    def test_list_tasks_by_status(self, mock_tasks_dir, capsys):
        """验证按状态筛选任务"""
        tmp_path, tasks_dir = mock_tasks_dir
        tasks = [SAMPLE_TASK, SAMPLE_TASK_2, SAMPLE_COMPLETED_TASK]
        create_task_file(tasks_dir, TEST_SID, tasks=tasks, requirement="需求")
        args = make_args(status="completed")
        with patch("core.task_crud.render_prompt", return_value=""):
            cmd_list_tasks(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "[OK] 已完成" in captured.out
        assert "[PENDING]" not in captured.out

    def test_list_tasks_missing_session_id(self, capsys):
        """验证缺少 session_id 时退出"""
        args = make_args(session_id=None, status="all")
        with pytest.raises(SystemExit):
            cmd_list_tasks(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 --session-id" in captured.out


# ══════════════════════════════════════════════════════════════════════════════
# cmd_get_task_detail
# ══════════════════════════════════════════════════════════════════════════════

class TestCmdGetTaskDetail:
    """测试 cmd_get_task_detail()"""

    def test_get_task_detail_found(self, mock_tasks_dir, capsys):
        """验证找到任务时打印详情"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"])
        cmd_get_task_detail(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "[TASK]" in captured.out
        assert "实现用户登录功能" in captured.out
        assert "pending" in captured.out

    def test_get_task_detail_not_found(self, mock_tasks_dir, capsys):
        """验证找不到任务时退出"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[])
        args = make_args(id="nonexistent-id")
        with pytest.raises(SystemExit):
            cmd_get_task_detail(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "找不到任务" in captured.out

    def test_get_task_detail_missing_session_id(self, capsys):
        """验证缺少 session_id 时退出"""
        args = make_args(session_id=None, id="test")
        with pytest.raises(SystemExit):
            cmd_get_task_detail(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 --session-id" in captured.out


# ══════════════════════════════════════════════════════════════════════════════
# cmd_execute_task
# ══════════════════════════════════════════════════════════════════════════════

class TestCmdExecuteTask:
    """测试 cmd_execute_task()"""

    def test_execute_success(self, mock_tasks_dir, capsys, fixed_now):
        """验证成功将任务状态改为 in_progress（SAMPLE_TASK 字段齐全故无 WARNING）"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"])
        with patch("core.task_crud.render_prompt", return_value=""):
            cmd_execute_task(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        assert data["tasks"][0]["status"] == "in_progress"
        captured = capsys.readouterr()
        # render_prompt 被 mock 返回空字符串，所以输出为空
        # 重点是状态正确变更
        assert data["tasks"][0]["status"] == "in_progress"

    def test_execute_blocked_by_dependency(self, mock_tasks_dir, capsys):
        """验证依赖未完成时无法执行"""
        tmp_path, tasks_dir = mock_tasks_dir
        dep_task = dict(SAMPLE_TASK_2, id="dep-id-0001", status="pending")
        task_with_dep = dict(SAMPLE_TASK,
                             dependencies=[{"taskId": "dep-id-0001"}])
        create_task_file(tasks_dir, TEST_SID, tasks=[dep_task, task_with_dep])
        args = make_args(id=SAMPLE_TASK["id"])
        with pytest.raises(SystemExit):
            cmd_execute_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "依赖未完成" in captured.out

    def test_execute_already_completed(self, mock_tasks_dir, capsys):
        """验证已完成的任务不能再次执行"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_COMPLETED_TASK])
        args = make_args(id=SAMPLE_COMPLETED_TASK["id"])
        with pytest.raises(SystemExit):
            cmd_execute_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "无需再执行" in captured.out

    def test_execute_not_found(self, mock_tasks_dir, capsys):
        """验证找不到任务时退出"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[])
        args = make_args(id="nonexistent")
        with pytest.raises(SystemExit):
            cmd_execute_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "找不到任务" in captured.out

    def test_execute_missing_session_id(self, capsys):
        """验证缺少 session_id 时退出"""
        args = make_args(session_id=None, id="test")
        with pytest.raises(SystemExit):
            cmd_execute_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 --session-id" in captured.out


# ══════════════════════════════════════════════════════════════════════════════
# cmd_verify_task
# ══════════════════════════════════════════════════════════════════════════════

class TestCmdVerifyTask:
    """测试 cmd_verify_task()"""

    def test_verify_success(self, mock_tasks_dir, capsys, fixed_now):
        """验证成功验证一个 in_progress 任务"""
        tmp_path, tasks_dir = mock_tasks_dir
        in_progress_task = dict(SAMPLE_TASK, status="in_progress")
        create_task_file(tasks_dir, TEST_SID, tasks=[in_progress_task])
        args = make_args(id=SAMPLE_TASK["id"], summary="功能验证通过", work_log=None)
        with patch("core.task_crud.render_prompt", return_value=""):
            cmd_verify_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "验证任务" in captured.out

    def test_verify_with_work_log(self, mock_tasks_dir, capsys, fixed_now):
        """验证 verify 时传入 work_log JSON"""
        tmp_path, tasks_dir = mock_tasks_dir
        in_progress_task = dict(SAMPLE_TASK, status="in_progress")
        create_task_file(tasks_dir, TEST_SID, tasks=[in_progress_task])
        work_log_json = json.dumps({"type": "code_change", "content": "修改了 auth 逻辑"})
        args = make_args(id=SAMPLE_TASK["id"], summary="验证通过", work_log=work_log_json)
        with patch("core.task_crud.render_prompt", return_value=""):
            cmd_verify_task(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        assert len(data["tasks"][0]["workLog"]) == 1

    def test_verify_not_in_progress(self, mock_tasks_dir, capsys):
        """验证非 in_progress 状态任务无法验证"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"], summary=None, work_log=None)
        with pytest.raises(SystemExit):
            cmd_verify_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "只有 in_progress 任务可以验证" in captured.out

    def test_verify_missing_session_id(self, capsys):
        """验证缺少 session_id 时退出"""
        args = make_args(session_id=None, id="test", summary=None, work_log=None)
        with pytest.raises(SystemExit):
            cmd_verify_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 --session-id" in captured.out


# ══════════════════════════════════════════════════════════════════════════════
# cmd_complete_task
# ══════════════════════════════════════════════════════════════════════════════

class TestCmdCompleteTask:
    """测试 cmd_complete_task()"""

    def test_complete_success(self, mock_tasks_dir, capsys, fixed_now):
        """验证完成任务，状态变为 completed"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"], summary="完成登录功能",
                         work_log=None, skip_memory=False)
        cmd_complete_task(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        assert data["tasks"][0]["status"] == "completed"
        assert data["tasks"][0]["summary"] == "完成登录功能"
        captured = capsys.readouterr()
        assert "[OK] 任务已完成" in captured.out

    def test_complete_with_work_log(self, mock_tasks_dir, capsys, fixed_now):
        """验证完成时附带 work_log"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        work_log_json = json.dumps([{"type": "code_change", "content": "实现 JWT 认证"}])
        args = make_args(id=SAMPLE_TASK["id"], summary="完成登录",
                         work_log=work_log_json, skip_memory=False)
        cmd_complete_task(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        assert len(data["tasks"][0]["workLog"]) == 1

    def test_complete_not_found(self, mock_tasks_dir, capsys):
        """验证找不到任务时退出"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[])
        args = make_args(id="nonexistent", summary="test", work_log=None, skip_memory=False)
        with pytest.raises(SystemExit):
            cmd_complete_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "找不到任务" in captured.out

    def test_complete_missing_session_id(self, capsys):
        """验证缺少 session_id 时退出"""
        args = make_args(session_id=None, id="test", summary="test",
                         work_log=None, skip_memory=False)
        with pytest.raises(SystemExit):
            cmd_complete_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 --session-id" in captured.out


# ══════════════════════════════════════════════════════════════════════════════
# cmd_update_task
# ══════════════════════════════════════════════════════════════════════════════

class TestCmdUpdateTask:
    """测试 cmd_update_task()"""

    def test_update_fields(self, mock_tasks_dir, capsys, fixed_now):
        """验证更新任务各字段"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"],
                         name="新名称", description="新描述",
                         notes="新备注", implementation_guide="新指南",
                         verification_criteria="新标准", analysis="新分析",
                         related_files=None)
        cmd_update_task(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert task["name"] == "新名称"
        assert task["description"] == "新描述"
        assert task["notes"] == "新备注"
        assert task["implementationGuide"] == "新指南"
        assert task["verificationCriteria"] == "新标准"
        assert task["analysisResult"] == "新分析"
        captured = capsys.readouterr()
        assert "已更新" in captured.out

    def test_update_completed_task_forbidden(self, mock_tasks_dir, capsys):
        """验证已完成任务不可更新"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_COMPLETED_TASK])
        args = make_args(id=SAMPLE_COMPLETED_TASK["id"], name="改名",
                         description=None, notes=None, implementation_guide=None,
                         verification_criteria=None, analysis=None, related_files=None)
        with pytest.raises(SystemExit):
            cmd_update_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "已完成的任务不可更新" in captured.out

    def test_update_no_changes(self, mock_tasks_dir, capsys):
        """验证未提供更新字段时的警告"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"],
                         name=None, description=None, notes=None,
                         implementation_guide=None, verification_criteria=None,
                         analysis=None, related_files=None)
        cmd_update_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "没有提供" in captured.out


# ══════════════════════════════════════════════════════════════════════════════
# cmd_delete_task
# ══════════════════════════════════════════════════════════════════════════════

class TestCmdDeleteTask:
    """测试 cmd_delete_task()"""

    def test_delete_success(self, mock_tasks_dir, capsys):
        """验证成功删除任务"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(id=SAMPLE_TASK["id"])
        cmd_delete_task(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        assert len(data["tasks"]) == 0
        captured = capsys.readouterr()
        assert "已删除" in captured.out

    def test_delete_with_dependents(self, mock_tasks_dir, capsys):
        """验证有依赖的任务不可删除"""
        tmp_path, tasks_dir = mock_tasks_dir
        dependent = dict(SAMPLE_TASK_2, dependencies=[{"taskId": SAMPLE_TASK["id"]}])
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK, dependent])
        args = make_args(id=SAMPLE_TASK["id"])
        with pytest.raises(SystemExit):
            cmd_delete_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "依赖此任务" in captured.out

    def test_delete_completed_forbidden(self, mock_tasks_dir, capsys):
        """验证已完成任务不可删除"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_COMPLETED_TASK])
        args = make_args(id=SAMPLE_COMPLETED_TASK["id"])
        with pytest.raises(SystemExit):
            cmd_delete_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "已完成的任务不可删除" in captured.out

    def test_delete_not_found(self, mock_tasks_dir, capsys):
        """验证找不到任务时退出"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[])
        args = make_args(id="nonexistent")
        with pytest.raises(SystemExit):
            cmd_delete_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "找不到任务" in captured.out


# ══════════════════════════════════════════════════════════════════════════════
# cmd_query_task
# ══════════════════════════════════════════════════════════════════════════════

class TestCmdQueryTask:
    """测试 cmd_query_task()"""

    def test_query_by_keyword(self, mock_tasks_dir, capsys):
        """验证按关键词搜索当前 session 的任务"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK, SAMPLE_TASK_2])
        args = make_args(keyword="登录", page=1, page_size=10)
        cmd_query_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "共找到" in captured.out
        assert "登录" in captured.out  # 结果中包含登录功能

    def test_query_no_results(self, mock_tasks_dir, capsys):
        """验证搜索无结果时输出 0 条"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK])
        args = make_args(keyword="不存在的关键词", page=1, page_size=10)
        cmd_query_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "共找到 0 条" in captured.out

    def test_query_missing_session_id(self, capsys):
        """验证缺少 session_id 时退出"""
        args = make_args(session_id=None, keyword="test", page=1, page_size=10)
        with pytest.raises(SystemExit):
            cmd_query_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "缺少 --session-id" in captured.out


# ══════════════════════════════════════════════════════════════════════════════
# cmd_archive
# ══════════════════════════════════════════════════════════════════════════════

class TestCmdArchive:
    """测试 cmd_archive()"""

    def test_archive_with_confirm(self, mock_tasks_dir, capsys, fixed_now_stamp):
        """验证确认归档后删除任务文件并备份"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID,
                         tasks=[SAMPLE_COMPLETED_TASK, SAMPLE_TASK])
        args = make_args(confirm=True)
        cmd_archive(TEST_AGENT, args)
        # 原任务文件被删除
        assert not (tasks_dir / f"tasks-{TEST_SID}.json").exists()
        # 备份文件应在 memory 目录
        memory_dir = tasks_dir / "memory"
        backup_files = list(memory_dir.glob("*.json"))
        assert len(backup_files) >= 1
        captured = capsys.readouterr()
        assert "已归档" in captured.out

    def test_archive_without_confirm(self, capsys):
        """验证未加 --confirm 参数时退出"""
        args = make_args(confirm=False)
        with pytest.raises(SystemExit):
            cmd_archive(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "请加 --confirm" in captured.out


# ══════════════════════════════════════════════════════════════════════════════
# cmd_complete_session
# ══════════════════════════════════════════════════════════════════════════════

class TestCmdCompleteSession:
    """测试 cmd_complete_session()"""

    def test_complete_session_batch(self, mock_tasks_dir, capsys, fixed_now):
        """验证批量完成 todo/doing 状态的任务"""
        tmp_path, tasks_dir = mock_tasks_dir
        todo_task = dict(SAMPLE_TASK, id="todo-1", name="todo任务", status="todo")
        doing_task = dict(SAMPLE_TASK_2, id="doing-1", name="doing任务", status="doing")
        create_task_file(tasks_dir, TEST_SID, tasks=[todo_task, doing_task, SAMPLE_COMPLETED_TASK])
        args = make_args()
        cmd_complete_session(TEST_AGENT, args)
        data = json.loads((tasks_dir / f"tasks-{TEST_SID}.json").read_text(encoding="utf-8"))
        completed = [t for t in data["tasks"] if t["status"] == "completed"]
        assert len(completed) == 3  # 原有的 completed + 2 个新完成的
        captured = capsys.readouterr()
        assert "批量标记" in captured.out

    def test_complete_session_no_todo(self, mock_tasks_dir, capsys):
        """验证无 todo/doing 任务时提示无需操作"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_COMPLETED_TASK])
        args = make_args()
        cmd_complete_session(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "无需操作" in captured.out


# ══════════════════════════════════════════════════════════════════════════════
# cmd_claim_task
# ══════════════════════════════════════════════════════════════════════════════

class TestCmdClaimTask:
    """测试 cmd_claim_task()"""

    def test_claim_task_success(self, mock_tasks_dir, capsys):
        """验证认领其他 session 的任务文件"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, "old-sid", tasks=[SAMPLE_TASK],
                         owner_session="old-sid")
        args = make_args(session_id=None, file=f"tasks-old-sid.json",
                         new_session_id=TEST_SID)
        cmd_claim_task(TEST_AGENT, args)
        # 新文件存在
        new_file = tasks_dir / f"tasks-{TEST_SID}.json"
        assert new_file.exists()
        data = json.loads(new_file.read_text(encoding="utf-8"))
        assert data["ownerSession"] == TEST_SID
        # 旧文件已被删除
        old_file = tasks_dir / "tasks-old-sid.json"
        assert not old_file.exists()
        captured = capsys.readouterr()
        assert "任务认领成功" in captured.out

    def test_claim_same_session(self, mock_tasks_dir, capsys):
        """验证认领已属于当前 session 的任务文件时提示无需操作"""
        tmp_path, tasks_dir = mock_tasks_dir
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK],
                         owner_session=TEST_SID)
        args = make_args(session_id=None, file=f"tasks-{TEST_SID}.json",
                         new_session_id=TEST_SID)
        cmd_claim_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "无需认领" in captured.out

    def test_claim_file_not_found(self, mock_tasks_dir, capsys):
        """验证找不到任务文件时退出"""
        tmp_path, tasks_dir = mock_tasks_dir
        args = make_args(session_id=None, file="nonexistent.json",
                         new_session_id=TEST_SID)
        with pytest.raises(SystemExit):
            cmd_claim_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "找不到任务文件" in captured.out

    def test_claim_missing_new_session_id(self, capsys):
        """验证未提供 --new-session-id 时退出"""
        args = make_args(session_id=None, file="tasks-old.json",
                         new_session_id="")
        with pytest.raises(SystemExit):
            cmd_claim_task(TEST_AGENT, args)
        captured = capsys.readouterr()
        assert "--new-session-id" in captured.out
