"""core/prompts/__init__.py - 提示词模板渲染"""
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def _load(template_name: str) -> str:
    p = _PROMPTS_DIR / f"{template_name}.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def render_prompt(template_name: str, **kwargs) -> str:
    """加载并渲染提示词模板，支持 {key} 占位符替换"""
    tpl = _load(template_name)
    for k, v in kwargs.items():
        tpl = tpl.replace("{" + k + "}", str(v) if v is not None else "")
    # 清理未替换的占位符
    import re
    tpl = re.sub(r"\{[a-z_]+_section\}", "", tpl)
    return tpl.strip()


def render_plan_task(req: str, tasks: list) -> str:
    completed = [t for t in tasks if t["status"] == "completed"]
    unfinished = [t for t in tasks if t["status"] != "completed"]
    section = ""
    if completed or unfinished:
        lines = ["### 现有任务参考", ""]
        if completed:
            lines.append("#### 已完成任务")
            for t in completed:
                lines.append(f"- [{t['id'][:8]}] {t['name']}")
        if unfinished:
            lines.append("\n#### 未完成任务")
            for t in unfinished:
                lines.append(f"- [{t['id'][:8]}] [{t['status']}] {t['name']}")
        lines += [
            "",
            "**任务保留原则：**",
            "1. 已完成任务不可修改或删除",
            "2. 未完成任务可根据需要修改",
            "3. 保持任务 ID 一致性",
        ]
        section = "\n".join(lines)
    return render_prompt("plan_task", req=req, existing_tasks_section=section)


def render_split_tasks(mode: str, created: list) -> str:
    lines = []
    for i, t in enumerate(created, 1):
        deps = t.get("dependencies", [])
        dep_str = f"依赖: {', '.join(d['taskId'][:8] for d in deps)}" if deps else "无依赖"
        lines.append(f"### 任务 {i}：{t['name']}")
        lines.append(f"**ID:** `{t['id']}`")
        lines.append(f"**描述:** {t['description'][:100]}")
        if t.get("implementationGuide"):
            lines.append(f"**实现指南:** {t['implementationGuide'][:100]}")
        if t.get("verificationCriteria"):
            lines.append(f"**验证标准:** {t['verificationCriteria'][:100]}")
        lines.append(f"**{dep_str}**")
        lines.append("")
    return render_prompt("split_tasks", mode=mode, task_list="\n".join(lines)) + "\n\n" + render_fields_guide()


def render_fields_guide() -> str:
    return render_prompt("task_fields_guide")


def render_execute_task(task: dict, id_map: dict) -> str:
    notes_section = f"**注意事项:** {task['notes']}\n" if task.get("notes") else ""
    guide_section = f"## 实现指南\n\n{task['implementationGuide']}\n" if task.get("implementationGuide") else ""
    criteria_section = f"## 验证标准\n\n{task['verificationCriteria']}\n" if task.get("verificationCriteria") else ""
    analysis_section = f"## 分析结果\n\n{task['analysisResult'][:500]}\n" if task.get("analysisResult") else ""

    deps = task.get("dependencies", [])
    deps_lines = []
    if deps:
        deps_lines.append("## 依赖任务摘要\n")
        for d in deps:
            dep_task = id_map.get(d["taskId"])
            if dep_task:
                summary = dep_task.get("summary", "（无摘要）")
                deps_lines.append(f"- [{dep_task['name']}]: {summary[:100]}")
    deps_section = "\n".join(deps_lines)

    desc_len = len(task.get("description", ""))
    dep_count = len(deps)
    if desc_len > 2000 or dep_count >= 10:
        complexity = "极高复杂度"
    elif desc_len > 1000 or dep_count >= 5:
        complexity = "高复杂度"
    elif desc_len > 500 or dep_count >= 2:
        complexity = "中等复杂度"
    else:
        complexity = "低复杂度"

    return render_prompt(
        "execute_task",
        name=task["name"], id=task["id"],
        description=task["description"],
        notes_section=notes_section,
        guide_section=guide_section,
        criteria_section=criteria_section,
        analysis_section=analysis_section,
        deps_section=deps_section,
        complexity=complexity,
        desc_len=desc_len,
        dep_count=dep_count,
    ) + "\n\n" + render_fields_guide()


def render_verify_task(task: dict, all_tasks: list) -> str:
    pending = [t for t in all_tasks if t["status"] == "pending"]
    in_progress = [t for t in all_tasks if t["status"] == "in_progress" and t["id"] != task["id"]]
    next_tasks = (pending[:3] + in_progress[:2])[:3]
    section = ""
    if next_tasks:
        lines = ["## 下一步任务建议", ""]
        for t in next_tasks:
            lines.append(f"- [{t['id'][:8]}] [{t['status']}] {t['name']}")
            if t.get("implementationGuide"):
                lines.append(f"  实现指南: {t['implementationGuide'][:80]}")
        section = "\n".join(lines)
    return render_prompt("verify_task", name=task["name"], id=task["id"], next_tasks_section=section)


def render_list_tasks(tasks: list, status_filter: str) -> str:
    status_map = {"pending": "待执行", "in_progress": "进行中", "completed": "已完成", "blocked": "已阻塞"}
    counts = {}
    for t in tasks:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    count_str = "  ".join(f"{status_map.get(s, s)}: {n}" for s, n in counts.items()) or "暂无任务"
    empty = "" if tasks else "目前系统中没有任何任务。\n请使用 `split_tasks` 工具创建任务结构，再进行后续操作。"
    return render_prompt("list_tasks", count_str=count_str, empty_section=empty)
