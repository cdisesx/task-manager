# 测试指南

## 快速开始

```bash
# 安装 pytest
pip install pytest

# 运行全部 113 个测试
pytest tests/ -v

# 运行单个模块
pytest tests/test_task_crud.py -v
pytest tests/test_memory_hook.py -v
pytest tests/test_block.py -v

# 运行单个测试用例
pytest tests/test_task_crud.py::TestCmdExecuteTask::test_execute_success -v
```

---

## 测试文件总览

| 文件 | 覆盖模块 | 用例数 |
|------|----------|--------|
| `test_time_utils.py` | `utils/time_utils.py` | 4 |
| `test_data_io.py` | `utils/data_io.py` | 7 |
| `test_task_crud.py` | `core/task_crud.py`（核心 CRUD） | 38 |
| `test_memory_hook.py` | `core/memory_hook.py`（向量内存评分） | 13 |
| `test_block.py` | `skills/block.py`（阻塞/解除阻塞） | 9 |
| `test_subtask.py` | `skills/subtask.py`（子任务拆分） | 8 |
| `test_worklog.py` | `skills/worklog.py`（工作记录/取消） | 9 |
| `test_todo.py` | `skills/todo.py`（Todo 流程） | 8 |
| `test_data_io.py` | `utils/data_io.py`（数据读写） | 7 |
| **合计** | | **113** |

---

## 测试架构

### 核心 fixture：`test_config`

所有涉及文件写入的测试都依赖 `test_config` fixture（定义在 `conftest.py`）。

它的工作原理：

1. 构建一个测试用配置 dict，将所有路径指向 `tmp_path`（pytest 自动分配的临时目录）
2. patch `utils.paths.load_config` 返回该配置
3. 后续所有路径函数（`get_base_dir` / `get_agent_workspace` / `get_tasks_path` 等）通过**真实代码链路**解析到 `tmp_path`

```python
# conftest.py 中的简化逻辑
@pytest.fixture
def test_config(tmp_path):
    config = {
        "base_dir": str(tmp_path),
        "agents": [
            {"id": "test_agent", "workSpace": str(tmp_path / "workspace-test_agent")},
        ],
        ...
    }
    with patch("utils.paths.load_config", return_value=config):
        yield tmp_path, workspace_dir, config
```

**优点**：只 patch `load_config` 一个入口，路径解析走完整真实链路，而非逐个 mock 各个路径函数。

### 衍生 fixture：`mock_tasks_dir`

```python
@pytest.fixture
def mock_tasks_dir(test_config):
    tmp_path, workspace_dir, _ = test_config
    tasks_dir = workspace_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    yield tmp_path, tasks_dir
```

测试方法直接使用 `mock_tasks_dir` 即可获得一个隔离的临时 tasks 目录。

### 其他 fixture

| fixture | 作用 | 定义位置 |
|---------|------|----------|
| `fixed_uuid` | 固定 `uuid.uuid4()` | `conftest.py` |
| `fixed_now` | 固定 `now_iso()` 和 `now_stamp()` | `conftest.py` |
| `fixed_session_id` | 固定 `resolve_session_id()` | `conftest.py` |

---

## 测试编写规范

### mock 策略

所有涉及文件系统操作的测试都使用 `mock_tasks_dir` fixture，确保：

- **隔离性**：每个测试有自己的 `tmp_path`，互不干扰
- **可重复性**：`fixed_uuid` / `fixed_now` 消除时间随机性
- **自动清理**：pytest 自动清理 `tmp_path`，无需手动删除

### 测试模式

测试覆盖正常路径和异常路径：

```
正常路径：
  test_xxx_success          → 验证操作成功完成
  test_xxx_with_xxx         → 验证带参数的操作

异常路径：
  test_xxx_not_found        → 找不到资源时退出
  test_xxx_missing_session_id → 缺少 session_id 时退出
  test_xxx_forbidden        → 非法状态操作被拒绝
  test_xxx_invalid_json     → 输入 JSON 格式错误
```

### 断言方式

由于 Windows 终端编码差异，涉及中文输出的断言尽量使用 ASCII / 英文字段：

```python
# 推荐（避免编码问题）：
assert "claim_task" in captured.out
assert "ownerSession" in captured.out

# 避免依赖中文精确匹配：
assert "找不到任务" in captured.out   # OK，但可能因编码问题失败
```

---

## 配置管理

### 测试配置文件

`tests/configs/test_config.json` 是测试配置的参考模板，供 fixture 读取后动态替换路径。

该文件不作为独立 JSON 直接加载（路径占位符由 fixture 在内存中替换为 `tmp_path`）。
在 fixture 中构建配置 dict 而非通过文件模板，是为了避免 Windows 路径反斜杠在 JSON 中的转义问题。

### 在真实 workspace 上运行

如果需要观察文件在真实 workspace 上如何生成，使用 `tests_demo/demo_real_workspace.py`：

```bash
python tests_demo/demo_real_workspace.py
```

该脚本会临时改写 `config/config.json` 指向 `workspace/demo_agent/`，执行 plan 和 split 操作后恢复原配置。

---

## --config 参数验证

`task-manager.py` 的 `--config` 参数可通过以下方式验证：

```bash
# 方式一：CLI 参数
python task-manager.py --agent demo --config my_cfg.json get_session_id

# 方式二：环境变量
export TASK_MANAGER_CONFIG=my_cfg.json
python task-manager.py --agent demo get_session_id
```

不传 `--config` 时默认读取 `config/config.json` → `config/config.example.json`（回退）。
