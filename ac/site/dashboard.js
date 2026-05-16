const API_BASE = 'http://localhost:8001';
const API_TIMEOUT = 15000;

// ── Store ──
const store = {
  currentPage: 'chat',
  loading: new Set(),
  errors: new Map(),
  cache: new Map(),
  _pollTimer: null,
  _abortControllers: new Map(),
};

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function debounce(fn, ms = 300) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), ms);
  };
}

async function api(path, opts = {}) {
  const url = `${API_BASE}${path}`;
  const key = opts.method || 'GET';
  const ctrl = new AbortController();
  store._abortControllers.set(path + key, ctrl);
  const timeoutId = setTimeout(() => ctrl.abort(), API_TIMEOUT);
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...opts.headers },
      signal: ctrl.signal,
      ...opts,
    });
    clearTimeout(timeoutId);
    store._abortControllers.delete(path + key);
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new ApiError(res.status, text || res.statusText);
    }
    const text = await res.text();
    try {
      return JSON.parse(text);
    } catch {
      throw new ApiError(0, `JSON parse error: ${(text || '').slice(0, 80)}`);
    }
  } catch (err) {
    clearTimeout(timeoutId);
    store._abortControllers.delete(path + key);
    if (err.name === 'AbortError') throw new ApiError(408, 'Request timeout');
    throw err;
  }
}

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

// ── Page routing ──
function cancelPageRequests(name) {
  for (const [, ctrl] of store._abortControllers) ctrl.abort();
  store._abortControllers.clear();
}

