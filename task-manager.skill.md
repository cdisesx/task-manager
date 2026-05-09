---
parameters:
  agent: myagent
  task_manager_path: Y:\wpAI\skills\task-manager
---

# task-manager Skill

任务管理器 CLI，支持 session 级任务隔离、Todo 工作流、任务阻塞/协作、Dashboard 看板和可选的向量记忆集成。

**安装路径：** `{{task_manager_path}}`
**入口：** `python {{task_manager_path}}\task-manager.py`
**配置：** `{{task_manager_path}}\config\config.json`
**默认代理：** `--agent {{agent}}`

> 使用前请将上方 `parameters` 中的 `agent` 值改为你在 config.json 中配置的代理 ID（如 `linshu`、`feiliu` 等）。

---

## 基本用法

```bash
python {{task_manager_path}}\task-manager.py --agent {{agent}} [--session-id <SID>] <命令> [选项]
```

| 参数 | 说明 |
|------|------|
| `--agent` | 代理标识符，对应 config.json 中 agents[].id。当前默认值：`{{agent}}` |
| `--session-id` | 大部分命令需要。任务组标识符，格式 `si-{timestamp}-{hash}`。首次使用通过 `get-session-id` 获取 |
| `--config` | 可选。配置路径，默认 `{{task_manager_path}}\config\config.json` |

> **编码说明：** 如果终端输出中文乱码，先执行 `set PYTHONUTF8=1`（cmd）或 `$env:PYTHONUTF8=1`（PowerShell）。

---

## 命令速查

### Session 管理

| 命令 | 用途 | 示例 |
|------|------|------|
| `get-session-id` | 生成 session ID | `python {{task_manager_path}}\task-manager.py --agent {{agent}} get-session-id` |
| `claim-task` | 接管其他 session 的任务文件 | `... claim-task --file tasks-si-xxx.json --new-session-id <SID>` |

### 任务规划

| 命令 | 用途 | 关键参数 |
|------|------|----------|
| `plan-task` | 设置需求描述 | `--description "需求"` |
| `split-tasks` | 拆分子任务 | `--mode overwrite\|append\|selective\|clearAllTasks --tasks '[...]'` |
| `resplit-task` | 二次拆分 | `--id <task-id> --tasks '[...]'` |
| `add-subtask` | 添加子任务 | `--parent-id <task-id> --name "名称" --desc "描述" [--guide] [--criteria] [--notes]` |

### 任务执行

| 命令 | 用途 | 关键参数 |
|------|------|----------|
| `list-tasks` | 列出任务 | `[--status all\|pending\|in_progress\|completed\|blocked]` |
| `get-task-detail` | 任务详情 | `--id <task-id>` |
| `execute-task` | 开始执行 | `--id <task-id>` |
| `complete-task` | 标记完成 | `--id <task-id> --summary "摘要" [--work-log '{"type":"code_change","content":"..."}'] [--skip-memory]` |
| `verify-task` | 验证任务 | `--id <task-id> [--summary] [--work-log '...']` |
| `update-task` | 更新字段 | `--id <task-id> [--name] [--description] [--notes] [--implementation-guide] [--verification-criteria] [--analysis] [--related-files '["a","b"]']` |
| `add-work-log` | 追加工作记录 | `--id <task-id> --type code_change\|answer\|thought\|action\|other --content "描述" [--files '[...]'] [--line-range "23-45"]` |
| `delete-task` | 删除任务 | `--id <task-id>` |

### 阻塞 / 取消

| 命令 | 用途 | 关键参数 |
|------|------|----------|
| `block-task` | 阻塞并提问 | `--id <task-id> --reason "原因" --question "问题"` |
| `block-queue` | 加入阻塞队列 | `--id <task-id> --reason "原因" --waiting-for "等待内容"` |
| `unblock-task` | 解除阻塞 | `--id <task-id> --answer "答案"` |
| `cancel-task` | 取消任务 | `--id <task-id> --reason "原因"` |

### Todo 工作流

| 命令 | 用途 | 关键参数 |
|------|------|----------|
| `create-todo` | 创建待办 | `--description "需求" [--creator "名称"]` |
| `plan-from-todo` | 从待办生成任务文件 | `--todo-session-id <sid>` |
| `assign-task` | 指派给其他 agent | `--todo-session-id <sid> --target-agent <name> --target-session-id <sid>` |
| `list-todos` | 列出待办 | `[--status all\|pending\|planned\|assigned]` |

### 查询 / 管理

