/**
 * server.js - Node.js 看板 Web 服务
 * 启动: node dashboard/server.js
 * 默认端口: 3002 (可通过 PORT 环境变量覆盖)
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const { execFile } = require('child_process');
const tasksApi = require('./api/tasks');
const { getAllAgentsData, getAgentData, getAllTaskGroups } = tasksApi;

function getAgentsConfig() {
  return tasksApi.AGENTS_CONFIG;
}

function getAgents() {
  return tasksApi.AGENTS;
}

function getDashboardPortFromConfig() {
  try {
    const cfgPath = path.join(__dirname, '..', 'config', 'config.json');
    const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
    return cfg.dashboard?.port || null;
  } catch {
    return null;
  }
}

const PORT = process.env.PORT || getDashboardPortFromConfig() || 3002;
const PUBLIC_DIR = path.join(__dirname, 'public');
const SERVICES_FILE = path.join(__dirname, '..', 'data', 'services.json');

// 从 config.json 读取 base_dir
function getBaseDirFromConfig() {
  try {
    const cfgPath = path.join(__dirname, '..', 'config', 'config.json');
    const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
    return cfg.base_dir || path.join(__dirname, '..');
  } catch {
    return path.join(__dirname, '..');
  }
}

// 获取指定 agent 的工作区路径
function getAgentWorkspace(agentId) {
  const configs = getAgentsConfig();
  const found = configs.find(c => c.agentId === agentId || c.code === agentId);
  if (found && found.workspace) return found.workspace;
  return path.join(getBaseDirFromConfig(), `workspace-${agentId}`);
}

// MIME 类型
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css':  'text/css',
  '.js':   'application/javascript',
  '.json': 'application/json',
  '.png':  'image/png',
  '.ico':  'image/x-icon',
};

function serveStatic(res, filePath) {
  try {
    const data = fs.readFileSync(filePath);
    const ext = path.extname(filePath);
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'text/plain' });
    res.end(data);
  } catch {
    res.writeHead(404); res.end('Not Found');
  }
}

function json(res, data, status = 200) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(data));
}

function readServices() {
  try {
    const content = fs.readFileSync(SERVICES_FILE, 'utf8');
    return JSON.parse(content);
  } catch { return []; }
}

function writeServices(services) {
  try {
    fs.mkdirSync(path.dirname(SERVICES_FILE), { recursive: true });
    fs.writeFileSync(SERVICES_FILE, JSON.stringify(services, null, 2), 'utf8');
    return true;
  } catch (e) {
    console.error('[writeServices] failed:', e.message);
    return false;
  }
}

function getNetstatMap() {
  try {
    const { execSync } = require('child_process');
    const output = execSync('netstat -ano', { encoding: 'utf8' });
    const lines = output.split(/\r?\n/);
    const map = {};
    for (const line of lines) {
      const parts = line.trim().split(/\s+/);
      if (parts.length >= 5 && (parts[0] === 'TCP' || parts[0] === 'UDP')) {
        const local = parts[1];
        if (!local.includes(':')) continue;
        const port = local.split(':').pop();
        const pid = parts[parts.length - 1];
        if (!map[port]) map[port] = new Set();
        map[port].add(pid);
      }
    }
    return map;
  } catch (e) {
    console.error('[getNetstatMap] failed:', e.message);
    return {};
  }
}

function getProcessStartTime(pid) {
  try {
    const { execSync } = require('child_process');
    const out = execSync(
      `powershell -NoProfile -Command "(Get-Process -Id ${pid} -ErrorAction SilentlyContinue).StartTime | Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"`,
      { encoding: 'utf8', windowsHide: true, timeout: 3000 }
    ).trim();
    return out || null;
  } catch { return null; }
}

function getDockerStartTime(container) {
  try {
    const { execSync } = require('child_process');
    const out = execSync(
      `docker inspect --format "{{.State.StartedAt}}" ${container}`,
      { encoding: 'utf8', windowsHide: true, timeout: 3000 }
    ).trim();
    if (!out) return null;
    // Convert ISO8601 to local readable format
    const d = new Date(out);
    if (isNaN(d.getTime())) return out;
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch { return null; }
}

function checkServiceStatus(services) {
  const map = getNetstatMap();
  return services.map(svc => {
    const pids = map[String(svc.port)] ? Array.from(map[String(svc.port)]) : [];
    const running = pids.length > 0;
    let startTime = null;
    if (running) {
      if (svc.type === 'docker' && svc.dockerContainer) {
        startTime = getDockerStartTime(svc.dockerContainer);
      } else {
        // host type: use first valid pid
        const pid = pids.find(p => p && p !== '0');
        if (pid) startTime = getProcessStartTime(pid);
      }
    }
    return {
      ...svc,
      status: running ? 'running' : 'stopped',
      pid: pids.join(',') || null,
      startTime,
    };
  });
}

function killPort(port) {
  const map = getNetstatMap();
  const pids = map[String(port)];
  if (!pids || !pids.size) return { ok: false, message: 'no process on port' };
  const killed = [];
  for (const pid of pids) {
    try {
      const { execSync } = require('child_process');
      execSync(`taskkill /PID ${pid} /F`);
      killed.push(pid);
    } catch (e) {
      console.warn('[killPort] failed to kill', pid, e.message);
    }
  }
  return { ok: killed.length > 0, killed };
}

function stopDockerContainer(container) {
  if (!container) return { ok: false, message: 'missing docker container' };
  try {
    const { execSync } = require('child_process');
    const safeContainer = JSON.stringify(String(container));
    const out = execSync(`docker stop ${safeContainer}`, {
      encoding: 'utf8',
      windowsHide: true,
      timeout: 15000,
    }).trim();
    return { ok: true, stopped: container, output: out };
  } catch (e) {
    const stderr = typeof e?.stderr === 'string' ? e.stderr.trim() : '';
    const stdout = typeof e?.stdout === 'string' ? e.stdout.trim() : '';
    return {
      ok: false,
      message: stderr || stdout || e.message || 'docker stop failed',
    };
  }
}

function killService(service) {
  if (!service || !service.port) return { ok: false, message: 'missing service config' };
  if (service.type === 'docker') {
    return stopDockerContainer(service.dockerContainer || service.name);
  }
  return killPort(service.port);
}


function normalizeHistoryAgentsParam(value) {
  if (!value) return null;
  const requested = String(value)
    .split(',')
    .map(item => item.trim())
    .filter(Boolean);
  if (requested.length === 0) return null;
  const allowed = new Set(getAgents());
  return Array.from(new Set(requested.filter(agent => allowed.has(agent))));
}

function parseHistoryLimitParam(value) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return 20;
  return Math.min(parsed, 100);
}

function extractArchiveTimestamp(fileName) {
  const name = String(fileName || '');
  // 格式一：tasks-si-YYYYMMDDHHMMSS-hash.json
  const m1 = name.match(/^tasks-(si-)?(\d{14})-[^.]+\.json$/);
  if (m1) return m1[2];
  // 格式二：YYYYMMDD_HHMMSS.json（旧版归档）
  const m2 = name.match(/^(\d{8})_(\d{6})\.json$/);
  if (m2) return m2[1] + m2[2];
  // 格式三：si-YYYYMMDDHHMMSS-hash.json
  const m3 = name.match(/^si-(\d{14})-[^.]+\.json$/);
  if (m3) return m3[1];
  return '';
}

function formatArchiveTimestamp(ts14) {
  if (!ts14 || !/^\d{14}$/.test(ts14)) return '';
  return `${ts14.slice(0, 4)}-${ts14.slice(4, 6)}-${ts14.slice(6, 8)}T${ts14.slice(8, 10)}:${ts14.slice(10, 12)}:${ts14.slice(12, 14)}`;
}

function normalizeBeforeCursor(beforeValue) {
  if (!beforeValue) return null;
  const raw = String(beforeValue).trim();
  if (!raw) return null;
  const sidMatch = raw.match(/^si-(\d{14})-[a-f0-9]+$/i);
  if (sidMatch) return sidMatch[1];
  const digits = raw.match(/^(\d{14})$/);
  if (digits) return digits[1];
  const dateMs = Date.parse(raw);
  if (Number.isFinite(dateMs)) {
    const d = new Date(dateMs);
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
  }
  return raw;
}

function readArchivedHistoryForAgent(agentConfig, perAgentLimit, beforeCursor) {
  const agent = agentConfig.agentId;
  // 同时支持两个归档路径
  const memDirs = [
    path.join(agentConfig.workspace, 'tasks', 'memory'),
    path.join(agentConfig.workspace, 'memory', 'agent', agent),
  ];
  const results = [];
  const seenFiles = new Set();
  // 合并两个目录的文件列表
  const allFiles = [];
  for (const memDir of memDirs) {
    try {
      const files = fs.readdirSync(memDir)
        .filter(file => file.endsWith('.json') && !seenFiles.has(file))
        .map(file => { seenFiles.add(file); return { file, dir: memDir, sortKey: extractArchiveTimestamp(file) }; })
        .filter(item => item.sortKey);
      allFiles.push(...files);
    } catch { /* dir not found, skip */ }
  }
  allFiles.sort((a, b) => b.sortKey.localeCompare(a.sortKey));
  try {
    const files = allFiles;

    for (const entry of files) {
      if (beforeCursor && entry.sortKey >= beforeCursor) continue;
      try {
        const raw = fs.readFileSync(path.join(entry.dir, entry.file), 'utf8');
        const data = JSON.parse(raw);
        const tasks = Array.isArray(data) ? data : (data.tasks || []);
        results.push({
          agent,
          agentId: agent,
          agentCode: agentConfig.code,
          agentName: agentConfig.name,
          fileName: entry.file,
          userRequirement: data.userRequirement || '',
          taskCount: tasks.length,
          completedAt: formatArchiveTimestamp(entry.sortKey),
          createdAt: formatArchiveTimestamp(entry.sortKey),
          sortKey: entry.sortKey,
          tasks,
          source: 'archive',
        });
        if (results.length >= perAgentLimit) break;
      } catch { /* skip bad file */ }
    }
  } catch { /* dir not found */ }
  return results;
}

