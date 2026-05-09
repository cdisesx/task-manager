"""skills/worklog.py - add_work_log / cancel_task 命令"""
import json
import sys
from utils import now_iso, read_data, write_data


def cmd_add_work_log(agent: str, args):
    sid = getattr(args, "session_id", None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    task = next((t for t in data["tasks"] if t["id"] == args.id or t["id"].startswith(args.id)), None)
    if not task:
        print(f"[ERR] 找不到任务 {args.id}"); sys.exit(1)
    entry = {"type": args.type, "content": args.content, "createdAt": now_iso()}
    if args.files:
        try:
            entry["files"] = json.loads(args.files)
        except json.JSONDecodeError:
            entry["files"] = [f.strip() for f in args.files.split(",") if f.strip()]
    if args.line_range:
        entry["lineRange"] = args.line_range
    task.setdefault("workLog", []).append(entry)
    task["updatedAt"] = now_iso()
    write_data(agent, data, sid)
    print(f"[OK] 已向任务 [{task['id'][:8]}] {task['name']} 追加工作记录：")
    print(f"     type={entry['type']}  content={entry['content'][:80]}")


def cmd_cancel_task(agent: str, args):
    sid = getattr(args, "session_id", None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    task = next((t for t in data["tasks"] if t["id"] == args.id or t["id"].startswith(args.id)), None)
    if task:
        if task["status"] == "completed":
            print("[ERR] 已完成的任务不可取消"); sys.exit(1)
        task["status"] = "cancelled"
        task["cancelReason"] = args.reason
        task["cancelledAt"] = now_iso()
        task["updatedAt"] = now_iso()
        write_data(agent, data, sid)
        print(f"[OK] 任务已取消：[{task['id'][:8]}] {task['name']}")
        print(f"     原因：{args.reason}")
        return
    for t in data["tasks"]:
        for sub in t.get("subtasks", []):
            if sub["id"] == args.id or sub["id"].startswith(args.id):
                sub["status"] = "cancelled"
                sub["cancelReason"] = args.reason
                sub["cancelledAt"] = now_iso()
                t["updatedAt"] = now_iso()
                write_data(agent, data, sid)
                print(f"[OK] 子任务已取消：[{sub['id'][:8]}] {sub['name']}")
                print(f"     原因：{args.reason}")
                return
    print(f"[ERR] 找不到任务或子任务 {args.id}"); sys.exit(1)