function showPage(name) {
  if (store.currentPage !== name) cancelPageRequests(name);
  store.currentPage = name;
  $$('.page').forEach(p => p.classList.toggle('active', p.id === `page-${name}`));
  $$('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.page === name));
  if (name === 'chat') { chat.focusInput(); }
  if (name === 'ai-monitor') monitor.refresh();
  if (name === 'aggregation') { loadAggDates(); loadAggregation(); loadAITasks(); }
}

document.addEventListener('click', e => {
  const nav = e.target.closest('.nav-item');
  if (nav && nav.dataset.page) showPage(nav.dataset.page);
});

// ── System status ──
async function loadSystemStatus() {
  try {
    const data = await api('/api/health');
    const badge = $('.status-badge');
    badge.textContent = '系统正常';
    badge.className = 'status-badge online';
  } catch {
    const badge = $('.status-badge');
    badge.textContent = '离线';
    badge.className = 'status-badge offline';
  }
}

// ── DeepSeek Chat ──

const chat = {
  messages: [],
  sending: false,

  init() {
    this.input = document.getElementById('chat-input');
    this.sendBtn = document.getElementById('chat-send-btn');
    this.messagesEl = document.getElementById('chat-messages');
    this.statusEl = document.getElementById('chat-status');
    this.tokensEl = document.getElementById('chat-tokens');
    this._inited = false;

    // Enter to send, Shift+Enter for newline
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.send();
      }
    });

    // Auto-resize textarea
    this.input.addEventListener('input', () => {
      this.input.style.height = 'auto';
      this.input.style.height = Math.min(this.input.scrollHeight, 120) + 'px';
    });

    // Auto-init: 页面加载时主动问候
    this.loadInitGreeting();
  },

  async loadInitGreeting() {
    if (this._inited) return;
    this._inited = true;
    try {
      const data = await api('/api/jarvis/chat', {
        method: 'POST',
        body: JSON.stringify({ query: '__init__' }),
      });
      if (data && data.reply) {
        // Remove default welcome if any
        const welcome = this.messagesEl.querySelector('.welcome-msg');
        if (welcome) welcome.remove();
        this.addMessage('ai', data.reply);
      }
    } catch {
      // Offline or no jarvis — silently skip
    }
  },

  focusInput() {
    setTimeout(() => { if (this.input) this.input.focus(); }, 100);
  },

  addMessage(role, content, meta = null) {
    const div = document.createElement('div');
    div.className = `msg ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = role === 'user' ? 'U' : 'D';

    const bubbleWrap = document.createElement('div');
    bubbleWrap.style.maxWidth = '100%';

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    // Simple markdown-ish render
    bubble.innerHTML = this.renderContent(content);

    bubbleWrap.appendChild(bubble);

    if (meta) {
      const metaEl = document.createElement('div');
      metaEl.className = 'msg-meta';
      metaEl.textContent = meta;
      bubbleWrap.appendChild(metaEl);
    }

    div.appendChild(avatar);
    div.appendChild(bubbleWrap);
    this.messagesEl.appendChild(div);
    this.scrollToBottom();
  },

  renderContent(text) {
    // Escape HTML first
    const el = document.createElement('div');
    el.textContent = text;
    let html = el.innerHTML;

    // Code blocks
    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
      const langAttr = lang ? ` class="language-${lang}"` : '';
      return `<pre><code${langAttr}>${this.escapeHtml(code.trim())}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Lines to paragraphs
    html = html.split('\n').filter(l => l.trim()).map(l => `<p>${l}</p>`).join('');

    return html;
  },

  escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  },

  showTyping() {
    this.hideTyping();
    const div = document.createElement('div');
    div.className = 'msg ai typing';
    div.id = 'chat-typing';
    div.innerHTML = '<div class="msg-avatar">D</div><div class="typing"><div class="typing-dots"><span></span><span></span><span></span></div></div>';
    this.messagesEl.appendChild(div);
    this.scrollToBottom();
  },

  hideTyping() {
    const el = document.getElementById('chat-typing');
    if (el) el.remove();
  },

  scrollToBottom() {
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  },

  async send() {
    if (this.sending) return;
    const text = this.input.value.trim();
    if (!text) return;

    // Remove welcome
    const welcome = this.messagesEl.querySelector('.welcome-msg');
    if (welcome) welcome.remove();

    this.addMessage('user', text);
    this.input.value = '';
    this.input.style.height = 'auto';
    this.sending = true;
    this.sendBtn.disabled = true;
    this.statusEl.textContent = '思考中...';
    this.showTyping();

    // Check model health first
    try {
      const modelCheck = await api('/api/models');
      const deepseekAvail = modelCheck.env_configured?.deepseek;
      if (!deepseekAvail) {
        this.hideTyping();
        this.addMessage('ai', 'DeepSeek API 密钥未配置。请在环境变量中设置 DEEPSEEK_FREE_API_KEY 或 DEEPSEEK_API_KEY。');
        this.statusEl.textContent = 'API 未配置';
        this.sending = false;
        this.sendBtn.disabled = false;
        return;
      }
    } catch {
      // proceed anyway
    }

    try {
      const data = await api('/api/deepseek/chat', {
        method: 'POST',
        body: JSON.stringify({
          messages: this.messages.map(m => ({ role: m.role, content: m.content })),
        }),
      });
      this.hideTyping();
      const meta = data.model ? `${data.model} · ${data.latency_ms}ms · ${data.tokens_in}→${data.tokens_out} tokens` : '';
      this.addMessage('ai', data.reply, meta);
      if (this.tokensEl) {
        this.tokensEl.textContent = `${data.tokens_in || 0} in / ${data.tokens_out || 0} out`;
      }
      this.statusEl.textContent = '就绪';
    } catch (err) {
      this.hideTyping();
      let msg = err.message || '网络错误';
      if (err instanceof ApiError && err.status === 502) {
        msg = 'DeepSeek API 返回错误，请检查 API 密钥和网络连接。';
      }
      this.addMessage('ai', `对话失败: ${msg}`);
      this.statusEl.textContent = '错误';
    }

    this.sending = false;
    this.sendBtn.disabled = false;
    this.input.focus();
  },
};

// ── Dashboard ──

async function loadImmuneSystem() {
  const ids = ['immune-fraud', 'immune-endpoint', 'immune-pipeline', 'immune-core', 'immune-bus', 'immune-ghost'];
  const keys = ['fraud_test', 'endpoint_verify', 'pipeline_check', 'core_reachable', 'bus_guard', 'hunt_status'];

  const setCard = (i, text, cls) => {
    const el = document.getElementById(ids[i]);
    if (el) { el.textContent = text; el.className = 'value ' + cls; }
  };

  try {
    const data = await api('/api/archguard/scan');
    if (!data || !data.results) { throw new Error('No results'); }
    const fmt = [
      r => `${r.passed ? '通过' : '失败'} · ${r.passed_count||0}/${(r.passed_count||0)+(r.failed_count||0)}`,
      r => `${r.passed ? '一致' : '不一致'} · ${r.cli_status||'?'}`,
      r => `${r.passed ? '存活' : '异常'} · ${r.checks||0}检查`,
      r => `${r.passed ? '可达' : '不可达'}`,
      r => `${r.passed ? '完整' : '异常'} · ${r.guard_count||0}守卫`,
      r => `${r.date||'无'} · ${r.ghost_count||0}只`,
    ];
    keys.forEach((key, i) => {
      const r = data.results[key];
      if (r) setCard(i, fmt[i](r), r.passed ? 'green' : 'red');
      else setCard(i, '缺失', 'red');
    });
  } catch {
    return loadImmuneFallback();
  }
}

