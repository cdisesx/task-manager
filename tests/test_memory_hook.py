"""tests/test_memory_hook.py - 测试 core/memory_hook.py

测试方法:
  - infer_task_type()              → 根据任务文本推断任务类型
  - score_importance()             → 计算任务重要性评分
  - build_memory_text_template()   → 构建记忆文本模板
  - _is_enabled()                  → 检查 vector_memory 是否启用

使用:
  pytest tests/test_memory_hook.py -v

预期输出:
  test_infer_type_architecture ... PASSED
  test_infer_type_bugfix ......... PASSED
  test_infer_type_integration .... PASSED
  test_infer_type_tooling ........ PASSED
  test_infer_type_cleanup ........ PASSED
  test_infer_type_general ........ PASSED
  test_score_importance_base ..... PASSED
  test_score_importance_bugfix ... PASSED
  test_score_bounds .............. PASSED
  test_build_text_high_value ..... PASSED
  test_build_text_normal ......... PASSED
  test_build_text_truncation ..... PASSED
  test_is_enabled_default ........ PASSED
"""
import json
from pathlib import Path
from unittest.mock import patch

from core.memory_hook import infer_task_type, score_importance, build_memory_text_template, _is_enabled


class TestInferTaskType:
    """测试 infer_task_type() - 根据文本推断任务类型"""

    def test_infer_type_architecture(self):
        """包含"架构"、"设计"、"方案"、rule 等关键词 → architecture"""
        cases = [
            ("系统架构设计", "architecture"),
            ("数据库设计方案", "architecture"),
            ("制定编码规范", "architecture"),
            ("编写开发 workflow", "architecture"),
        ]
        for text, expected in cases:
            task = {"name": text, "description": "", "summary": ""}
            assert infer_task_type(task) == expected, f"'{text}' 应推断为 {expected}"

    def test_infer_type_bugfix(self):
        """包含"bug"、"修复"、"排查"等关键词 → bugfix"""
        cases = [
            ("修复登录 bug", "bugfix"),
            ("排查内存泄漏故障", "bugfix"),
            ("fix 页面崩溃问题", "bugfix"),
        ]
        for text, expected in cases:
            task = {"name": text, "description": "", "summary": ""}
            assert infer_task_type(task) == expected, f"'{text}' 应推断为 {expected}"

    def test_infer_type_integration(self):
        """包含"集成"、"接入"、"hook"等关键词 → integration"""
        cases = [
            ("集成第三方支付", "integration"),
            ("接入微信登录", "integration"),
            ("编写 git hook", "integration"),
        ]
        for text, expected in cases:
            task = {"name": text, "description": "", "summary": ""}
            assert infer_task_type(task) == expected, f"'{text}' 应推断为 {expected}"

    def test_infer_type_tooling(self):
        """包含"脚本"、"tool"、"cli"等关键词 → tooling"""
        cases = [
            ("编写部署脚本", "tooling"),
            ("开发命令行 tool", "tooling"),
            ("实现自动化流程", "tooling"),
        ]
        for text, expected in cases:
            task = {"name": text, "description": "", "summary": ""}
            assert infer_task_type(task) == expected, f"'{text}' 应推断为 {expected}"

    def test_infer_type_cleanup(self):
        """包含"整理"、"搬运"、"格式"等关键词 → cleanup"""
        cases = [
            ("整理代码格式", "cleanup"),
            ("搬运数据文件", "cleanup"),
        ]
        for text, expected in cases:
            task = {"name": text, "description": "", "summary": ""}
            assert infer_task_type(task) == expected, f"'{text}' 应推断为 {expected}"

    def test_infer_type_general(self):
        """无匹配关键词 → general"""
        task = {"name": "日常任务", "description": "一些普通工作", "summary": ""}
        assert infer_task_type(task) == "general"


class TestScoreImportance:
    """测试 score_importance() - 重要性评分"""

    def test_score_base_value(self):
        """验证 general 类型任务的基础分值"""
        task = {
            "name": "普通任务",
            "description": "普通描述",
            "summary": "",
            "notes": "",
            "workLog": [],
            "relatedFiles": [],
            "analysisResult": "",
            "verificationCriteria": "",
        }
        result = score_importance(task)
        assert result["rule_score"] >= 0.20
        assert result["rule_score"] <= 0.95
        assert result["type"] in ("general",)

    def test_score_architecture_boost(self):
        """验证 architecture 类型且有验证标准时，评分不低于 0.70"""
        task = {
            "name": "系统架构设计方案",
            "description": "设计微服务架构",
            "summary": "",
            "notes": "",
            "workLog": [],
            "relatedFiles": ["arch.md", "design.md", "api.md", "deploy.md"],
            "analysisResult": "涉及多个模块，需要详细架构设计",
            "verificationCriteria": "架构评审通过",
        }
        result = score_importance(task)
        assert result["rule_score"] >= 0.70, f"architecture 任务评分应 >= 0.70, 实际 {result['rule_score']}"

    def test_score_bugfix_with_pitfall(self):
        """验证 bugfix 类型且有踩坑信息时加分"""
        task = {
            "name": "修复编码问题",
            "description": "修复 GBK 编码兼容问题",
            "summary": "踩坑：Windows 下编码冲突",
            "notes": "",
            "workLog": ["遇到报错"],
            "relatedFiles": ["a.py"],
            "analysisResult": "",
            "verificationCriteria": "",
        }
        result = score_importance(task)
        assert result["detail"]["pitfall_w"] > 0
        assert result["detail"]["type_w"] > 0

    def test_score_bounds(self):
        """验证评分始终在 [0.20, 0.95] 范围内"""
        task = {
            "name": "",
            "description": "",
            "summary": "",
            "notes": "",
            "workLog": [],
            "relatedFiles": [],
            "analysisResult": "",
            "verificationCriteria": "",
        }
        for _ in range(10):
            result = score_importance(task)
            assert 0.20 <= result["rule_score"] <= 0.95, (
                f"评分超出范围: {result['rule_score']}"
            )

    def test_score_detail_structure(self):
        """验证返回的 detail 字典包含所有预期字段"""
        task = {
            "name": "测试",
            "description": "测试描述",
            "summary": "测试摘要",
            "notes": "测试备注",
            "workLog": [{"type": "code_change", "content": "修改代码"}],
            "relatedFiles": ["a.py", "b.py", "c.py"],
            "analysisResult": "分析结果较长时加分 " * 10,
            "verificationCriteria": "验证标准",
        }
        result = score_importance(task)
        detail = result["detail"]
        assert "base" in detail
        assert "type_w" in detail
        assert "pitfall_w" in detail
        assert "fallback_w" in detail
        assert "files_w" in detail
        assert "verify_w" in detail
        assert "reuse_w" in detail
        assert "analysis_w" in detail


