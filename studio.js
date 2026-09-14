(() => {
  'use strict';
  document.documentElement.classList.add('js');
  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.site-nav');
  function closeMenu() {
    if (!menu || !nav) return;
    menu.setAttribute('aria-expanded', 'false');
    nav.classList.remove('is-open');
    menu.querySelector('span').textContent = '＋';
  }
  menu?.addEventListener('click', () => {
    const open = menu.getAttribute('aria-expanded') !== 'true';
    menu.setAttribute('aria-expanded', String(open));
    nav.classList.toggle('is-open', open);
    menu.querySelector('span').textContent = open ? '－' : '＋';
  });
  nav?.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
  document.addEventListener('keydown', event => { if (event.key === 'Escape') closeMenu(); });
  document.addEventListener('click', event => { if (!event.target.closest('.site-header')) closeMenu(); });
  matchMedia('(min-width: 701px)').addEventListener('change', closeMenu);

  const filters = [...document.querySelectorAll('[data-filter]')];
  const cards = [...document.querySelectorAll('.works-grid .project-card')];
  function applyFilter(category, updateURL = false) {
    if (!filters.some(button => button.dataset.filter === category)) category = '全部';
    let count = 0;
    cards.forEach(card => {
      card.hidden = category !== '全部' && card.dataset.category !== category;
      if (!card.hidden) count++;
    });
    filters.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.filter === category)));
    const counter = document.querySelector('.filter-count');
    if (counter) counter.textContent = `${count} 组作品`;
    if (updateURL) {
      const url = new URL(location.href);
      if (category === '全部') url.searchParams.delete('category');
      else url.searchParams.set('category', category);
      try { history.pushState(null, '', url); } catch (_) { /* Standalone previews still filter without URL updates. */ }
    }
  }
  filters.forEach(button => button.addEventListener('click', () => applyFilter(button.dataset.filter, true)));
  if (filters.length) {
    applyFilter(new URL(location.href).searchParams.get('category') || '全部');
    window.addEventListener('popstate', () => applyFilter(new URL(location.href).searchParams.get('category') || '全部'));
  }

  document.querySelectorAll('[data-copy]').forEach(button => {
    button.addEventListener('click', async () => {
      const note = button.closest('.contact-content').querySelector('.contact-note');
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        note.textContent = '微信号已复制。打开微信搜索 fcf9999，加好友请备注「院子」。';
        button.textContent = '已复制 ✓';
      } catch (_) {
        note.textContent = '微信号：fcf9999。请长按或选中文字复制。';
      }
    });
  });

  const dialog = document.querySelector('.lightbox');
  const gallery = [...document.querySelectorAll('.gallery-link')];
  if (dialog && gallery.length && typeof dialog.showModal === 'function') {
    const photo = dialog.querySelector('.lightbox-image');
    const stage = dialog.querySelector('.lightbox-stage');
    const caption = dialog.querySelector('.lightbox-caption');
    const counter = dialog.querySelector('.lightbox-counter');
    const zoom = dialog.querySelector('.lightbox-zoom');
    const previous = dialog.querySelector('.lightbox-prev');
    const next = dialog.querySelector('.lightbox-next');
    let current = 0;
    let opener;
    function renderImage(index) {
      current = (index + gallery.length) % gallery.length;
      const link = gallery[current];
      photo.src = link.href;
      photo.alt = link.querySelector('img').alt;
      caption.textContent = link.dataset.caption || photo.alt;
      counter.textContent = `${String(current + 1).padStart(2, '0')} / ${String(gallery.length).padStart(2, '0')}`;
      stage.classList.remove('is-zoomed');
      zoom.textContent = '放大 ＋';
      zoom.setAttribute('aria-pressed', 'false');
      zoom.setAttribute('aria-label', '放大图片');
      previous.disabled = next.disabled = gallery.length < 2;
    }
    gallery.forEach((link, index) => link.addEventListener('click', event => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      opener = link;
      renderImage(index);
      dialog.showModal();
    }));
    dialog.querySelector('.lightbox-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => opener?.focus());
    previous.addEventListener('click', () => renderImage(current - 1));
    next.addEventListener('click', () => renderImage(current + 1));
    zoom.addEventListener('click', () => {
      const enlarged = stage.classList.toggle('is-zoomed');
      zoom.textContent = enlarged ? '适合屏幕 −' : '放大 ＋';
      zoom.setAttribute('aria-pressed', String(enlarged));
      zoom.setAttribute('aria-label', enlarged ? '缩小图片' : '放大图片');
    });
    dialog.addEventListener('keydown', event => {
      if (event.key === 'ArrowLeft') { event.preventDefault(); renderImage(current - 1); }
      if (event.key === 'ArrowRight') { event.preventDefault(); renderImage(current + 1); }
    });
    let touchStart;
    stage.addEventListener('touchstart', event => { touchStart = event.touches[0].clientX; }, {passive:true});
    stage.addEventListener('touchend', event => {
      if (stage.classList.contains('is-zoomed') || touchStart === undefined) return;
      const delta = event.changedTouches[0].clientX - touchStart;
      if (Math.abs(delta) > 70) renderImage(current + (delta < 0 ? 1 : -1));
      touchStart = undefined;
    }, {passive:true});
  }

  // Keep price selection in sync whether chosen in the cards or the payment section.
  const tiers = [...document.querySelectorAll('.tier-tab')];
  function selectTier(amount, name) {
    tiers.forEach(tab => {
      const active = tab.dataset.amount === amount;
      tab.classList.toggle('active', active);
      tab.setAttribute('aria-pressed', String(active));
    });
    const amountDisplay = document.getElementById('payAmount');
    const tierName = document.getElementById('payTierName');
    if (amountDisplay) amountDisplay.textContent = amount + ' 元';
    if (tierName) tierName.textContent = name;
  }
  tiers.forEach(tab => tab.addEventListener('click', () => selectTier(tab.dataset.amount, tab.dataset.tier)));
  document.querySelectorAll('.tier-pay-btn').forEach(link => link.addEventListener('click', () => selectTier(link.dataset.amount, link.dataset.tier)));
  if (tiers.length) {
    tiers.forEach(tab => tab.setAttribute('aria-pressed', String(tab.classList.contains('active'))));
    document.getElementById('payAmount')?.setAttribute('aria-live', 'polite');
  }
})();
