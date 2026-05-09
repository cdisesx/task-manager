"""skills/block.py - block_task / block_queue / unblock_task 命令"""
import sys
from utils import now_iso, read_data, write_data


def cmd_block_task(agent: str, args):
    sid = getattr(args, "session_id", None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    task = next((t for t in data["tasks"] if t["id"] == args.id), None)
    if not task:
        print(f"[ERR] 找不到任务 {args.id}"); sys.exit(1)
    if task["status"] == "completed":
        print("[ERR] 已完成的任务不可阻塞"); sys.exit(1)
    task["status"] = "blocked"
    task["blockInfo"] = {
        "blockType": "question",
        "reason": args.reason,
        "question": args.question,
        "blockedAt": now_iso(),
        "unblockAnswer": None,
        "unblockedAt": None,
    }
    task["updatedAt"] = now_iso()
    write_data(agent, data, sid)
    print(f"[BLOCKED] 任务已阻塞：{task['name']}")
    print(f"  原因：{args.reason}")
    print(f"  问题：{args.question}")


def cmd_block_queue(agent: str, args):
    sid = getattr(args, "session_id", None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    task = next((t for t in data["tasks"] if t["id"] == args.id), None)
    if not task:
        print(f"[ERR] 找不到任务 {args.id}"); sys.exit(1)
    if task["status"] == "completed":
        print("[ERR] 已完成的任务不可阻塞"); sys.exit(1)
    task["status"] = "blocked"
    task["blockInfo"] = {
        "blockType": "queue",
        "reason": args.reason,
        "waitingFor": args.waiting_for,
        "blockedAt": now_iso(),
        "unblockAnswer": None,
        "unblockedAt": None,
    }
    task["updatedAt"] = now_iso()
    write_data(agent, data, sid)
    print(f"[BLOCKED/QUEUE] 任务排队等待：{task['name']}")
    print(f"  原因：{args.reason}")
    print(f"  等待：{args.waiting_for}")


def cmd_unblock_task(agent: str, args):
    sid = getattr(args, "session_id", None)
    if not sid:
        print("ERROR: 缺少 --session-id"); sys.exit(1)
    data = read_data(agent, sid)
    task = next((t for t in data["tasks"] if t["id"] == args.id), None)
    if not task:
        print(f"[ERR] 找不到任务 {args.id}"); sys.exit(1)
    if task["status"] != "blocked":
        print(f"[ERR] 任务状态为 {task['status']}，只有 blocked 任务可以解除阻塞"); sys.exit(1)
    task["status"] = "in_progress"
    block_info = task.get("blockInfo", {})
    block_info["unblockAnswer"] = args.answer
    block_info["unblockedAt"] = now_iso()
    task["blockInfo"] = block_info
    task["updatedAt"] = now_iso()
    write_data(agent, data, sid)
    print(f"[UNBLOCKED] 任务已解除阻塞：{task['name']}")
    print(f"  回答：{args.answer}")
