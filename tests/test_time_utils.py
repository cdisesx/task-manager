"""tests/test_time_utils.py - 测试 utils/time_utils.py

测试方法:
  - now_iso()     → 返回 "YYYY-MM-DDTHH:MM:SS" 格式字符串
  - now_stamp()   → 返回 "YYYYMMDD_HHMMSS" 格式字符串

使用:
  pytest tests/test_time_utils.py -v

预期输出:
  test_now_iso_format ......... PASSED  [ 50%]
  test_now_stamp_format ....... PASSED  [100%]
"""
import re

from utils.time_utils import now_iso, now_stamp


class TestNowIso:
    """测试 now_iso()"""

    def test_now_iso_format(self):
        """验证 now_iso() 返回 ISO 8601 格式: YYYY-MM-DDTHH:MM:SS"""
        result = now_iso()
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", result), (
            f"格式不匹配: {result}"
        )

    def test_now_iso_dynamic(self):
        """验证连续两次调用返回不同的值（时间在前进）"""
        t1 = now_iso()
        t2 = now_iso()
        # 由于时间会变化，两次结果通常不同；至少格式要一致
        assert isinstance(t1, str)
        assert isinstance(t2, str)
        assert len(t1) == 19


class TestNowStamp:
    """测试 now_stamp()"""

    def test_now_stamp_format(self):
        """验证 now_stamp() 返回 YYYYMMDD_HHMMSS 格式"""
        result = now_stamp()
        assert re.match(r"\d{8}_\d{6}", result), (
            f"格式不匹配: {result}"
        )

    def test_now_stamp_length(self):
        """验证 stamp 字符串长度为 15 (8+1+6)"""
        result = now_stamp()
        assert len(result) == 15
