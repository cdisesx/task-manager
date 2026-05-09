# 入门指南 — task-manager

---

## 前置要求

- Python 3.8+
- Node.js 16+（仅 Dashboard 需要）
- pip

---

## 安装

### 1. 获取代码

```bash
git clone <仓库地址>
cd task-manager
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

当前 `requirements.txt` 没有外部依赖（仅使用 Python 标准库），但保留以备后续扩展。

### 3. 创建配置文件

```bash
cp config/config.example.json config/config.json
```

编辑 `config/config.json`，填入实际环境值：

```json
{
  "base_dir": "Y:\\path\\to\\task-manager",
  "agents": [
    { "name": "代理A", "id": "agent-a", "workSpace": "Y:\\path\\to\\agent-a\\workspace" }
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

所有字段说明 → [configuration.md](configuration.md)

---

## 核心概念

### Session ID

每个任务组由一个唯一的 session ID 标识，格式为 `si-{YYYYMMDDHHMMSS}-{uuid[:8]}`。

- session ID 是 CLI 的必选参数（`--session-id`）
- 使用 `get-session-id` 命令生成
- 不同的 session 互不干扰，各自有独立的任务文件

### 任务文件

任务以 JSON 文件形式存储在代理的工作区中：

```
{workSpace}/tasks/tasks-{sessionId}.json
```

文件结构：

```json
{
  "userRequirement": "用户需求描述",
  "tasks": [
    {
      "id": "t1",
      "name": "任务名称",
      "description": "任务描述",
      "implementationGuide": "实现指引",
      "verificationCriteria": "验证标准",
      "status": "pending",
      "relatedFiles": [],
      "dependencies": [],
      "subtasks": [],
      "workLog": [],
      "createdAt": "2026-05-09T13:58:39",
      "updatedAt": "2026-05-09T13:58:39"
    }
  ],
  "ownerSession": "si-20260509135839-d1c6011f",
  "sessionHistory": [],
  "lastUpdatedAt": "2026-05-09T13:58:39"
}
```

### 任务状态生命周期

```
pending ──→ in_progress ──→ completed
  │                            │
  ├──→ blocked                 ├──→ archived（归档）
  │                            │
  └──→ cancelled               └──→ cancelled
```

- `pending` — 待执行，初始状态
- `in_progress` — 执行中（由 `execute-task` 设置）
- `completed` — 已完成（由 `complete-task` 设置）
- `blocked` — 已阻塞（由 `block-task` 设置，可 `unblock-task` 恢复为 `in_progress`）
- `cancelled` — 已取消（由 `cancel-task` 设置）

---

## CLI 命令详解

### 全局参数

```
python task-manager.py --agent <代理ID> [--session-id <SID>] [--config <配置文件路径>] <命令> [选项]
```

| 参数 | 说明 |
|------|------|
| `--agent` | **必填**。代理标识符，对应 config.json 中 agents[].id |
| `--session-id` | 大部分命令需要。任务组标识符。首次使用需通过 `get-session-id` 获取 |
| `--config` | 可选。覆盖配置文件路径，等价于设置 `TASK_MANAGER_CONFIG` 环境变量 |

### Session 管理

#### `get-session-id`

生成新的 session ID，不创建任何文件。

```
python task-manager.py --agent myagent get-session-id
# 输出：si-20260509135839-d1c6011f
```

#### `claim-task`

接管其他 session 的任务文件。当你因某种原因 session ID 变化但想继续操作已有的任务文件时使用。

```
python task-manager.py --agent myagent --session-id <新SID> \
  claim-task --target <目标SID>
```

### 任务规划

#### `plan-task`

设置当前 session 的需求描述。如果已有需求，会自动备份到 `sessionHistory`。

```
python task-manager.py --agent myagent --session-id <SID> \
  plan-task --description "实现用户注册功能，包括邮箱验证和密码加密"
```

| 选项 | 说明 |
|------|------|
| `--description` | **必填**。任务需求描述文本 |

#### `split-tasks`

将需求拆分为具体的子任务。支持四种模式：

```
python task-manager.py --agent myagent --session-id <SID> \
  split-tasks --mode overwrite \
  --tasks '[{"name":"任务","description":"描述","implementationGuide":"指引","verificationCriteria":"标准"}]'
```

| 选项 | 说明 |
|------|------|
| `--mode` | **必填**。`append`（追加）/ `overwrite`（覆盖）/ `selective`（选择性更新）/ `clearAllTasks`（清空所有任务） |
| `--tasks` | **必填**。JSON 数组，每个元素为一个任务对象 |

`--tasks` 中每个任务对象的字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 任务名称 |
| `description` | string | 是 | 任务描述 |
| `implementationGuide` | string | 否 | 实现指引 |
| `verificationCriteria` | string | 否 | 验证标准 |
| `relatedFiles` | string[] | 否 | 相关文件路径列表 |
| `dependencies` | string[] | 否 | 依赖的任务 name 列表（split-tasks 时会解析为对应的 task id） |
| `analysisResult` | string | 否 | 分析结果 |
| `notes` | string | 否 | 备注 |

#### `resplit-task`

将单个已存在的任务替换为多个子任务。

```
python task-manager.py --agent myagent --session-id <SID> \
  resplit-task --id t1 \
  --tasks '[{"name":"子任务1","description":"..."},{"name":"子任务2","description":"..."}]'
```

| 选项 | 说明 |
|------|------|
| `--id` | **必填**。要替换的任务 ID |
| `--tasks` | **必填**。JSON 数组，新子任务列表 |

### 任务执行

#### `execute-task`

标记任务为 `in_progress`。如果任务有未完成的依赖，会报错并拒绝执行。

```
python task-manager.py --agent myagent --session-id <SID> \
  execute-task --id t1
```

| 选项 | 说明 |
|------|------|
| `--id` | **必填**。任务 ID |

#### `complete-task`

标记任务为 `completed`。如果启用了向量记忆，会自动触发记忆写入。

```
python task-manager.py --agent myagent --session-id <SID> \
  complete-task --id t1 --summary "完成摘要"
```

| 选项 | 说明 |
|------|------|
| `--id` | **必填**。任务 ID |
| `--summary` | **必填**。完成摘要 |

#### `verify-task`

打印该任务的验证检查清单（从 prompt 模板生成）。

```
python task-manager.py --agent myagent --session-id <SID> \
  verify-task --id t1
```

| 选项 | 说明 |
|------|------|
| `--id` | **必填**。任务 ID |

#### `add-work-log`

为任务添加一条工作日志。

```
python task-manager.py --agent myagent --session-id <SID> \
  add-work-log --id t1 --content "完成了数据库表设计"
```

| 选项 | 说明 |
|------|------|
| `--id` | **必填**。任务 ID |
| `--content` | **必填**。日志内容 |

#### `update-task`

更新任务的字段（仅非 `completed` 状态的任务可修改）。

```
python task-manager.py --agent myagent --session-id <SID> \
  update-task --id t1 --field name --value "新任务名"
```

| 选项 | 说明 |
|------|------|
| `--id` | **必填**。任务 ID |
| `--field` | **必填**。要更新的字段名（name / description / implementationGuide / verificationCriteria 等） |
| `--value` | **必填**。新的值 |

#### `delete-task`

删除指定任务。如果其他任务依赖此任务，会报错并拒绝删除。

```
python task-manager.py --agent myagent --session-id <SID> \
  delete-task --id t1
```

| 选项 | 说明 |
|------|------|
| `--id` | **必填**。任务 ID |

### 阻塞 & 协作

#### `block-task`

阻塞任务，记录阻塞原因。任务状态变为 `blocked`。

```
python task-manager.py --agent myagent --session-id <SID> \
  block-task --id t1 --question "数据库连接字符串是什么？"
```

| 选项 | 说明 |
|------|------|
| `--id` | **必填**。任务 ID |
| `--question` | **必填**。阻塞原因或问题 |

#### `block-queue`

将任务加入阻塞队列（记录但阻塞状态不同）。

```
python task-manager.py --agent myagent --session-id <SID> \
  block-queue --id t1 --reason "等待审批"
```

#### `unblock-task`

解除阻塞，恢复任务为 `in_progress`，并记录答案。

```
python task-manager.py --agent myagent --session-id <SID> \
  unblock-task --id t1 --answer "连接字符串在配置文件中"
```

| 选项 | 说明 |
|------|------|
| `--id` | **必填**。任务 ID |
| `--answer` | **必填**。阻塞问题的答案 |

#### `add-subtask`

为任务添加子任务。

```
python task-manager.py --agent myagent --session-id <SID> \
  add-subtask --id t1 --name "子任务名" --description "描述"
```

| 选项 | 说明 |
|------|------|
| `--id` | **必填**。父任务 ID |
| `--name` | **必填**。子任务名称 |
| `--description` | **必填**。子任务描述 |

### Todo 工作流

Todo 是一个独立于 session 的待办系统。可以从 todo 生成任务文件。

#### `create-todo`

创建一条待办项。

```
python task-manager.py --agent myagent --session-id <SID> \
  create-todo --description "需要重构登录模块"
```

| 选项 | 说明 |
|------|------|
| `--description` | **必填**。待办描述 |

#### `plan-from-todo`

从指定待办生成任务文件。

```
python task-manager.py --agent myagent --session-id <SID> \
  plan-from-todo --todo-id <todo-id>
```

| 选项 | 说明 |
|------|------|
| `--todo-id` | **必填**。待办 ID |

#### `assign-task`

分配任务给指定代理。

```
python task-manager.py --agent myagent --session-id <SID> \
  assign-task --task-id t1 --target-agent other-agent
```

#### `list-todos`

列出当前代理的所有待办。

```
python task-manager.py --agent myagent --session-id <SID> list-todos
```

### 查询 & 管理

#### `list-tasks`

按状态分组列出当前 session 的所有任务。

```
python task-manager.py --agent myagent --session-id <SID> list-tasks
```

#### `get-task-detail`

显示任务的完整信息，包括日志、依赖、子任务等。

```
python task-manager.py --agent myagent --session-id <SID> \
  get-task-detail --id t1
```

#### `query-task`

在所有 session（含归档）中按关键词搜索任务。

```
python task-manager.py --agent myagent --session-id <SID> \
  query-task --keyword "数据库"
```

| 选项 | 说明 |
|------|------|
| `--keyword` | **必填**。搜索关键词 |

#### `cancel-task`

取消任务并记录取消原因。

```
python task-manager.py --agent myagent --session-id <SID> \
  cancel-task --id t1 --reason "需求变更"
```

#### `complete-session`

批量完成当前 session 中所有未完成的任务。

```
python task-manager.py --agent myagent --session-id <SID> complete-session
```

#### `archive`

归档 session：将所有任务文件备份到 `tasks/memory/` 目录，然后删除原任务文件。**需要 `--confirm` 确认**。

```
python task-manager.py --agent myagent --session-id <SID> archive --confirm
```

---

## Dashboard 看板

### 启动方式

**方式一：使用启动脚本（推荐）**

```bash
# Git Bash / Linux / macOS
./start.sh

# Windows
start.bat
```

启动脚本会自动执行 `pip install`、`npm install`（仅在首次或依赖变更时），然后启动 server。

**方式二：手动启动**

```bash
cd dashboard
npm install
node server.js
```

### 访问

```
http://localhost:3010
```

端口可在 `config.json` 的 `dashboard.port` 中配置。也可通过 `PORT` 环境变量覆盖。

### Dashboard API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/agents` | GET | 所有代理的任务数据、进度、活跃状态 |
| `/api/agents/:id` | GET | 单个代理的详细数据 |
| `/api/agents/:id/history` | GET | 单个代理的归档历史 |
| `/api/history` | GET | 所有代理的归档 + 当前任务分组（支持分页、按代理过滤） |
| `/api/unblock` | POST | 解除阻塞（绕过 Python CLI，直接写 JSON 文件） |
| `/api/services` | GET | 注册的服务列表 |
| `/api/services/status` | GET | 服务运行状态检查（通过 netstat / docker） |
| `/api/services/kill` | POST | 停止服务（taskkill 或 docker stop） |
| `/api/services/register` | POST | 注册新服务 |
| `/api/services/:name` | DELETE | 删除服务记录 |
| `/api/task-groups` | GET | 所有 session 任务组（含代理信息和活跃状态） |
| `/api/tasks/empty` | GET | 空任务文件列表 |
| `/api/tasks/empty` | DELETE | 删除所有空任务文件 |

---

## 完整工作流示例

```bash
# 1. 生成 session
sid=$(python task-manager.py --agent myagent get-session-id)
echo "Session: $sid"

# 2. 规划
python task-manager.py --agent myagent --session-id $sid \
  plan-task --description "为系统添加用户注册和登录功能"

# 3. 拆分子任务
python task-manager.py --agent myagent --session-id $sid \
  split-tasks --mode overwrite \
  --tasks '[
    {
      "name": "设计用户表",
      "description": "设计 users 表结构",
      "implementationGuide": "使用迁移脚本创建表",
      "verificationCriteria": "表中有 id, email, password_hash, created_at 字段"
    },
    {
      "name": "实现注册接口",
      "description": "POST /api/register",
      "dependencies": ["设计用户表"]
    },
    {
      "name": "实现登录接口",
      "description": "POST /api/login",
      "dependencies": ["设计用户表"]
    }
  ]'

# 4. 执行任务
python task-manager.py --agent myagent --session-id $sid \
  execute-task --id t1

# 5. 如果遇到问题，阻塞
python task-manager.py --agent myagent --session-id $sid \
  block-task --id t1 --question "密码加密用什么算法？"

# 6. 解除阻塞
python task-manager.py --agent myagent --session-id $sid \
  unblock-task --id t1 --answer "使用 bcrypt"

# 7. 完成任务
python task-manager.py --agent myagent --session-id $sid \
  complete-task --id t1 --summary "完成用户表设计，包含 id, email, password_hash(bcrypt), created_at 字段"

# 8. 重复 4-7 完成其他任务

# 9. 归档
python task-manager.py --agent myagent --session-id $sid archive --confirm
```

---

## 常见问题

| 问题 | 解决方式 |
|------|----------|
| `ModuleNotFoundError` | 运行 `pip install -r requirements.txt` |
| `config.json` 找不到 | 复制 `config/config.example.json` 为 `config/config.json` 并填写 |
| Session ID 丢失 | 使用 `claim-task` 重新关联到已有任务文件 |
| `list-tasks` 显示空 | 当前 session 没有任务；先用 `plan-task` + `split-tasks` 创建 |
| `execute-task` 报依赖未完成 | 先完成被依赖的任务，或 `update-task` 移除依赖 |
| Dashboard 无法访问 | 确认 `node server.js` 正在运行，端口未被占用 |
| 向量记忆不生效 | 检查 `config.json` 中 `vector_memory.enabled` 是否为 `true` |
| 归档命令报错 | 需要添加 `--confirm` 参数确认归档操作 |
| 输出中文乱码或 `UnicodeEncodeError` | 运行 `set PYTHONUTF8=1`（cmd）或 `$env:PYTHONUTF8=1`（PowerShell），然后重试。或使用 `python -X utf8 task-manager.py ...`。启动脚本已自动设置此变量 |
| 想知道当前编码设置 | 运行 `python task-manager.py --agent test encoding-info` 查看 |