// 根据任务文件的 lastUpdatedAt 判断是否活跃（3分钟内 = active）
function getSpawnStatusByLastUpdate(lastUpdatedAt) {
  if (!lastUpdatedAt) return null;
  const last = new Date(lastUpdatedAt).getTime();
  if (isNaN(last)) return null;
  const diffMs = Date.now() - last;
  return diffMs <= 3 * 60 * 1000 ? 'active' : 'inactive';
}

// 路由处理
const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const pathname = url.pathname;

  // API: 所有代理数据
  if (pathname === '/api/agents' && req.method === 'GET') {
    try {
      const data = getAllAgentsData();
      // 根据任务文件 lastUpdatedAt 判断活跃状态（3分钟内 = active）
      for (const agent of data) {
        agent.spawnStatus = getSpawnStatusByLastUpdate(agent.lastUpdatedAt);
      }
      return json(res, { ok: true, agents: data, agentConfigs: getAgentsConfig(), ts: Date.now() });
    } catch (e) {
      return json(res, { ok: false, error: e.message }, 500);
    }
    return; // 异步处理，不继续往下走
  }

  // API: 单个代理历史归档（必须在单个代理数据路由之前）
  if (pathname.match(/^\/api\/agents\/[^/]+\/history$/) && req.method === 'GET') {
    const agentId = pathname.split('/')[3];
    if (!getAgents().includes(agentId)) return json(res, { ok: false, error: 'unknown agent' }, 404);
    try {
      const memDir = path.join(
        getAgentWorkspace(agentId), 'tasks', 'memory'
      );
      const history = [];
      try {
        const files = fs.readdirSync(memDir).filter(f => f.endsWith('.json')).sort().reverse();
        for (const file of files) {
          try {
            const raw = fs.readFileSync(path.join(memDir, file), 'utf8');
            const data = JSON.parse(raw);
            const tasks = Array.isArray(data) ? data : (data.tasks || []);
            history.push({
              fileName: file,
              completedAt: file.replace('.json', ''),
              userRequirement: data.userRequirement || '',
              tasks,
            });
          } catch { /* skip bad file */ }
        }
      } catch { /* dir not found */ }
      return json(res, { ok: true, history });
    } catch (e) {
      return json(res, { ok: false, error: e.message }, 500);
    }
  }

  // API: 单个代理数据
  if (pathname.startsWith('/api/agents/') && req.method === 'GET') {
    const agentId = pathname.split('/')[3];
    if (!getAgents().includes(agentId)) return json(res, { ok: false, error: 'unknown agent' }, 404);
    try {
      return json(res, { ok: true, agent: getAgentData(agentId), ts: Date.now() });
    } catch (e) {
      return json(res, { ok: false, error: e.message }, 500);
    }
  }

  // API: 历史任务（归档历史 + 当前未归档任务组）
  if (pathname === '/api/history' && req.method === 'GET') {
    try {
      const requestedAgents = normalizeHistoryAgentsParam(url.searchParams.get('agents'));
      const selectedAgentSet = requestedAgents ? new Set(requestedAgents) : null;
      const selectedConfigs = getAgentsConfig().filter(cfg => !selectedAgentSet || selectedAgentSet.has(cfg.agentId));
      const perAgentLimit = parseHistoryLimitParam(url.searchParams.get('limit'));
      const beforeCursor = normalizeBeforeCursor(url.searchParams.get('before'));
      const results = [];
      const seenCurrentSessions = new Set();

      for (const agentConfig of selectedConfigs) {
        results.push(...readArchivedHistoryForAgent(agentConfig, perAgentLimit, beforeCursor));
      }

      const currentGroups = getAllTaskGroups();
      const currentPerAgentCount = new Map();
      const sortedCurrentGroups = currentGroups
        .filter(group => !selectedAgentSet || selectedAgentSet.has(group.agent))
        .sort((a, b) => {
          const ta = new Date(a.lastUpdatedAt || 0).getTime() || 0;
          const tb = new Date(b.lastUpdatedAt || 0).getTime() || 0;
          return tb - ta;
        });

      for (const group of sortedCurrentGroups) {
        const sessionKey = `${group.agent}::${group.sid}`;
        if (seenCurrentSessions.has(sessionKey)) continue;
        seenCurrentSessions.add(sessionKey);
        if (!group.tasks || group.tasks.length === 0) continue;

        const currentCursor = normalizeBeforeCursor(group.sid || group.lastUpdatedAt || '');
        if (beforeCursor && currentCursor && currentCursor >= beforeCursor) continue;

        const count = currentPerAgentCount.get(group.agent) || 0;
        if (count >= perAgentLimit) continue;
        currentPerAgentCount.set(group.agent, count + 1);

        results.push({
          agent: group.agent,
          agentId: group.agent,
          agentCode: group.agentConfig?.code || group.agent,
          agentName: group.agentConfig?.name || group.agentLabel || group.agent,
          fileName: group.filename,
          userRequirement: group.userRequirement || '',
          taskCount: group.tasks.length,
          completedAt: group.lastUpdatedAt || '',
          createdAt: group.lastUpdatedAt || '',
          sortKey: currentCursor || normalizeBeforeCursor(group.lastUpdatedAt || '') || '',
          tasks: group.tasks,
          sid: group.sid,
          source: 'current',
        });
      }

      results.sort((a, b) => {
        const aKey = a.sortKey || normalizeBeforeCursor(a.completedAt || a.createdAt || '') || '';
        const bKey = b.sortKey || normalizeBeforeCursor(b.completedAt || b.createdAt || '') || '';
        return bKey.localeCompare(aKey);
      });

      return json(res, {
        ok: true,
        history: results,
        agentConfigs: getAgentsConfig(),
        pagination: {
          agents: selectedConfigs.map(cfg => cfg.agentId),
          limit: perAgentLimit,
          before: beforeCursor,
        },
      });
    } catch (e) {
      return json(res, { ok: false, error: e.message }, 500);
    }
  }

  // API: 解除任务阻塞
  if (pathname === '/api/unblock' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      let agentId, taskId, sessionId, answer;
      try {
        const parsed = JSON.parse(body);
        agentId = parsed.agentId;
        taskId = parsed.taskId;
        sessionId = parsed.sessionId;
        answer = parsed.answer;
      } catch {}
      if (!agentId || !taskId || !answer) {
        return json(res, { ok: false, error: 'missing agentId/taskId/answer' }, 400);
      }
      if (!getAgents().includes(agentId)) {
        return json(res, { ok: false, error: 'unknown agent' }, 404);
      }

      // 直接读写任务文件，无需通过 python 脚本
      try {
        const taskFilePath = path.join(getAgentWorkspace(agentId), 'tasks', `tasks-${sessionId}.json`);
        const raw = fs.readFileSync(taskFilePath, 'utf8');
        const data = JSON.parse(raw);
        const tasks = data.tasks || [];
        const task = tasks.find(t => t.id === taskId);
        if (!task) {
          return json(res, { ok: false, error: 'task not found' }, 404);
        }
        task.status = 'in_progress';
        task.blockInfo = null;
        task.unblockAnswer = answer;
        task.updatedAt = new Date().toISOString();
        fs.writeFileSync(taskFilePath, JSON.stringify(data, null, 2), 'utf8');
        return json(res, { ok: true, unblocked: true });
      } catch (e) {
        return json(res, { ok: false, error: e.message }, 500);
      }
    });
    return;
  }

  // API: 服务列表
  if (pathname === '/api/services' && req.method === 'GET') {
    return json(res, { ok: true, services: readServices() });
  }

  if (pathname === '/api/services/status' && req.method === 'GET') {
    const services = readServices();
    return json(res, { ok: true, services: checkServiceStatus(services) });
  }

  if (pathname === '/api/services/kill' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      let payload;
      try { payload = JSON.parse(body); } catch {}
      const port = payload?.port;
      if (!port) return json(res, { ok: false, error: 'missing port' }, 400);
      const services = readServices();
      const service = services.find(s => String(s.port) === String(port));
      if (!service) return json(res, { ok: false, error: 'service not found' }, 404);
      const result = killService(service);
      if (!result.ok) return json(res, { ok: false, error: result.message || 'kill failed' }, 400);
      return json(res, {
        ok: true,
        mode: service.type === 'docker' ? 'docker-stop' : 'taskkill',
        killed: result.killed || [],
        stopped: result.stopped || null,
        output: result.output || null,
      });
    });
    return;
  }

  // API: 删除服务记录
  if (pathname.startsWith('/api/services/') && req.method === 'DELETE') {
    const name = decodeURIComponent(pathname.split('/api/services/')[1]);
    if (!name) return json(res, { ok: false, error: 'missing name' }, 400);
    const services = readServices();
    const idx = services.findIndex(s => s.name === name);
    if (idx === -1) return json(res, { ok: false, error: 'service not found' }, 404);
    services.splice(idx, 1);
    if (!writeServices(services)) return json(res, { ok: false, error: 'write failed' }, 500);
    return json(res, { success: true });
  }

  if (pathname === '/api/services/register' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      let payload;
      try { payload = JSON.parse(body); } catch {}
      if (!payload || !payload.name || !payload.description || !payload.startCommand || !payload.port || !payload.type) {
        return json(res, { ok: false, error: 'missing fields' }, 400);
      }
      const services = readServices();
      if (services.some(s => s.name === payload.name)) {
        return json(res, { ok: false, error: 'service exists' }, 400);
      }
      const entry = {
        name: payload.name,
        description: payload.description,
        startCommand: payload.startCommand,
        port: payload.port,
        type: payload.type,
        dockerPort: payload.dockerPort || null,
        dockerContainer: payload.dockerContainer || null,
        registeredAt: payload.registeredAt || new Date().toISOString(),
      };
      services.push(entry);
      if (!writeServices(services)) {
        return json(res, { ok: false, error: 'write failed' }, 500);
      }
      return json(res, { ok: true, service: entry });
    });
    return;
  }

  // API: 获取所有 session 任务组（以 tasks-{sid}.json 为单元）
  if (pathname === '/api/task-groups' && req.method === 'GET') {
    try {
      const { getAllSessionGroups } = require('./api/tasks');
      const groups = getAllSessionGroups().map(group => {
        const agentConfig = getAgentsConfig().find(item => item.agentId === group.agent || item.code === group.agent) || null;
        return {
          ...group,
          agentCode: agentConfig?.code || group.agent,
          agentName: agentConfig?.name || group.agentName || group.agent,
          agentConfig,
        };
      });
      // 根据任务文件 lastUpdatedAt 判断活跃状态（3分钟内 = active）
      for (const g of groups) {
        g.spawnStatus = getSpawnStatusByLastUpdate(g.lastUpdatedAt);
      }
      return json(res, { ok: true, groups, agentConfigs: getAgentsConfig(), ts: Date.now() });
    } catch (e) {
      return json(res, { ok: false, error: e.message }, 500);
    }
    return;
  }

  // API: 获取所有空任务文件（tasks 数组为空或不存在）
  if (pathname === '/api/tasks/empty' && req.method === 'GET') {
    try {
      const BASE = getBaseDirFromConfig();
      const emptyFiles = [];
      for (const agent of getAgents()) {
        const tasksDir = path.join(BASE, `workspace-${agent}`, 'tasks');
        try {
          const files = fs.readdirSync(tasksDir).filter(f => /^tasks-.+\.json$/.test(f));
          for (const file of files) {
            try {
              const raw = fs.readFileSync(path.join(tasksDir, file), 'utf8');
              const data = JSON.parse(raw);
              const tasks = data.tasks || [];
              if (tasks.length === 0) {
                emptyFiles.push({
                  agent,
                  filename: file,
                  userRequirement: data.userRequirement || '',
                  filePath: path.join(tasksDir, file),
                });
              }
            } catch { /* skip bad file */ }
          }
        } catch { /* dir not found */ }
      }
      return json(res, { ok: true, files: emptyFiles });
    } catch (e) {
      return json(res, { ok: false, error: e.message }, 500);
    }
  }

  // API: 删除所有空任务文件
  if (pathname === '/api/tasks/empty' && req.method === 'DELETE') {
    try {
      const BASE = getBaseDirFromConfig();
      const deleted = [];
      const errors = [];
      for (const agent of getAgents()) {
        const tasksDir = path.join(BASE, `workspace-${agent}`, 'tasks');
        try {
          const files = fs.readdirSync(tasksDir).filter(f => /^tasks-.+\.json$/.test(f));
          for (const file of files) {
            try {
              const filePath = path.join(tasksDir, file);
              const raw = fs.readFileSync(filePath, 'utf8');
              const data = JSON.parse(raw);
              const tasks = data.tasks || [];
              if (tasks.length === 0) {
                fs.unlinkSync(filePath);
                deleted.push({ agent, filename: file });
              }
            } catch (e) {
              errors.push({ agent, filename: file, error: e.message });
            }
          }
        } catch { /* dir not found */ }
      }
      return json(res, { ok: true, deleted, errors });
    } catch (e) {
      return json(res, { ok: false, error: e.message }, 500);
    }
  }

  // 静态文件
  if (pathname === '/' || pathname === '/index.html') {
    return serveStatic(res, path.join(PUBLIC_DIR, 'index.html'));
  }
  if (pathname === '/detail.html') {
    return serveStatic(res, path.join(PUBLIC_DIR, 'detail.html'));
  }

  // 其他静态资源
  const staticPath = path.join(PUBLIC_DIR, pathname);
  if (fs.existsSync(staticPath) && fs.statSync(staticPath).isFile()) {
    return serveStatic(res, staticPath);
  }

  res.writeHead(404); res.end('Not Found');
});

server.listen(PORT, () => {
  console.log(`🏯 琅琊阁看板已启动: http://localhost:${PORT}`);
  console.log(`   API: http://localhost:${PORT}/api/agents`);
});
