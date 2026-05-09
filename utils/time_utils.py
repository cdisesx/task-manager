"""utils/time_utils.py - 时间工具函数"""
from datetime import datetime


def now_iso() -> str:
    """返回当前时间 ISO 格式字符串"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def now_stamp() -> str:
    """返回当前时间戳字符串，用于文件名"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