| 命令 | 用途 | 关键参数 |
|------|------|----------|
| `query-task` | 跨 session 搜索任务 | `--keyword "关键词" [--page 1] [--page-size 10]` |
| `complete-session` | 批量完成所有任务 | 无 |
| `archive` | 归档并清空 | `--confirm` |
| `encoding-info` | 查看编码信息 | `[--verbose]` |

---

## split-tasks 的 --tasks JSON 格式

```bash
python {{task_manager_path}}\task-manager.py --agent {{agent}} --session-id $SID split-tasks \
  --mode overwrite \
  --tasks '[
    {
      "name": "实现登录接口",
      "description": "POST /api/login 返回 JWT token",
      "implementationGuide": "使用 pyjwt，RS256 算法",
      "verificationCriteria": "登录成功返回 token，失败返回 401",
      "relatedFiles": ["app.py", "auth.py"],
      "dependencies": []
    }
  ]'
```

### --tasks 字段说明

| 字段 | 类型 | 必填 | 说明 | 记忆影响 |
|------|------|------|------|---------|
| `name` | string | 是 | 任务名称 | 检索标签 |
| `description` | string | 是 | 任务描述 | 记忆中的问题/目标 |
| `implementationGuide` | string | 推荐 | 实现指引 | 记忆中的方案要点 |
| `verificationCriteria` | string | 推荐 | 验收标准 | 影响记忆重要性评分 |
| `relatedFiles` | string[] | 推荐 | 涉及的文件路径 | 影响记忆重要性评分（文件数权重） |
| `dependencies` | string[] | 否 | 依赖的其他任务 name | 仅用于执行顺序控制 |
| `analysisResult` | string | 推荐 | 调研结论、关键决策 | 影响记忆重要性评分（最多 +0.18） |
| `notes` | string | 推荐 | 踩坑记录、边界条件 | 影响记忆重要性评分（踩坑/复用权重） |

### 错误示例

```
# ❌ 不能传字符串列表
split-tasks --mode overwrite --tasks '["123"]'

# ❌ 不能传单个对象（必须用 [] 包裹）
split-tasks --mode overwrite --tasks '{"name": "123"}'

# ❌ 每个对象必须包含 name 字段
split-tasks --mode overwrite --tasks '[{"description": "xxx"}]'
```

---

## 完整工作流

```bash
# 0. 设置别名（可选）
TASK="python {{task_manager_path}}\task-manager.py --agent {{agent}}"

# 1. 生成 session ID（仅一次）
SID=$($TASK get-session-id)

# 2. 规划
$TASK --session-id $SID plan-task --description "实现用户注册和登录功能"

# 3. 拆分子任务
$TASK --session-id $SID split-tasks --mode overwrite --tasks '[
  {"name":"设计用户表","description":"设计 users 表结构","implementationGuide":"使用迁移脚本","verificationCriteria":"表包含 id,email,password_hash"},
  {"name":"注册接口","description":"POST /api/register","dependencies":["设计用户表"]}
]'

# 4. 执行 → 完成（循环）
$TASK --session-id $SID execute-task --id <task-id>
$TASK --session-id $SID complete-task --id <task-id> --summary "完成"

# 5. 如需阻塞/解阻塞
$TASK --session-id $SID block-task --id <task-id> --reason "需确认" --question "加密算法？"
$TASK --session-id $SID unblock-task --id <task-id> --answer "bcrypt"

# 6. 归档
$TASK --session-id $SID archive --confirm
```

## 任务状态生命周期

```
pending ──→ in_progress ──→ completed
  │                            │
  ├──→ blocked                 ├──→ archived
  │                            │
  └──→ cancelled               └──→ cancelled
```

---

## Dashboard 看板

```bash
# 启动
start {{task_manager_path}}\start.bat
```

启动后访问 `http://localhost:3010`（端口可在 config.json 的 `dashboard.port` 中配置）。

---

## 编码诊断

如果遇到中文乱码，先查看编码状态：

```bash
python {{task_manager_path}}\task-manager.py --agent {{agent}} encoding-info
```

---

## 配置文件

`{{task_manager_path}}\config\config.json` 示例：

```json
{
  "base_dir": "Y:\\wpAI\\skills\\task-manager",
  "agents": [
    { "name": "agent名称", "id": "{{agent}}", "workSpace": "Y:\\path\\to\\workspace" }
  ],
  "dashboard": {
    "port": 3010
  },
  "vector_memory": {
    "enabled": false,
    "service_url": "http://localhost:3019",
    "skill_path": ""
  }
}
```

---

## 参数说明

文件顶部 `parameters` 块中的变量可自定义：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `agent` | `myagent` | 代理 ID，对应 config.json 中 agents[].id |
| `task_manager_path` | `Y:\wpAI\skills\task-manager` | task-manager 安装目录的绝对路径 |
