/* 🧠 元演心智 · 审批面板交互逻辑 v2
   改用本地 HTTP API（避免 file:// 无法写入的问题）*/

// ── 配置 ──────────────────────────────────────────
const API_BASE = window.location.origin;
const REFRESH_INTERVAL = 30000;  // 30 秒自动刷新

let pendingData = [];
let isDirty = false;
let refreshTimer = null;

// ── 工具函数 ──────────────────────────────────────
function getStatusCounts(items) {
    return {
        pending: items.filter(i => i.status === 'pending').length,
        video: items.filter(i => i.output_tag === 'video' && i.status === 'pending').length,
        article: items.filter(i => i.output_tag === 'article' && i.status === 'pending').length,
        tool: items.filter(i => i.output_tag === 'tool' && i.status === 'pending').length,
    };
}

function cardStatusClass(item) {
    if (item.status === 'approved') return 'card-approved';
    if (item.status === 'skipped') return 'card-skipped';
    return '';
}

function tagHtml(tag) {
    const map = {
        'video': '<span class="tag tag-video">📹 视频</span>',
        'article': '<span class="tag tag-article">📝 文章</span>',
        'tool': '<span class="tag tag-tool">🔧 工具</span>',
        'none': '<span class="tag tag-none">⛔ 归档</span>',
        'explore': '<span class="tag tag-explore">❓ 待深入</span>',
    };
    return map[tag] || `<span class="tag tag-none">${tag}</span>`;
}

function layerLabel(layer) {
    const map = {
        'ontology': '🧬 本体',
        'ability': '🛠️ 能力',
        'rule': '📏 规则',
        'event': '📡 事件',
        'action': '✅ 行动',
    };
    return map[layer] || layer;
}

// ── API 调用 ──────────────────────────────────────

