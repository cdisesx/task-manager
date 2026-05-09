# 向量记忆集成指南

将 task-manager 与向量记忆服务集成后，完成任务时会自动写入向量库，为 AI 代理提供跨 session 的持久记忆能力。

---

## 是否必须？

**否。** 向量记忆是可选扩展。默认关闭（`enabled: false`），关闭时所有记忆钩子静默跳过，不影响任何功能。

---

## 工作原理

当集成启用时，`complete-task` 执行后会触发 `core/memory_hook.py` 中的工作流：

```
complete-task
  └→ run_memory_hook()
       ├→ infer_task_type()     → 分类任务类型
       ├→ score_importance()    → 计算重要性分数
       ├→ build_memory_text()   → 构造结构化记忆文本
       └→ write_task_memory()   → 调用外部写入脚本
```

### 任务类型分类

`infer_task_type()` 根据任务名称、描述、摘要自动判断类型：

| 类型 | 触发关键词 | 重要性权重 |
|------|-----------|-----------|
| `architecture` | 架构、设计、方案、规范、rule、workflow | +0.28 |
| `integration` | 集成、接入、对接、hook、pipeline、cron | +0.22 |
| `bugfix` | bug、修复、fix、排查、故障 | +0.15 |
| `tooling` | 脚本、tool、cli、自动化 | +0.08 |
| `general` | 其他 | +0.08 |
| `cleanup` | 整理、搬运、格式 | +0.02 |

### 重要性评分

`score_importance()` 从多个维度综合打分（范围 0.20 ~ 0.95）：

| 维度 | 加分条件 | 最高加分 |
|------|----------|---------|
| 基础分 | 所有任务 | 0.35 |
| 任务类型 | 根据分类（见上表） | +0.28 |
| 踩坑记录 | 摘要/日志包含"踩坑""报错""异常"等 | +0.12 |
| 降级方案 | 包含"降级""fallback""retry"等 | +0.08 |
| 文件数量 | 根据关联文件数量（1~7+个） | +0.14 |
| 验证标准 | 有验证标准且测试通过 | +0.15 |
| 复用价值 | 包含"模板""标准""通用"等 | +0.18 |
| 分析深度 | 分析结果 >50 字或含架构/方案等关键词 | +0.18 |

### 记忆文本格式

高分任务（重要性 ≥0.70 或 architecture/integration 类型或 4+ 个文件）会生成详细格式：

```
【任务主题】xxx
【任务类型】architecture
【要解决的问题】xxx
【最终产出】xxx
【实现方案要点】xxx
【分析发现】xxx
【踩坑记录】xxx
【验证与证据】xxx
【关键踩坑/约束】xxx
【影响范围】xxx
【关联文件】xxx
【检索标签】xxx
```

低分任务生成精简格式，总长度均截断为 800 字符以内。

---

## 安装步骤

### 1. 安装向量记忆服务

```bash
# 克隆到 extensions/ 目录
git clone <vector-memory仓库地址> extensions/vector-memory

# 安装依赖
pip install -r extensions/vector-memory/requirements.txt
```

### 2. 配置向量记忆服务

```bash
cp extensions/vector-memory/config.example.json extensions/vector-memory/config.json
```

编辑 `extensions/vector-memory/config.json`：

```json
{
  "model": {
    "name": "BAAI/bge-m3",
    "hf_home": "",
    "offline": false
  },
  "server": {
    "host": "0.0.0.0",
    "port": 3019,
    "http_base": "http://localhost:3019"
  },
  "paths": {
    "workspace_root": "Y:\\path\\to\\workspace"
  }
}
```

### 3. 启动嵌入服务

```bash
# Linux / macOS
bash extensions/vector-memory/start.sh

# Windows
extensions\vector-memory\start.bat
```

验证服务运行：

```bash
curl http://localhost:3019/health
# {"status":"ok","model":"BAAI/bge-m3"}
```

### 4. 在 task-manager 配置中启用

编辑 `config/config.json`：

```json
{
  "vector_memory": {
    "enabled": true,
    "service_url": "http://localhost:3019",
    "skill_path": "extensions/vector-memory"
  }
}
```

| 字段 | 说明 |
|------|------|
| `enabled` | `true` 激活记忆钩子 |
| `service_url` | 嵌入服务的 URL |
| `skill_path` | 向量记忆扩展的路径（相对于项目根目录或绝对路径） |

### 5. 初始化向量库

每个工作区只需运行一次：

```bash
python extensions/vector-memory/scripts/memory_init.py --workspace Y:\path\to\workspace
```

预期输出：
```
[OK] 已创建表：memory_tasks
[OK] 已创建表：memory_dialogs
[OK] 初始化完成
```

### 6. 验证集成

运行一个完整的任务工作流，然后检查是否有记忆写入日志：

```bash
python task-manager.py --agent myagent get-session-id
python task-manager.py --agent myagent --session-id <sid> plan-task --description "..."
python task-manager.py --agent myagent --session-id <sid> split-tasks --mode overwrite --tasks '...'
python task-manager.py --agent myagent --session-id <sid> execute-task --id t1
python task-manager.py --agent myagent --session-id <sid> complete-task --id t1 --summary "完成"
```

如果集成成功，`complete-task` 输出中会包含：
```
[M] importance=0.65 type=general
[M] 写入成功：1 条记录（tasks，1 个chunk）
```

如果禁用或不成功，task 中会记录：
```
memoryWriteStatus: "skipped"   （disabled）
memoryWriteStatus: "pending"   （写入失败）
```

---

## 关闭集成

两种方式：

**方式一：设置 enabled 为 false**

```json
{
  "vector_memory": {
    "enabled": false
  }
}
```

**方式二：在 complete-task 时跳过**

```bash
python task-manager.py --agent myagent --session-id <sid> \
  complete-task --id t1 --summary "完成" --skip-memory
```

---

## 常见问题

**记忆钩子静默跳过**
- 检查 `config.json` 中 `vector_memory.enabled` 是否为 `true`
- 确认嵌入服务在运行：`curl http://localhost:3019/health`

**连接被拒**
- 启动嵌入服务：`bash extensions/vector-memory/start.sh`
- 检查端口是否与 `vector_memory.service_url` 一致

**`memory_init.py` 失败**
- 确保 `paths.workspace_root` 在向量记忆的 `config.json` 中正确设置
- 确保已安装 `lancedb`、`sentence-transformers` 等依赖

**写入失败但不影响任务**
- 这是设计行为：`run_memory_hook()` 的异常不会阻止 `complete-task` 完成
- 错误信息会写入任务的 `memoryWriteError` 字段
