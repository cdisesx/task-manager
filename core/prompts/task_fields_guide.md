## 任务字段参考指南

每个任务是一个 JSON 对象，包含以下字段。填写越完善，向量记忆的检索质量和重要性评分越高。

### 字段一览

| 字段 | 类型 | 用途 | 记忆影响 | 填写建议 |
|------|------|------|---------|---------|
| `name` | string | 任务标题 | 作为**检索标签**和记忆主题 | 简洁明确，概括任务核心（10-30 字） |
| `description` | string | 任务描述 | 作为记忆中**要解决的问题/目标** | 详细描述任务背景、上下文和具体内容 |
| `implementationGuide` | string | 实现指引 | 作为记忆中的**方案要点** | 记录关键实现路径、技术选型、核心逻辑 |
| `verificationCriteria` | string | 验证标准 | 影响重要性评分（`verify_w`），作为记忆中的**验证证据** | 明确可验证的验收条件，越具体越好 |
| `relatedFiles` | string[] | 关联文件列表 | 影响重要性评分（`files_w`，最多 +0.14），作为记忆中的**关联文件** | 列出所有修改或涉及的文件路径，>=4 个文件可提升评分 |
| `analysisResult` | string | 分析结果 | 影响重要性评分（`analysis_w`，最多 +0.18），作为记忆中的**分析发现** | 记录遇到的坑、架构决策、设计思路、优化方案（>50 字 + 含关键词加分） |
| `notes` | string | 备注 | 影响重要性评分（`pitfall_w`/`fallback_w`/`reuse_w`） | 记录约束条件、注意事项、可复用经验 |
| `workLog` | array | 工作日志 | 踩坑关键词（"bug""报错""异常""冲突"等）识别触发 `pitfall_w`（+0.12） | 记录实施过程中的问题和解决方案 |

### 对记忆的重要性评分影响

向量记忆系统在写入时，会根据以下维度为任务打分（0.20 ~ 0.95），**高分任务在检索时优先返回**：

| 维度 | 触发条件 | 最高加分 |
|------|---------|---------|
| 基础分 | 所有任务 | 0.35 |
| 任务类型 | 类型自动推断（architecture/integration/bugfix 等） | +0.28 |
| 踩坑记录 | `summary`/`notes`/`workLog` 含"踩坑""报错""异常""冲突"等关键词 | +0.12 |
| 降级方案 | `summary`/`notes`/`workLog` 含"降级""fallback""retry"等关键词 | +0.08 |
| 文件数量 | `relatedFiles` 数量 2~7+ 个 | +0.14 |
| 验证标准 | `verificationCriteria` 非空且摘要含"测试通过""验证通过"等 | +0.15 |
| 复用价值 | `summary`/`notes` 含"模板""标准""通用""复用"等 | +0.18 |
| 分析深度 | `analysisResult` >50 字且含"架构""方案""设计"等 | +0.18 |

### 填写示例

```json
{
  "name": "实现用户注册接口",
  "description": "开发 POST /api/register 接口，支持邮箱+密码注册，密码使用 bcrypt 加密存储",
  "implementationGuide": "1. 在 routes/auth.py 中添加 register 路由\n2. 使用 werkzeug.security.generate_password_hash(bcrypt)\n3. 返回 {ok, userId, email} JSON",
  "verificationCriteria": "1. curl 测试返回 201 + 正确 JSON\n2. 数据库 users 表新增记录，password_hash 为 bcrypt 格式\n3. 重复注册返回 409",
  "relatedFiles": ["app/routes/auth.py", "app/models/user.py", "app/schemas/auth.py"],
  "analysisResult": "使用 bcrypt 而非 SHA256 的原因是用户安全要求。注册流程需增加邮箱唯一性校验，避免重复注册。后续可加入邮箱验证步骤。",
  "notes": "注意：密码长度至少 8 位，邮箱需通过基础格式校验"
}
```

### 各阶段填写要点

- **`split-tasks` 时**：尽量填写 `implementationGuide`、`verificationCriteria`、`relatedFiles`、`notes`。这 4 个字段直接影响记忆质量和评分。
- **`execute-task` 过程中**：如发现上下文不足，可使用 `update-task` 补充字段。
- **`complete-task` 时**：务必提供详尽的 `--summary`，并通过 `--work-log` 记录遇到的问题和解决方案。
