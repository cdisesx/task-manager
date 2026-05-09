## 任务拆分 - {mode} 模式

**拆分原则：**
1. 垂直切分法 - 按可测试的子功能，确保独立可验证
2. 按架构层次分解 - 基础架构层分离，确保接口明确
3. 按开发阶段分解 - 遵循开发流程，优化功能和测试
4. 按前后分解 - 前后端分离，保持接口同步

**字段指南：** 每个任务应尽可能完善以下字段以提升向量记忆质量：
- `implementationGuide` — 实现指引（缺失时会收到 WARNING）
- `verificationCriteria` — 验证标准（缺失时会收到 WARNING）
- `relatedFiles` — 关联文件列表
- `notes` — 备注、约束条件
- `analysisResult` — 分析结果、架构决策
详细说明请参考 `task_fields_guide`。

**任务列表：**

{task_list}

**依赖关系说明：**
- 任务间依赖使用任务名称或 ID
- 小任务只能依赖直接前置任务
- 避免循环依赖，确保依赖图无环

**下一步（两种流程可选）：**

**方式一：直接执行（当前 session 自己干）**
使用 `list-tasks` 查看完整任务列表，然后使用 `execute-task --id <taskId>` 逐个执行。

**方式二：Todos 流程（创建待办 → 生成计划 → 指派给其他 agent）**
1. `create-todo --description "需求描述"` — 快速记录一条待办需求
2. `list-todos` — 查看当前所有 todo 及其状态
3. `plan-from-todo --todo-session-id <sid>` — 从 todo 生成任务计划文件（状态为 unassigned）
4. `assign-task --todo-session-id <sid> --target-agent <agent> --target-session-id <sid>` — 将任务指派给目标 agent 执行

💡 Todos 流程适合跨 agent 协作场景：由上级创建 todo，生成计划后指派给下级 agent 认领执行。
