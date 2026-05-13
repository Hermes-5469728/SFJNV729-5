function initTheme() {
  const saved = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = saved || (prefersDark ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', theme);
  const btn = document.getElementById('themeToggle');
  if (btn) btn.textContent = theme === 'dark' ? '☀️' : '🌙';
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
  const btn = document.getElementById('themeToggle');
  if (btn) btn.textContent = next === 'dark' ? '☀️' : '🌙';
}

async function loadBlogPreview() {
  const container = document.getElementById('blogPreview');
  if (!container) return;
  try {
    const res = await fetch('blog/index.html');
    const html = await res.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const articles = doc.querySelectorAll('.blog-list article');
    let html_out = '';
    articles.forEach(article => {
      const link = article.querySelector('a');
      const title = article.querySelector('h3');
      const date = article.querySelector('.date');
      if (link && title) {
        html_out += `
          <div class="blog-card">
            <a href="${link.getAttribute('href')}">
              <h3>${title.textContent}</h3>
              ${date ? `<span class="date">${date.textContent}</span>` : ''}
            </a>
          </div>`;
      }
    });
    container.innerHTML = html_out || '<p style="color:var(--text-secondary)">暂无博客文章</p>';
  } catch {
    container.innerHTML = '<p style="color:var(--text-secondary)">暂无博客文章</p>';
  }
}

function initScrollAnimations() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, { threshold: 0.1 });
  document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));
}

