"""skills/subtask.py - add_subtask / resplit_task 命令"""
import json
import sys
import uuid
from utils import now_iso, read_data, write_data


def cmd_add_subtask(agent: str, args):
    sid = getattr(args, "session_id", None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    parent = next((t for t in data["tasks"] if t["id"] == args.parent_id or t["id"].startswith(args.parent_id)), None)
    if not parent:
        print(f"[ERR] 找不到父任务 {args.parent_id}"); sys.exit(1)
    subtask = {
        "id": str(uuid.uuid4()),
        "name": args.name,
        "desc": args.desc,
        "status": "todo",
        "createdAt": now_iso(),
        "parentId": parent["id"],
    }
    # 补充可选字段
    if getattr(args, 'guide', None):
        subtask["implementationGuide"] = args.guide
    if getattr(args, 'criteria', None):
        subtask["verificationCriteria"] = args.criteria
    if getattr(args, 'notes', None):
        subtask["notes"] = args.notes
    parent.setdefault("subtasks", []).append(subtask)
    parent["updatedAt"] = now_iso()
    write_data(agent, data, sid)
    print(f"[OK] 已向任务 [{parent['id'][:8]}] {parent['name']} 追加子任务：")
    print(f"     [{subtask['id'][:8]}] {subtask['name']}")


def cmd_resplit_task(agent: str, args):
    sid = getattr(args, "session_id", None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    original = next(
        (t for t in data["tasks"] if t["id"] == args.id or t["id"].startswith(args.id)), None
    )
    if not original:
        print(f"[ERR] 找不到任务 {args.id}"); sys.exit(1)
    if original["status"] == "completed":
        print(f"[ERR] 任务 [{original['id'][:8]}] {original['name']} 已完成，不允许二次拆分"); sys.exit(1)
    try:
        new_task_list = json.loads(args.tasks)
    except json.JSONDecodeError as e:
        print(f"[ERR] --tasks JSON 解析失败：{e}"); sys.exit(1)
    if not new_task_list:
        print("[ERR] 新子任务列表不能为空"); sys.exit(1)

    inherited_deps = original.get("dependencies", [])
    original_id = original["id"]
    original_name = original["name"]
    created = []
    for td in new_task_list:
        task = {
            "id": str(uuid.uuid4()),
            "name": td.get("name", ""),
            "description": td.get("description", ""),
            "notes": td.get("notes"),
            "status": "pending",
            "dependencies": list(inherited_deps),
            "parentTaskId": original_id,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "completedAt": None,
            "summary": None,
            "relatedFiles": td.get("relatedFiles", []),
            "implementationGuide": td.get("implementationGuide"),
            "verificationCriteria": td.get("verificationCriteria"),
            "analysisResult": td.get("analysisResult"),
            "workLog": [],
        }
        created.append(task)

    data["tasks"] = [t for t in data["tasks"] if t["id"] != original_id] + created
    write_data(agent, data, sid)
    print(f"[OK] 原任务 [{original_id[:8]}] {original_name} 已删除，创建了 {len(created)} 个新子任务：")
    for t in created:
        print(f"  [{t['id'][:8]}] {t['name']}（parentTaskId: {original_id[:8]}）")
