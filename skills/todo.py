"""skills/todo.py - create_todo / plan_from_todo / assign_task / list_todos 命令"""
import json
import sys
from pathlib import Path
from utils import now_iso, resolve_session_id, get_tasks_dir, get_todo_path, get_agent_workspace


def cmd_create_todo(agent: str, args):
    sid = resolve_session_id()
    description = args.description
    creator = getattr(args, 'creator', None) or agent
    todo_data = {
        "sessionId": sid,
        "description": description,
        "creator": creator,
        "createdAt": now_iso(),
        "status": "pending",
        "linkedTaskFile": None,
    }
    todo_path = get_todo_path(agent, sid)
    todo_path.parent.mkdir(parents=True, exist_ok=True)
    with open(todo_path, "w", encoding="utf-8") as f:
        json.dump(todo_data, f, ensure_ascii=False, indent=2)
    print(f"[OK] Todo 已创建：{todo_path.name}")
    print(f"  sessionId: {sid}")
    print(f"  描述: {description}")
    print(f"  创建者: {creator}")
    print(f"\n下一步：使用 plan_from_todo --todo-session-id {sid} 生成任务计划")


def cmd_plan_from_todo(agent: str, args):
    todo_sid = args.todo_session_id
    todo_path = get_todo_path(agent, todo_sid)
    if not todo_path.exists():
        print(f"[ERR] 找不到 todo 文件：{todo_path}"); sys.exit(1)
    with open(todo_path, encoding="utf-8") as f:
        todo_data = json.load(f)
    description = todo_data.get("description", "")
    creator = todo_data.get("creator", agent)
    task_sid = resolve_session_id()
    task_filename = f"tasks-{task_sid}.json"
    task_path = get_tasks_dir(agent) / task_filename
    task_data = {
        "userRequirement": description,
        "tasks": [],
        "ownerSession": task_sid,
        "sessionHistory": [],
        "status": "unassigned",
        "createdFrom": f"todo-{todo_sid}.json",
        "createdBy": creator,
        "createdAt": now_iso(),
    }
    task_path.parent.mkdir(parents=True, exist_ok=True)
    with open(task_path, "w", encoding="utf-8") as f:
        json.dump(task_data, f, ensure_ascii=False, indent=2)
    todo_data["linkedTaskFile"] = task_filename
    todo_data["linkedTaskSessionId"] = task_sid
    todo_data["status"] = "planned"
    with open(todo_path, "w", encoding="utf-8") as f:
        json.dump(todo_data, f, ensure_ascii=False, indent=2)
    print(f"[OK] 任务计划已生成（待指派）")
    print(f"  task 文件: {task_filename}")
    print(f"  task sessionId: {task_sid}")
    print(f"\n下一步：使用 assign_task --todo-session-id {todo_sid} --target-agent <agent> --target-session-id <sid> 指派")


def cmd_assign_task(agent: str, args):
    todo_sid = args.todo_session_id
    target_agent = args.target_agent
    target_sid = args.target_session_id
    todo_path = get_todo_path(agent, todo_sid)
    if not todo_path.exists():
        print(f"[ERR] 找不到 todo 文件：{todo_path}"); sys.exit(1)
    with open(todo_path, encoding="utf-8") as f:
        todo_data = json.load(f)
    linked_task_file = todo_data.get("linkedTaskFile")
    if not linked_task_file:
        print("[ERR] todo 文件尚未关联 task 文件，请先执行 plan_from_todo"); sys.exit(1)
    src_task_path = get_tasks_dir(agent) / linked_task_file
    if not src_task_path.exists():
        print(f"[ERR] 找不到 task 文件：{src_task_path}"); sys.exit(1)
    with open(src_task_path, encoding="utf-8") as f:
        task_data = json.load(f)
    old_owner = task_data.get("ownerSession", "")
    history = task_data.get("sessionHistory", [])
    if old_owner:
        history.append({"sessionId": old_owner, "transferredAt": now_iso()})
    task_data["sessionHistory"] = history
    task_data["ownerSession"] = target_sid
    task_data["status"] = "assigned"
    task_data["assignedTo"] = target_agent
    task_data["assignedAt"] = now_iso()
    target_tasks_dir = get_tasks_dir(target_agent)
    target_tasks_dir.mkdir(parents=True, exist_ok=True)
    new_task_filename = f"tasks-{target_sid}.json"
    with open(target_tasks_dir / new_task_filename, "w", encoding="utf-8") as f:
        json.dump(task_data, f, ensure_ascii=False, indent=2)
    todo_data["status"] = "assigned"
    todo_data["assignedTo"] = target_agent
    todo_data["assignedSession"] = target_sid
    todo_data["assignedAt"] = now_iso()
    with open(todo_path, "w", encoding="utf-8") as f:
        json.dump(todo_data, f, ensure_ascii=False, indent=2)
    print(f"[OK] 任务已指派！目标 agent: {target_agent}  session: {target_sid}")


def cmd_list_todos(agent: str, args):
    tasks_dir = get_tasks_dir(agent)
    if not tasks_dir.exists():
        print("[INFO] 暂无 todo 文件"); return
    todos = []
    for p in sorted(tasks_dir.glob("todo*")):
        try:
            with open(p, encoding="utf-8") as f:
                todos.append((p, json.load(f)))
        except Exception:
            pass
    if not todos:
        print("[INFO] 暂无 todo 文件"); return
    status_filter = getattr(args, 'status', 'all')
    print(f"[TODO 列表] agent={agent}，共 {len(todos)} 条\n")
    for p, data in todos:
        status = data.get("status", "unknown")
        if status_filter != "all" and status != status_filter:
            continue
        sid = data.get("sessionId", "")
        desc = data.get("description", "")[:60]
        creator = data.get("creator", "")
        linked = data.get("linkedTaskFile") or "无"
        assigned_to = data.get("assignedTo", "")
        print(f"  [{sid[:20]}] [{status}] {desc}")
        print(f"    创建者: {creator}  关联task: {linked}" + (f"  指派给: {assigned_to}" if assigned_to else ""))
        print()
