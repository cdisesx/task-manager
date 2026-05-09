"""skills/archive.py - archive 命令（从 core/task_crud 重导出）"""
from core.task_crud import cmd_archive, cmd_clear_tasks

__all__ = ["cmd_archive", "cmd_clear_tasks"]
