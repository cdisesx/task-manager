# AGENTS.md — 工作协议

## 变量说明

使用前请将以下变量替换为实际值：

| 变量 | 说明 | 示例 |
|------|------|------|
| `{TASK_MANAGER_SCRIPT}` | task-manager.py 绝对路径 | `C:\Users\.xxx\skills\task-manager\task-manager.py` |
| `{WORKSPACE_DIR}` | 当前 agent 的 workspace 目录 | `C:\Users\.xxx\workspace-myagent` |
| `{AGENT_NAME}` | 当前 agent 名称 | `myagent` |

---

## 一、Task Manager 强制规范（最高优先级）

**执行任何实质性任务前，必须先使用 Task Manager 创建任务计划、拆分子任务，无一例外。**

### 执行方式
所有 Task Manager 命令通过 Python 脚本执行（不是 MCP 或 HTTP 请求）：
```bash
python {TASK_MANAGER_SCRIPT} --agent {AGENT_NAME} <command> [args]
```

### 工作流（不可跳过）
```
get-session-id → plan-task → split-tasks → execute-task → complete-task
```

### 详细流程
1. **接到任务** → 立即回复"收到任务，开始通过TaskManager规划"，然后执行以下步骤
2. **获取 session ID**（整个对话只做一次）
   ```bash
   python {TASK_MANAGER_SCRIPT} --agent {AGENT_NAME} get-session-id
   # 保存输出的 session-id，后续所有命令复用
   ```
3. **创建任务计划**
   ```bash
   python {TASK_MANAGER_SCRIPT} --agent {AGENT_NAME} --session-id <sid> plan-task --description "需求描述"
   ```
4. **拆分子任务**
   ```bash
   python {TASK_MANAGER_SCRIPT} --agent {AGENT_NAME} --session-id <sid> split-tasks --mode overwrite --tasks '[...]'
   ```
5. **逐一执行子任务**（每完成一个立即更新状态）
   ```bash
   python {TASK_MANAGER_SCRIPT} --agent {AGENT_NAME} --session-id <sid> execute-task --id <task-id>
   # ... 实际工作 ...
   python {TASK_MANAGER_SCRIPT} --agent {AGENT_NAME} --session-id <sid> complete-task --id <task-id> --summary "完成摘要"
   ```
6. **所有任务完成后** → 执行 `complete-session`，上报等待授权归档
   ```bash
   python {TASK_MANAGER_SCRIPT} --agent {AGENT_NAME} --session-id <sid> complete-session
   ```

### 规则
- ❌ 禁止在无 Task Manager 记录的情况下默默干活
- ❌ 禁止代理自行执行 `archive` 命令（必须等待授权）
- ✅ 每个子任务完成后立即更新状态
- ✅ 输出必须包含：任务 ID、结果、证据/文件路径、阻塞项（如有）

## 二、代理中断恢复规范（最高优先级）

**当代理因 token 超长或其它异常中断，或必须接手某个开发一般的task任务时，必须按以下流程恢复，不得重新派发全新任务！**

### 恢复流程
1. 检查该代理 workspace 下是否有 `tasks-si-*.json` 文件：
   ```bash
   ls {WORKSPACE_DIR}/tasks/tasks-si-*.json 2>/dev/null
   ```
2. 如果有 → 新起一个 session，认领并继续：
   ```bash
   # 1. 生成新 session ID
   python {TASK_MANAGER_SCRIPT} --agent {AGENT_NAME} get-session-id

   # 2. 认领旧任务文件，将 ownerSession 更新为新 session
   python {TASK_MANAGER_SCRIPT} --agent {AGENT_NAME} claim-task \
     --file tasks-si-xxx.json \
     --new-session-id <new_sid>

   # 3. 查看现有任务，排查完成情况
   python {TASK_MANAGER_SCRIPT} --agent {AGENT_NAME} --session-id <new_sid> list-tasks
   ```
3. 认领完成后：
   - 查看标记为 `in_progress`（doing）的任务 → 检查实际完成情况，补完未完成部分
   - 查看标记为 `pending` 的任务 → 继续执行
   - 完成后更新状态 → 最终 `complete-session`

### 规则
- ❌ 绝对禁止：中断后直接重新派发全新任务（会导致重复工作、task 文件冲突）
- ✅ 正确做法：先检查 `tasks-si-*.json`，有则 claim 继续，无则重新派发

---

## 三、协作规范

1. 遇到阻塞或需要协作时，明确标注阻塞原因并上报
2. 涉及删除/外发动作必须明确标注并等待批准
3. 所有输出必须包含：任务 ID、结果、证据/文件路径、阻塞项（如有）
