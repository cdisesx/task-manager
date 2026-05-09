/**
 * tasks.js - 读取各代理的任务数据
 * 核心变更：以 tasks-{sid}.json 为展示单元，不再以代理为单元
 */
const fs = require('fs');
const path = require('path');

const AGENTS_CONFIG_MODULE = path.join(__dirname, 'agents-config.js');

function loadAgentsConfigModule() {
  delete require.cache[require.resolve(AGENTS_CONFIG_MODULE)];
  return require(AGENTS_CONFIG_MODULE);
}

function getAgentsConfigState() {
  const configModule = loadAgentsConfigModule();
  const agentsConfig = Array.isArray(configModule.AGENTS_CONFIG) ? configModule.AGENTS_CONFIG : [];
  const agentsConfigByAgentId = configModule.AGENTS_CONFIG_BY_AGENT_ID
    || Object.fromEntries(agentsConfig.map(item => [item.agentId, item]));
  const getAgentConfigByAgentId = configModule.getAgentConfigByAgentId
    || function(agentId) {
      return agentsConfigByAgentId[agentId] || null;
    };

  return {
    OPENCLAW_BASE: configModule.OPENCLAW_BASE,
    AGENTS_CONFIG: agentsConfig,
    AGENTS_CONFIG_BY_AGENT_ID: agentsConfigByAgentId,
    getAgentConfigByAgentId,
    AGENTS: agentsConfig.map(item => item.agentId),
    AGENT_LABELS: Object.fromEntries(agentsConfig.map(item => [item.agentId, item.name])),
  };
}

function getBaseDir() {
  return getAgentsConfigState().OPENCLAW_BASE;
}