async function loadImmuneFallback() {
  try {
    const results = await Promise.allSettled([
      api('/api/audit/fraud-test'),
      api('/api/audit/endpoint-verify'),
      api('/api/audit/pipeline-check'),
      api('/api/audit/core-check'),
      api('/api/audit/bus-whitelist'),
      api('/api/audit/last-hunt'),
    ]);
    const ids = ['immune-fraud', 'immune-endpoint', 'immune-pipeline', 'immune-core', 'immune-bus', 'immune-ghost'];
    results.forEach((r, i) => {
      const el = document.getElementById(ids[i]);
      if (r.status === 'fulfilled') {
        const d = r.value;
        if (i === 0) {
          el.textContent = d.passed ? '通过' : '失败';
          el.className = 'value ' + (d.passed ? 'green' : 'red');
        } else if (i === 1) {
          el.textContent = d.consistent ? '一致' : '不一致';
          el.className = 'value ' + (d.consistent ? 'green' : 'red');
        } else if (i === 2) {
          el.textContent = d.alive ? '存活' : '异常';
          el.className = 'value ' + (d.alive ? 'green' : 'red');
        } else if (i === 3) {
          el.textContent = d.success ? '可达' : '不可达';
          el.className = 'value ' + (d.success ? 'green' : 'red');
        } else if (i === 4) {
          el.textContent = d.intact ? '完整' : '异常';
          el.className = 'value ' + (d.intact ? 'green' : 'red');
        } else if (i === 5) {
          el.textContent = `${d.date} · ${d.ghost_count} 只`;
          el.className = 'value blue';
        }
      } else {
        el.textContent = '离线';
        el.className = 'value red';
      }
    });
  } catch { /* ignore */ }
}

async function loadDashboard() {
  try {
    const [status, gov, events, dbInfo] = await Promise.all([
      api('/api/status'),
      api('/api/governance/status'),
      api('/api/bus/events?limit=5'),
      api('/api/db/tables'),
    ]);
    document.getElementById('stat-experts').textContent = status.experts;
    document.getElementById('stat-truths').textContent = status.truths;
    document.getElementById('stat-gov-total').textContent = gov.total;
    document.getElementById('stat-pass-rate').textContent = gov.pass_rate + '%';
    document.getElementById('stat-pass-rate').className = 'value ' + (gov.pass_rate >= 80 ? 'green' : gov.pass_rate >= 50 ? 'yellow' : 'red');
    document.getElementById('stat-tables').textContent = dbInfo.tables.length;
    document.getElementById('stat-guard').textContent = status.guard_events;
    try {
      const aiResp = await api('/api/bus/ledger?limit=1');
      document.getElementById('stat-ai-alive').textContent = aiResp.agents_alive || '?';
      document.getElementById('stat-ai-alive').className = 'value blue';
    } catch {
      document.getElementById('stat-ai-alive').textContent = '?';
    }
    const alerts = document.getElementById('recent-alerts');
    const recent = gov.recent || [];
    if (recent.length === 0) {
      alerts.innerHTML = '<div class="event-item">暂无告警</div>';
    } else {
      alerts.innerHTML = recent.slice(0, 5).map(r => {
        const preview = (r.input_preview || r.command || '').slice(0, 40);
        return `<div class="event-item">
          <span class="tag ${r.passed ? 'tag-pass' : 'tag-fail'}">${r.passed ? '通过' : '失败'}</span>
          <span class="cmd">${r.command || '?'}</span>
          <span class="q">${preview}</span>
          <div class="time">${r.created_at ? r.created_at.slice(0, 19).replace('T', ' ') : ''}</div>
        </div>`;
      }).join('');
    }
    const eventList = document.getElementById('event-list');
    const sched = events.schedule || [];
    if (sched.length === 0) {
      eventList.innerHTML = '<div class="event-item">暂无事件</div>';
    } else {
      eventList.innerHTML = sched.slice(0, 5).map(e => {
        const q = (e.query_preview || '').slice(0, 30);
        return `<div class="event-item">
          <span class="cmd">${e.response_mode || '?'}</span>
          <span class="q">${q}</span>
          <div class="time">${e.created_at ? e.created_at.slice(0, 19).replace('T', ' ') : ''}</div>
        </div>`;
      }).join('');
    }
  } catch { /* ignore */ }
}

// ── Ghosts ──

