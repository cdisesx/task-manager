# task-manager

面向 AI 编码代理的模块化任务管理 CLI。提供 session 级任务隔离、提示驱动的工作流、可选的向量记忆集成，以及 Node.js 实时看板 Dashboard。

---

## 亮点

- **模块化架构** — `core/`（核心 CRUD）、`skills/`（扩展技能）、`utils/`（工具函数）
- **Session 隔离** — 每个任务组由唯一 `si-{timestamp}-{hash}` ID 标识，互不干扰
- **提示驱动工作流** — `plan` → `split` → `execute` → `complete`，全程由 prompt 模板引导 AI 行为
- **Todo 委派机制** — `create-todo` / `plan-from-todo` / `assign-task` / `list-todos` 完整待办工作流
- **任务阻塞与协作** — 遇到问题时阻塞任务并提问，其他角色可解除阻塞
- **向量记忆集成（可选）** — 完成任务时自动写入向量库，支持跨 session 上下文检索
- **Dashboard 看板** — Node.js HTTP 服务，实时查看所有代理的任务进度、历史记录、服务状态

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 复制配置
cp config/config.example.json config/config.json

# 3. 编辑 config/config.json，设置 base_dir 和 agents

# 4. 生成 session ID
python task-manager.py --agent myagent get-session-id
# → si-20260509135839-d1c6011f

# 5. 规划任务
python task-manager.py --agent myagent --session-id <sid> plan-task --description "..."

# 6. 拆分子任务
python task-manager.py --agent myagent --session-id <sid> \
  split-tasks --mode overwrite \
  --tasks '[{"name":"任务1","description":"描述"}]'

# 7. 执行并完成
python task-manager.py --agent myagent --session-id <sid> execute-task --id <task-id>
python task-manager.py --agent myagent --session-id <sid> complete-task --id <task-id> --summary "完成摘要"

# 8. 启动看板
./start.sh          # Git Bash / Linux / macOS
start.bat           # Windows
```

详细指引 → [getting-started.md](getting-started.md)

---

## 项目结构

```
task-manager/
├── task-manager.py         # CLI 入口：argparse 分发所有 24+ 个命令
├── requirements.txt        # Python 依赖（当前仅使用标准库）
├── start.bat               # Windows 启动脚本
├── start.sh                # Unix/Git Bash 启动脚本
├── config/
│   ├── config.example.json # 配置模板
│   └── config.json         # 实际配置（已 gitignore）
├── core/
│   ├── task_crud.py        # 核心 CRUD：plan / split / execute / complete / query / archive 等
│   ├── memory_hook.py      # 向量记忆写入钩子
│   └── prompts/            # AI 提示模板（plan / split / execute / verify / list）
├── skills/
│   ├── block.py            # block-task / block-queue / unblock-task
│   ├── subtask.py          # add-subtask / resplit-task
│   ├── worklog.py          # add-work-log / cancel-task
│   ├── todo.py             # create-todo / plan-from-todo / assign-task / list-todos
│   ├── plan.py             # plan-task 薄封装
│   ├── split.py            # split-tasks 薄封装
│   ├── execute.py          # execute-task 薄封装
│   ├── complete.py         # complete-task 薄封装
│   └── archive.py          # archive / clear-tasks 薄封装
├── utils/
│   ├── paths.py            # 配置加载、路径解析、session ID 生成
│   ├── data_io.py          # 任务文件读写（JSON）
│   └── time_utils.py       # 时间格式化工具
├── dashboard/              # Node.js HTTP 看板
│   ├── server.js           # HTTP 服务器（纯 Node，无框架）
│   ├── api/                # 代理配置 & 任务数据 API
│   └── public/             # 前端静态文件（index.html + detail.html）
├── tests/                  # pytest 测试套件
└── docs/                   # 文档
```

---

## 命令参考

### Session 管理

| 命令 | 描述 |
|------|------|
| `get-session-id` | 生成新的 session ID |
| `claim-task` | 接管其他 session 的任务文件 |

### 任务规划

| 命令 | 描述 |
|------|------|
| `plan-task` | 设定当前 session 的需求描述 |
| `split-tasks` | 拆分子任务（支持 append / overwrite / selective / clearAllTasks 四种模式） |
| `resplit-task` | 将单个任务替换为多个子任务 |

### 任务执行

| 命令 | 描述 |
|------|------|
| `execute-task` | 标记任务为 in_progress，检查依赖是否全部 resolved |
| `complete-task` | 标记任务为 completed，触发向量记忆写入 |
| `verify-task` | 打印该任务的验证检查清单 |
| `add-work-log` | 为任务添加一条工作日志 |
| `update-task` | 更新任务字段（仅非 completed 状态可修改） |
| `delete-task` | 删除任务（会检查是否有其他任务依赖它） |

### 阻塞 & 协作

| 命令 | 描述 |
|------|------|
| `block-task` | 阻塞任务并附带阻塞原因 |
| `block-queue` | 将任务加入阻塞队列 |
| `unblock-task` | 解除阻塞并记录答案 |
| `add-subtask` | 为任务添加子任务 |

### Todo 工作流

| 命令 | 描述 |
|------|------|
| `create-todo` | 创建待办项 |
| `plan-from-todo` | 从待办项生成任务文件 |
| `assign-task` | 分配任务给指定代理 |
| `list-todos` | 列出所有待办 |

### 查询 & 管理

| 命令 | 描述 |
|------|------|
| `list-tasks` | 按状态分组列出当前 session 的所有任务 |
| `get-task-detail` | 显示任务详细信息（含日志、依赖、子任务） |
| `query-task` | 跨所有 session 和归档搜索任务（按关键词） |
| `cancel-task` | 取消任务并记录原因 |
| `complete-session` | 批量完成当前 session 所有剩余任务 |
| `archive` | 归档当前 session 并删除任务文件（需 --confirm） |

---

## 工作流

```
┌──────────────┐   ┌──────────┐   ┌────────────┐   ┌─────────────┐   ┌──────────────┐
│ get-session  │ → │  plan    │ → │   split    │ → │   execute   │ → │   complete   │
│    -id       │   │  -task   │   │  -tasks    │   │   -task     │   │   -task      │
└──────────────┘   └──────────┘   └────────────┘   └─────────────┘   └──────┬───────┘
                                                                           │
                                                                    ┌──────▼───────┐
                                                                    │   archive    │
                                                                    │  (可选归档)   │
                                                                    └──────────────┘

执行阶段可选分支：
execute-task ──┬── block-task → unblock-task → 继续执行
               ├── add-subtask / resplit-task → 继续执行
               ├── add-work-log → 继续执行
               └── cancel-task → 结束

规划阶段可选分支：
split-tasks ──→ create-todo ──→ plan-from-todo ──→ assign-task ──→ 生成 tasks 文件
```

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [getting-started.md](getting-started.md) | 安装、配置、完整工作流、全部 CLI 命令说明、Dashboard 启动 |
| [configuration.md](configuration.md) | config.json 所有字段详解 |
| [vector-memory-integration.md](vector-memory-integration.md) | 可选向量记忆扩展的安装与配置 |
