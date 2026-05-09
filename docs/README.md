# task-manager

A modular, agent-friendly task management CLI for AI coding agents running inside OpenClaw-compatible environments.

## Highlights

- Modular architecture (`core/`, `skills/`, `utils/`)
- Session-based task isolation
- Prompt-driven workflow for agent execution
- Optional vector-memory integration
- Node.js dashboard for visual task tracking
- Open-source-ready packaging with config template, startup scripts, requirements file, and ignore rules

## Quick Start

```bash
cp config/config.example.json config/config.json
python task-manager.py --agent myagent get-session-id
python task-manager.py --agent myagent --session-id <sid> plan-task --description "Build feature X"
python task-manager.py --agent myagent --session-id <sid> split-tasks --mode overwrite --tasks '[{"name":"t1","description":"d1"}]'
python task-manager.py --agent myagent --session-id <sid> execute-task --id <task-id>
python task-manager.py --agent myagent --session-id <sid> complete-task --id <task-id> --summary "done"
```

## Structure

```text
task-manager/
├── task-manager.py
├── requirements.txt
├── start.bat
├── start.sh
├── .gitignore
├── config/
├── core/
├── skills/
├── utils/
├── dashboard/
└── docs/
```

## Key Commands

| Command | Description |
|---------|-------------|
| `get-session-id` | Generate a new session ID |
| `plan-task` | Set the requirement for this session |
| `split-tasks` | Create or replace task list |
| `list-tasks` | Show tasks with status |
| `execute-task` | Mark task as in progress |
| `complete-task` | Mark task as completed |
| `verify-task` | Print verification checklist |
| `update-task` | Update task fields |
| `block-task` | Block with a question |
| `unblock-task` | Unblock with an answer |
| `resplit-task` | Replace one task with subtasks |
| `claim-task` | Claim another session's task file |

See [getting-started.md](getting-started.md) for setup details.