async function loadGhosts() {
  try {
    const data = await api('/api/ghosts');
    const container = document.getElementById('ghost-list');
    if (data.ghosts.length === 0) {
      container.innerHTML = '<div class="ghost-card"><div class="ghost-name">暂无猎鬼记录</div><div class="ghost-meta">点击扫描按钮检查系统</div></div>';
      return;
    }
    container.innerHTML = data.ghosts.map(g => `
      <div class="ghost-card" onclick="showGhostDetail(this)">
        <div class="ghost-name">${g.name}</div>
        <div class="ghost-meta">${g.size} 字节 · ${(g.modified || '').slice(0, 19).replace('T', ' ')}</div>
        <div class="ghost-preview">${(g.preview || '').slice(0, 200)}</div>
      </div>
    `).join('');
    document.getElementById('scan-status').textContent = `共 ${data.total} 条记录`;
  } catch { /* ignore */ }
}

function showGhostDetail(el) {
  const preview = el.querySelector('.ghost-preview');
  if (preview) preview.style.whiteSpace = preview.style.whiteSpace === 'pre-wrap' ? 'nowrap' : 'pre-wrap';
}

async function scanGhosts() {
  const btn = document.getElementById('btn-scan');
  const status = document.getElementById('scan-status');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> 扫描中...';
  status.textContent = '';
  try {
    const data = await api('/api/ghosts/scan', { method: 'POST' });
    btn.innerHTML = '一键扫描';
    btn.disabled = false;
    let msg = `扫描完成 · 检测到 ${data.test_files.length} 个测试文件`;
    if (data.server_instances > 1) msg += ` · 注意: ${data.server_instances} 个服务实例`;
    if (data.warnings && data.warnings[0]) msg += ` · ${data.warnings[0]}`;
    status.textContent = msg;
    loadGhosts();
  } catch (err) {
    btn.innerHTML = '一键扫描';
    btn.disabled = false;
    status.textContent = '扫描失败: ' + err.message;
  }
}

// ── Governance ──

async function loadGovernance() {
  try {
    const data = await api('/api/governance/status');
    document.getElementById('gov-total').textContent = data.total;
    document.getElementById('gov-passed').textContent = data.passed;
    document.getElementById('gov-failed').textContent = data.failed;
    document.getElementById('gov-corrected').textContent = data.corrected;
    document.getElementById('gov-pass-rate').textContent = data.pass_rate + '%';
    try {
      const fb = await api('/api/feedback/summary');
      document.getElementById('gov-feedback').textContent = fb.total || 0;
    } catch { document.getElementById('gov-feedback').textContent = '?'; }
    const tbody = document.getElementById('gov-table');
    tbody.innerHTML = (data.recent || []).map(r => {
      const checks = (() => { try { return JSON.parse(r.checks_json || '[]'); } catch { return []; } })();
      const checkSummary = checks.map(c => `<span class="tag ${c.passed ? 'tag-pass' : 'tag-fail'}">${c.checker}</span>`).join(' ');
      const govId = r.id || r.governance_id || '';
      return `<tr>
        <td>${r.created_at ? r.created_at.slice(0, 19).replace('T', ' ') : ''}</td>
        <td>${r.command || ''}</td>
        <td>${(r.input_preview || '').slice(0, 30)}</td>
        <td>${checkSummary}</td>
        <td><span class="tag ${r.passed ? 'tag-pass' : 'tag-fail'}">${r.passed ? '通过' : '失败'}</span></td>
        <td>${feedbackButtons(govId)}</td>
      </tr>`;
    }).join('');
    loadFeedbackSummary();
  } catch { /* ignore */ }
}

function feedbackButtons(id) {
  return `<div class="fb-row" style="display:flex;gap:4px">
    <button class="fb-btn fb-btn-good" onclick="submitFeedback('${id}','useful')">+1</button>
    <button class="fb-btn fb-btn-bad" onclick="submitFeedback('${id}','useless')">-1</button>
    <button class="fb-btn fb-btn-harm" onclick="submitFeedback('${id}','harmful')">!</button>
  </div>`;
}

async function submitFeedback(targetId, type) {
  try {
    await api('/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ message_id: targetId, feedback_type: type }),
    });
    showToast('反馈已提交', 'info');
    loadGovernance();
  } catch (err) {
    showToast('反馈提交失败: ' + (err.message || '网络错误'), 'error');
  }
}

