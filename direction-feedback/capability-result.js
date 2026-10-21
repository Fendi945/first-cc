// DAY1 customer result viewer: same-page auto resume + secure capability-based polling.
// Only an order owner token or a separately issued result link grants access.
(function () {
  'use strict';
  var API = 'https://fhvhnibznphatfnbvvnb.supabase.co/functions/v1/direction-feedback-api';
  var PUBLIC_KEY = 'sb_publishable_8_ElUXtWKbEM9Of37zdYug_mdWjcV4B';
  var STORAGE_KEY = 'dayi_customer_order_v2';
  var codeRule = /^(?:DAYI|DAY1|DY)-[A-Z0-9-]{6,50}$/;
  var tokenRule = /^[a-f0-9]{64}$/;
  var $ = function (id) { return document.getElementById(id); };
  var timer = null, pending = false, active = null, generation = 0, viewed = {};

  function readSaved() {
    try {
      var data = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
      return data && codeRule.test(data.code) && tokenRule.test(data.key)
        ? {code: data.code, key: data.key} : null;
    } catch (_) { return null; }
  }
  function save(code, key) {
    if (!codeRule.test(code) || !tokenRule.test(key)) return false;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({code: code, key: key, stored_at: Date.now()}));
      // Compatibility with older order UI. An order code alone is NOT a credential.
      localStorage.setItem('dayi_last_order', code);
    } catch (_) { /* Private-mode browsers may refuse persistent storage. */ }
    return true;
  }
  function viewResult() {
    if (typeof window.DayiSetStep === 'function') {
      window.DayiSetStep(8);
    } else {
      document.querySelectorAll('.step').forEach(function (el) {
        el.classList.toggle('active', el.getAttribute('data-step') === '8');
      });
      $('progress').style.width = '100%';
    }
  }
  function next(delay, run) {
    clearTimeout(timer);
    if (!active || run !== generation) return;
    if (document.hidden) return;
    timer = setTimeout(function () { void poll(run); }, delay);
  }
  async function request(action, deliveryId) {
    if (!active) throw new Error('missing_order');
    var payload = {action: action, order_code: active.code, access_token: active.key};
    if (deliveryId) payload.delivery_id = deliveryId;
    var r = await fetch(API, {
      method: 'POST',
      headers: {apikey: PUBLIC_KEY, 'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
      cache: 'no-store',
      signal: AbortSignal.timeout(25000)
    });
    if (!r.ok) {
      var err = new Error('result_request_failed');
      err.denied = r.status === 403;
      throw err;
    }
    return r.json();
  }
  function state(title, description) {
    $('statusTitle').textContent = title;
    $('statusText').textContent = description;
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
    if (pending || !active || run !== generation || document.hidden) return;
    pending = true;
    try {
      var x = await request('result');
      if (run !== generation || x.order_code !== active.code) return;
      if (x.process_status !== 'completed' || !x.image_url || !Array.isArray(x.advice) || x.advice.length !== 3) {
        $('resultBox').classList.add('hidden');
        if (x.checkout_stage === 'draft') {
          state('订单尚未提交完成', '这笔订单暂未完成照片与付款凭证提交，请返回原下单页面完成步骤，避免重复付款。');
        } else if (x.payment_status === 'pending_verification') {
          state('订单已保存，等待核实付款', '不必重新下单。系统将在这里自动检查结果，请保留此页面。');
        } else {
          state('正在查看你的院子', '反馈还在准备中。完成后，这个页面会自动刷新显示效果图。');
        }
        next(15000, run);
        return;
      }
      await showImage(x.image_url);
      if (run !== generation) return;
      var advice = $('advice'); advice.replaceChildren();
      x.advice.forEach(function (t, i) {
        var line = document.createElement('div'), n = document.createElement('b');
        n.textContent = '0' + (i + 1);
        line.appendChild(n);
        line.appendChild(document.createTextNode('｜' + String(t)));
        advice.appendChild(line);
      });
      $('resultBox').classList.remove('hidden');
      state('你的方向反馈已完成', '效果图和三条设计建议已更新，可以直接查看。');
      if (x.delivery_id && !viewed[x.delivery_id] && !document.hidden) {
        viewed[x.delivery_id] = true;
        // Viewing acknowledgement is best effort; never hide a successfully loaded result.
        request('result_seen', x.delivery_id).catch(function () { delete viewed[x.delivery_id]; });
      }
      // Results are immutable per delivery; reload to inspect a new version.
      clearTimeout(timer);
    } catch (error) {
      if (run !== generation) return;
      if ($('resultBox').classList.contains('hidden')) {
        state(error.denied ? '无法验证订单访问权限' : '连接暂时中断',
          error.denied ? '请使用原浏览器或有效的专用结果链接；不必重新付款。'
            : '系统会自动重试，你也可以稍后重新打开这个页面。');
      }
      if (!error.denied) next(30000, run);
    } finally {
      pending = false;
    }
  }
  function start(code, key) {
    if (!save(code, key)) return false;
    generation += 1;
    clearTimeout(timer);
    active = {code: code, key: key};
    $('orderCodeText').textContent = code;
    $('resultBox').classList.add('hidden');
    state('正在读取本次订单', '正在检查交付结果…');
    viewResult();
    void poll(generation);
    return true;
  }
  window.DayiResultViewer = { start: start };

  var hash = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  var fromLink = hash.has('order') || hash.has('key');
  var goNew = new URLSearchParams(window.location.search).get('new') === '1';
  if (fromLink) {
    if (!start(hash.get('order') || '', hash.get('key') || '')) {
      viewResult();
      state('订单链接不完整', '请使用完整的结果链接。');
    }
  } else if (!goNew) {
    var saved = readSaved();
    if (saved) start(saved.code, saved.key);
    else if ((function () { try { return !!localStorage.getItem('dayi_last_order'); } catch (_) { return false; } })()) {
      // Legacy orders stored only the code. Do not grant private photo access with a guessable code.
      var hint = document.getElementById('dayiRecoverHint');
      if (hint) {
        hint.textContent = '检测到此前的订单。旧版网站只保存了订单号，不能直接读取私人效果图。请勿再次付款；使用已收到的完整结果链接打开一次后，以后在本设备打开此网址就会自动显示。';
        hint.classList.remove('hidden');
      }
    }
  }
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden && active && $('resultBox').classList.contains('hidden')) {
      clearTimeout(timer);
      void poll(generation);
    }
  });
})();