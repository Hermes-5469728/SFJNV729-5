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

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  const toggle = document.getElementById('themeToggle');
  if (toggle) toggle.addEventListener('click', toggleTheme);
  loadBlogPreview();
  initScrollAnimations();
  initBackToTop();
  initActiveNav();
});
