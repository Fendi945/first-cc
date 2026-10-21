// DAY1 customer result viewer + device-scoped multi-order history.
// Each order requires its own 256-bit access credential; order numbers are not authorization.
(function () {
  'use strict';
  var API = 'https://fhvhnibznphatfnbvvnb.supabase.co/functions/v1/direction-feedback-api';
  var PUBLIC_KEY = 'sb_publishable_8_ElUXtWKbEM9Of37zdYug_mdWjcV4B';
  var HISTORY_KEY = 'dayi_customer_orders_v3';
  var LEGACY_KEY = 'dayi_customer_order_v2';
  var MAX_ORDERS = 80;
  var codeRule = /^(?:DAYI|DAY1|DY)-[A-Z0-9-]{6,50}$/;
  var keyRule = /^[a-f0-9]{64}$/;
  var $ = function (id) { return document.getElementById(id); };
  var timer = null, requestInFlight = 0, active = null, generation = 0, viewed = {}, statusByCode = {};
  var book = {orders: [], activeCode: null};

  function valid(o) {
    return o && typeof o === 'object' && typeof o.code === 'string' &&
      typeof o.key === 'string' && codeRule.test(o.code) && keyRule.test(o.key);
  }
  function normalize(entry) {
    return {code: entry.code, key: entry.key,
      stored_at: Number.isFinite(entry.stored_at) && entry.stored_at > 0 ? entry.stored_at : Date.now()};
  }
  function loadHistory() {
    var saved = null, legacy = null;
    try {
      saved = JSON.parse(localStorage.getItem(HISTORY_KEY) || 'null');
      legacy = JSON.parse(localStorage.getItem(LEGACY_KEY) || 'null');
    } catch (_) { /* Treat inaccessible or corrupt local data as empty. */ }
    var entries = [], used = {};
    if (saved && Array.isArray(saved.orders)) {
      saved.orders.forEach(function (o) {
        if (valid(o) && !used[o.code] && entries.length < MAX_ORDERS) {
          entries.push(normalize(o)); used[o.code] = true;
        }
      });
    }
    if (valid(legacy) && !used[legacy.code]) {
      entries.unshift(normalize(legacy));
    }
    var selected = saved && typeof saved.activeCode === 'string' ? saved.activeCode : null;
    if (!entries.some(function (x) { return x.code === selected; })) {
      selected = valid(legacy) ? legacy.code : (entries[0] ? entries[0].code : null);
    }
    book = {orders: entries.slice(0, MAX_ORDERS), activeCode: selected};
    // Do not erase legacy order-number-only hints before the customer has recovered access.
    if (book.orders.length || (saved && Array.isArray(saved.orders))) persist();
  }
  function persist() {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(book));
      var top = book.orders.find(function (o) { return o.code === book.activeCode; });
      if (top) {
        // Keep previous viewer versions able to resume the current order.
        localStorage.setItem(LEGACY_KEY, JSON.stringify(top));
        localStorage.setItem('dayi_last_order', top.code);
      } else {
        localStorage.removeItem(LEGACY_KEY);
        localStorage.removeItem('dayi_last_order');
      }
      return true;
    } catch (_) { return false; }
  }
  function save(code, key) {
    if (!valid({code: code, key: key})) return false;
    var old = book.orders.find(function (o) { return o.code === code; });
    book.orders = book.orders.filter(function (o) { return o.code !== code; });
    book.orders.unshift({code: code, key: key, stored_at: old ? old.stored_at : Date.now()});
    book.orders = book.orders.slice(0, MAX_ORDERS);
    book.activeCode = code;
    return persist();
  }
  function cleanNavigation() {
    try {
      var u = new URL(window.location.href);
      u.searchParams.delete('new');
      u.hash = '';
      window.history.replaceState(null, '', u.pathname + u.search);
    } catch (_) { /* A failed cleanup must never block a customer result. */ }
  }
  function renderHistory() {
    ['Home', 'Result'].forEach(function (name) {
      var outer = $('savedOrders' + name), list = $('savedOrderList' + name);
      if (!outer || !list) return;
      outer.classList.toggle('hidden', book.orders.length === 0);
      list.replaceChildren();
      book.orders.forEach(function (entry) {
        var item = document.createElement('div'), details = document.createElement('div'),
          actions = document.createElement('div'), code = document.createElement('strong'),
          meta = document.createElement('span'), open = document.createElement('button'),
          remove = document.createElement('button');
        item.className = 'order-history-item';
        details.className = 'order-history-details';
        code.className = 'order-history-code';
        code.textContent = entry.code;
        meta.className = 'order-history-meta';
        var checked = statusByCode[entry.code];
        var date = new Date(entry.stored_at).toLocaleDateString('zh-CN');
        meta.textContent = (entry.code === book.activeCode ? '当前订单 · ' : '') +
          (checked ? checked + ' · ' : '') + '本设备保存于 ' + date;
        details.appendChild(code);
        details.appendChild(meta);
        actions.className = 'order-history-actions';
        open.type = 'button';
        open.className = 'primary';
        open.dataset.openOrder = entry.code;
        open.textContent = entry.code === book.activeCode && checked === '已交付' ? '查看效果图' : '查看订单';
        remove.type = 'button';
        remove.dataset.removeOrder = entry.code;
        remove.textContent = '从本设备移除';
        remove.setAttribute('aria-label', '从本设备移除订单' + entry.code);
        actions.appendChild(open);
        actions.appendChild(remove);
        item.appendChild(details);
        item.appendChild(actions);
        list.appendChild(item);
      });
    });
  }
  function state(title, description) {
    $('statusTitle').textContent = title;
    $('statusText').textContent = description;
  }
  function viewResult() {
    if (typeof window.DayiSetStep === 'function') window.DayiSetStep(8);
    else {
      document.querySelectorAll('.step').forEach(function (el) {
        el.classList.toggle('active', el.getAttribute('data-step') === '8');
      });
      $('progress').style.width = '100%';
    }
  }
  function next(delay, run) {
    clearTimeout(timer);
    if (!active || run !== generation || document.hidden) return;
    timer = setTimeout(function () { void poll(run); }, delay);
  }
  async function request(action, deliveryId) {
    if (!active) throw new Error('missing_order');
    var chosen = active;
    var body = {action: action, order_code: chosen.code, access_token: chosen.key};
    if (deliveryId) body.delivery_id = deliveryId;
    var r = await fetch(API, {
      method: 'POST',
      headers: {apikey: PUBLIC_KEY, 'Content-Type': 'application/json'},
      body: JSON.stringify(body), cache: 'no-store', signal: AbortSignal.timeout(25000)
    });
    if (!r.ok) {
      var error = new Error('result_request_failed');
      error.denied = r.status === 403 || r.status === 401;
      throw error;
    }
    return r.json();
  }
  async function showImage(url) {
    var img = $('resultImg'), timeout;
    img.referrerPolicy = 'no-referrer';
    img.src = url;
    try {
      await Promise.race([
        new Promise(function (resolve, reject) {
          if (img.complete && img.naturalWidth) { resolve(); return; }
          img.onload = resolve;
          img.onerror = function () { reject(new Error('image_unavailable')); };
        }),
        new Promise(function (_, reject) {
          timeout = setTimeout(function () { reject(new Error('image_timeout')); }, 30000);
        })
      ]);
      if (!img.naturalWidth) throw new Error('image_unavailable');
    } finally { clearTimeout(timeout); }
  }
  async function poll(run) {
    if (!active || run !== generation || document.hidden || requestInFlight === run) return;
    // Switching to a second order must not be blocked by a request for the first.
    requestInFlight = run;
    try {
      var x = await request('result');
      if (run !== generation || x.order_code !== active.code) return;
      if (x.process_status !== 'completed' || !x.image_url ||
          !Array.isArray(x.advice) || x.advice.length !== 3) {
        $('resultBox').classList.add('hidden');
        if (x.checkout_stage === 'draft') {
          statusByCode[active.code] = '尚未提交';
          state('订单尚未提交完成', '请返回原下单流程完成上传。此订单尚未完成，请不要重复付款。');
        } else if (x.payment_status === 'pending_verification') {
          statusByCode[active.code] = '待核实付款';
          state('订单已保存，等待核实付款', '不必重新下单。页面会自动检查交付结果。');
        } else {
          statusByCode[active.code] = '准备中';
          state('正在查看你的院子', '反馈正在准备中。完成后页面会自动显示效果图与设计建议。');
        }
        renderHistory();
        next(15000, run);
        return;
      }
      await showImage(x.image_url);
      if (run !== generation) return;
      var advice = $('advice'); advice.replaceChildren();
      x.advice.forEach(function (t, i) {
        var item = document.createElement('div'), n = document.createElement('b');
        n.textContent = '0' + (i + 1);
        item.appendChild(n);
        item.appendChild(document.createTextNode('｜' + String(t)));
        advice.appendChild(item);
      });
      $('resultBox').classList.remove('hidden');
      statusByCode[active.code] = '已交付';
      state('你的方向反馈已完成', '效果图和三条设计建议已加载。');
      renderHistory();
      if (x.delivery_id && !viewed[active.code + ':' + x.delivery_id] && !document.hidden) {
        var id = active.code + ':' + x.delivery_id;
        viewed[id] = true;
        request('result_seen', x.delivery_id).catch(function () { delete viewed[id]; });
      }
      // Check occasionally for a revised delivery while the page remains open.
      next(60000, run);
    } catch (error) {
      if (run !== generation) return;
      if ($('resultBox').classList.contains('hidden')) {
        state(error.denied ? '无法验证此订单的访问权限' : '连接暂时中断',
          error.denied ? '请使用已保存订单的原浏览器或完整安全链接；不必再次付款。'
            : '页面会自动重试，你也可以稍后重新打开原网址。');
      }
      if (!error.denied) next(30000, run);
    } finally {
      if (requestInFlight === run) requestInFlight = 0;
    }
  }
  // Return whether the credential was persisted on this device.
  function start(code, key, options) {
    if (!valid({code: code, key: key})) return false;
    var stored = save(code, key);
    generation += 1;
    clearTimeout(timer);
    active = {code: code, key: key};
    $('orderCodeText').textContent = code;
    $('resultBox').classList.add('hidden');
    state('正在读取本次订单', '正在检查交付结果…');
    if (!options || !options.fromLink) cleanNavigation();
    renderHistory();
    viewResult();
    void poll(generation);
    return stored;
  }
  function removeOrder(code) {
    var matches = book.orders.some(function (x) { return x.code === code; });
    if (!matches || !confirm('仅从本设备清除这笔订单的访问记录？不会取消订单或删除服务器上的效果图。')) return;
    book.orders = book.orders.filter(function (x) { return x.code !== code; });
    if (book.activeCode === code) {
      book.activeCode = book.orders[0] ? book.orders[0].code : null;
      active = null;
      generation++;
      clearTimeout(timer);
      persist();
      renderHistory();
      cleanNavigation();
      if (book.activeCode) {
        var chosen = book.orders[0];
        start(chosen.code, chosen.key);
      } else {
        window.location.assign('/direction-feedback/?new=1');
      }
    } else {
      persist();
      renderHistory();
    }
  }
  function handleHistoryClick(event) {
    var button = event.target.closest('button');
    if (!button) return;
    if (button.dataset.openOrder) {
      var entry = book.orders.find(function (x) { return x.code === button.dataset.openOrder; });
      if (entry) start(entry.code, entry.key);
    } else if (button.dataset.removeOrder) {
      removeOrder(button.dataset.removeOrder);
    }
  }
  ['savedOrderListHome', 'savedOrderListResult'].forEach(function (name) {
    var el = $(name);
    if (el) el.addEventListener('click', handleHistoryClick);
  });
  window.DayiResultViewer = {start: start, listSaved: function () {
    return book.orders.map(function (o) { return o.code; }); // Never expose credentials through this listing.
  }};

  loadHistory();
  renderHistory();
  var fragment = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  var fromLink = fragment.has('order') || fragment.has('key');
  var goNew = new URLSearchParams(window.location.search).get('new') === '1';
  if (fromLink) {
    var linkedCode = fragment.get('order') || '', linkedKey = fragment.get('key') || '';
    if (valid({code: linkedCode, key: linkedKey})) start(linkedCode, linkedKey, {fromLink: true});
    else {
      viewResult();
      state('订单链接不完整', '请使用完整的安全订单链接。');
    }
  } else if (!goNew) {
    var recent = book.orders.find(function (o) { return o.code === book.activeCode; });
    if (recent) start(recent.code, recent.key);
    else {
      var oldCode = false;
      try { oldCode = !!localStorage.getItem('dayi_last_order'); } catch (_) { /* no storage */ }
      if (oldCode && $('dayiRecoverHint')) {
        $('dayiRecoverHint').textContent =
          '旧版订单只保存了订单号。请勿再次付款；使用完整结果链接打开一次后，以后可在本设备的“我的订单”里查看。';
        $('dayiRecoverHint').classList.remove('hidden');
      }
    }
  }
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden && active) {
      clearTimeout(timer);
      void poll(generation);
    }
  });
})();