"""core/task_crud.py - 核心任务 CRUD 和状态机逻辑"""
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from utils import now_iso, now_stamp, resolve_session_id
from utils import read_data, write_data, scan_all_session_tasks
from utils import get_tasks_path, get_memory_dir, get_tasks_dir
from core.prompts import (
    render_prompt,
    render_plan_task,
    render_split_tasks,
    render_execute_task,
    render_verify_task,
    render_list_tasks,
)


def cmd_get_session_id(agent: str, args):
    print(resolve_session_id())


def cmd_plan_task(agent: str, args):
    sid = getattr(args, 'session_id', None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    tasks_path = get_tasks_path(agent, sid)
    if tasks_path.exists():
        data = read_data(agent, sid)
        old_req = data.get("userRequirement", "")
        if old_req:
            data.setdefault("history", [])
            data["history"].append({"description": old_req, "archivedAt": now_iso()})
    else:
        data = read_data(agent, sid)
    req = args.description
    if getattr(args, 'requirements', None):
        req += f"\n\n技术要求：{args.requirements}"
    data["userRequirement"] = req
    data["ownerSession"] = sid
    data.setdefault("sessionHistory", [])
    write_data(agent, data, sid)
    print(f"[OK] 已设置用户需求（session: {sid}）：\n{req}")
    print()
    print(render_plan_task(req=req, tasks=data["tasks"]))


def cmd_split_tasks(agent: str, args):
    sid = getattr(args, 'session_id', None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    mode = args.mode
    try:
        new_task_list = json.loads(args.tasks)
    except json.JSONDecodeError as e:
        print(f"[ERR] --tasks JSON 解析失败：{e}")
        print()
        print("--tasks 必须是一个合法的 JSON 数组，示例：")
        print('''  --tasks '[
    {"name": "任务名", "description": "描述", "implementationGuide": "实现指南", "verificationCriteria": "验收标准"}
  ]' ''')
        sys.exit(1)

    # 校验 tasks 数组的每一项必须是对象
    if not isinstance(new_task_list, list):
        print("[ERR] --tasks 必须是一个 JSON 数组 []，请检查输入格式")
        print()
        print("正确示例：")
        print('''  --tasks '[
    {"name": "任务名", "description": "描述"}
  ]' ''')
        sys.exit(1)

    for i, td in enumerate(new_task_list):
        if not isinstance(td, dict):
            print(f"[ERR] --tasks 的第 {i+1} 项不是任务对象（应为 {{...}}，实际收到 {type(td).__name__}）")
            print()
            print("正确格式：每一项必须是包含 name / description 等字段的 JSON 对象")
            print("错误示例：--tasks '[\"123\"]'          ← 字符串列表，无效")
            print("正确示例：--tasks '[{\"name\": \"123\"}]'  ← 对象列表，有效")
            sys.exit(1)
        if not td.get("name") or not isinstance(td.get("name"), str):
            print(f"[ERR] --tasks 的第 {i+1} 项缺少 name 字段或 name 不是字符串")
            print()
            print("每项任务必须包含 name 字段，示例：")
            print('''  {"name": "任务名称", "description": "任务描述"}''')
            sys.exit(1)

    if getattr(args, 'user_requirement', None):
        if mode in ("append", "selective") and data.get("userRequirement"):
            data["userRequirement"] += f"\n\n--- 追加需求 ---\n{args.user_requirement}"
        else:
            data["userRequirement"] = args.user_requirement

    existing = data["tasks"]
    if mode == "append":
        tasks_to_keep = list(existing)
    elif mode == "overwrite":
        tasks_to_keep = [t for t in existing if t["status"] == "completed"]
    elif mode == "selective":
        update_names = {t["name"] for t in new_task_list}
        tasks_to_keep = [t for t in existing if t["name"] not in update_names]
    elif mode == "clearAllTasks":
        completed = [t for t in existing if t["status"] == "completed"]
        if completed:
            mem_dir = get_memory_dir(agent)
            mem_dir.mkdir(parents=True, exist_ok=True)
            backup_path = mem_dir / f"{now_stamp()}.json"
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump({"userRequirement": data.get("userRequirement", ""), "tasks": completed},
                          f, ensure_ascii=False, indent=2)
            print(f"[BACKUP] 已备份 {len(completed)} 个已完成任务到 {backup_path}")
        tasks_to_keep = []
    else:
        print(f"[ERR] 未知 mode: {mode}"); sys.exit(1)

    name_to_id = {t["name"]: t["id"] for t in tasks_to_keep}
    created = []
    for td in new_task_list:
        if mode == "selective":
            existing_task = next(
                (t for t in existing if t["name"] == td["name"] and t["status"] != "completed"), None)
            if existing_task:
                existing_task.update({
                    "name": td.get("name", existing_task["name"]),
                    "description": td.get("description", existing_task["description"]),
                    "notes": td.get("notes", existing_task.get("notes")),
                 "implementationGuide": td.get("implementationGuide", existing_task.get("implementationGuide")),
                    "verificationCriteria": td.get("verificationCriteria", existing_task.get("verificationCriteria")),
                    "analysisResult": getattr(args, 'analysis', None) or existing_task.get("analysisResult"),
                    "relatedFiles": td.get("relatedFiles", existing_task.get("relatedFiles", [])),
                    "updatedAt": now_iso(),
                })
                name_to_id[existing_task["name"]] = existing_task["id"]
                created.append(existing_task)
                continue
        missing_fields = []
        if not td.get("implementationGuide"):
            missing_fields.append("implementationGuide")
        if not td.get("verificationCriteria"):
            missing_fields.append("verificationCriteria")
        if missing_fields:
            print(f"[WARNING] 任务 \"{td.get('name', '')}\" 缺少字段：{', '.join(missing_fields)}。补充这些字段可提升向量记忆质量，详见 task_fields_guide。")
        tid = str(uuid.uuid4())
        name_to_id[td["name"]] = tid
        task = {
            "id": tid, "name": td.get("name", ""), "description": td.get("description", ""),
            "notes": td.get("notes"), "status": "pending", "dependencies": [],
            "createdAt": now_iso(), "updatedAt": now_iso(), "completedAt": None,
            "summary": None, "relatedFiles": td.get("relatedFiles", []),
            "implementationGuide": td.get("implementationGuide"),
            "verificationCriteria": td.get("verificationCriteria"),
            "analysisResult": getattr(args, 'analysis', None) or td.get("analysisResult"),
            "workLog": [],
        }
        created.append(task)

    for i, td in enumerate(new_task_list):
        task = created[i]
        task["dependencies"] = [{"taskId": name_to_id.get(dep, dep)} for dep in td.get("dependencies", [])]

    existing_ids = {t["id"] for t in tasks_to_keep}
    data["tasks"] = tasks_to_keep + [t for t in created if t["id"] not in existing_ids]
    write_data(agent, data, sid)
    print(f"[OK] 已创建/更新 {len(created)} 个任务（mode={mode}）")
    for t in created:
        print(f"  [{t['id'][:8]}] {t['name']}")
    print()
    print(render_split_tasks(mode=mode, created=created))


def cmd_list_tasks(agent: str, args):
    sid = getattr(args, 'session_id', None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    status_filter = getattr(args, 'status', 'all')
    all_session_files = scan_all_session_tasks(agent)
    matched = [s for s in all_session_files if s["ownerSession"] == sid]
    if not matched:
        print("（暂无任务）\n\n# 当前任务总览\n\n## 任务状态统计\n暂无任务\n")
        if all_session_files:
            print("[INFO] 当前工作区存在以下任务文件（可通过 claim_task 认领）：")
            for s in all_session_files:
                active = [t for t in s["tasks"] if t.get("status") != "completed"]
                print(f"  {s['filename']}  ownerSession={s['ownerSession']}  活跃任务={len(active)}")
        return
    data = matched[0]
    tasks = data["tasks"]
    req = ""
    try:
        with open(data["path"], encoding="utf-8") as f:
            full_data = json.load(f)
        req = full_data.get("userRequirement", "")
    except Exception:
        pass
    if req:
        print(f"[REQ] 当前需求：{req[:100]}\n")
    groups = {
        "in_progress": ("[IN_PROGRESS] 进行中", []),
        "pending": ("[PENDING] 待执行", []),
        "blocked": ("[BLOCKED] 已阻塞", []),
        "completed": ("[OK] 已完成", []),
    }
    for t in tasks:
        s = t["status"]
        if s in groups:
            groups[s][1].append(t)
    for key in ["in_progress", "pending", "blocked", "completed"]:
        if status_filter != "all" and status_filter != key:
            continue
        label, items = groups[key]
        if not items:
            continue
        print(f"\n{label}（{len(items)}）")
        for t in items:
            deps = t.get("dependencies", [])
            dep_str = f"  [deps:{len(deps)}]" if deps else ""
            block_info = t.get("blockInfo", {})
            block_str = ""
            if t["status"] == "blocked":
                bt = block_info.get("blockType", "question")
                if bt == "question":
                    block_str = f"  ❓{(block_info.get('question') or '')[:50]}"
                else:
                    block_str = f"  ⏳等待中：{(block_info.get('waitingFor') or '')[:50]}"
            print(f"  [{t['id'][:8]}] {t['name']}{dep_str}{block_str}")
    if not tasks:
        print("（暂无任务）")
    print()
    print(render_list_tasks(tasks=tasks, status_filter=status_filter))


def cmd_claim_task(agent: str, args):
    new_sid = args.new_session_id
    if not new_sid:
        print("[ERR] 认领任务需要提供 --new-session-id"); sys.exit(1)
    tasks_dir = get_tasks_dir(agent)
    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = tasks_dir / args.file
    if not file_path.exists():
        print(f"[ERR] 找不到任务文件：{file_path}"); sys.exit(1)
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)
    old_owner = data.get("ownerSession", "")
    if old_owner == new_sid:
        print(f"[INFO] 该任务文件已属于当前 session（{new_sid}），无需认领"); return
    raw_history = data.get("sessionHistory", [])
    history = [
        entry if isinstance(entry, dict) else {"sessionId": entry, "transferredAt": ""}
        for entry in (raw_history if isinstance(raw_history, list) else [])
    ]
    if old_owner:
        history.append({"sessionId": old_owner,
                        "transferredAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    data["sessionHistory"] = history
    data["ownerSession"] = new_sid
    new_path = tasks_dir / f"tasks-{new_sid}.json"
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if file_path.resolve() != new_path.resolve():
        file_path.unlink()
        print(f"[OK] 任务认领成功！原文件：{file_path.name}  新文件：tasks-{new_sid}.json")
    else:
        print(f"[OK] 任务 ownerSession 已更新为 {new_sid}")
    active = [t for t in data.get("tasks", []) if t.get("status") != "completed"]
    print(f"  任务总数：{len(data.get('tasks', []))}，活跃任务：{len(active)}")
    print(f"\n请执行 list_tasks 查看认领的任务列表，继续干活。")


def cmd_get_task_detail(agent: str, args):
    sid = getattr(args, 'session_id', None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    id_map = {t["id"]: t for t in data["tasks"]}
    task = id_map.get(args.id)
    if not task:
        print(f"[ERR] 找不到任务 {args.id}"); sys.exit(1)
    print(f"[TASK] [{task['id'][:8]}] {task['name']}")
    print(f"   状态：{task['status']}")
    print(f"   创建：{task.get('createdAt', '')}  更新：{task.get('updatedAt', '')}")
    if task.get("completedAt"):
        print(f"   完成：{task['completedAt']}")
    print(f"\n描述：\n{task['description']}")
    if task.get("notes"):
        print(f"\n备注：\n{task['notes']}")
    if task.get("implementationGuide"):
        print(f"\n[GUIDE] 实现指南：\n{task['implementationGuide']}")
    if task.get("verificationCriteria"):
        print(f"\n[CHECK] 验证标准：\n{task['verificationCriteria']}")
    if task.get("summary"):
        print(f"\n[NOTE] 完成摘要：\n{task['summary']}")
    deps = task.get("dependencies", [])
    if deps:
        print(f"\n依赖（{len(deps)}）：")
        for d in deps:
            dep_task = id_map.get(d["taskId"])
            name = dep_task["name"] if dep_task else d["taskId"]
            status = dep_task["status"] if dep_task else "unknown"
            print(f"  [{d['taskId'][:8]}] {name}  [{status}]")
    work_log = task.get("workLog", [])
    if work_log:
        print(f"\n工作记录（{len(work_log)} 条）：")
        for i, wl in enumerate(work_log, 1):
            print(f"  [{i}] [{wl.get('type', 'other')}] {wl.get('content', '')[:100]}")
            print(f"       @ {wl.get('createdAt', '')}")


def cmd_execute_task(agent: str, args):
    sid = getattr(args, "session_id", None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    task = next((t for t in data["tasks"] if t["id"] == args.id or t["id"].startswith(args.id)), None)
    if not task:
        print(f"[ERR] 找不到任务 {args.id}"); sys.exit(1)
    if task["status"] in ("completed", "cancelled"):
        print(f"[ERR] 任务状态为 {task['status']}，无需再执行"); sys.exit(1)
    id_map = {t["id"]: t for t in data["tasks"]}
    blocked_by = [
        dep["taskId"] for dep in task.get("dependencies", [])
        if not id_map.get(dep["taskId"]) or id_map[dep["taskId"]]["status"] != "completed"
    ]
    if blocked_by:
        print("[ERR] 依赖未完成，无法执行：")
        for bid in blocked_by:
            dep_task = id_map.get(bid)
            print(f"  [{bid[:8]}] {dep_task['name'] if dep_task else bid}")
        sys.exit(1)
    missing = [f for f in ["implementationGuide", "verificationCriteria", "relatedFiles"] if not task.get(f)]
    if missing:
        print(f"[WARNING] 任务上下文不足，缺少字段：{', '.join(missing)}。建议在执行前使用 update-task 补充，各字段说明请参考 task_fields_guide。")
    task["status"] = "in_progress"
    task["updatedAt"] = now_iso()
    write_data(agent, data, sid)
    print()
    print(render_execute_task(task=task, id_map=id_map))


def cmd_verify_task(agent: str, args):
    sid = getattr(args, "session_id", None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    task = next((t for t in data["tasks"] if t["id"] == args.id or t["id"].startswith(args.id)), None)
    if not task:
        print(f"[ERR] 找不到任务 {args.id}"); sys.exit(1)
    if task["status"] != "in_progress":
        print(f"[ERR] 任务状态为 {task['status']}，只有 in_progress 任务可以验证"); sys.exit(1)
    work_log_str = getattr(args, "work_log", None)
    if work_log_str:
        task.setdefault("workLog", [])
        try:
            entry = json.loads(work_log_str)
            entries = entry if isinstance(entry, list) else [entry]
            for e in entries:
                e.setdefault("createdAt", now_iso())
                task["workLog"].append(e)
            task["updatedAt"] = now_iso()
            write_data(agent, data, sid)
        except json.JSONDecodeError as e:
            print(f"[WARN] --work-log JSON 解析失败，已忽略：{e}")
    print(f"[SEARCH] 验证任务：{task['name']}")
    if task.get("verificationCriteria"):
        print(f"\n验证标准：\n{task['verificationCriteria']}")
    if getattr(args, 'summary', None):
        print(f"\n验证说明：{args.summary}")
    print()
    print(render_verify_task(task=task, all_tasks=data["tasks"]))


def cmd_complete_task(agent: str, args):
    sid = getattr(args, "session_id", None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    task = next((t for t in data["tasks"] if t["id"] == args.id), None)
    if not task:
        print(f"[ERR] 找不到任务 {args.id}"); sys.exit(1)
    task["status"] = "completed"
    task["summary"] = args.summary
    task["completedAt"] = now_iso()
    task["updatedAt"] = now_iso()
    work_log_str = getattr(args, "work_log", None)
    if work_log_str:
        task.setdefault("workLog", [])
        try:
            entry = json.loads(work_log_str)
            entries = entry if isinstance(entry, list) else [entry]
            for e in entries:
                e.setdefault("createdAt", now_iso())
                task["workLog"].append(e)
        except json.JSONDecodeError as e:
            print(f"[WARN] --work-log JSON 解析失败，已忽略：{e}")
    write_data(agent, data, sid)
    if not task.get("relatedFiles"):
        print(f"[REMIND] 任务 \"{task['name']}\" 完成时 relatedFiles 为空。记录关联文件可提升向量记忆检索质量。")
    print(f"[OK] 任务已完成：{task['name']}\n摘要：{args.summary}")
    if getattr(args, 'skip_memory', False):
        return
    try:
        from core.memory_hook import run_memory_hook
        from utils.paths import get_agent_workspace
        run_memory_hook(agent, sid, task, str(get_agent_workspace(agent)))
    except Exception as e:
        print(f"[WARNING] memory 写库失败（不影响任务完成）：{e}")


def cmd_update_task(agent: str, args):
    sid = getattr(args, "session_id", None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    task = next((t for t in data["tasks"] if t["id"] == args.id), None)
    if not task:
        print(f"[ERR] 找不到任务 {args.id}"); sys.exit(1)
    if task["status"] == "completed":
        print("[ERR] 已完成的任务不可更新"); sys.exit(1)
    updated = []
    for field, attr in [
        ("name", getattr(args, 'name', None)),
        ("description", getattr(args, 'description', None)),
        ("notes", getattr(args, 'notes', None)),
        ("implementationGuide", getattr(args, 'implementation_guide', None)),
        ("verificationCriteria", getattr(args, 'verification_criteria', None)),
        ("analysisResult", getattr(args, 'analysis', None)),
    ]:
        if attr is not None:
            task[field] = attr
            updated.append(field)
    related_files_str = getattr(args, "related_files", None)
    if related_files_str is not None:
        try:
            new_files = json.loads(related_files_str)
            if isinstance(new_files, list):
                existing_files = task.get("relatedFiles") or []
                merged = list(existing_files)
                for f in new_files:
                    if f not in merged:
                        merged.append(f)
                task["relatedFiles"] = merged
                updated.append(f"relatedFiles(+{len(new_files)})")
        except json.JSONDecodeError as e:
            print(f"[WARN] --related-files JSON 解析失败，已忽略：{e}")
    if updated:
        task["updatedAt"] = now_iso()
        write_data(agent, data, sid)
        print(f"[OK] 已更新任务 [{args.id[:8]}] {task['name']}：{', '.join(updated)}")
    else:
        print("[WARN] 没有提供需要更新的内容")


def cmd_delete_task(agent: str, args):
    sid = getattr(args, "session_id", None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    task = next((t for t in data["tasks"] if t["id"] == args.id or t["id"].startswith(args.id)), None)
    if task:
        if task["status"] == "completed":
            print("[ERR] 已完成的任务不可删除"); sys.exit(1)
        dependents = [t for t in data["tasks"]
                      if any(d["taskId"] == task["id"] for d in t.get("dependencies", []))]
        if dependents:
            print("[ERR] 以下任务依赖此任务，无法删除：")
            for dt in dependents:
                print(f"  [{dt['id'][:8]}] {dt['name']}")
            sys.exit(1)
        data["tasks"] = [t for t in data["tasks"] if t["id"] != task["id"]]
        write_data(agent, data, sid)
        print(f"[DEL] 已删除任务：{task['name']}")
        return
    print(f"[ERR] 找不到任务 {args.id}"); sys.exit(1)


def cmd_archive(agent: str, args):
    if not getattr(args, 'confirm', False):
        print("[WARN] 请加 --confirm 参数确认清空操作"); sys.exit(1)
    sid = getattr(args, 'session_id', None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    tasks_file = get_tasks_path(agent, sid)
    if not tasks_file.exists():
        print(f"未找到属于当前 session 的任务文件：{tasks_file.name}"); sys.exit(0)
    with open(tasks_file, encoding="utf-8") as f:
        data = json.load(f)
    all_tasks = data.get("tasks", [])
    mem_dir = get_memory_dir(agent)
    mem_dir.mkdir(parents=True, exist_ok=True)
    backup_path = mem_dir / f"{sid}.json"
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tasks_file.unlink()
    completed = [t for t in all_tasks if t["status"] == "completed"]
    incomplete = [t for t in all_tasks if t["status"] != "completed"]
    print(f"[DEL] 已归档并删除：{tasks_file.name}（共 {len(all_tasks)} 个任务）")
    print(f"[OK] 归档完成：共清空 {len(all_tasks)} 个任务，备份 {len(completed)} 个已完成 + {len(incomplete)} 个未完成任务")


def cmd_clear_tasks(agent: str, args):
    """clear_tasks 已更名为 archive，此函数保留为兼容别名。"""
    print("[WARN] 该命令已更名为 archive，请使用：task-manager.py --agent <agent> --session-id <sid> archive --confirm")
    cmd_archive(agent, args)


def cmd_complete_session(agent: str, args):
    sid = getattr(args, 'session_id', None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    tasks = data.get("tasks", [])
    updated = []
    for t in tasks:
        if t.get("status") in {"todo", "doing"}:
            t["status"] = "completed"
            t["completedAt"] = now_iso()
            t.setdefault("summary", "由 complete_session 批量标记为完成")
            updated.append(t)
    write_data(agent, data, sid)
    if updated:
        print(f"[OK] 已将 {len(updated)} 个任务批量标记为 completed：")
        for t in updated:
            print(f"     [{t['id'][:8]}] {t['name']}")
    else:
        print("[INFO] 当前 session 下没有 todo/doing 状态的任务，无需操作")


def cmd_query_task(agent: str, args):
    keyword = args.keyword.lower()
    page = getattr(args, 'page', 1)
    page_size = getattr(args, 'page_size', 10)
    sid = getattr(args, "session_id", None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    all_tasks = [dict(t, _source="current") for t in data["tasks"]]
    mem_dir = get_memory_dir(agent)
    if mem_dir.exists():
        for f in sorted(mem_dir.glob("*.json"), reverse=True):
            try:
                with open(f, encoding="utf-8") as fh:
                    archive = json.load(fh)
                for t in archive.get("tasks", []):
                    all_tasks.append(dict(t, _source=f.name))
            except Exception:
                pass

    def matches(t):
        return any(keyword in (t.get(field) or "").lower()
                   for field in ("name", "description", "notes", "summary"))

    results = [t for t in all_tasks if matches(t)]
    total = len(results)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    print(f"[SEARCH] 关键词「{args.keyword}」共找到 {total} 条，第 {page}/{total_pages} 页\n")
    for t in results[start:start + page_size]:
        summary = (t.get("summary") or "")[:80]
        print(f"  [{t['id'][:8]}] [{t['status']}] {t['name']}  ({t.get('_source', '')})")
        if summary:
            print(f"           摘要: {summary}")
