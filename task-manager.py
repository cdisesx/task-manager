#!/usr/bin/env python3
"""task-manager.py - task-manager 主入口（开源封装版）"""
import argparse
import logging
import os
import sys
from pathlib import Path

# 强制 UTF-8 输出
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 将当前目录加入 sys.path，确保模块可导入
_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from core.task_crud import (
    cmd_get_session_id, cmd_plan_task, cmd_split_tasks, cmd_list_tasks,
    cmd_get_task_detail, cmd_execute_task, cmd_verify_task, cmd_complete_task,
    cmd_update_task, cmd_delete_task, cmd_query_task, cmd_archive,
    cmd_complete_session, cmd_claim_task,
)
from skills.block import cmd_block_task, cmd_block_queue, cmd_unblock_task
from skills.subtask import cmd_add_subtask, cmd_resplit_task
from skills.worklog import cmd_add_work_log, cmd_cancel_task
from skills.todo import cmd_create_todo, cmd_plan_from_todo, cmd_assign_task, cmd_list_todos

# ── 日志初始化 ─────────────────────────────────────────────────────────────────

def _init_logger(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("task_manager")
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(log_dir / "task_manager.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"
        ))
        logger.addHandler(fh)
    return logger


def _log(logger, agent, sid, cmd, result, error=""):
    logger.info("agent=%s | session=%s | cmd=%s | result=%s%s",
                agent, sid or "(none)", cmd, result, f" | error={error}" if error else "")


# ── argparse 注册 ──────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="task_manager")
    p.add_argument("--agent", required=True)
    p.add_argument("--session-id", dest="session_id", default=None)
    p.add_argument("--config", default=None,
                   help="指向 config.json 的路径，默认读取 config/config.json")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("get-session-id")

    s = sub.add_parser("plan-task")
    s.add_argument("--description", required=True)
    s.add_argument("--requirements")

    s = sub.add_parser("split-tasks")
    s.add_argument("--mode", required=True, choices=["append", "overwrite", "selective", "clearAllTasks"])
    s.add_argument("--tasks", required=True)
    s.add_argument("--user-requirement", dest="user_requirement")
    s.add_argument("--analysis")

    s = sub.add_parser("list-tasks")
    s.add_argument("--status", default="all", choices=["all", "pending", "in_progress", "completed", "blocked"])

    s = sub.add_parser("get-task-detail")
    s.add_argument("--id", required=True)

    s = sub.add_parser("execute-task")
    s.add_argument("--id", required=True)

    s = sub.add_parser("verify-task")
    s.add_argument("--id", required=True)
    s.add_argument("--summary")
    s.add_argument("--work-log", dest="work_log", default=None)

    s = sub.add_parser("complete-task")
    s.add_argument("--id", required=True)
    s.add_argument("--summary", required=True)
    s.add_argument("--work-log", dest="work_log", default=None)
    s.add_argument("--skip-memory", dest="skip_memory", action="store_true")

    s = sub.add_parser("update-task")
    s.add_argument("--id", required=True)
    s.add_argument("--name"); s.add_argument("--description"); s.add_argument("--notes")
    s.add_argument("--implementation-guide", dest="implementation_guide")
    s.add_argument("--verification-criteria", dest="verification_criteria")
    s.add_argument("--analysis")
    s.add_argument("--related-files", dest="related_files")

    s = sub.add_parser("delete-task")
    s.add_argument("--id", required=True)

    s = sub.add_parser("query-task")
    s.add_argument("--keyword", required=True)
    s.add_argument("--page", type=int, default=1)
    s.add_argument("--page-size", dest="page_size", type=int, default=10)

    s = sub.add_parser("archive"); s.add_argument("--confirm", action="store_true")
    sub.add_parser("complete-session")

    s = sub.add_parser("claim-task")
    s.add_argument("--file", required=True)
    s.add_argument("--new-session-id", dest="new_session_id", required=True)

    s = sub.add_parser("block-task")
    s.add_argument("--id", required=True); s.add_argument("--reason", required=True); s.add_argument("--question", required=True)

    s = sub.add_parser("block-queue")
    s.add_argument("--id", required=True); s.add_argument("--reason", required=True)
    s.add_argument("--waiting-for", dest="waiting_for", required=True)

    s = sub.add_parser("unblock-task")
    s.add_argument("--id", required=True); s.add_argument("--answer", required=True)

    s = sub.add_parser("add-subtask")
    s.add_argument("--parent-id", dest="parent_id", required=True)
    s.add_argument("--name", required=True); s.add_argument("--desc", required=True)
    s.add_argument("--guide", default=None, help="实现指引")
    s.add_argument("--criteria", default=None, help="验证标准")
    s.add_argument("--notes", default=None, help="备注")

    s = sub.add_parser("resplit-task")
    s.add_argument("--id", required=True); s.add_argument("--tasks", required=True)

    s = sub.add_parser("add-work-log")
    s.add_argument("--id", required=True)
    s.add_argument("--type", required=True, choices=["code_change", "answer", "thought", "action", "other"])
    s.add_argument("--content", required=True)
    s.add_argument("--files", default=None); s.add_argument("--line-range", dest="line_range", default=None)

    s = sub.add_parser("cancel-task")
    s.add_argument("--id", required=True); s.add_argument("--reason", required=True)

    s = sub.add_parser("create-todo")
    s.add_argument("--description", required=True); s.add_argument("--creator", default=None)

    s = sub.add_parser("plan-from-todo")
    s.add_argument("--todo-session-id", dest="todo_session_id", required=True)

    s = sub.add_parser("assign-task")
    s.add_argument("--todo-session-id", dest="todo_session_id", required=True)
    s.add_argument("--target-agent", dest="target_agent", required=True)
    s.add_argument("--target-session-id", dest="target_session_id", required=True)

    s = sub.add_parser("list-todos")
    s.add_argument("--status", default="all", choices=["all", "pending", "planned", "assigned"])

    return p


