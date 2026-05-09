# 配置说明 — task-manager

所有运行时配置位于 `config/config.json`。首次使用请复制模板：

```bash
cp config/config.example.json config/config.json
# Windows PowerShell
# Copy-Item config/config.example.json config/config.json
```

`config.json` 已被 `.gitignore` 忽略，不会提交到版本库。

---

## 完整示例

```json
{
  "base_dir": "Y:\\wpAI\\skills\\task-manager",
  "agents": [
    {
      "name": "代理名称",
      "id": "agent-id",
      "workSpace": "Y:\\path\\to\\agent\\workspace"
    }
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

## 字段说明

### 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `base_dir` | string | 是 | 项目根目录。仅当 agents 未配置 workSpace 时，作为 workspace 路径的基础目录 |
| `agents` | object[] | 是 | 代理列表。每个代理为一个对象（详见下方） |

### agents[]

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 代理显示名称（看板上显示的名称） |
| `id` | string | 是 | 代理标识符（CLI 中 `--agent` 参数使用的值） |
| `workSpace` | string | 否 | 该代理的任务文件存放目录。若未设置，则回退为 `{base_dir}/workspace/{agent.id}` |

示例：

```json
{
  "agents": [
    { "name": "林殊", "id": "linshu", "workSpace": "Y:\\projects\\workspace\\linshu" },
    { "name": "飞流", "id": "feiliu", "workSpace": "Y:\\projects\\workspace\\feiliu" }
  ]
}
```

### dashboard

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `port` | number | `3010` | Dashboard HTTP 服务端口 |

### vector_memory

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | boolean | `false` | 是否启用向量记忆集成。false 时所有记忆钩子静默跳过 |
| `service_url` | string | `http://localhost:3019` | 向量记忆嵌入服务地址 |
| `skill_path` | string | `""` | 向量记忆扩展的路径（绝对或相对路径） |

---

## 配置优先级

1. **环境变量 `TASK_MANAGER_CONFIG`** — 若设置了此环境变量，CLI 会优先读取其指向的配置文件
2. **默认路径** — `config/config.json`
3. **回退** — `config/config.example.json`（仅提供默认值，不保证完整）

---

## 数据路径

### 任务文件

```
{agent.workSpace}/tasks/tasks-{sessionId}.json
```

若未配置 `workSpace`，则回退为：

```
{base_dir}/workspace/{agentId}/tasks/tasks-{sessionId}.json
```

### 任务文件结构

```json
{
  "userRequirement": "用户需求描述",
  "tasks": [],
  "ownerSession": "si-20260509135839-d1c6011f",
  "sessionHistory": [],
  "lastUpdatedAt": "2026-05-09T13:58:39"
}
```

### 归档路径

```
{agent.workSpace}/tasks/memory/
```

完成归档后的任务文件会被移至此目录，文件名保持不变（`tasks-si-{timestamp}-{hash}.json`）。

### Todo 文件

```
{agent.workSpace}/tasks/todo-{sessionId}.json
```

### 日志路径

```
logs/task-manager.log
```

日志由 `task-manager.py` 自动创建，使用标准 logging 模块输出到 `logs/task_manager.log`，同时输出到 stderr。

---

## 环境变量覆盖

| 环境变量 | 作用 |
|----------|------|
| `TASK_MANAGER_CONFIG` | 覆盖 config.json 的路径。设置为绝对路径，指向另一个配置文件 |
| `PORT` | 覆盖 Dashboard 端口（优先级高于 config.json 中的 `dashboard.port`） |