async function loadFeedbackSummary() {
  try {
    const data = await api('/api/feedback/summary');
    const container = document.getElementById('feedback-summary');
    if (!data.total) { container.innerHTML = '<div class="event-item">暂无反馈</div>'; return; }
    const total = data.total;
    const useful = data.types?.useful || 0;
    const useless = data.types?.useless || 0;
    const harmful = data.types?.harmful || 0;
    container.innerHTML = `<div class="cards" style="grid-template-columns:repeat(4,1fr)">
      <div class="card"><div class="label">总反馈</div><div class="value blue">${total}</div></div>
      <div class="card"><div class="label">有用</div><div class="value green">${useful}</div></div>
      <div class="card"><div class="label">无用</div><div class="value yellow">${useless}</div></div>
      <div class="card"><div class="label">有害</div><div class="value red">${harmful}</div></div>
    </div>`;
  } catch { /* ignore */ }
}

// ── AI Monitor ──

const monitor = {
  agents: ['ac_server', 'ac_core', 'ac_orchestrator'],
  async refresh() {
    try {
      const data = await api('/api/bus/ledger?limit=20');
      this.renderLedger(data);
      this.updateCards(data);
    } catch (err) {
      document.getElementById('ai-ledger').innerHTML = `<div class="event-item">加载失败: ${err.message}</div>`;
    }
  },
  renderLedger(data) {
    const container = document.getElementById('ai-ledger');
    const msgs = data.messages || [];
    if (msgs.length === 0) { container.innerHTML = '<div class="event-item">暂无通信记录</div>'; return; }
    container.innerHTML = msgs.map(m => `<div class="ledger-item">
      <span class="time">${(m.timestamp || '').slice(0, 19).replace('T', ' ')}</span>
      <span class="from">${m.from || '?'}</span>
      <span class="arrow">&rarr;</span>
      <span class="to">${m.to || '?'}</span>
      <span class="status-tag status-${(m.response?.status || 'pending')}">${m.response?.status || 'pending'}</span>
      <span class="msg-preview">${JSON.stringify(m.content || m.payload || {}).slice(0, 50)}</span>
    </div>`).join('');
  },
  updateCards(data) {
    const alive = data.agents_alive || 0;
    const container = document.getElementById('ai-status-cards');
    const msgs = data.messages || [];
    const senders = new Set(msgs.map(m => m.from).filter(Boolean));
    container.innerHTML = `
      <div class="card"><div class="label">AI 存活数</div><div class="value green">${alive}</div></div>
      <div class="card"><div class="label">活跃发送者</div><div class="value blue">${senders.size}</div></div>
      <div class="card"><div class="label">通信记录</div><div class="value blue">${msgs.length}</div></div>`;
  },
  async pingAll() {
    const statusEl = document.getElementById('ai-ping-status');
    statusEl.textContent = '查验中...';
    const promises = this.agents.map(ai =>
      api('/api/bus/ping', {
        method: 'POST',
        body: JSON.stringify({ target: ai }),
      }).then(r => ({ ai, alive: r.alive })).catch(() => ({ ai, alive: false }))
    );
    const results = await Promise.all(promises);
    const alive = results.filter(r => r.alive).length;
    statusEl.textContent = `${alive}/${results.length} AI 存活`;
    this.refresh();
  },
};

// ── Data ──

async function loadTables() {
  try {
    const data = await api('/api/db/tables');
    const sel = document.getElementById('table-select');
    sel.innerHTML = '<option value="">-- 选择表 --</option>' +
      data.tables.map(t => `<option value="${t.name}">${t.name} (${t.row_count} 行)</option>`).join('');
    document.getElementById('table-info').innerHTML = data.tables.map(t => `<tr>
      <td>${t.name}</td>
      <td>${t.row_count}</td>
      <td>${t.columns.map(c => `${c.name} <span style="color:var(--text2);font-size:11px">${c.type}</span>`).join(', ')}</td>
      <td><button class="btn-ghost" style="padding:2px 8px;font-size:11px" onclick="quickQuery('${t.name}')">查看</button></td>
    </tr>`).join('');
  } catch { /* ignore */ }
}

