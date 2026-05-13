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