function toTimestamp(value) {
  if (value === null || value === undefined || value === '') return null;
  if (value instanceof Date) {
    const ms = value.getTime();
    return Number.isNaN(ms) ? null : ms;
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  const str = String(value).trim();
  if (!str) return null;
  const direct = new Date(str).getTime();
  if (!Number.isNaN(direct)) return direct;
  const match = str.match(/^(\d{4})(\d{2})(\d{2})(?:[_-]?(\d{2})(\d{2})(\d{2}))?$/);
  if (match) {
    const [, y, mo, d, h = '00', mi = '00', s = '00'] = match;
    const parsed = new Date(
      Number(y),
      Number(mo) - 1,
      Number(d),
      Number(h),
      Number(mi),
      Number(s)
    ).getTime();
    return Number.isNaN(parsed) ? null : parsed;
  }
  return null;
}

function pickLastUpdatedAt(data, tasks, stat) {
  const candidates = [
    data?.lastUpdatedAt,
    data?.updatedAt,
    data?.lastModifiedAt,
    stat?.mtimeMs,
  ];
  for (const task of (tasks || [])) {
    candidates.push(task?.updatedAt, task?.completedAt, task?.startedAt, task?.createdAt);
  }
  let latest = null;
  for (const candidate of candidates) {
    const ts = toTimestamp(candidate);
    if (ts === null) continue;
    if (latest === null || ts > latest) latest = ts;
  }
  return latest === null ? null : new Date(latest).toISOString();
}

function calcProgress(tasks) {
  if (!tasks || tasks.length === 0) {
    return { total: 0, done: 0, inProgress: 0, blocked: 0, cancelled: 0 };
  }
  const done       = tasks.filter(t => t.status === 'completed').length;
  const inProgress = tasks.filter(t => t.status === 'in_progress' || t.status === 'pending').length;
  const blocked    = tasks.filter(t => t.status === 'blocked').length;
  const cancelled  = tasks.filter(t => t.status === 'cancelled').length;
  return { total: tasks.length, done, inProgress, blocked, cancelled };
}

/**
 * 扫描单个代理下所有 tasks-{sid}.json，返回 taskGroup 数组
 */
function getAgentTaskGroups(agentId) {
  const { getAgentConfigByAgentId, AGENT_LABELS } = getAgentsConfigState();
  const agentConfig = getAgentConfigByAgentId(agentId);
  const tasksDir = path.join(agentConfig?.workspace || path.join(getBaseDir(), `workspace-${agentId}`), 'tasks');
  const groups = [];
  let files;
  try {
    files = fs.readdirSync(tasksDir).filter(f => /^tasks-.+\.json$/.test(f)).sort();
  } catch {
    return groups;
  }
  for (const filename of files) {
    try {
      const fullPath = path.join(tasksDir, filename);
      const raw = fs.readFileSync(fullPath, 'utf8');
      const data = JSON.parse(raw);
      const stat = fs.statSync(fullPath);
      const tasks = Array.isArray(data) ? data : (data.tasks || []);
      const sid = data.ownerSession || filename.replace(/^tasks-/, '').replace(/\.json$/, '');
      groups.push({
        agent: agentId,
        agentLabel:      agentConfig?.name || AGENT_LABELS[agentId] || agentId,
        agentConfig: agentConfig || null,
        sid,
        filename,
        tasks,
        userRequirement: data.userRequirement || '',
        ownerSession:    sid,
        sessionHistory:  data.sessionHistory || [],
        history:         data.history || [],
        blockInfo:       data.blockInfo || null,
        lastUpdatedAt:   pickLastUpdatedAt(data, tasks, stat),
        progress:        calcProgress(tasks),
      });
    } catch { /* skip bad file */ }
  }
  return groups;
}

/**
 * 获取所有代理的所有 taskGroup
 */
function getAllTaskGroups() {
  const { AGENTS } = getAgentsConfigState();
  const all = [];
  for (const agentId of AGENTS) {
    all.push(...getAgentTaskGroups(agentId));
  }
  return all;
}

// ── 保留旧接口兼容 ──────────────────────────────────────────────────────────

function getAgentNames() {
  return getAgentsConfigState().AGENT_LABELS;
}

function calcProgressLegacy(tasks) {
  if (!tasks || tasks.length === 0) return { total: 0, done: 0, running: 0, pending: 0, blocked: 0, pct: 0 };
  const done    = tasks.filter(t => t.status === 'completed').length;
  const running = tasks.filter(t => t.status === 'in_progress').length;
  const pending = tasks.filter(t => t.status === 'pending').length;
  const blocked = tasks.filter(t => t.status === 'blocked').length;
  const pct = Math.round((done / tasks.length) * 100);
  return { total: tasks.length, done, running, pending, blocked, pct };
}

function getAgentSessionGroups(agentName) {
  return getAgentTaskGroups(agentName).map(g => ({
    ...g,
    agentName: g.agentLabel,
    status: g.tasks.some(t => t.status === 'blocked') ? 'blocked'
          : g.tasks.some(t => t.status === 'in_progress' || t.status === 'pending') ? 'active'
          : 'idle',
    progress: calcProgressLegacy(g.tasks),
  }));
}

function getAllSessionGroups() {
  const { AGENTS } = getAgentsConfigState();
  const all = [];
  for (const agent of AGENTS) all.push(...getAgentSessionGroups(agent));
  all.sort((a, b) => {
    const diff = (toTimestamp(b.lastUpdatedAt) || 0) - (toTimestamp(a.lastUpdatedAt) || 0);
    if (diff !== 0) return diff;
    return String(a.sid || '').localeCompare(String(b.sid || ''));
  });
  return all;
}

function loadTasksJson(agentName) {
  const { getAgentConfigByAgentId } = getAgentsConfigState();
  const agentConfig = getAgentConfigByAgentId(agentName);
  const filePath = path.join(agentConfig?.workspace || path.join(getBaseDir(), `workspace-${agentName}`), 'tasks.json');
  try {
    const raw = fs.readFileSync(filePath, 'utf8');
    const data = JSON.parse(raw);
    if (Array.isArray(data)) return { userRequirement: '', tasks: data };
    if (data && Array.isArray(data.tasks)) return data;
    return { userRequirement: '', tasks: [] };
  } catch { return null; }
}

function loadArchives(agentName) {
  const { getAgentConfigByAgentId } = getAgentsConfigState();
  const agentConfig = getAgentConfigByAgentId(agentName);
  const memDir = path.join(agentConfig?.workspace || path.join(getBaseDir(), `workspace-${agentName}`), 'tasks', 'memory');
  const archives = [];
  try {
    const files = fs.readdirSync(memDir).filter(f => f.endsWith('.json')).sort().reverse();
    for (const file of files) {
      try {
        const raw = fs.readFileSync(path.join(memDir, file), 'utf8');
        const data = JSON.parse(raw);
        let tasks = [];
        if (Array.isArray(data)) tasks = data;
        else if (data && Array.isArray(data.tasks)) tasks = data.tasks;
        else if (data && (data.id || data.name)) tasks = [data];
        if (tasks.length > 0) archives.push({ file, archivedAt: file.replace('.json', ''), tasks });
      } catch { /* skip */ }
    }
  } catch { /* dir not found */ }
  return archives;
}

function getAgentData(agentName) {
  const { getAgentConfigByAgentId } = getAgentsConfigState();
  const agentConfig = getAgentConfigByAgentId(agentName);
  const current  = loadTasksJson(agentName);
  const archives = loadArchives(agentName);
  const sessions = getAgentSessionGroups(agentName);
  const mainTasks = current ? current.tasks : [];
  const allSessionTasks = sessions.flatMap(s => s.tasks);
  const tasks = mainTasks.length > 0 ? mainTasks : allSessionTasks;
  const progress = calcProgressLegacy(tasks);
  const sessionsWithProgress = sessions.map(s => ({
    ...s,
    hasBlockedTasks: s.tasks.some(t => t.status === 'blocked'),
    hasActiveTasks:  s.tasks.some(t => t.status === 'in_progress' || t.status === 'pending'),
  }));
  const lastUpdatedCandidates = [];
  if (current) lastUpdatedCandidates.push(current.lastUpdatedAt, current.updatedAt);
  for (const s of sessions) lastUpdatedCandidates.push(s.lastUpdatedAt);
  let lastUpdatedAt = null;
  for (const candidate of lastUpdatedCandidates) {
    const ts = toTimestamp(candidate);
    if (ts === null) continue;
    if (lastUpdatedAt === null || ts > lastUpdatedAt) lastUpdatedAt = ts;
  }
  return {
    id: agentConfig?.code || agentName,
    code: agentConfig?.code || agentName,
    name: agentConfig?.name || agentName,
    label: agentConfig?.name || agentName,
    agent: agentName,
    agentId: agentName,
    workspace: agentConfig?.workspace || path.join(getBaseDir(), `workspace-${agentName}`),
    agentConfig: agentConfig || null,
    userRequirement: current ? (current.userRequirement || '') : '',
    tasks,
    progress,
    sessions: sessionsWithProgress,
    archives,
    lastUpdatedAt: lastUpdatedAt === null ? null : new Date(lastUpdatedAt).toISOString(),
    hasActiveTasks:  tasks.some(t => t.status === 'in_progress' || t.status === 'pending'),
    hasBlockedTasks: tasks.some(t => t.status === 'blocked'),
  };
}

function getAllAgentsData() {
  const { AGENTS } = getAgentsConfigState();
  return AGENTS.map(a => getAgentData(a));
}

module.exports = {
  getAllTaskGroups,
  getAllSessionGroups,
  getAgentSessionGroups,
  getAgentTaskGroups,
  getAllAgentsData,
  getAgentData,
  getAgentsConfigState,
  get AGENTS_CONFIG() {
    return getAgentsConfigState().AGENTS_CONFIG;
  },
  get AGENTS_CONFIG_BY_AGENT_ID() {
    return getAgentsConfigState().AGENTS_CONFIG_BY_AGENT_ID;
  },
  get AGENTS() {
    return getAgentsConfigState().AGENTS;
  },
  get AGENT_LABELS() {
    return getAgentsConfigState().AGENT_LABELS;
  },
  get AGENT_NAMES() {
    return getAgentNames();
  },
};
