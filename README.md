# task-manager

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

```bash
cp config/config.example.json config/config.json
# Windows PowerShell
# Copy-Item config/config.example.json config/config.json
```

Edit `config/config.json` and set `base_dir` to your workspace root and list your agent names under `agents`.

### 3. Run

```bash
# Generate a session ID (do this once per conversation)
python task-manager.py --agent myagent get-session-id

# Plan a task
python task-manager.py --agent myagent --session-id <sid> plan-task --description "Build feature X"

# Split into subtasks
python task-manager.py --agent myagent --session-id <sid> split-tasks --mode overwrite \
  --tasks '[{"name":"Step 1","description":"Do X","implementationGuide":"...","verificationCriteria":"..."}]'

# Execute → Complete
python task-manager.py --agent myagent --session-id <sid> execute-task --id <task-id>
python task-manager.py --agent myagent --session-id <sid> complete-task --id <task-id> --summary "Done"
```

### 4. Start the dashboard (optional)

```bash
cd dashboard
npm install
node server.js
# Open http://localhost:3010
```

---

## Directory Structure

```
task-manager/
├── task-manager.py          # CLI entry point
├── requirements.txt         # Python dependencies
├── start.bat                # Windows startup helper
├── start.sh                 # Linux/macOS startup helper
├── pytest.ini               # pytest configuration
├── .gitignore               # Ignore local config, caches, logs
├── config/
│   └── config.example.json  # Configuration template (copy → config.json)
├── core/
│   ├── task_crud.py         # Core CRUD + state machine + session ownership
│   ├── memory_hook.py       # Vector memory write hook (optional)
│   └── prompts/             # AI prompt templates (.md files)
├── skills/
│   ├── block.py             # block-task / block-queue / unblock-task
│   ├── subtask.py           # add-subtask / resplit-task
│   ├── worklog.py           # add-work-log / cancel-task
│   ├── todo.py              # create-todo / plan-from-todo / assign-task / list-todos
│   ├── plan.py              # plan-task re-export
│   ├── split.py             # split-tasks re-export
│   ├── execute.py           # execute-task re-export
│   ├── complete.py          # complete-task re-export
│   └── archive.py           # archive re-export
├── utils/
│   ├── data_io.py           # JSON read/write helpers
│   ├── paths.py             # Path resolution
│   └── time_utils.py        # ISO timestamp helpers
├── dashboard/               # Node.js kanban UI
│   ├── server.js
│   ├── api/
│   └── public/
├── tests/                   # Pytest test suite
│   ├── conftest.py
│   ├── configs/
│   └── ...
├── tests_demo/              # Real workspace demo
└── docs/
    ├── README.md                      # Architecture overview
    ├── getting-started.md             # Step-by-step setup guide
    ├── configuration.md               # All config fields explained
    └── vector-memory-integration.md   # Optional vector memory setup
```

---

## Documentation

| File | Description |
|------|-------------|
| [docs/README.md](docs/README.md) | Architecture overview and command reference |
| [docs/getting-started.md](docs/getting-started.md) | Installation, configuration, first run |
| [docs/configuration.md](docs/configuration.md) | All `config.json` fields explained |
| [docs/vector-memory-integration.md](docs/vector-memory-integration.md) | Optional vector memory setup |

---

## License

MIT License. See [LICENSE](LICENSE) for details.
