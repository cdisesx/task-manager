"""tests/test_data_io.py - 测试 utils/data_io.py

测试方法:
  - ensure_tasks_file()       → 创建/返回 tasks JSON 文件路径
  - read_data()               → 读取并返回完整数据字典，带默认值
  - write_data()              → 写入数据并附加 lastUpdatedAt
  - scan_all_session_tasks()  → 扫描所有 tasks-*.json 文件

使用:
  pytest tests/test_data_io.py -v

预期输出:
  test_ensure_tasks_file_creates_new ...... PASSED
  test_ensure_tasks_file_returns_existing . PASSED
  test_read_data_defaults ................. PASSED
  test_read_data_existing ................. PASSED
  test_write_data ........................ PASSED
  test_write_data_adds_timestamp .......... PASSED
  test_scan_all_session_tasks_empty ....... PASSED
  test_scan_all_session_tasks_multiple .... PASSED
"""
import json

import pytest

from utils.data_io import ensure_tasks_file, read_data, write_data, scan_all_session_tasks
from utils import now_iso

from tests.conftest import TEST_AGENT, TEST_SID


class TestEnsureTasksFile:
    """测试 ensure_tasks_file()"""

    def test_ensure_tasks_file_creates_new(self, mock_tasks_dir):
        """验证当文件不存在时，创建含有默认值的 JSON 文件"""
        tmp_path, tasks_dir = mock_tasks_dir
        result = ensure_tasks_file(TEST_AGENT, TEST_SID)
        assert result.exists()
        data = json.loads(result.read_text(encoding="utf-8"))
        assert data["userRequirement"] == ""
        assert data["tasks"] == []
        assert data["ownerSession"] == TEST_SID
        assert data["sessionHistory"] == []

    def test_ensure_tasks_file_returns_existing(self, mock_tasks_dir):
        """验证当文件已存在时，不覆盖原有内容"""
        tmp_path, tasks_dir = mock_tasks_dir
        from tests.conftest import create_task_file
        pre_data = {"userRequirement": "已有需求", "tasks": [], "ownerSession": TEST_SID, "sessionHistory": []}
        (tasks_dir / f"tasks-{TEST_SID}.json").write_text(
            json.dumps(pre_data), encoding="utf-8")

        result = ensure_tasks_file(TEST_AGENT, TEST_SID)
        data = json.loads(result.read_text(encoding="utf-8"))
        assert data["userRequirement"] == "已有需求"


class TestReadData:
    """测试 read_data()"""

    def test_read_data_defaults(self, mock_tasks_dir):
        """验证读取新 session 时返回带默认值的数据"""
        data = read_data(TEST_AGENT, TEST_SID)
        assert data["userRequirement"] == ""
        assert data["tasks"] == []
        assert data["ownerSession"] == TEST_SID
        assert "sessionHistory" in data

    def test_read_data_existing(self, mock_tasks_dir):
        """验证读取已有 session 时正确加载数据"""
        tmp_path, tasks_dir = mock_tasks_dir
        from tests.conftest import create_task_file, SAMPLE_TASK
        create_task_file(tasks_dir, TEST_SID, tasks=[SAMPLE_TASK], requirement="测试需求")
        data = read_data(TEST_AGENT, TEST_SID)
        assert data["userRequirement"] == "测试需求"
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["name"] == "实现用户登录功能"


class TestWriteData:
    """测试 write_data()"""

    def test_write_data(self, mock_tasks_dir):
        """验证 write_data 写入的数据能被 read_data 正确读取"""
        data = {"userRequirement": "新需求", "tasks": [], "ownerSession": TEST_SID, "sessionHistory": []}
        write_data(TEST_AGENT, data, TEST_SID)
        loaded = read_data(TEST_AGENT, TEST_SID)
        assert loaded["userRequirement"] == "新需求"

    def test_write_data_adds_timestamp(self, mock_tasks_dir):
        """验证 write_data 自动添加 lastUpdatedAt 字段"""
        data = {"userRequirement": "测试", "tasks": [], "ownerSession": TEST_SID, "sessionHistory": []}
        write_data(TEST_AGENT, data, TEST_SID)
        assert "lastUpdatedAt" in data


class TestScanAllSessionTasks:
    """测试 scan_all_session_tasks()"""

    def test_scan_all_session_tasks_empty(self, mock_tasks_dir):
        """验证无任务文件时返回空列表"""
        results = scan_all_session_tasks(TEST_AGENT)
        assert results == []

    def test_scan_all_session_tasks_multiple(self, mock_tasks_dir):
        """验证扫描到多个 tasks-*.json 文件"""
        tmp_path, tasks_dir = mock_tasks_dir
        from tests.conftest import create_task_file, SAMPLE_TASK
        create_task_file(tasks_dir, "sid-1", tasks=[SAMPLE_TASK], requirement="需求1", owner_session="sid-1")
        create_task_file(tasks_dir, "sid-2", tasks=[], requirement="需求2", owner_session="sid-2")

        results = scan_all_session_tasks(TEST_AGENT)
        assert len(results) == 2
        sessions = {r["sessionId"] for r in results}
        assert sessions == {"sid-1", "sid-2"}
        # 验证 sid-1 有任务数据
        r1 = next(r for r in results if r["sessionId"] == "sid-1")
        assert len(r1["tasks"]) == 1
