/* 🧠 元演心智 · 审批面板交互逻辑 */

// ── 配置 ──────────────────────────────────────────
const PENDING_JSON_PATH = '待审批.json';  // 实际路径通过 .bat 启动时传入
let pendingData = [];

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
            <div style="margin-top:24px;padding:12px 0;border-top:1px solid var(--border-glass);font-size:13px;color:var(--text-secondary)">
            📋 已处理 (${doneItems.length})
            </div>
            ${doneItems.map(item => renderCard(item)).join('')}`;
    }
}

function renderCard(item) {
    const title = item.suggested_title || item.summary || item.original_text.slice(0, 40);
    return `
    <div class="card ${cardStatusClass(item)}" data-id="${item.id}">
        <div class="card-header">
            <div class="card-title">${item.output_tag === 'video' ? '📹' : item.output_tag === 'article' ? '📝' : item.output_tag === 'tool' ? '🔧' : '📄'} ${escapeHtml(title)}</div>
            <div class="card-tags">
                ${tagHtml(item.output_tag)}
                <span class="tag" style="background:rgba(255,255,255,0.05);color:var(--text-secondary)">${layerLabel(item.layer)}</span>
            </div>
        </div>
        <div class="card-meta">
            <span>📅 ${item.source_date}</span>
            <span>🎯 ${item.suitable_platform || '待定'}</span>
            ${item.status !== 'pending' ? `<span>${item.status === 'approved' ? '✅ 已通过' : '⏭️ 已跳过'}</span>` : ''}
        </div>
        <div class="card-text" onclick="this.classList.toggle('expanded')">
            ${escapeHtml(item.original_text)}
        </div>
        ${item.status === 'pending' ? `
        <div class="card-actions">
            <button class="btn btn-approve" onclick="approveItem('${item.id}')">✅ 通过 → 进入生产</button>
            <button class="btn btn-edit" onclick="editItem('${item.id}')">✏️ 修改</button>
            <button class="btn btn-skip" onclick="skipItem('${item.id}')">🗑️ 跳过</button>
        </div>` : ''}
    </div>`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ── 操作 ──────────────────────────────────────────
function approveItem(id) {
    const item = pendingData.find(i => i.id === id);
    if (item) {
        item.status = 'approved';
        item.approved_at = new Date().toLocaleString('zh-CN');
        saveData();
        render();
    }
}

function skipItem(id) {
    const item = pendingData.find(i => i.id === id);
    if (item) {
        item.status = 'skipped';
        item.skipped_at = new Date().toLocaleString('zh-CN');
        saveData();
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

function saveEdit() {
    const modal = document.getElementById('edit-modal');
    const id = modal.dataset.editId;
    const item = pendingData.find(i => i.id === id);
    if (!item) return;
    try {
        const edited = JSON.parse(document.getElementById('edit-textarea').value);
        if (edited.suggested_title) item.suggested_title = edited.suggested_title;
        if (edited.summary) item.summary = edited.summary;
        if (edited.original_text) item.original_text = edited.original_text;
    } catch(e) { alert('JSON 格式错误'); return; }
    modal.classList.remove('active');
    saveData();
    render();
}

function approveAll() {
    const pending = pendingData.filter(i => i.status === 'pending');
    if (pending.length === 0) return;
    document.getElementById('confirm-modal').classList.add('active');
}

function confirmApproveAll() {
    pendingData.forEach(i => {
        if (i.status === 'pending') {
            i.status = 'approved';
            i.approved_at = new Date().toLocaleString('zh-CN');
        }
    });
    document.getElementById('confirm-modal').classList.remove('active');
    saveData();
    render();
}

// ── 数据读写 ──────────────────────────────────────
async function loadData() {
    try {
        // 尝试从查询参数获取 JSON 路径
        const params = new URLSearchParams(window.location.search);
        const jsonPath = params.get('json') || '待审批.json';

        const resp = await fetch(jsonPath);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        pendingData = Array.isArray(data) ? data : [];
        render();
    } catch(e) {
        console.warn('加载待审批数据失败（首次使用或文件不存在）:', e.message);
        // 创建示例数据
        pendingData = getSampleData();
        render();
        document.querySelector('.empty-state p:last-child')?.textContent =
            '提示：尚未检测到真实数据，当前显示示例';
    }
}

function getSampleData() {
    const today = new Date().toISOString().slice(0, 10);
    return [
        {
            id: `${today}-0`,
            source_date: today,
            original_text: "今天发现水景视频的评论区很多人问过滤系统到底要不要做，感觉这是个高频痛点",
            layer: "event",
            output_tag: "video",
            summary: "过滤系统高频问题",
            suggested_title: "锦鲤池过滤系统到底要不要做？一次说清楚",
            suitable_platform: "视频号",
            status: "pending",
            created_at: new Date().toLocaleString('zh-CN'),
        },
        {
            id: `${today}-1`,
            source_date: today,
            original_text: "庭院预算分配：土建40%，植物30%，硬景20%，预留10%应急",
            layer: "ability",
            output_tag: "article",
            summary: "预算分配公式",
            suggested_title: "家庭庭院预算分配的5个误区",
            suitable_platform: "公众号",
            status: "pending",
            created_at: new Date().toLocaleString('zh-CN'),
        },
        {
            id: `${today}-2`,
            source_date: today,
            original_text: "用'你家的院子'开头比'大家好'完播率高30%",
            layer: "ability",
            output_tag: "tool",
            summary: "口播开头公式",
            suggested_title: "",
            suitable_platform: "",
            status: "pending",
            created_at: new Date().toLocaleString('zh-CN'),
        },
    ];
}

async function saveData() {
    try {
        const resp = await fetch(PENDING_JSON_PATH, {
            method: 'PUT',
            body: JSON.stringify(pendingData, null, 2),
        });
        if (!resp.ok) console.warn('保存失败：HTTP', resp.status);
    } catch(e) {
        console.warn('保存失败（file:// 模式不支持写入，需要本地服务器）:', e.message);
        // file:// 模式下不阻塞交互
    }
}

// ── 初始化 ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadData();

    // 刷新按钮
    document.getElementById('btn-refresh')?.addEventListener('click', () => {
        loadData();
    });
});
