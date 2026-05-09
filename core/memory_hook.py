"""core/memory_hook.py - vector-memory 集成逻辑，支持 enabled/disabled 配置"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.json"


def _is_enabled() -> bool:
    """读取 config.json 中 vector_memory.enabled，默认 False"""
    try:
        if _CONFIG_PATH.exists():
            cfg = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            return bool(cfg.get("vector_memory", {}).get("enabled", False))
    except Exception:
        pass
    return False


def infer_task_type(task: dict) -> str:
    text = " ".join(filter(None, [
        task.get("name", ""), task.get("description", ""), task.get("summary", ""),
    ])).lower()
    if any(k in text for k in ["架构", "设计", "方案", "规范", "rule", "workflow"]):
        return "architecture"
    if any(k in text for k in ["bug", "修复", "fix", "排查", "故障"]):
        return "bugfix"
    if any(k in text for k in ["集成", "接入", "对接", "hook", "pipeline", "cron"]):
        return "integration"
    if any(k in text for k in ["脚本", "tool", "cli", "自动化"]):
        return "tooling"
    if any(k in text for k in ["整理", "搬运", "格式"]):
        return "cleanup"
    return "general"


def score_importance(task: dict) -> dict:
    base = 0.35
    task_type = infer_task_type(task)
    type_weights = {
        "cleanup": 0.02, "tooling": 0.08, "bugfix": 0.15,
        "general": 0.08, "integration": 0.22, "architecture": 0.28,
    }
    type_w = type_weights.get(task_type, 0.08)

    scan_text = " ".join(filter(None, [
        task.get("summary", ""), task.get("notes", ""), str(task.get("workLog", "")),
    ])).lower()
    pitfall_w = 0.12 if any(k in scan_text for k in ["踩坑", "问题", "失败", "报错", "异常", "兼容", "编码", "gbk", "utf-8", "冲突"]) else 0.0
    fallback_w = 0.08 if any(k in scan_text for k in ["降级", "fallback", "pending", "retry", "回退", "不阻断", "ignore", "容错"]) else 0.0

    related_files = task.get("relatedFiles") or []
    file_count = len([f for f in related_files if f]) if isinstance(related_files, list) else 0
    files_w = 0.0 if file_count <= 1 else (0.05 if file_count <= 3 else (0.10 if file_count <= 7 else 0.14))

    analysis = task.get("analysisResult") or ""
    analysis_w = 0.0
    if len(analysis) > 50:
        analysis_w += 0.08
    if any(k in analysis for k in ["架构", "方案", "设计", "接口", "协议", "优化", "重构"]):
        analysis_w += 0.10

    has_criteria = bool(task.get("verificationCriteria"))
    combined = (task.get("summary", "") or "").lower() + " " + str(task.get("workLog", "")).lower()
    if not has_criteria:
        verify_w = 0.0
    elif any(k in combined for k in ["测试通过", "验证通过", "可重复执行"]):
        verify_w = 0.15 if any(k in combined for k in ["pytest", "script 验证"]) else 0.10
    elif any(k in combined for k in ["通过", "verified", "pass", "已验证", "tested", "可运行"]):
        verify_w = 0.10
    else:
        verify_w = 0.03

    reuse_text = (task.get("summary", "") or "") + " " + (task.get("notes", "") or "")
    if any(k in reuse_text for k in ["模板", "标准", "规范", "通用", "复用", "后续可用"]):
        reuse_w = 0.18
    elif task_type in ("architecture", "integration"):
        reuse_w = 0.10
    elif file_count >= 2:
        reuse_w = 0.10
    else:
        reuse_w = 0.0

    raw = base + type_w + pitfall_w + fallback_w + files_w + verify_w + reuse_w + analysis_w
    if task_type == "cleanup" and pitfall_w == 0 and reuse_w == 0 and verify_w == 0:
        raw = min(raw, 0.45)
    if task_type == "architecture" and (has_criteria or pitfall_w > 0):
        raw = max(raw, 0.70)
    raw = max(0.20, min(0.95, raw))

    return {
        "rule_score": round(raw, 2),
        "type": task_type,
        "detail": {
            "base": base, "type_w": type_w, "pitfall_w": pitfall_w,
            "fallback_w": fallback_w, "files_w": files_w,
            "verify_w": verify_w, "reuse_w": reuse_w, "analysis_w": analysis_w,
        }
    }


def build_memory_text_template(task: dict, score_detail: dict) -> str:
    importance = score_detail["rule_score"]
    task_type = score_detail["type"]
    related_files = task.get("relatedFiles") or []
    file_count = len([f for f in related_files if f]) if isinstance(related_files, list) else 0

    use_high_value = (
        importance >= 0.70 or task_type in ("architecture", "integration")
        or file_count >= 4
        or score_detail["detail"].get("pitfall_w", 0) > 0
        or score_detail["detail"].get("fallback_w", 0) > 0
    )

    f_name = task.get("name") or ""
    f_desc = task.get("description") or ""
    f_summary = task.get("summary") or f_desc
    f_notes = task.get("notes") or ""
    f_criteria = task.get("verificationCriteria") or ""
    f_impl = task.get("implementationGuide") or ""
    f_analysis = task.get("analysisResult") or ""
    work_log = task.get("workLog") or []
    pitfall_entries = [str(e) for e in (work_log if isinstance(work_log, list) else [str(work_log)])
                       if any(k in str(e) for k in ["bug", "fix", "error", "failed", "注意", "坑", "踩坑", "报错", "失败"])]
    f_pitfalls = " | ".join(pitfall_entries[:3])
    f_lessons = " ".join(filter(None, [f_summary, f_notes]))
    f_files = ", ".join(str(f) for f in related_files[:5] if f) if related_files else "无显式文件"

    def _proportional_truncate(fields, max_total=800):
        total = sum(len(s) for s in fields)
        if total <= max_total:
            return fields
        return [s[:max(1, int(len(s) / total * max_total))] for s in fields]

    if use_high_value:
        impact_scope = " + ".join(filter(None, [task_type, f"{file_count}个文件" if file_count else ""])) or "单模块"
        tags_str = ", ".join(filter(None, [task_type, (f_name[:20] if f_name else "")]))
        raw_fields = [f_name, f_desc, f_summary, f_criteria, f_lessons, f_impl, f_analysis, f_pitfalls]
        t = _proportional_truncate(raw_fields)
        parts = [f"【任务主题】{t[0]}", f"【任务类型】{task_type}", f"【要解决的问题】{t[1]}", f"【最终产出】{t[2]}"]
        if t[5]: parts.append(f"【实现方案要点】{t[5]}")
        if t[6]: parts.append(f"【分析发现】{t[6]}")
        if t[7]: parts.append(f"【踩坑记录】{t[7]}")
        parts += [f"【验证与证据】{t[3] or '无'}", f"【关键踩坑/约束】{t[4] or '无'}",
                  f"【影响范围】{impact_scope}", f"【关联文件】{f_files}", f"【检索标签】{tags_str}"]
    else:
        raw_fields = [f_desc, f_summary, f_criteria, f_lessons, f_impl, f_analysis, f_pitfalls]
        t = _proportional_truncate(raw_fields)
        parts = [f"【任务类型】{task_type}", f"【任务目标】{t[0]}", f"【最终结果】{t[1]}"]
        if t[4]: parts.append(f"【实现方案要点】{t[4]}")
        if t[5]: parts.append(f"【分析发现】{t[5]}")
        if t[6]: parts.append(f"【踩坑记录】{t[6]}")
        parts += [f"【验证结果】{t[2] or '无'}", f"【经验与约束】{t[3] or '无'}", f"【关联文件】{f_files}"]

    return "\n".join(parts)[:800]


def write_task_memory(payload: dict, workspace: str):
    """调用 memory_writer.py 写入向量库，失败时抛出异常"""
    writer_path = Path(__file__).parent.parent.parent / "vector-memory" / "scripts" / "memory_writer.py"
    tmp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=False)
    tmp.write(payload["text"])
    tmp.close()
    try:
        cmd = [
            sys.executable, str(writer_path),
            "--agent", payload["agent"],
            "--table", payload["table"],
            "--text-file", tmp.name,
            "--type", payload.get("type", "task_result"),
            "--task-id", payload.get("task_id", ""),
            "--session-id", payload.get("session_id", ""),
            "--importance", str(payload.get("importance", 0.5)),
            "--tags", payload.get("tags", ""),
            "--workspace", workspace,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=30)
        if result.returncode != 0 or "[ERROR]" in result.stdout:
            raise RuntimeError(result.stdout.strip() or result.stderr.strip())
        return result.stdout.strip()
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def run_memory_hook(agent: str, session_id: str, task: dict, workspace: str, skip: bool = False):
    """complete_task 后调用的 memory 写入钩子，失败不阻断主流程"""
    if skip or not _is_enabled():
        task["memoryWriteStatus"] = "skipped"
        return

    try:
        score_detail = score_importance(task)
        memory_text = build_memory_text_template(task, score_detail)
        importance = score_detail["rule_score"]
        task_type = score_detail["type"]
        tags = ",".join(filter(None, [task_type, (task.get("name") or "")[:20]]))
        payload = {
            "agent": agent, "table": "tasks", "text": memory_text,
            "type": "task_result", "task_id": task.get("id", ""),
            "session_id": session_id, "importance": importance, "tags": tags,
        }
        write_result = write_task_memory(payload, workspace)
        task["memoryWriteStatus"] = "success"
        task["memoryImportance"] = importance
        task["memoryTextPreview"] = memory_text[:160]
        task["memoryLLMUsed"] = False
        _sd = score_detail.get("detail", {})
        bonus = [f"{k.replace('_w','')}+{v:.2f}" for k, v in _sd.items() if k.endswith("_w") and v > 0]
        task["memoryScoreReason"] = " | ".join([task_type, f"importance={importance:.2f}"] + bonus)
        print(f"[M] importance={importance} type={task_type}")
        if write_result:
            print(f"    {write_result}")
    except Exception as e:
        task["memoryWriteStatus"] = "pending"
        task["memoryWriteError"] = str(e)[:300]
        print(f"[WARNING] memory 写库失败（不影响任务完成）：{e}")
