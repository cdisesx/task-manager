# Configuration — task-manager

All runtime configuration lives in `config/config.json`.
Create it by copying `config/config.example.json`.

---

## Full example

```json
{
  "basedir": "/path/to/your/object",
  "agents": ["agent1", "agent2"],
  "log": {
    "dir": "logs",
    "filename": "task-manager.log"
  },
  "dashboard": {
    "port": 3010,
    "python_path": "python",
    "task_manager_script": "task-manager.py"
  },
  "vector_memory": {
    "enabled": false,
    "service_url": "http://localhost:3019",
    "skill_path": ""
  }
}
```

---

## Fields

### Top-level

| Field | Type | Required | Description |
|------|------|--------|------|
| `basedir` | string | yes | Root OpenClaw directory. Task files are stored under `{basedir}/workspace/{agent}/tasks/` |
| `agents` | string[] | yes | Agent names displayed and allowed by the dashboard/CLI environment |

### `log`

| Field | Type | Default | Description |
|------|------|--------|------|
| `log.dir` | string | `logs` | Log directory relative to the project root |
| `log.filename` | string | `task-manager.log` | Log filename |

### `dashboard`

| Field | Type | Default | Description |
|------|------|--------|------|
| `dashboard.port` | number | `3010` | HTTP port used by the dashboard |
| `dashboard.python_path` | string | `python` | Python executable used by dashboard server hooks |
| `dashboard.task_manager_script` | string | `task-manager.py` | Relative path to the CLI entry script |

### `vector_memory`

| Field | Type | Default | Description |
|------|------|--------|------|
| `vector_memory.enabled` | boolean | `false` | If false, vector-memory integration is skipped silently |
| `vector_memory.service_url` | string | `http://localhost:3019` | Vector-memory service endpoint |
| `vector_memory.skill_path` | string | `""` | Absolute or project-relative path to the vector-memory skill |

---

## Optional dependency behavior

When `vector_memory.enabled` is `false`, all vector-memory hooks must be skipped without raising runtime errors.
When it is `true`, make sure the related service is reachable and the skill path is valid.

---

## Data paths

Task files are stored at:

```text
{basedir}/workspace/{agent}/tasks/tasks-{sessionId}.json
```

Example:

```text
/path/to/your/object/workspace/{agent}/tasks/tasks-si-20260415135839-d1c6011f.json
```
