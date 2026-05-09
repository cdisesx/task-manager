"""conftest.py - 共享 fixtures 和 mock 工具函数

架构说明：
  test_config fixture 是核心 —— 它读取 tests/configs/test_config.json 模板，
  将路径占位符替换为 tmp_path，然后 patch utils.paths.load_config。
  后续所有路径函数（get_base_dir / get_agent_workspace / get_tasks_path 等）
  都通过真实的 load_config → 真实函数链路解析到 tmp_path，无需逐个 patch。
"""
import json
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest


# ── 常量 ───────────────────────────────────────────────────────────────────────

TEST_AGENT = "test_agent"
TEST_SID = "test-session-id-001"
TEST_SID_2 = "test-session-id-002"

SAMPLE_TASK = {
    "id": "task-11111111-1111-1111-1111-111111111111",
    "name": "实现用户登录功能",
    "description": "实现基于 JWT 的用户登录接口",
    "notes": "注意密码加密",
    "status": "pending",
    "dependencies": [],
    "createdAt": "2026-05-09T10:00:00",
    "updatedAt": "2026-05-09T10:00:00",
    "completedAt": None,
    "summary": None,
    "relatedFiles": ["src/auth.py"],
    "implementationGuide": "使用 pyjwt 库，RS256 算法",
    "verificationCriteria": "登录成功返回 token，失败返回 401",
    "analysisResult": "需要新增 auth 模块",
    "workLog": [],
}

SAMPLE_TASK_2 = {
    "id": "task-22222222-2222-2222-2222-222222222222",
    "name": "实现用户注册功能",
    "description": "实现用户注册接口，含邮箱验证",
    "notes": None,
    "status": "pending",
    "dependencies": [],
    "createdAt": "2026-05-09T10:00:00",
    "updatedAt": "2026-05-09T10:00:00",
    "completedAt": None,
    "summary": None,
    "relatedFiles": ["src/register.py"],
    "implementationGuide": "使用邮箱验证码",
    "verificationCriteria": "注册成功返回用户信息",
    "analysisResult": None,
    "workLog": [],
}

SAMPLE_COMPLETED_TASK = {
    "id": "task-33333333-3333-3333-3333-333333333333",
    "name": "项目初始化",
    "description": "初始化项目结构",
    "notes": None,
    "status": "completed",
    "dependencies": [],
    "createdAt": "2026-05-09T09:00:00",
    "updatedAt": "2026-05-09T09:30:00",
    "completedAt": "2026-05-09T09:30:00",
    "summary": "已完成项目初始化",
    "relatedFiles": [],
    "implementationGuide": None,
    "verificationCriteria": None,
    "analysisResult": None,
    "workLog": [],
}


# ── 核心 fixture：test_config ──────────────────────────────────────────────────

@pytest.fixture
def test_config(tmp_path):
    """创建测试用配置并 patch load_config。

    读取 tests/configs/test_config.json，将其中的 base_dir 和 agent workspace
    动态替换为 tmp_path 下的隔离目录。patch utils.paths.load_config 返回该配置，
    使得 get_base_dir / get_agent_workspace / get_tasks_path 等真实函数
    直接基于 tmp_path 解析路径。

    Yields (tmp_path, workspace_dir, config_dict)
    """
    config_file = Path(__file__).parent / "configs" / "test_config.json"
    config = json.loads(config_file.read_text(encoding="utf-8"))

    # 将 base_dir 和 test agent 的 workspace 指向 tmp_path
    workspace_dir = tmp_path / "workspace" / TEST_AGENT
    config["base_dir"] = str(tmp_path)

    agents = config.setdefault("agents", [])
    found = False
    for a in agents:
        if isinstance(a, dict) and a.get("id") == TEST_AGENT:
            a["workSpace"] = str(workspace_dir)
            found = True
            break
    if not found:
        agents.append({"id": TEST_AGENT, "workSpace": str(workspace_dir)})

    with patch("utils.paths.load_config", return_value=config):
        yield tmp_path, workspace_dir, config


# ── 衍生 fixture ───────────────────────────────────────────────────────────────

@pytest.fixture
def mock_tasks_dir(test_config):
    """在 test_config 基础上创建 tasks/ 目录，返回 (tmp_path, tasks_dir)"""
    tmp_path, workspace_dir, _ = test_config
    tasks_dir = workspace_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    yield tmp_path, tasks_dir


@pytest.fixture
def fixed_uuid():
    """固定 uuid.uuid4 的返回值"""
    with patch("uuid.uuid4", return_value=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")):
        yield


@pytest.fixture
def fixed_now_iso():
    """固定 now_iso 的返回值"""
    with patch("utils.time_utils.now_iso", return_value="2026-05-09T12:00:00"):
        yield


@pytest.fixture
def fixed_now_stamp():
    """固定 now_stamp 的返回值"""
    with patch("utils.time_utils.now_stamp", return_value="20260509_120000"):
        yield


@pytest.fixture
def fixed_now(fixed_now_iso, fixed_now_stamp):
    """同时固定 now_iso 和 now_stamp"""
    yield


@pytest.fixture
def fixed_session_id():
    """固定 resolve_session_id 的返回值（patch 所有导入该函数的模块）"""
    with patch("utils.paths.resolve_session_id", return_value=TEST_SID):
        with patch("utils.resolve_session_id", return_value=TEST_SID):
            with patch("core.task_crud.resolve_session_id", return_value=TEST_SID):
                with patch("skills.todo.resolve_session_id", return_value=TEST_SID):
                    yield


# ── Helper 函数 ───────────────────────────────────────────────────────────────

def create_task_file(tasks_dir: Path, sid: str, tasks: list = None,
                     requirement: str = "", owner_session: str = None):
    """创建一个测试用的 tasks-{sid}.json 文件"""
    data = {
        "userRequirement": requirement,
        "tasks": tasks or [],
        "ownerSession": owner_session or sid,
        "sessionHistory": [],
    }
    file_path = tasks_dir / f"tasks-{sid}.json"
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return file_path