DISPATCH = {
    "get-session-id": cmd_get_session_id,
    "plan-task": cmd_plan_task, "split-tasks": cmd_split_tasks,
    "list-tasks": cmd_list_tasks, "get-task-detail": cmd_get_task_detail,
    "execute-task": cmd_execute_task, "verify-task": cmd_verify_task,
    "complete-task": cmd_complete_task, "update-task": cmd_update_task,
    "delete-task": cmd_delete_task, "query-task": cmd_query_task,
    "archive": cmd_archive, "complete-session": cmd_complete_session,
    "claim-task": cmd_claim_task,
    "block-task": cmd_block_task, "block-queue": cmd_block_queue, "unblock-task": cmd_unblock_task,
    "add-subtask": cmd_add_subtask, "resplit-task": cmd_resplit_task,
    "add-work-log": cmd_add_work_log, "cancel-task": cmd_cancel_task,
    "create-todo": cmd_create_todo, "plan-from-todo": cmd_plan_from_todo,
    "assign-task": cmd_assign_task, "list-todos": cmd_list_todos,
}


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help(); sys.exit(1)

    # 支持 --config 参数指向外部 config 文件
    if getattr(args, "config", None):
        os.environ["TASK_MANAGER_CONFIG"] = args.config

    log_dir = _HERE / "logs"
    logger = _init_logger(log_dir)
    sid = getattr(args, "session_id", None) or ""

    fn = DISPATCH.get(args.command)
    if not fn:
        print(f"[ERR] 未知命令：{args.command}"); sys.exit(1)

    _log(logger, args.agent, sid, args.command, "started")
    try:
        fn(args.agent, args)
        _log(logger, args.agent, sid, args.command, "ok")
    except SystemExit as e:
        if e.code != 0:
            _log(logger, args.agent, sid, args.command, f"exit({e.code})", "non-zero exit")
        raise
    except Exception as e:
        _log(logger, args.agent, sid, args.command, "error", str(e))
        raise


if __name__ == "__main__":
    main()