function initBackToTop() {
  const btn = document.getElementById('backToTop');
  if (!btn) return;
  window.addEventListener('scroll', () => {
    btn.classList.toggle('show', window.scrollY > 400);
  });
  btn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

function initActiveNav() {
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-links a');
  if (!sections.length || !navLinks.length) return;
  window.addEventListener('scroll', () => {
    let current = '';
    sections.forEach(section => {
      const top = section.offsetTop - 100;
      if (window.scrollY >= top) current = section.getAttribute('id');
    });
    navLinks.forEach(link => {
      link.classList.toggle('active', link.getAttribute('href') === `#${current}`);
    });
  });
}

const MODAL_CONTENT = {
  'ac-platform': {
    title: 'AC Platform · E/D/S/Q 流水线',
    sub: '用户输入 → L0编码 → Dispatch → Orchestrator → Governance → stdout',
    desc: '四层架构的 AI 调度与治理平台。输入经编码层清洗后，由 Dispatch 匹配专家，Orchestrator 多轮编排，最终经 Governance 检查后输出。各环节共用统一数据底座。'
  },
  'orchestrator': {
    title: 'Orchestrator · 多轮规划编排引擎',
    sub: '任务状态机 · 五阶段循环 · HITL 人在回路',
    desc: '多轮规划循环引擎，按 PLAN→EXECUTE→VERIFY→RESOLVE→LOG 五阶段运行。支持依赖树调度、异步并行、HITL中断、自动重试与回滚。'
  },
  'governance': {
    title: 'Governance · 协同治理管道',
    sub: '多层检查 + 自动修正 + 协同治理',
    desc: '质量安全层。多道检查依次过滤各类错误，未通过项交由自动修正器处理。上层协同治理模块提供契约验证、风险评估、资源锁等能力。'
  },
  'anchor-engine': {
    title: 'Anchor Engine · 事实核验引擎',
    sub: 'Entity-Attribute-Value · 确定性规则 · 零幻觉',
    desc: '纯规则 EAV 抽取引擎，从文本提取 (实体, 属性, 值) 三元组，配合极性检测和锚点库进行事实比对。检测到矛盾时直接拦截，不依赖任何 AI 推理。'
  },
  'case-center': {
    title: 'Case Center · 案例中心',
    sub: '失败捕获 → 检索 → 同步 → 改进',
    desc: '经验学习系统。治理失败时自动捕获信息存入向量库，后续相似输入可检索历史案例避免重复失败。与真值表双向同步，形成持续改进闭环。'
  },
  'phil-1n': {
    title: '1 · 核心平台 · 统一底座',
    sub: 'AC Platform 作为单一入口',
    desc: '提供统一的 CLI 入口和完整的 E/D/S/Q 流水线，所有调度请求经由单一入口处理，确保治理覆盖率和数据一致性。'
  },
  'phil-n': {
    title: 'N · 独立模块 · 契约解耦',
    sub: '各模块独立演进，通过契约对接平台',
    desc: '以 AC Platform 为核心的一系列独立子模块。每个模块通过契约接口与平台对接，可独立开发、测试和演进，不产生循环依赖。'
  },
  'phil-eav': {
    title: 'EAV 事实模型 · 零幻觉核验',
    sub: 'Entity-Attribute-Value 三元组模型',
    desc: '知识表示为 (实体, 属性, 值) 三元组。用确定性规则抽取 EAV，判断语义极性，与锚点库比对。发现矛盾时直接拦截输出，实现零幻觉的事实核验。'
  },

  /* 数据库表 */
  'db-experts': {
    title: 'ac_experts · 专家注册表',
    sub: '24 个专家，按 L/T/M/A 分类，P1-P5 优先级',
    desc: '存储所有注册专家的元数据。包括名称、分类、触发词、角色定义、规则约束。Dispatch 模块通过 trigger_words 匹配查询，按 priority 排序选取 Top 2 返回。'
  },
  'db-schedule': {
    title: 'ac_schedule_log · 调度日志',
    sub: '11 条调度记录',
    desc: '记录每次 dispatch 的完整调用链。含 session_id、查询哈希、匹配的专家名、响应模式。用于调度审计和性能分析。'
  },
  'db-governance': {
    title: 'ac_governance_log · 治理审计日志',
    sub: '14 条记录，全部通过',
    desc: '治理管道的完整审计轨迹。记录每次治理检查的通过状态、错误详情、修正次数、编码修复事件。是系统可信度的核心证据链。'
  },
  'db-truth': {
    title: 'ac_truth · 真值知识库',
    sub: '90 条已验证知识，7 个分类',
    desc: '存储经过 L5 验证的确定性知识。Case Center 与此表双向同步，治理管道的 semantic check 以此为锚点进行事实比对。'
  },
  'db-taskgraphs': {
    title: 'task_graphs · 编排任务图',
    sub: 'Orchestrator 任务持久化',
    desc: '存储 Orchestrator 的多轮编排任务图。含完整 PlanSteps、Agent 池、HITL 队列、执行指标。支持任务断点恢复和事后审计。'
  },
  'db-migration': {
    title: 'migration_history · 迁移审计',
    sub: '2 次迁移，版本 v1 → v2',
    desc: '数据库 schema 版本管理和迁移审计。每次 DDL 变更必须走 migration 脚本，记录版本号、变更名称、执行时间、成功状态。违反此流程的修改会被拦截。'
  },

  /* 架构层 */
  'arch-l0': {
    title: 'L0 编码层',
    sub: '输入清洗与编码修复 · 治理管道的第一道防线',
    desc: '在输入进入核心流水线之前进行编码清洗：U+FFFD 替换字符检测、GBK→UTF-8 字节流恢复、stdin/stdout 代码页重配置。确保后续所有处理在正确的编码基础上进行。'
  },
  'arch-dispatch': {
    title: 'D · Dispatch 调度引擎',
    sub: '专家匹配 · 优先级排序 · 案例检索',
    desc: '将用户输入与 24 个专家的 trigger_words 进行匹配。按 P1(安全) > P2(权益) > P3(心理) > P4(技术) > P5(通用) 排序，选取前 2 个返回。同时检索 Case Center 的相似案例辅助决策。'
  },
  'arch-orchestrator': {
    title: 'S · Orchestrator 编排引擎',
    sub: '13 态状态机 · 五阶段循环 · HITL 人在回路',
    desc: '多轮规划循环引擎，按 PLAN→EXECUTE→VERIFY→RESOLVE→LOG 五阶段运行。13 态任务状态机管理每一步生命周期，支持依赖树调度、异步并行执行、HITL 中断、自动重试与回滚。'
  },
  'arch-gov': {
    title: 'Q · Governance Pipeline',
    sub: '多层检查 · 自动修正 · 协同治理',
    desc: '质量安全层。encoding/syntax/semantic/security 四道检查依次过滤各类错误，未通过项交由 corrector ×3 自动修正。上层协同治理提供契约验证、风险评估、资源锁管理。'
  },

  /* 架构侧边栏 */
  'arch-anchor': {
    title: 'Anchor Engine · 锚点引擎',
    sub: 'EAV 事实核验 · 确定性规则 · 零幻觉',
    desc: '纯规则 EAV 抽取引擎，从文本提取 (实体, 属性, 值) 三元组。配合极性检测（positive/negative）和锚点库 JSON 比对，发现事实矛盾时直接硬拦截。'
  },
  'arch-case': {
    title: 'Case Center · 案例中心',
    sub: '失败捕获 → ChromaDB 检索 → 真值同步',
    desc: '治理失败时自动捕获案例（query+command+error），存入 ChromaDB 向量库。后续调度前检索相似案例避免重复失败。与 ac_truth 真值表双向同步。'
  },
  'arch-collab': {
    title: 'Collaborative Governor · 协同治理',
    sub: '契约验证 · 风险评估 · 资源锁 · 端到端验证',
    desc: '多 Agent 协作时的治理协调层。提供 agent 输出的契约校验、高风险操作拦截、资源竞争锁管理、以及完整的任务完成验证流程。'
  },
  'arch-db': {
    title: 'ac_platform.db · 统一数据底座',
    sub: 'SQLite · 6 张核心表 · Schema 版本控制',
    desc: '单文件 SQLite 数据库，集中存储专家注册表、调度日志、治理审计、真值知识、任务图、迁移历史。所有模块共享同一数据源，确保数据一致性和可审计性。'
  }
};

function initModal() {
  const overlay = document.getElementById('modalOverlay');
  const modal = document.getElementById('modal');
  const body = document.getElementById('modalBody');
  const closeBtn = document.getElementById('modalClose');

  function open(key) {
    const data = MODAL_CONTENT[key];
    if (!data) return;
    body.innerHTML = `
      <div class="modal-title">${data.title}</div>
      <div class="modal-sub">${data.sub}</div>
      ${data.diagram ? `<div class="modal-diagram"><pre>${data.diagram}</pre></div>` : ''}
      <div class="modal-desc">${data.desc}</div>
    `;
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  document.querySelectorAll('[data-modal]').forEach(el => {
    el.style.cursor = 'pointer';
    el.addEventListener('click', () => open(el.dataset.modal));
  });

  closeBtn.addEventListener('click', close);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') close();
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  const toggle = document.getElementById('themeToggle');
  if (toggle) toggle.addEventListener('click', toggleTheme);
  loadBlogPreview();
  initScrollAnimations();
  initBackToTop();
  initActiveNav();
  initModal();
});
