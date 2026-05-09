"""utils/paths.py - 路径工具函数（从 config.json 读取 base_dir）"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path


def resolve_session_id() -> str:
    """生成一个唯一的 session ID，格式: si-{timestamp}-{uuid[:8]}"""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    uid = uuid.uuid4().hex[:8]
    return f"si-{ts}-{uid}"


def load_config() -> dict:
    """加载 config.json，找不到则返回默认值。

    优先级：
    1. TASK_MANAGER_CONFIG 环境变量指向的路径
    2. config/config.json
    3. config/config.example.json（回退）
    """
    # 优先：环境变量 TASK_MANAGER_CONFIG
    env_config = os.environ.get("TASK_MANAGER_CONFIG")
    if env_config:
        config_path = Path(env_config)
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)

    # 默认路径
    config_path = Path(__file__).parent.parent / "config" / "config.json"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    # 回退：尝试 config.example.json
    example_path = Path(__file__).parent.parent / "config" / "config.example.json"
    if example_path.exists():
        with open(example_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_base_dir() -> Path:
    cfg = load_config()
    base = cfg.get("base_dir", "")
    if base:
        return Path(base)
    raise RuntimeError(
        "未找到 config.json 或 base_dir 未配置。\n"
        "请复制 config/config.example.json 为 config/config.json 并填入 base_dir。"
    )


def get_agent_workspace(agent: str) -> Path:
    """读取 config.json 中 agents 列表，返回指定 agent 的工作区路径。
    若未配置则回退到 base_dir/workspace-{agent}。
    """
    cfg = load_config()
    agents = cfg.get("agents", [])
    for a in agents:
        if isinstance(a, dict):
            agent_id = a.get("id") or a.get("agentId") or a.get("code")
            if agent_id == agent:
                ws = a.get("workSpace") or a.get("workspace")
                if ws:
                    return Path(ws)
    return get_base_dir() / f"workspace/{agent}"


def get_tasks_path(agent: str, session_id: str) -> Path:
    if not session_id:
        raise ValueError("session_id 不能为空，请先执行 get_session_id 获取")
    return get_agent_workspace(agent) / "tasks" / f"tasks-{session_id}.json"


def get_memory_dir(agent: str) -> Path:
    return get_agent_workspace(agent) / "tasks" / "memory"


def get_tasks_dir(agent: str) -> Path:
    return get_agent_workspace(agent) / "tasks"


def get_todo_path(agent: str, session_id: str) -> Path:
    return get_agent_workspace(agent) / "tasks" / f"todo-{session_id}.json"