async function runQuery() {
  const sql = document.getElementById('query-input').value.trim();
  if (!sql) return;
  const resultDiv = document.getElementById('query-result');
  resultDiv.innerHTML = '<span class="spinner"></span> 查询中...';
  try {
    const data = await api('/api/db/query', {
      method: 'POST',
      body: JSON.stringify({ sql }),
    });
    if (data.rows.length === 0) { resultDiv.innerHTML = '<div class="dispatch-result">无结果</div>'; return; }
    const cols = Object.keys(data.rows[0]);
    let html = '<table><thead><tr>' + cols.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>';
    html += data.rows.map(r => '<tr>' + cols.map(c => {
      const v = r[c];
      return `<td>${v === null ? '<span style="color:var(--text2)">NULL</span>' : typeof v === 'string' && v.length > 100 ? v.slice(0, 100) + '...' : String(v)}</td>`;
    }).join('') + '</tr>').join('');
    html += '</tbody></table>';
    html += `<div style="margin-top:8px;color:var(--text2);font-size:12px">${data.count} 行结果</div>`;
    resultDiv.innerHTML = html;
  } catch (err) {
    resultDiv.innerHTML = `<div class="dispatch-result" style="border-color:var(--red)">错误: ${err.message}</div>`;
  }
}

function quickQuery(tableName) {
  document.getElementById('query-input').value = `SELECT * FROM ${tableName} LIMIT 20`;
  runQuery();
}

// ── Dispatch ──

async function loadExperts() {
  try {
    const data = await api('/api/dispatch/experts');
    document.getElementById('expert-table').innerHTML = data.experts.map(e => `<tr>
      <td>${e.name}</td>
      <td>${e.category}</td>
      <td>${e.priority || 'P5'}</td>
      <td>${(e.trigger_words || '').slice(0, 40)}</td>
    </tr>`).join('');
  } catch { /* ignore */ }
}

async function runDispatch() {
  const query = document.getElementById('dispatch-input').value.trim();
  if (!query) return;
  const resultDiv = document.getElementById('dispatch-result');
  resultDiv.innerHTML = '<span class="spinner"></span> 调度中...';
  try {
    const data = await api('/api/dispatch', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
    resultDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
  } catch (err) {
    resultDiv.innerHTML = `<div class="dispatch-result" style="border-color:var(--red)">错误: ${err.message}</div>`;
  }
}

// ── Truth ──

async function loadTruth() {
  try {
    const [data, cats] = await Promise.all([
      api('/api/truth?limit=100'),
      api('/api/truth/categories'),
    ]);
    const sel = document.getElementById('truth-cat-select');
    sel.innerHTML = '<option value="">全部分类</option>' + cats.categories.map(c => `<option value="${c}">${c}</option>`).join('');
    renderTruthTable(data.truths || []);
  } catch { /* ignore */ }
}

function renderTruthTable(truths) {
  document.getElementById('truth-table').innerHTML = truths.map(t => `<tr>
    <td>${(t.title || '').slice(0, 40)}</td>
    <td>${t.category || ''}</td>
    <td>${t.truth_count || 0}</td>
    <td><span class="tag ${t.verified ? 'tag-pass' : 'tag-fail'}">${t.verified ? '已验证' : '未验证'}</span></td>
    <td style="font-size:11px;color:var(--text2)">${t.source || '-'}</td>
    <td>${t.created_at ? t.created_at.slice(0, 19).replace('T', ' ') : ''}</td>
  </tr>`).join('');
}

async function filterTruth() {
  const cat = document.getElementById('truth-cat-select').value;
  const search = document.getElementById('truth-search').value.trim().toLowerCase();
  try {
    const url = cat ? `/api/truth?limit=100&category=${encodeURIComponent(cat)}` : '/api/truth?limit=100';
    const data = await api(url);
    let truths = data.truths || [];
    if (search) truths = truths.filter(t =>
      (t.title || '').toLowerCase().includes(search) || (t.content || '').toLowerCase().includes(search));
    renderTruthTable(truths);
  } catch { /* ignore */ }
}

// ── External Sources ──

async function ingestYuanbao() {
  const textarea = document.getElementById('yb-urls');
  const urls = textarea.value.trim().split('\n').map(u => u.trim()).filter(Boolean);
  if (urls.length === 0) return;
  const resultDiv = document.getElementById('yb-result');
  resultDiv.innerHTML = '<span class="spinner"></span> 爬取并验证中...';
  try {
    const data = await api('/api/yuanbao/ingest', { method: 'POST', body: JSON.stringify(urls) });
    const lines = data.results.map(r =>
      `${r.status === 'ingested' ? '✅' : '⏭️'} ${r.title} -> ${r.validation || '?'} (score=${r.score || '?'})`).join('\n');
    resultDiv.innerHTML = `<div class="dispatch-result"><pre>${lines}</pre>
      <div style="margin-top:8px;color:var(--text2);font-size:12px">入库 ${data.ingested} 篇，跳过 ${data.duplicates} 篇重复</div></div>`;
  } catch (err) {
    resultDiv.innerHTML = `<div class="dispatch-result" style="border-color:var(--red)">错误: ${err.message}</div>`;
  }
}

async function verifyExternal() {
  const query = document.getElementById('metaso-query').value.trim();
  if (!query) return;
  const resultDiv = document.getElementById('metaso-result');
  resultDiv.innerHTML = '<span class="spinner"></span> 搜索中...';
  try {
    const data = await api('/api/metaso/search', { method: 'POST', body: JSON.stringify({ query }) });
    if (!data.results || data.results.length === 0) { resultDiv.innerHTML = '<div class="dispatch-result">无搜索结果</div>'; return; }
    document.getElementById('metaso-status').textContent = `已连接 (${data.results.length} 条)`;
    document.getElementById('metaso-status').className = 'value green';
    resultDiv.innerHTML = data.results.map(r => `<div class="ghost-card">
      <div class="ghost-name">${r.title}</div>
      <div class="ghost-meta">${r.date || ''} ${r.url ? '<a href="'+r.url+'" target="_blank" style="color:var(--accent)">来源</a>' : ''}</div>
      <div class="ghost-preview">${r.snippet || ''}</div>
    </div>`).join('');
  } catch (err) {
    document.getElementById('metaso-status').textContent = '未配置';
    document.getElementById('metaso-status').className = 'value yellow';
    resultDiv.innerHTML = `<div class="dispatch-result" style="border-color:var(--red)">搜索失败: ${err.message}</div>`;
  }
}

// ── Aggregation ──

function _(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === 'className') el.className = v;
    else if (k === 'innerHTML') el.innerHTML = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v);
  });
  children.forEach(c => typeof c === 'string' ? el.appendChild(document.createTextNode(c)) : el.appendChild(c));
  return el;
}

