# Getting Started — task-manager

## Prerequisites

- Python 3.8+
- Node.js 16+ (dashboard only)
- pip

---

## Install

### 1. Get the code

```bash
git clone https://github.com/your-org/task-manager.git
cd task-manager
```

Or place the `task-manager/` directory anywhere you keep local tools.

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Create config.json

```bash
cp config/config.example.json config/config.json
# Windows PowerShell
# Copy-Item config/config.example.json config/config.json
```

Edit `config/config.json` and fill in your own environment values.

Example:

```json
{
  "basedir": "/path/to/your/object",
  "agents": ["agent"],
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

> `config.json` is gitignored and should stay local.

Full field reference: [configuration.md](configuration.md)

---

## First run

### Generate a session ID

```bash
python task-manager.py --agent myagent get-session-id
```

### Plan a task

```bash
python task-manager.py --agent myagent --session-id <sid> \
  plan-task --description "Add email verification to the user module"
```

### Split subtasks

```bash
python task-manager.py --agent myagent --session-id <sid> \
  split-tasks --mode overwrite \
  --tasks '[
    {
      "name": "Design database field",
      "description": "Add email_verified to users table",
      "implementationGuide": "Update schema and migration",
      "verificationCriteria": "Migration succeeds and field exists"
    }
  ]'
```

### Execute and complete

```bash
python task-manager.py --agent myagent --session-id <sid> execute-task --id <task-id>
python task-manager.py --agent myagent --session-id <sid> complete-task --id <task-id> --summary "Done"
```

---

## Start the dashboard

### Option A: helper script

```bash
./start.sh
```

Windows:

```bat
start.bat
```

### Option B: manual

```bash
cd dashboard
npm install
node server.js
```

Default URL: `http://localhost:3010`

---

## Verify setup

- `python task-manager.py --agent myagent get-session-id` returns an `si-...` session ID
- Dashboard opens successfully on the configured port
- `plan-task` and `split-tasks` create `tasks/tasks-<sid>.json` under your configured `basedir`

---

## Troubleshooting

| Problem | Fix |
|------|---------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` again |
| `config.json` missing | Copy `config/config.example.json` to `config/config.json` and fill it in |
| `list-tasks` shows no tasks for current session | Session changed; use `claim-task` to reattach the old file |
| `split-tasks` complains about `--mode` | Add `--mode overwrite` or another valid mode |
| Dashboard cannot open | Make sure `node server.js` is running and the configured port is free |
| Vector memory hook does nothing | Check `vector_memory.enabled` and the related service/path configuration |