class TestBuildMemoryTextTemplate:
    """测试 build_memory_text_template()"""

    def test_build_text_high_value(self):
        """验证高价值任务(importance>=0.70)包含【实现方案要点】等字段"""
        task = {
            "name": "实现用户认证模块",
            "description": "基于 JWT 实现用户认证",
            "summary": "已完成认证模块开发",
            "notes": "使用 RS256 算法",
            "workLog": [],
            "relatedFiles": ["auth.py", "middleware.py", "config.py", "test_auth.py"],
            "implementationGuide": "使用 pyjwt 库",
            "verificationCriteria": "测试通过",
            "analysisResult": "",
        }
        score_detail = {
            "rule_score": 0.82,
            "type": "architecture",
            "detail": {"base": 0.35, "type_w": 0.28, "pitfall_w": 0.0,
                       "fallback_w": 0.0, "files_w": 0.14, "verify_w": 0.0,
                       "reuse_w": 0.0, "analysis_w": 0.0}
        }
        text = build_memory_text_template(task, score_detail)
        assert "【实现方案要点】" in text, "高价值文本应包含实现方案要点"
        assert "【任务主题】" in text, "高价值文本应包含任务主题"
        assert "【影响范围】" in text, "高价值文本应包含影响范围"
        assert "【检索标签】" in text, "高价值文本应包含检索标签"
        assert "architecture" in text

    def test_build_text_normal(self):
        """验证普通任务文本格式"""
        task = {
            "name": "整理文档",
            "description": "整理 API 文档格式",
            "summary": "已完成格式整理",
            "notes": "",
            "workLog": [],
            "relatedFiles": ["readme.md"],
            "implementationGuide": "",
            "verificationCriteria": "",
            "analysisResult": "",
        }
        score_detail = {
            "rule_score": 0.40,
            "type": "cleanup",
            "detail": {"base": 0.35, "type_w": 0.02, "pitfall_w": 0.0,
                       "fallback_w": 0.0, "files_w": 0.0, "verify_w": 0.0,
                       "reuse_w": 0.0, "analysis_w": 0.0}
        }
        text = build_memory_text_template(task, score_detail)
        assert "【任务目标】" in text, "普通文本应包含任务目标"
        assert "【任务类型】" in text
        assert "cleanup" in text

    def test_build_text_truncation(self):
        """验证文本长度被截断到 800 字符以内"""
        task = {
            "name": "A" * 500,
            "description": "B" * 500,
            "summary": "C" * 500,
            "notes": "D" * 500,
            "workLog": [],
            "relatedFiles": ["x.py", "y.py", "z.py", "w.py"],
            "implementationGuide": "E" * 500,
            "verificationCriteria": "F" * 500,
            "analysisResult": "",
        }
        score_detail = {
            "rule_score": 0.75,
            "type": "general",
            "detail": {"base": 0.35, "type_w": 0.08, "pitfall_w": 0.0,
                       "fallback_w": 0.0, "files_w": 0.10, "verify_w": 0.0,
                       "reuse_w": 0.0, "analysis_w": 0.0}
        }
        text = build_memory_text_template(task, score_detail)
        assert len(text) <= 800, f"文本长度 {len(text)} 超过 800"


class TestIsEnabled:
    """测试 _is_enabled()"""

    def test_is_enabled_default(self, tmp_path):
        """验证默认情况下（无配置文件）返回 False"""
        result = _is_enabled()
        assert result is False

    def test_is_enabled_true(self):
        """验证配置 vector_memory.enabled=True 时返回 True"""
        config_json = json.dumps({"vector_memory": {"enabled": True}})
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=config_json):
                assert _is_enabled() is True

    def test_is_enabled_exception(self):
        """验证配置文件解析异常时返回 False"""
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", side_effect=Exception("读文件失败")):
                assert _is_enabled() is False
