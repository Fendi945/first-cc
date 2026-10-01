// Compatibility viewer for existing capability-based deliveries on the public customer route.
// The fragment is a bearer credential. Do not send it to analytics or store it outside this URL.
(function(){
  var hash=new URLSearchParams(window.location.hash.slice(1));
  if(!hash.has('order')&&!hash.has('key'))return;

  var api='https://fhvhnibznphatfnbvvnb.supabase.co/functions/v1/direction-feedback-api';
  var anon='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZodmhuaWJ6bnBoYXRmbmJ2dm5iIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk3MzMzNDgsImV4cCI6MjEwNTMwOTM0OH0.OSuLOzcuMLmPnZ17EMaz6lXrOY4CGgBJWMV96HHg1LU';
  var code=hash.get('order')||'',key=hash.get('key')||'';
  var $=function(id){return document.getElementById(id)};
  var timer,inFlight=false,acknowledged=0;

  document.querySelectorAll('.step').forEach(function(step){step.classList.toggle('active',step.getAttribute('data-step')==='8')});
  $('progress').style.width='100%';
  $('orderCodeText').textContent=code;
  $('resultBox').classList.add('hidden');
  if(!/^(?:DAYI|DAY1|DY)-[A-Z0-9-]{6,50}$/.test(code)||!/^[a-f0-9]{64}$/.test(key)){
    $('statusTitle').textContent='订单链接不完整';
    $('statusText').textContent='请使用完整的订单结果链接。';
    return;
  }

  function schedule(){clearTimeout(timer);}
  async function request(action,deliveryId){
    var body={action:action,order_code:code,access_token:key};
    if(deliveryId)body.delivery_id=deliveryId;
    var response=await fetch(api,{
      method:'POST',headers:{apikey:anon,Authorization:'Bearer '+anon,'Content-Type':'application/json'},
      body:JSON.stringify(body),signal:AbortSignal.timeout(25000)
    });
    if(!response.ok){var error=new Error('暂时无法读取这笔订单，请稍后重试。');error.denied=response.status===403;throw error;}
    return response.json();
  }
  async function decodeImage(url){
    var img=$('resultImg'),timeout;
    img.referrerPolicy='no-referrer';
    img.src=url;
    try{
      await Promise.race([
        new Promise(function(resolve,reject){
          if(img.complete&&img.naturalWidth){resolve();return}
          img.onload=function(){resolve()};
          img.onerror=function(){reject(new Error('image_unavailable'))};
        }),
        new Promise(function(_,reject){timeout=setTimeout(function(){reject(new Error('image_timeout'))},30000)})
      ]);
      if(!img.complete||!img.naturalWidth)throw new Error('image_unavailable');
    }finally{clearTimeout(timeout);}
  }
  async function poll(){
    if(inFlight)return;
    clearTimeout(timer);inFlight=true;
    $('statusTitle').textContent='正在读取本次订单';
    $('statusText').textContent='正在检查交付结果…';
    try{
      var x=await request('result');
      if(x.order_code!==code)throw new Error('order_mismatch');
      if(x.process_status!=='completed'||!x.image_url||!Array.isArray(x.advice)||x.advice.length!==3){
        $('resultBox').classList.add('hidden');
        $('statusTitle').textContent='结果正在准备中';
        $('statusText').textContent='这笔订单已保存，请稍后刷新查看。';
        schedule();return;
      }
      await decodeImage(x.image_url);
      var advice=$('advice');advice.replaceChildren();
      x.advice.forEach(function(t,i){
        var row=document.createElement('div'),number=document.createElement('b');
        number.textContent='0'+(i+1);row.appendChild(number);
        row.appendChild(document.createTextNode('｜'+String(t)));advice.appendChild(row);
      });
      $('resultBox').classList.remove('hidden');
      $('statusTitle').textContent='你的方向反馈已完成';
      $('statusText').textContent='图片和三条建议已加载。';
      if(!x.delivery_id||document.hidden||acknowledged===x.delivery_id){if(document.hidden)schedule();return;}
      await new Promise(function(resolve){requestAnimationFrame(function(){requestAnimationFrame(resolve)})});
      if(document.hidden){schedule();return;}
      await request('result_seen',x.delivery_id);
      acknowledged=x.delivery_id;
    }catch(error){
      if($('resultBox').classList.contains('hidden')){
        $('statusTitle').textContent=error.denied?'订单链接暂时无法读取':'暂时无法读取反馈';
        $('statusText').textContent=error.denied?'链接可能已过期，请向大一索取新的结果链接。':'请稍后刷新页面重试。';
      }else{
        $('statusText').textContent='图片已显示，正在重试查看回执。';
      }
      schedule();
    }finally{inFlight=false;}
  }
  poll();
})();
