// Scroll-aware nav + theme toggle
(function() {
  const nav = document.querySelector('nav');
  const toggle = document.getElementById('theme-toggle');
  const html = document.documentElement;

  // Theme
  const saved = localStorage.getItem('theme');
  if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    html.setAttribute('data-theme', 'dark');
    if (toggle) toggle.innerHTML = '☀ 亮';
  }

  toggle?.addEventListener('click', () => {
    const isDark = html.getAttribute('data-theme') === 'dark';
    if (isDark) { html.removeAttribute('data-theme'); localStorage.setItem('theme', 'light'); toggle.innerHTML = '🌙 暗'; }
    else { html.setAttribute('data-theme', 'dark'); localStorage.setItem('theme', 'dark'); toggle.innerHTML = '☀ 亮'; }
  });

  // Scroll effects
  let ticking = false;
  window.addEventListener('scroll', () => {
    if (!ticking) {
      requestAnimationFrame(() => {
        if (nav) nav.classList.toggle('scrolled', window.scrollY > 10);
        ticking = false;
      });
      ticking = true;
    }
  });
})();
