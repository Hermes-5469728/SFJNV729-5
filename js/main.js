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
    diagram: `
╔═══════════════════════════════════════╗
║           用户输入 (stdin)             ║
╚══════════════════════╤════════════════╝
                       │
┌──────────────────────▼──────────────────────┐
│  L0 编码层                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │U+FFFD检测 │→│GBK→UTF-8 │→│stdin/stdout│  │
│  │           │  │  恢复    │  │  重配置   │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└──────────────────────┬──────────────────────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
┌─────────▼────────┐ ┌─▼────────────▼─┐
│  Dispatch         │ │  Orchestrator  │
│  ┌──────────────┐ │ │  ┌──────────┐ │
│  │trigger 匹配  │ │ │  │13态状态机│ │
│  │优先级 P1-P5  │ │ │  │PLAN/EXEC │ │
│  │案例检索      │ │ │  │/VERIFY   │ │
│  └──────────────┘ │ │  │HITL 回路 │ │
└───────────────────┘ │  └──────────┘ │
                      └───────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│  Governance Pipeline                        │
│  ┌────────┐→┌────────┐→┌────────┐→┌────────┐ │
│  │encoding│ │ syntax │ │semantic│ │security│ │
│  └────────┘ └────────┘ └────────┘ └────────┘ │
│  ┌─────────────────────────────────────────┐ │
│  │          corrector ×3                   │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────┘
                       │
╔══════════════════════▼══════════════════════╗
║          stdout (L5 标注输出)               ║
╚═════════════════════════════════════════════╝`,
    desc: 'AC Platform 是完整的 E/D/S/Q 四层调度与治理流水线。输入经过 L0 编码层清洗后，由 Dispatch 匹配专家并排序，Orchestrator 执行多轮编排，最终经 Governance 四重检查+三重修正后输出 L5 标注结果。所有环节共享 ac_platform.db 统一数据底座。'
  },

  'orchestrator': {
    title: 'Orchestrator · 多轮规划编排引擎',
    sub: '13态状态机 · PLAN/EXECUTE/VERIFY/RESOLVE/LOG 五阶段循环',
    diagram: `
┌─────────────────────────────────────────────┐
│              Orchestrator Cycle              │
│                                             │
│   ┌────────────────────────────────────┐    │
│   │          1. PLAN phase             │    │
│   │  任务拆解 → Agent分配 → HITL确认   │    │
│   └──────────────┬─────────────────────┘    │
│                  │                          │
│   ┌──────────────▼─────────────────────┐    │
│   │       2. EXECUTE phase (循环)       │    │
│   │  ┌────────┐  ┌────────┐  ┌──────┐ │    │
│   │  │依赖检查│→│并行执行│→│验证  │ │    │
│   │  └────────┘  └────────┘  └──┬───┘ │    │
│   │              ┌──────────┐  │     │    │
│   │              │ 重试(x3) │←─┘     │    │
│   │              └──────────┘        │    │
│   └──────────────┬─────────────────────┘    │
│                  │                          │
│   ┌──────────────▼─────────────────────┐    │
│   │        3. RESOLVE phase             │    │
│   │  汇总/降级/回滚                      │    │
│   └──────────────┬─────────────────────┘    │
│                  │                          │
│   ┌──────────────▼─────────────────────┐    │
│   │          4. LOG phase              │    │
│   │   持久化 → 经验写入 ac_truth        │    │
│   └────────────────────────────────────┘    │
└─────────────────────────────────────────────┘

┌─ 13态状态机 ─────────────────────────────┐
│ CREATED → QUEUED → EXECUTING → VERIFYING │
│   → VERIFIED → COMPLETED                 │
│   → REJECTED → RETRYING → QUEUED (循环)   │
│   → FAILED → ROLLING_BACK → ROLLED_BACK  │
│   → BLOCKED (HITL 等待中)                 │
└───────────────────────────────────────────┘`,
    desc: 'Orchestrator 是 AC 的多轮规划循环引擎。核心为 13 态任务状态机（含 BLOCKED/ROLLING_BACK 等高级状态），按 PLAN→EXECUTE→VERIFY→RESOLVE→LOG 五阶段循环运行。支持依赖树驱动的任务调度、异步并行执行、HITL人在回路中断、自动重试与回滚。'
  },

  'governance': {
    title: 'Governance · 协同治理管道',
    sub: '四层检查 + 三重自动修正 + 协同治理',
    diagram: `
┌─────────────────────────────────────────────┐
│           Governance Pipeline                │
│                                             │
│   ┌──────────────┐                          │
│   │ encoding check│  ← U+FFFD / GBK→UTF-8   │
│   └──────┬───────┘                          │
│          ▼                                  │
│   ┌──────────────┐                          │
│   │  syntax check │  ← JSON结构/格式校验     │
│   └──────┬───────┘                          │
│          ▼                                  │
│   ┌──────────────┐                          │
│   │ semantic check│  ← 语义一致性/锚点比对   │
│   └──────┬───────┘                          │
│          ▼                                  │
│   ┌──────────────┐                          │
│   │ security check│  ← 敏感信息/注入检测     │
│   └──────┬───────┘                          │
│          ▼                                  │
│   ┌──────────────────────────┐              │
│   │   corrector ×3           │              │
│   │   (自动修正 → 重检 → 确认) │              │
│   └──────────────────────────┘              │
└─────────────────────────────────────────────┘

┌─ 协同治理 ────────────────────────────────┐
│  • 契约验证 (Contract Validation)          │
│  • 端到端验证 (End-to-End Verification)    │
│  • 风险评估 (Risk Interceptor)            │
│  • 资源锁管理 (Resource Lock)             │
└───────────────────────────────────────────┘`,
    desc: 'Governance Pipeline 是 AC 的质量安全层。四道检查依次过滤编码错误、格式错误、语义错误和安全风险，未通过项交由 corrector ×3 进行最多三轮自动修正。上层协同治理模块提供契约验证、风险评估、资源锁等高级治理能力。'
  },

  'anchor-engine': {
    title: 'Anchor Engine · EAV 事实核验引擎',
    sub: 'Entity-Attribute-Value · 确定性规则 · 零幻觉',
    diagram: `
┌─────────────────────────────────────────────┐
│           Anchor Engine v3                    │
│                                             │
│   ┌──────────────┐                          │
│   │   输入文本    │                          │
│   └──────┬───────┘                          │
│          ▼                                  │
│   ┌──────────────┐                          │
│   │  极性检测     │  ← positive / negative   │
│   └──────┬───────┘                          │
│          ▼                                  │
│   ┌──────────────────────────────────────┐  │
│   │      EAV 抽取 (确定性规则)             │  │
│   │  R1: X的Y是Z → {E:X, A:Y, V:Z}       │  │
│   │  R2: X是Y的Z → {E:X, A:Z, V:Y}       │  │
│   │  R3: 具备X管理 → {A:管理能力, V:X}     │  │
│   │  R4: X: Y    → {E:X, A:定义, V:Y}     │  │
│   │  R5: 必须/不得 → 对立词检测            │  │
│   └──────┬───────────────────────────────┘  │
│          ▼                                  │
│   ┌──────────────┐                          │
│   │  锚点库比对   │  ← anchor_db.json       │
│   └──────┬───────┘                          │
│          ▼                                  │
│   ┌──────────────┐                          │
│   │  硬拦截/通过  │                          │
│   └──────────────┘                          │
└─────────────────────────────────────────────┘`,
    desc: 'Anchor Engine 使用纯规则 EAV 抽取（不依赖任何模型推理），从文本中提取 (实体, 属性, 值) 三元组，配合极性检测和人工维护的锚点库进行事实比对。检测到矛盾时直接硬拦截，是 AC 治理层的最后防线。'
  },

  'case-center': {
    title: 'Case Center · 案例中心',
    sub: '失败捕获 → 向量检索 → 真值同步 → 持续改进',
    diagram: `
┌─────────────────────────────────────────────┐
│              Case Center                     │
│                                             │
│   ┌──────────────┐                         │
│   │  治理失败触发  │                         │
│   └──────┬───────┘                         │
│          ▼                                 │
│   ┌──────────────┐                         │
│   │  失败捕获     │  ← query+command+error  │
│   └──────┬───────┘                         │
│          ▼                                 │
│   ┌──────────────────────────┐             │
│   │  ChromaDB 向量存储       │             │
│   │  (相似案例检索 top_k=3)  │             │
│   └──────┬─────────┬────────┘             │
│          │         │                       │
│          ▼         ▼                       │
│   ┌──────────┐ ┌──────────┐               │
│   │ 检索复用  │ │ 真值同步  │               │
│   │ 相似案例  │ │ ac_truth │               │
│   └──────────┘ └──────────┘               │
│          │                                │
│          ▼                                │
│   ┌──────────────┐                        │
│   │  经验回放     │  ← 避免重复失败        │
│   └──────────────┘                        │
└─────────────────────────────────────────────┘`,
    desc: 'Case Center 是 AC 的经验学习系统。治理失败时自动捕获 query+command+error 三元组，存入 ChromaDB 向量库。后续相似输入可检索到历史案例，避免重复失败。同时与 ac_truth 真值表双向同步，构建持续改进的闭环。'
  },

  'phil-1n': {
    title: '1 · 核心平台 · 统一底座',
    sub: 'AC Platform 作为单一入口，统一调度与治理',
    diagram: `
┌─────────────────────────────────────────────┐
│            1 · AC Platform                   │
│  ┌───────────────────────────────────────┐  │
│  │           CLI 入口 (cli.py)            │  │
│  │  dispatch / annotate / seed / validate │  │
│  └──────────────┬────────────────────────┘  │
│                 │                           │
│  ┌──────────────▼────────────────────────┐  │
│  │      E/D/S/Q Pipeline                 │  │
│  │  ┌────┐ ┌────┐ ┌────┐ ┌────┐        │  │
│  │  │ L0 │→│ D  │→│ S  │→│ Q  │        │  │
│  │  └────┘ └────┘ └────┘ └────┘        │  │
│  └──────────────┬────────────────────────┘  │
│                 │                           │
│  ┌──────────────▼────────────────────────┐  │
│  │    ac_platform.db (统一持久化)          │  │
│  │  专家表 / 调度日志 / 治理审计 / 真值    │  │
│  │  任务图 / 迁移历史                      │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘`,
    desc: '“1” 指 AC Platform 核心平台，提供统一的 CLI 入口、完整的 E/D/S/Q 流水线，以及 ac_platform.db 统一数据持久化。所有调度请求经由单一入口处理，确保治理覆盖率和数据一致性。'
  },

  'phil-n': {
    title: 'N · 独立模块 · 契约解耦',
    sub: '各模块独立演进，通过契约对接平台',
    diagram: `
┌─────────────────────────────────────────────┐
│          N · 独立模块生态                     │
│                                             │
│   ┌─────────────────────────────────────┐   │
│   │       AC Platform (核心平台)         │   │
│   │        ┌─── 契约接口 ───┐            │   │
│   └────────┼───────────────┼────────────┘   │
│            │               │                │
│   ┌────────▼──┐  ┌────────▼──┐             │
│   │ Orchestrator│  │  Anchor    │           │
│   │ 编排引擎    │  │  Engine    │           │
│   │ •13态状态机 │  │ •EAV抽取   │           │
│   │ •HITL      │  │ •锚点比对  │           │
│   └───────────┘  └───────────┘             │
│                                             │
│   ┌────────▼──┐  ┌────────▼──┐             │
│   │ Case Center│  │ QA 框架   │             │
│   │ •向量检索  │  │ •评测集   │             │
│   │ •真值同步  │  │ •自动化   │             │
│   └───────────┘  └───────────┘             │
│                                             │
│   ┌────────▼──┐  ┌────────▼──┐             │
│   │ Gov 治理  │  │ 00-AC/    │             │
│   │ •四层检查  │  │ projects │             │
│   │ •修正器   │  │ •独立子项目│             │
│   └───────────┘  └───────────┘             │
└─────────────────────────────────────────────┘`,
    desc: '“N” 表示以 AC Platform 为核心的一系列独立子模块和子项目。每个模块通过明确定义的契约接口与平台对接，可独立开发、测试和演进，不产生循环依赖。这种 1+N 结构兼顾了平台的统一治理和模块的灵活发展。'
  },

  'phil-eav': {
    title: 'EAV 事实模型 · 零幻觉核验',
    sub: 'Entity-Attribute-Value 三元组 + 极性 + 锚点库',
    diagram: `
┌─────────────────────────────────────────────┐
│            EAV 三元组模型                     │
│                                             │
│     ┌──────────────────────┐                │
│     │      Entity          │                │
│     │      (实体)           │                │
│     └──┬───────────────┬───┘                │
│        │               │                    │
│   ┌────▼────┐    ┌─────▼────┐              │
│   │Attribute │    │  Value   │              │
│   │ (属性)   │    │  (值)    │              │
│   └─────────┘    └──────────┘              │
│                                             │
│   ┌─ 示例 ───────────────────────────────┐  │
│   │  E: AC平台  A: 架构  V: E/D/S/Q      │  │
│   │  E: 调度器  A: 优先级 V: P1-P5       │  │
│   │  E: 治理层  A: 检查数 V: 4层          │  │
│   └──────────────────────────────────────┘  │
│                                             │
│   ┌─ 抽取规则 ───────────────────────────┐  │
│   │  R1: X的Y是Z                         │  │
│   │  R2: X是Y的Z                         │  │
│   │  R3: 具备/支持/包含X管理              │  │
│   │  R4: X: Y                            │  │
│   │  R5: 必须/不得 → 对立词检测           │  │
│   └──────────────────────────────────────┘  │
│                                             │
│   极性: positive / negative                  │
│   锚点库: anchor_db.json (人工维护)           │
└─────────────────────────────────────────────┘`,
    desc: 'EAV 模型将知识表示为 (实体, 属性, 值) 三元组。Anchor Engine 用确定性正则规则从文本中抽取 EAV，判断语义极性，并与锚点库比对。发现矛盾时直接拦截输出，不依赖任何 AI 推理，实现零幻觉的事实核验。'
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
      <div class="modal-diagram"><pre>${data.diagram}</pre></div>
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
