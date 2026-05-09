/**
 * agents-config.js - 从 config.json 动态加载代理配置
 */
const path = require('path');
const fs = require('fs');

// 查找 config.json：从项目根目录的 config/ 下查找
function loadConfig() {
  const rootDir = path.resolve(__dirname, '..', '..');
  const candidates = [
    path.join(rootDir, 'config', 'config.json'),
    path.join(rootDir, 'config.json'),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) {
      try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (_) {}
    }
  }
  return { base_dir: rootDir, agents: [] };
}

/**
 * 标准化单个 agent 配置。
 * config.json 中 agents 数组元素为对象：
 *   { "name": "显示名", "id": "唯一标识", "workSpace": "工作区路径" }
 * 也兼容传统的 { id, name, workspace, agentId, code } 和纯字符串格式。
 */
function normalizeAgent(item, base) {
  if (typeof item === 'string') {
    const id = item;
    return {
      code: id,
      name: id,
      agentId: id,
      workspace: path.join(base, `workspace-${id}`),
    };
  }
  const id = item.id || item.agentId || item.code;
  if (!id) return null;
  return {
    code: item.code || id,
    name: item.name || id,
    agentId: item.agentId || id,
    workspace: item.workSpace || item.workspace || path.join(base, `workspace-${id}`),
  };
}

function buildAgentsConfig() {
  const cfg = loadConfig();
  const base = cfg.base_dir || path.join(__dirname, '..', '..');
  const agents = cfg.agents || [];

  const AGENTS_CONFIG = agents.map(item => normalizeAgent(item, base)).filter(Boolean);
  const AGENTS_CONFIG_BY_CODE = Object.fromEntries(AGENTS_CONFIG.map(a => [a.code, a]));
  const AGENTS_CONFIG_BY_AGENT_ID = Object.fromEntries(AGENTS_CONFIG.map(a => [a.agentId, a]));

  return {
    BASE_DIR: base,
    AGENTS_CONFIG,
    AGENTS_CONFIG_BY_CODE,
    AGENTS_CONFIG_BY_AGENT_ID,
    getAgentConfigByCode: code => AGENTS_CONFIG_BY_CODE[code] || null,
    getAgentConfigByAgentId: id => AGENTS_CONFIG_BY_AGENT_ID[id] || null,
    // 兼容旧名
    get OPENCLAW_BASE() { return this.BASE_DIR; },
  };
}

module.exports = buildAgentsConfig();