async function loadAggDates() {
  try {
    const data = await api('/api/aggregate/dates');
    const select = $('#agg-date-select');
    select.innerHTML = '<option value="">今天</option>';
    (data.dates || []).forEach(d => {
      const opt = document.createElement('option');
      opt.value = d; opt.textContent = d; select.appendChild(opt);
    });
  } catch { /* ignore */ }
}

async function loadAggregation() {
  const dateSelect = $('#agg-date-select');
  const date = dateSelect.value || null;
  const status = $('#agg-status');
  status.textContent = '加载中...';
  try {
    const params = date ? `?date=${date}` : '';
    const data = await api(`/api/aggregate${params}`);
    $('#agg-total').textContent = data.total_events;
    $('#agg-opencode').textContent = data.sources?.opencode || 0;
    $('#agg-trae').textContent = data.sources?.trae || 0;
    $('#agg-gov').textContent = data.sources?.ac_governance || 0;
    $('#agg-ghost').textContent = data.sources?.ghost_hunt || 0;
    status.textContent = `哈希: ${(data.hash || '').slice(0, 12)}... · ${data.date}`;
    renderTimeline(data.timeline);
  } catch (e) {
    status.textContent = `加载失败: ${e.message}`;
    $('#agg-timeline').innerHTML = `<div class="dispatch-result error">聚合失败: ${e.message}</div>`;
  }
}

function renderTimeline(events) {
  const container = $('#agg-timeline');
  if (!events || events.length === 0) {
    container.innerHTML = '<div style="padding:20px;color:var(--text2);text-align:center">暂无事件</div>';
    return;
  }
  const sourceColors = { opencode: '#a29bfe', trae: '#74b9ff', ac_governance: '#00b894', ghost_hunt: '#e17055' };
  container.innerHTML = events.map((e, i) => {
    const color = sourceColors[e.source] || 'var(--text2)';
    const time = e.timestamp ? e.timestamp.split('T')[1].slice(0, 5) : '--:--';
    const date = e.timestamp ? e.timestamp.slice(0, 10) : '';
    const showDate = i === 0 || date !== (events[i - 1]?.timestamp || '').slice(0, 10);
    return `<div class="tl-row">
      <div class="tl-date">${showDate ? date : ''}</div>
      <div class="tl-line"><div class="tl-dot" style="background:${color}"></div></div>
      <div class="tl-content">
        <div class="tl-time">${time}</div>
        <div class="tl-icon">${e.icon || '?'}</div>
        <div class="tl-summary">
          <span class="tl-source" style="color:${color}">[${e.source}]</span>${e.summary}
        </div>
        ${e.reference ? `<div class="tl-ref">${e.reference}</div>` : ''}
      </div>
    </div>`;
  }).join('');
}

