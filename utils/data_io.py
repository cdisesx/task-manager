"""utils/data_io.py - 任务数据读写工具"""
import json
from pathlib import Path
from .time_utils import now_iso
from .paths import get_tasks_path, get_tasks_dir, get_memory_dir


def ensure_tasks_file(agent: str, session_id: str) -> Path:
    path = get_tasks_path(agent, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            json.dumps({
                "userRequirement": "",
                "tasks": [],
                "ownerSession": session_id,
                "sessionHistory": [],
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    return path


def read_data(agent: str, session_id: str) -> dict:
    path = ensure_tasks_file(agent, session_id)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("tasks", [])
    data.setdefault("userRequirement", "")
    data.setdefault("ownerSession", session_id)
    data.setdefault("sessionHistory", [])
    return data


def write_data(agent: str, data: dict, session_id: str):
    path = ensure_tasks_file(agent, session_id)
    data["lastUpdatedAt"] = now_iso()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def scan_all_session_tasks(agent: str) -> list:
    """扫描该代理所有 tasks-*.json 文件"""
    tasks_dir = get_tasks_dir(agent)
    results = []
    if not tasks_dir.exists():
        return results
    for p in sorted(tasks_dir.glob("tasks-*.json")):
        sid = p.stem[len("tasks-"):]
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            tasks = data.get("tasks", [])
            owner = data.get("ownerSession", sid)
            results.append({
                "sessionId": sid,
                "ownerSession": owner,
                "sessionHistory": data.get("sessionHistory", []),
                "tasks": tasks,
                "path": str(p),
                "filename": p.name,
            })
        except Exception:
            pass
    return results
