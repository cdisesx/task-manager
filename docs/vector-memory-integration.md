# vector-memory Integration Guide

This guide explains how to install and enable the optional `vector-memory` extension for task-manager.

When enabled, task-manager will automatically write task results to vector memory and retrieve relevant context before task execution, giving agents persistent memory across sessions.

---

## Is This Required?

No. `vector-memory` is an **optional** extension. task-manager works fully without it. When disabled (default), all memory hooks are silently skipped.

---

## Prerequisites

- Python 3.10+
- task-manager installed and configured
- Git

---

## 1. Install vector-memory

Clone the vector-memory repository into the `extensions/` directory:

```bash
git clone https://github.com/YOUR_ORG/vector-memory.git extensions/vector-memory
```

> **Note:** Replace `https://github.com/YOUR_ORG/vector-memory.git` with the actual repository URL once published.

Install its Python dependencies:

```bash
pip install -r extensions/vector-memory/requirements.txt
```

---

## 2. Configure vector-memory

```bash
cp extensions/vector-memory/config.example.json extensions/vector-memory/config.json
```

Edit `extensions/vector-memory/config.json` and set at minimum:

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
    "workspace_root": "/path/to/your/workspace"
  }
}
```

---

## 3. Start the Embedding Service

vector-memory requires an embedding service to be running:

```bash
# Linux/macOS
bash extensions/vector-memory/start.sh

# Windows
extensions\vector-memory\start.bat
```

Verify it's running:

```bash
curl http://localhost:3019/health
# {"status":"ok","model":"BAAI/bge-m3"}
```

---

## 4. Enable in task-manager config.json

Open `config/config.json` (copy from `config/config.example.json` if not done yet) and set:

```json
{
  "vector_memory": {
    "enabled": true,
    "service_url": "http://localhost:3019",
    "skill_path": "extensions/vector-memory"
  }
}
```

| Field | Description |
|-------|-------------|
| `enabled` | `true` to activate memory hooks |
| `service_url` | URL of the running embedding service |
| `skill_path` | Path to the vector-memory installation directory |

---

## 5. Initialize the Vector Store

Run this once per workspace to create the LanceDB tables:

```bash
python extensions/vector-memory/scripts/memory_init.py --workspace /path/to/your/workspace
```

Expected output:
```
[OK] 已创建表：memory_tasks
[OK] 已创建表：memory_dialogs
[OK] 初始化完成
```

---

## 6. Verify Integration

Run a task-manager command and check that memory hooks fire:

```bash
python task-manager.py --agent myagent get-session-id
```

If integration is working, you should see log lines like:
```
[M] 写入成功：1 条记录（tasks，1 个chunk）
```

---

## Disabling vector-memory

Set `vector_memory.enabled` to `false` in `config/config.json`:

```json
{
  "vector_memory": {
    "enabled": false
  }
}
```

No restart required. Memory hooks will be silently skipped on the next run.

---

## Troubleshooting

**Memory hook silently skipped**
- Check that `vector_memory.enabled` is `true` in `config/config.json`.
- Verify the embedding service is running: `curl http://localhost:3019/health`

**Connection refused to embedding service**
- Start the service: `bash extensions/vector-memory/start.sh`
- Check the port matches `vector_memory.service_url` in config.

**`memory_init.py` fails**
- Ensure `paths.workspace_root` is set correctly in vector-memory's `config.json`.
- Ensure `lancedb` and `sentence-transformers` are installed.
