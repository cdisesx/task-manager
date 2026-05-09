# task-manager Skill

**脚本路径：** `task-manager.py`（相对于 SKILL.md 所在目录）
**格式：** `python task-manager.py --agent <name> [--session-id <sid>] [--config <path>] <command> [options]`

## 核心概念

- **session-id**：一次对话生成一次，格式 `si-20260415135839-d1c6011f`，后续所有命令复用
- **`get-session-id`** → 获取 session-id，整个对话只调一次
- **`--config`**：可选参数，指定 config.json 路径，默认读取 `config/config.json`

---

## 命令速查

### 任务规划
| 命令 | 用途 | 关键参数 |
|------|------|----------|
| `get-session-id` | 生成 session ID | 无 |
| `plan-task` | 设置用户需求 | `--description "需求"` |
| `split-tasks` | 批量创建/更新任务 | `--mode overwrite\|append\|selective\|clearAllTasks --tasks '[...]'` |
| `create-todo` | 创建待办 | `--description "需求" [--creator "名称"]` |
| `plan-from-todo` | 从待办生成任务计划 | `--todo-session-id <sid>` |
| `list-todos` | 列出待办 | `[--status all\|pending\|planned\|assigned]` |
| `assign-task` | 指派任务给其他 agent | `--todo-session-id <sid> --target-agent <name> --target-session-id <sid>` |

### 任务执行
| 命令 | 用途 | 关键参数 |
|------|------|----------|
| `list-tasks` | 列出任务 | `[--status all\|pending\|in_progress\|completed\|blocked]` |
| `get-task-detail` | 获取任务详情 | `--id <task-id>` |
| `execute-task` | 开始执行任务 | `--id <task-id>` |
| `verify-task` | 验证任务完成 | `--id <task-id> --summary "摘要" [--work-log '...']` |
| `complete-task` | 标记任务完成 | `--id <task-id> --summary "摘要" [--work-log '...'] [--skip-memory]` |
| `update-task` | 更新任务字段 | `--id <task-id> [--name] [--description] [--notes] [--implementation-guide] [--verification-criteria] [--analysis] [--related-files '["a","b"]']` |
| `add-work-log` | 追加工作记录 | `--id <task-id> --type code_change\|answer\|thought\|action\|other --content "描述" [--files '[...]'] [--line-range "23-45"]` |

### 任务拆分
| 命令 | 用途 | 关键参数 |
|------|------|----------|
| `resplit-task` | 二次拆分未完成任务 | `--id <task-id> --tasks '[...]'` |
| `add-subtask` | 添加子任务 | `--parent-id <task-id> --name "名称" --desc "描述"` |

### 阻塞/取消
| 命令 | 用途 | 关键参数 |
|------|------|----------|
| `block-task` | 提问阻塞 | `--id <task-id> --reason "原因" --question "问题"` |
| `block-queue` | 排队阻塞 | `--id <task-id> --reason "原因" --waiting-for "等待内容"` |
| `unblock-task` | 解除阻塞 | `--id <task-id> --answer "回答"` |
| `cancel-task` | 取消任务 | `--id <task-id> --reason "原因"` |
| `delete-task` | 删除任务 | `--id <task-id>` |

### 查询/管理
| 命令 | 用途 | 关键参数 |
|------|------|----------|
| `query-task` | 搜索任务 | `--keyword "关键词" [--page 1] [--page-size 10]` |
| `claim-task` | 认领孤儿任务（agent 重启恢复用） | `--file tasks-old-xxx.json --new-session-id <sid>` |
| `complete-session` | 批量完成当前 session 所有未完成任务 | 无 |
| `archive` | 归档并清空（需上级授权） | `--confirm` |

## split-tasks 的 --tasks JSON 格式

`--tasks` 必须是一个 **JSON 对象数组**，每个对象代表一个子任务，字段说明如下：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `name` | ✅ | string | 子任务名称 |
| `description` | ✅ | string | 详细描述 |
| `implementationGuide` | ✅ | string | 实现步骤、参考文件、技术要点 |
| `verificationCriteria` | ✅ | string | 验收标准 |
| `relatedFiles` | 完成时推荐 | string[] | 涉及的文件路径列表 |
| `dependencies` | 可选 | string[] | 依赖的其他任务名称列表 |
| `analysisResult` | 推荐 | string | 调研结论、关键决策 |
| `notes` | 推荐 | string | 踩坑记录、边界条件 |

### 正确示例

```bash
# ✅ 完整格式
python task-manager.py --agent myagent --session-id $SID split-tasks \
  --mode overwrite \
  --tasks '[
    {
      "name": "实现用户登录接口",
      "description": "POST /api/login 返回 JWT token",
      "implementationGuide": "使用 pyjwt，RS256 算法",
      "verificationCriteria": "登录成功返回 token，失败返回 401",
      "relatedFiles": ["app.py", "auth.py"],
      "dependencies": []
    },
    {
      "name": "实现用户注册接口",
      "description": "POST /api/register 创建用户",
      "implementationGuide": "密码使用 bcrypt 加密",
      "verificationCriteria": "注册成功返回 201，重复用户名返回 409",
      "relatedFiles": ["app.py", "user.py"],
      "dependencies": ["实现用户登录接口"]
    }
  ]'

# ✅ 最少必需字段
python task-manager.py --agent myagent --session-id $SID split-tasks \
  --mode append \
  --tasks '[
    {"name": "任务名", "description": "描述", "implementationGuide": "指南", "verificationCriteria": "标准"}
  ]'
```

### 错误示例

```bash
# ❌ --tasks 不能传字符串列表
split-tasks --mode overwrite --tasks '["123"]'
# 报错：第 1 项不是任务对象（应为 {...}，实际收到 str）

# ❌ --tasks 不能传单个对象（必须用 [] 包裹）
split-tasks --mode overwrite --tasks '{"name": "123"}'
# 报错：--tasks 必须是一个 JSON 数组 []

# ❌ --tasks 不能传非 JSON 字符串
split-tasks --mode overwrite --tasks '不是JSON'
# 报错：JSON 解析失败

# ❌ 任务对象不能缺少 name 字段
split-tasks --mode overwrite --tasks '[{"description": "xxx"}]'
# 报错：第 1 项缺少 name 字段
```

## 完整工作流

```bash
# 1. 获取 session ID（仅一次）
SID=$(python task-manager.py --agent myagent get-session-id)

# 2. 规划
python task-manager.py --agent myagent --session-id $SID plan-task --description "需求"

# 3. 拆分子任务
python task-manager.py --agent myagent --session-id $SID split-tasks \
  --mode overwrite \
  --tasks '[
    {"name": "任务A", "description": "描述A", "implementationGuide": "指南A", "verificationCriteria": "标准A"},
    {"name": "任务B", "description": "描述B", "implementationGuide": "指南B", "verificationCriteria": "标准B"}
  ]'

# 4. 执行 → 完成（循环每个子任务）
python task-manager.py --agent myagent --session-id $SID execute-task --id <id>
# ... 实际工作 ...
python task-manager.py --agent myagent --session-id $SID complete-task --id <id> --summary "摘要"

# 5. 归档（所有任务完成后，需授权）
python task-manager.py --agent myagent --session-id $SID archive --confirm
```
