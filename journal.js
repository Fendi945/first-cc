(() => {
  'use strict';
  // Progressive enhancement: all stage photographs remain available without JavaScript.
  document.querySelectorAll('[data-stage-story]').forEach(story => {
    const tabs = [...story.querySelectorAll('[role="tab"]')];
    const panels = [...story.querySelectorAll('[role="tabpanel"]')];
    const select = index => {
      tabs.forEach((tab, i) => {
        tab.setAttribute('aria-selected', String(i === index));
        tab.tabIndex = i === index ? 0 : -1;
        panels[i].hidden = i !== index;
      });
    };
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => select(index));
      tab.addEventListener('keydown', event => {
        let next;
        if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
        if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = tabs.length - 1;
        if (next !== undefined) { event.preventDefault(); select(next); tabs[next].focus(); }
      });
    });
    select(0);
    story.classList.add('is-ready');
  });
  // Keep small historical images within their intrinsic width.
  document.querySelectorAll('.project-cover img, .project-gallery img').forEach(img => {
    const width = Number(img.getAttribute('width'));
    if (width > 0) img.style.setProperty('--image-natural-width', `${width}px`);
  });
  const form = document.getElementById('yard-form');
  if (!form) return;
  const lives = {
    tea: { title: '先留一个，你愿意坐下来的地方。', advice: '想想你通常什么时候喝茶、喜欢独处还是待客，再考虑座位朝向、遮阴与窗外的景色。', project: 'projects/lixiang.html' },
    family: { title: '先让全家人的日常，各有位置。', advice: '把孩子活动、家人停留与经常走的路放在一起考虑。有水景或高差时，应单独讨论儿童看护与防护需求。', project: 'projects/jiangdi.html' },
    grow: { title: '先看看阳光，再想种些什么。', advice: '记录不同时间的光照，列出想种的花木或蔬菜，以及每周愿意投入的打理时间，再考虑种植位置、取水与日常通行。', project: 'projects/lixiang.html' }
  };
  const states = {
    planning: { prepare: '咨询前可以准备：院子照片、大致尺寸、常住成员与最期待的三个功能。先理清方向，再决定设计范围。', target: 'yard-design.html#tiers' },
    before: { prepare: '硬化前建议先与设计及施工人员核对布局、种植预留和排水条件。请准备尺寸、现有方案及预计开工时间；咨询不替代施工图。', target: 'yard-design.html#tiers' },
    building: { prepare: '施工沟通前请准备：现有图纸、最新现场照片、当前工序和需要确认的问题。具体服务范围取决于图纸与现场条件。', target: 'yard-design.html#peipao' }
  };
  form.addEventListener('submit', event => {
    event.preventDefault();
    const input = new FormData(form);
    const life = lives[input.get('life')] || lives.tea;
    const state = states[input.get('status')] || states.planning;
    document.getElementById('yard-result-title').textContent = life.title;
    document.getElementById('yard-result-advice').textContent = life.advice;
    document.getElementById('yard-result-prepare').textContent = state.prepare;
    document.getElementById('yard-result-case').href = life.project;
    document.getElementById('yard-result-service').href = state.target;
    const result = document.getElementById('yard-result');
    result.hidden = false;
    result.focus({ preventScroll: true });
    result.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'center' });
  });
})();