async function apiGet(path) {
    const resp = await fetch(`${API_BASE}${path}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

async function apiPost(path, body = {}) {
    const resp = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

async function apiPut(path, body) {
    const resp = await fetch(`${API_BASE}${path}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

// ── 渲染 ──────────────────────────────────────────
function render() {
    const counts = getStatusCounts(pendingData);
    const pendingItems = pendingData.filter(i => i.status === 'pending');
    const doneItems = pendingData.filter(i => i.status !== 'pending');

    // 更新统计
    document.getElementById('stat-pending').textContent = counts.pending;
    document.getElementById('stat-video').textContent = counts.video;
    document.getElementById('stat-article').textContent = counts.article;
    document.getElementById('stat-tool').textContent = counts.tool;

    // 全部通过按钮禁用状态
    const btn = document.querySelector('.btn-approve-all');
    if (btn) btn.disabled = counts.pending === 0;

    const list = document.getElementById('pending-list');
    const doneList = document.getElementById('done-list');

    // 待审批
    if (pendingItems.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="icon">🎉</div>
                <p>暂无待审批项</p>
                <p style="font-size:13px;color:var(--text-secondary)">写一篇日输入，AI 会自动生成审批项</p>
            </div>`;
    } else {
        list.innerHTML = pendingItems.map(item => renderCard(item)).join('');
    }

    // 已处理
    if (doneItems.length === 0) {
        doneList.innerHTML = '';
    } else {
        doneList.innerHTML = `
            <div class="done-section-header">
            已处理 (${doneItems.length})
            </div>
            ${doneItems.map(item => renderCard(item)).join('')}`;
    }

    // 更新最后刷新时间
    document.getElementById('last-update').textContent = new Date().toLocaleString('zh-CN');
}

function renderCard(item) {
    const title = item.suggested_title || item.summary || item.original_text?.slice(0, 40) || '(无内容)';
    const safeId = item.id.replace(/'/g, "\\'").replace(/"/g, '&quot;');
    return `
    <div class="card ${cardStatusClass(item)}" data-id="${safeId}">
        <div class="card-header">
            <div class="card-title">${item.output_tag === 'video' ? '📹' : item.output_tag === 'article' ? '📝' : item.output_tag === 'tool' ? '🔧' : '📄'} ${escapeHtml(title)}</div>
            <div class="card-tags">
                ${tagHtml(item.output_tag)}
                <span class="tag" style="background:rgba(255,255,255,0.05);color:var(--text-secondary)">${layerLabel(item.layer)}</span>
            </div>
        </div>
        <div class="card-meta">
            <span>📅 ${item.source_date || '?'}</span>
            <span>🎯 ${item.suitable_platform || '待定'}</span>
            ${item.status !== 'pending' ? `<span>${item.status === 'approved' ? '✅ 已通过' : '⏭️ 已跳过'}</span>` : ''}
        </div>
        <div class="card-text" onclick="this.classList.toggle('expanded')">
            ${escapeHtml(item.original_text || item.summary || '(无内容)')}
        </div>
        ${item.status === 'pending' ? `
        <div class="card-actions">
            <button class="btn btn-approve" data-id="${safeId}" data-action="approve">✅ 通过 → 进入生产</button>
            <button class="btn btn-edit" data-id="${safeId}" data-action="edit">✏️ 修改</button>
            <button class="btn btn-skip" data-id="${safeId}" data-action="skip">🗑️ 跳过</button>
        </div>` : ''}
    </div>`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

// ── 操作 ──────────────────────────────────────────

async function approveItem(id) {
    const item = pendingData.find(i => i.id === id);
    if (!item) return;
    try {
        const btn = document.querySelector(`[data-id="${id.replace(/"/g, '&quot;')}"][data-action="approve"]`);
        if (btn) { btn.disabled = true; btn.textContent = '⏳ 处理中...'; }

        await apiPost('/api/approve', { id });
        item.status = 'approved';
        item.approved_at = new Date().toLocaleString('zh-CN');
        isDirty = true;
        render();
    } catch (e) {
        alert('❌ 审批失败: ' + e.message);
        render(); // 恢复按钮状态
    }
}

async function skipItem(id) {
    const item = pendingData.find(i => i.id === id);
    if (!item) return;
    try {
        const btn = document.querySelector(`[data-id="${id.replace(/"/g, '&quot;')}"][data-action="skip"]`);
        if (btn) { btn.disabled = true; btn.textContent = '⏳ 处理中...'; }

        await apiPost('/api/skip', { id });
        item.status = 'skipped';
        item.skipped_at = new Date().toLocaleString('zh-CN');
        isDirty = true;
        render();
    } catch (e) {
        alert('❌ 操作失败: ' + e.message);
        render();
    }
}

function editItem(id) {
    const item = pendingData.find(i => i.id === id);
    if (!item) return;
    const modal = document.getElementById('edit-modal');
    const textarea = document.getElementById('edit-textarea');
    textarea.value = JSON.stringify({
        suggested_title: item.suggested_title,
        summary: item.summary,
        original_text: item.original_text,
    }, null, 2);
    modal.dataset.editId = id;
    modal.classList.add('active');
}

async function saveEdit() {
    const modal = document.getElementById('edit-modal');
    const id = modal.dataset.editId;
    const item = pendingData.find(i => i.id === id);
    if (!item) return;
    try {
        const edited = JSON.parse(document.getElementById('edit-textarea').value);
        if (edited.suggested_title !== undefined) item.suggested_title = edited.suggested_title;
        if (edited.summary !== undefined) item.summary = edited.summary;
        if (edited.original_text !== undefined) item.original_text = edited.original_text;
        isDirty = true;
        await saveData();
    } catch(e) { alert('JSON 格式错误'); return; }
    modal.classList.remove('active');
    render();
}

async function approveAll() {
    const pending = pendingData.filter(i => i.status === 'pending');
    if (pending.length === 0) return;
    document.getElementById('confirm-modal').classList.add('active');
}

async function confirmApproveAll() {
    try {
        const result = await apiPost('/api/approve-all');
        if (result.ok) {
            pendingData.forEach(i => {
                if (i.status === 'pending') {
                    i.status = 'approved';
                    i.approved_at = new Date().toLocaleString('zh-CN');
                }
            });
            isDirty = true;
        }
    } catch (e) {
        alert('❌ 批量审批失败: ' + e.message);
    }
    document.getElementById('confirm-modal').classList.remove('active');
    render();
}

// C1: 卡片操作事件委托
function handleCardAction(e) {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    const id = btn.dataset.id;
    const action = btn.dataset.action;
    if (action === 'approve') approveItem(id);
    else if (action === 'edit') editItem(id);
    else if (action === 'skip') skipItem(id);
}

// ── 数据读写 ──────────────────────────────────────

async function loadData() {
    const statusEl = document.getElementById('connection-status');
    const list = document.getElementById('pending-list');

    try {
        // 显示加载状态
        if (statusEl) statusEl.textContent = '🔄';
        if (list) list.innerHTML = `
            <div class="empty-state">
                <div class="icon" style="animation: spin 1s linear infinite">⏳</div>
                <p>正在加载...</p>
            </div>`;

        const data = await apiGet('/api/pending');
        pendingData = Array.isArray(data) ? data : [];
        isDirty = false;

        // 连接正常
        if (statusEl) {
            statusEl.textContent = '🟢';
            statusEl.title = '服务器已连接';
        }

        render();
    } catch (e) {
        console.warn('加载失败:', e.message);
        if (statusEl) {
            statusEl.textContent = '🔴';
            statusEl.title = '服务器未连接 — 审批结果无法保存';
        }
        if (list) list.innerHTML = `
            <div class="empty-state">
                <div class="icon">🔴</div>
                <p>无法连接到审批服务器</p>
                <p style="font-size:13px;color:var(--text-secondary)">
                    请确保已启动服务器（双击桌面上的「元演审批面板.bat」）<br>
                    错误: ${escapeHtml(e.message)}
                </p>
            </div>`;
    }
}

async function saveData() {
    try {
        await apiPut('/api/pending', pendingData);
    } catch (e) {
        console.warn('保存失败:', e.message);
    }
}

// ── 自动刷新 ─────────────────────────────────────

function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(() => {
        // 不自动刷新用户在编辑的时候
        const editModal = document.getElementById('edit-modal');
        if (editModal && editModal.classList.contains('active')) return;
        loadData();
    }, REFRESH_INTERVAL);
}

// ── 初始化 ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    startAutoRefresh();

    document.getElementById('pending-list').addEventListener('click', handleCardAction);
    document.getElementById('done-list').addEventListener('click', handleCardAction);

    // 刷新按钮
    document.getElementById('btn-refresh')?.addEventListener('click', () => {
        if (isDirty && !confirm('有未保存的更改，刷新将丢失。是否继续？')) {
            return;
        }
        loadData();
    });
});