async function loadAITasks() {
  try {
    const data = await api('/api/aggregate/ai-tasks');
    const container = document.getElementById('ai-tasks');
    if (!data || !container) return;
    const icons = { done: '✅', pending: '⏳', in_progress: '🔄', blocked: '🚫', unknown: '❓' };
    let html = `<div class="ai-stats-summary">
      <span>总任务: ${data.total_tasks}</span>
      <span>✅ ${data.by_status?.done || 0}</span>
      <span>⏳ ${data.by_status?.pending || 0}</span>
      <span>🔄 ${data.by_status?.in_progress || 0}</span>
      <span>🚫 ${data.by_status?.blocked || 0}</span>
    </div>`;
    const byAi = data.by_ai || {};
    for (const [ai, stats] of Object.entries(byAi)) {
      const pct = stats.total > 0 ? (stats.done / stats.total * 100) : 0;
      html += `<div class="ai-group"><div class="ai-group-header">
        <span class="ai-name">${ai}</span>
        <span class="ai-progress">${stats.done}/${stats.total}</span>
        <div class="ai-mini-bar"><div class="ai-mini-fill" style="width:${pct}%"></div></div>
      </div></div>`;
    }
    const tasks = (data.tasks || []).slice(0, 30);
    html += `<div class="ai-task-list">`;
    if (tasks.length === 0) {
      html += '<p style="color:var(--text2);padding:10px">暂无 AI 任务</p>';
    } else {
      html += tasks.map(t => `<div class="ai-task-item status-${t.status}">
        <span class="ai-task-icon">${icons[t.status] || '❓'}</span>
        <span class="ai-task-text">${escHtml(t.task)}</span>
        <span class="ai-task-ai">${t.ai || t.assigned_ai || ''}</span>
      </div>`).join('');
    }
    html += '</div>';
    container.innerHTML = html;
    const progressEl = document.getElementById('agg-progress');
    if (progressEl && data.total_tasks > 0) {
      const done = data.by_status?.done || 0;
      const pct = Math.round(done / data.total_tasks * 100);
      progressEl.innerHTML = `
        <div class="card" style="text-align:center"><div class="label">完成率</div><div class="value green">${pct}%</div></div>
        <div style="margin-top:12px;background:var(--surface2);border-radius:8px;height:8px;overflow:hidden">
          <div style="height:100%;background:var(--green);border-radius:8px;width:${pct}%;transition:width .5s"></div>
        </div>
        <div style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:8px">
          <div class="card"><div class="label">总任务</div><div class="value blue">${data.total_tasks}</div></div>
          <div class="card"><div class="label">已完成</div><div class="value green">${data.by_status?.done || 0}</div></div>
          <div class="card"><div class="label">进行中</div><div class="value" style="color:var(--blue)">${data.by_status?.in_progress || 0}</div></div>
          <div class="card"><div class="label">阻塞</div><div class="value red">${data.by_status?.blocked || 0}</div></div>
        </div>`;
    }
  } catch { /* ignore */ }
}

async function refreshAITasks() {
  try {
    await api('/api/aggregate/ai-tasks/refresh', { method: 'POST' });
    showToast('已请求 AI 刷新任务状态', 'info');
    setTimeout(() => loadAITasks(), 5000);
  } catch (e) {
    showToast('刷新失败: ' + e.message, 'error');
  }
}

function showToast(msg, type = 'info') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();
  const toast = document.createElement('div');
  toast.className = 'toast toast-' + type;
  toast.textContent = msg;
  document.body.appendChild(toast);
  requestAnimationFrame(() => { toast.style.opacity = '1'; toast.style.transform = 'translateY(0)'; });
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transform = 'translateY(10px)'; setTimeout(() => toast.remove(), 300); }, 3000);
}

function escHtml(str) {
  const el = document.createElement('span');
  el.textContent = str;
  return el.innerHTML;
}

// ── Init ──

async function init() {
  chat.init();
  showPage('chat');

  const tasks = [
    loadSystemStatus(),
    loadImmuneSystem(),
    loadDashboard(),
    loadGhosts(),
    loadGovernance(),
    loadTables(),
    loadExperts(),
    loadTruth(),
  ];

  let done = 0;
  const updateProgress = () => { done++; };
  await Promise.all(tasks.map(t => t.then(updateProgress, updateProgress)));

  store._pollTimer = setInterval(async () => {
    if (document.hidden) return;
    if (store.currentPage === 'dashboard') {
      await loadImmuneSystem();
      await loadDashboard();
    } else if (store.currentPage === 'ai-monitor') {
      await monitor.refresh();
    }
  }, 30000);
}

document.addEventListener('DOMContentLoaded', init);
