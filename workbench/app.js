/* DAY1 Workbench V1.0 — private client-side interface, server-enforced admin authorization.
   NO private service keys, customer records, or passwords live in this source.
   All sensitive operations go through the existing Supabase Edge Function. */
(function () {
"use strict";
const BASE="https://fhvhnibznphatfnbvvnb.supabase.co";
const PUB="sb_publishable_8_ElUXtWKbEM9Of37zdYug_mdWjcV4B";
const ADMIN=BASE+"/functions/v1/direction-feedback-api";
const KEY="dayi-workbench-session-v1";
const $=id=>document.getElementById(id);
const S={session:null,approved:false,tab:"home",orders:[],selected:null,filter:"all",offset:0,loading:false,images:null,history:null};
const STATES={pending_verification:"待核实收款",confirmed:"已确认收款",verified:"已核实",paid:"已收款",rejected:"未通过",waiting_payment_verification:"待核实付款",waiting_payment:"待付款",queued:"排队中",processing:"处理中",running:"生成中",completed:"已交付",failed:"待处理异常"};
const status=x=>STATES[x]||x||"—";
const safeText=x=>x===undefined||x===null||x===""?"—":String(x);
function time(x){if(!x)return "—";const d=new Date(x);return isNaN(d.getTime())?String(x):d.toLocaleString("zh-CN",{year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"});}
function note(text,error=false){const e=$("notice");e.textContent=String(text);e.classList.toggle("is-error",error);e.hidden=false;clearTimeout(note.timer);note.timer=setTimeout(()=>{e.hidden=true},6000);}
function authMessage(msg,error=false){$("authMessage").textContent=msg;$("authMessage").style.color=error?"#b53d2e":"";}
function el(tag,className,text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=String(text);return node;}
function put(parent,...nodes){nodes.forEach(n=>parent.appendChild(n));return parent;}
function item(tag,label,value){const div=el("div","fact"),k=el("label","",label),v=el("div","",safeText(value));put(div,k,v);return div;}
function button(label,fn,className="btn outline small"){const b=el("button",className,label);b.type="button";b.addEventListener("click",fn);return b;}
function clearCredentials(){S.session=null;S.approved=false;try{sessionStorage.removeItem(KEY)}catch(_){/* storage unavailable */}}
function storedSession(){try{const d=JSON.parse(sessionStorage.getItem(KEY)||"null");return d&&typeof d.access_token==="string"&&typeof d.refresh_token==="string"?d:null}catch(_){return null}}
function remember(value){S.session=value;try{if(value)sessionStorage.setItem(KEY,JSON.stringify(value));else sessionStorage.removeItem(KEY)}catch(_){}}
async function authRequest(path,method="POST",body,auth){
 const headers={"apikey":PUB};if(body!==undefined)headers["Content-Type"]="application/json";if(auth)headers.Authorization="Bearer "+auth;
 const r=await fetch(BASE+path,{method,headers,body:body===undefined?undefined:JSON.stringify(body),cache:"no-store"});
 let data={};try{data=await r.json()}catch(_){}
 if(!r.ok)throw Object.assign(new Error(data.error_description||data.msg||data.message||data.error||"身份验证失败（"+r.status+"）"),{http:r.status});
 return data;
}
async function accessToken(){
 if(!S.session)throw new Error("请先登录");
 if(S.session.expires_at>Date.now()+60000)return S.session.access_token;
 try{
  const d=await authRequest("/auth/v1/token?grant_type=refresh_token","POST",{refresh_token:S.session.refresh_token});
  if(!d.access_token||!d.refresh_token)throw new Error("会话刷新失败");
  remember({access_token:d.access_token,refresh_token:d.refresh_token,expires_at:Date.now()+(d.expires_in||3600)*1000});
  return S.session.access_token;
 }catch(e){signOut("登录已失效，请重新登录。");throw e;}
}
async function callAdmin(action,data={},file){
 const token=await accessToken(),body={action,...data},headers={"apikey":PUB,"Authorization":"Bearer "+token};
 let payload;
 if(file){
  payload=new FormData();for(const [k,v] of Object.entries(body))payload.append(k,v);
  payload.append("file",file,file.name);
 }else{headers["Content-Type"]="application/json";payload=JSON.stringify(body);}
 const r=await fetch(ADMIN,{method:"POST",headers,body:payload,cache:"no-store"});
 let result={};try{result=await r.json()}catch(_){}
 if(!r.ok){
  if(r.status===401||r.status===403)signOut("管理员验证已失效，请重新登录。");
  throw Object.assign(new Error(result.message||result.error||"请求失败（"+r.status+"）"),{http:r.status});
 }
 return result;
}
function showAuth(which="login"){
 $("app").hidden=true;$("authView").hidden=false;
 ["loginForm","forgotForm","newPasswordForm"].forEach(id=>$(id).hidden=id!==({"login":"loginForm","forgot":"forgotForm","reset":"newPasswordForm"}[which]));
 if(which==="login")$("password").value="";
}
function signOut(message){
 clearCredentials();S.orders=[];S.selected=null;S.images=null;S.history=null;
 $("orderList").replaceChildren();$("orderDetail").replaceChildren();
 showAuth("login");authMessage(message||"登录后才可访问客户资料。");
}
async function verify(){
 // The existing protected admin API verifies the JWT AND the server-side administrator allowlist.
 await callAdmin("admin_business_status");
 S.approved=true;
 $("authView").hidden=true;$("app").hidden=false;
 $("userEmail").textContent=S.session?.email||"已授权账号";
 choose("home");
}
async function login(event){
 event.preventDefault();const email=$("email").value.trim(),password=$("password").value;
 if(!email||!password)return;
 const b=$("loginButton");b.disabled=true;authMessage("正在核实管理员身份…");
 try{
  const d=await authRequest("/auth/v1/token?grant_type=password","POST",{email,password});
  if(!d.access_token||!d.refresh_token)throw new Error("身份验证结果不完整");
  remember({access_token:d.access_token,refresh_token:d.refresh_token,expires_at:Date.now()+(d.expires_in||3600)*1000,email});
  await verify();$("password").value="";
 }catch(e){if(S.approved===false){clearCredentials();showAuth("login")}authMessage("登录失败："+e.message,true)}
 finally{b.disabled=false}
}
async function forgot(e){
 e.preventDefault();const email=$("resetEmail").value.trim();if(!email)return;
 authMessage("正在发送重置邮件…");
 try{
  const dest=window.location.origin+"/workbench/";
  await authRequest("/auth/v1/recover?redirect_to="+encodeURIComponent(dest),"POST",{email});
  authMessage("已请求发送重置邮件。请查收管理员邮箱；如邮件跳转不正确，需要核对 Supabase Auth 的允许跳转域名。");
 }catch(err){authMessage("重置邮件发送失败："+err.message,true)}
}
let resetToken=null;
function checkRecovery(){
 const hash=new URLSearchParams(window.location.hash.slice(1));
 if(hash.get("type")==="recovery"&&hash.get("access_token")){
  resetToken=hash.get("access_token");
  window.history.replaceState(null,"",window.location.pathname);
  showAuth("reset");authMessage("请设置至少12位的新密码。");
  return true;
 }
 const error=hash.get("error_description")||hash.get("error");
 if(error){showAuth("login");authMessage("邮件链接无效："+error,true);window.history.replaceState(null,"",window.location.pathname);}
 return false;
}
async function changePassword(e){
 e.preventDefault();const pw=$("newPassword").value,confirm=$("confirmPassword").value;
 if(pw.length<12||pw!==confirm){authMessage("请填写两次一致且不少于12位的密码。",true);return}
 try{await authRequest("/auth/v1/user","PUT",{password:pw},resetToken);resetToken=null;showAuth("login");authMessage("密码更新成功，请重新登录。")}
 catch(err){authMessage("更新密码失败："+err.message,true)}
}
function choose(tab){
 if(!S.approved)return;
 if(!["home","product","business","project","knowledge"].includes(tab))tab="home";
 S.tab=tab;
 document.querySelectorAll("[data-view]").forEach(x=>x.hidden=x.dataset.view!==tab);
 document.querySelectorAll("[data-tab]").forEach(x=>{x.classList.toggle("selected",x.dataset.tab===tab);x.setAttribute("aria-current",x.dataset.tab===tab?"page":"false")});
 if(tab==="business")showBusinessModule("overview");
 if(tab==="product")showProductModule("overview");
 if(tab==="home")void loadHomeQueue();
}
function showProductModule(which){
 if(!S.approved)return;
 if(S.tab!=="product")choose("product");
 const available={overview:"productOverview",consult:"productConsult",design:"productDesign",build:"productBuild",digital:"productDigital"};
 const wanted=Object.prototype.hasOwnProperty.call(available,which)?which:"overview";
 Object.values(available).forEach(id=>$(id).hidden=true);
 $(available[wanted]).hidden=false;
 S.productModule=wanted;
 // Switching between service descriptions should not touch order state
 // or perform any payment/fulfillment operation.
}
const BUSINESS_CATEGORIES={"customers":["客户","市场需求","客户资料与客户关系，将在建立安全的客户主档后接入。"],"opportunities":["商机","市场需求","管理有效线索、咨询转化与成交机会，尚未接入。"],"channels":["渠道","市场需求","展示真实获客渠道数据，尚未接入。"],"retention":["复购信号","市场需求","基于真实客户与历史订单分析复购，尚未接入。"],"sales":["销售","交易履行","基于真实到账的销售流水与收入尚未接入。"],"inventory":["库存","交易履行","实物商品、材料与库存数据尚未接入。"],"allocation":["分配","交易履行","履约任务与资源分配尚未接入。"],"revenue":["收入健康度","经营状态","需要真实到账与支出数据，不能展示模拟收入。"],"exceptions":["例外事项","经营状态","集中管理异常订单与特殊业务流程，尚未接入。"],"forecast":["预测","经营状态","预测需要经过核实的历史数据，尚未接入。"],"daily":["日结","经营状态","每日订单、收款与交付的正式日结尚未接入。"]};
function showBusinessModule(which){
 if(!S.approved)return;
 if(S.tab!=="business")choose("business");
 ["businessOverview","businessOrdersIndex","businessPlanned","businessOrders"].forEach(id=>$(id).hidden=true);
 const key=which==="orders"?"orders":which==="feedback"?"feedback":BUSINESS_CATEGORIES[which]?which:"overview";
 S.businessModule=key;
 if(key==="overview")$("businessOverview").hidden=false;
 else if(key==="orders")$("businessOrdersIndex").hidden=false;
 else if(key==="feedback"){
  $("businessOrders").hidden=false;
  if(!S.orders.length)void loadOrders();
 }else{
  $("businessPlanned").hidden=false;
  const [label,group,description]=BUSINESS_CATEGORIES[key];
  $("businessPlannedTitle").textContent=label;
  $("businessPlannedGroup").textContent=group+" / "+label;
  $("businessPlannedIntro").textContent=description;
 }
}
async function loadHomeQueue(){
 if(!S.approved)return;
 const list=$("homeQueue");
 list.replaceChildren();
 const busy=el("div","queue-item");
 put(busy,el("span","queue-no","—"),el("span","","正在读取真实订单…"),el("span","queue-context","即时反馈订单"),el("span","queue-state","连接中"));
 list.appendChild(busy);
 try{
  const [pending,processing]=await Promise.all([
   callAdmin("admin_business_orders",{filter:"pending",offset:0}),
   callAdmin("admin_business_orders",{filter:"processing",offset:0})
  ]);
  if(!S.approved)return;
  if(!Array.isArray(pending.orders)||!Array.isArray(processing.orders))throw new Error("订单格式不正确");
  const queue=[
   ...pending.orders.map(o=>({order:o,task:"核实收款 · "+safeText(o.order_code),label:"待确认",filter:"pending"})),
   ...processing.orders.map(o=>({order:o,task:"跟进效果图 · "+safeText(o.order_code),label:"待处理",filter:"processing"}))
  ].filter(x=>x.order&&x.order.order_code).slice(0,3);
  list.replaceChildren();
  if(queue.length){
   queue.forEach((entry,i)=>{
    const row=el("div","queue-item"),go=el("button","",entry.task);
    go.type="button";
    go.addEventListener("click",()=>{
     S.filter=entry.filter;$("orderFilter").value=entry.filter;
     S.selected=entry.order.order_code;S.offset=0;S.orders=[];
     showBusinessModule("feedback");
    });
    put(row,el("span","queue-no",String(i+1).padStart(2,"0")),go,el("span","queue-context","经营 · 即时反馈订单"),el("span","queue-state",entry.label));
    list.appendChild(row);
   });
  }else{
   const row=el("div","queue-item");
   put(row,el("span","queue-no","—"),el("span","","目前没有待核实付款或待处理交付的订单。"),el("span","queue-context","经营 · 即时反馈"),el("span","queue-state","无需处理"));
   list.appendChild(row);
  }
  const p=pending.orders.length,w=processing.orders.length;
  $("homeInsightTitle").textContent=p?"先核实实际收款，再安排交付。":w?"优先完成已付款订单的交付。":"当前没有待处理订单。";
  $("homeInsightText").textContent="最近最多25笔待核实订单："+p+" 笔；最近最多25笔处理中订单："+w+" 笔。只有实际到账才能确认付款。";
  $("homeBusinessCard").textContent=p||w?"近期待处理订单："+(p+w)+" 笔（每类最多25笔）":"即时反馈订单已接入";
 }catch(error){
  if(!S.approved)return;
  list.replaceChildren();
  const row=el("div","queue-item");
  put(row,el("span","queue-no","!"),el("span","","当前无法读取订单，请进入经营模块重试。"),el("span","queue-context","连接异常"),el("span","queue-state","重试"));
  list.appendChild(row);
  $("homeInsightTitle").textContent="订单状态暂时不可用。";
  $("homeInsightText").textContent="当前未取得真实数据，不展示推测的订单数量。";
 }
}
function counts(orders){
 $("countAll").textContent=orders.length;
 $("countPending").textContent=orders.filter(x=>x.payment_status==="pending_verification").length;
 $("countCompleted").textContent=orders.filter(x=>x.process_status==="completed").length;
}
async function loadOrders(preserve=true){
 if(S.loading||!S.approved)return;
 S.loading=true;$("refreshOrders").disabled=true;$("pageStatus").textContent="正在读取真实订单…";
 if(!preserve)S.selected=null;
 try{
  const x=await callAdmin("admin_business_orders",{filter:S.filter,offset:S.offset});
  if(!Array.isArray(x.orders))throw new Error("订单接口返回格式不正确");
  S.orders=x.orders;
  $("pageStatus").textContent="当前为服务器第 "+(Math.floor(S.offset/25)+1)+" 页。统计及搜索仅针对本页，最多显示25笔；数据不会公开。";
  $("pageLabel").textContent="第 "+(Math.floor(S.offset/25)+1)+" 页 · "+S.orders.length+" 笔";
  $("prevPage").disabled=S.offset<=0;
  $("nextPage").disabled=S.orders.length<25;
  counts(S.orders);
  renderOrders();
  const retained=S.orders.find(x=>x.order_code===S.selected);
  if(retained)void selectOrder(retained.order_code);
  else if(S.orders.length)void selectOrder(S.orders[0].order_code);
  else{$("orderDetail").replaceChildren(el("p","muted","本页暂时没有符合条件的订单。"))}
 }catch(err){$("pageStatus").textContent="订单加载失败："+err.message;note("读取真实订单失败："+err.message,true)}
 finally{S.loading=false;$("refreshOrders").disabled=false}
}
function renderOrders(){
 const dest=$("orderList");dest.replaceChildren();
 const term=$("orderSearch").value.trim().toLowerCase();
 const list=S.orders.filter(o=>!term||String(o.order_code||"").toLowerCase().includes(term));
 if(!list.length){dest.appendChild(el("div","empty",S.orders.length?"本页没有匹配的订单。":"本页没有订单。"));return}
 list.forEach(o=>{
  const card=el("button","order"+(o.order_code===S.selected?" active":""));
  card.type="button";
  const row=el("div","order-top");
  put(row,el("strong","order-name",safeText(o.order_code)),el("span","status "+(o.process_status==="completed"?"complete":o.payment_status==="pending_verification"?"waiting":""),status(o.process_status)));
  put(card,row,el("div","small muted",time(o.created_at)+" · "+status(o.payment_status)),el("div","small",String(o.style||"未填写风格")+" · "+String(o.yard_size||"未填写面积")));
  card.addEventListener("click",()=>void selectOrder(o.order_code));
  dest.appendChild(card);
 });
}
function renderImages(info){
 const wrapper=$("images");if(!wrapper)return;wrapper.replaceChildren();
 const list=[["庭院原始照片",info?.yard],["付款凭证",info?.proof]].filter(x=>x[1]);
 if(!list.length){wrapper.appendChild(el("p","muted small","暂时无法读取图片或尚未上传。"));return}
 const box=el("div","photos");
 list.forEach(([label,url])=>{
  if(!/^https:\/\//.test(url))return;
  const figure=el("figure","photo"),img=el("img");img.alt=label;img.referrerPolicy="no-referrer";img.loading="lazy";img.src=url;
  put(figure,img,el("figcaption","",label));box.appendChild(figure);
 });
 wrapper.appendChild(box);
}
function renderHistory(info){
 const wrapper=$("history");if(!wrapper)return;wrapper.replaceChildren();
 const list=Array.isArray(info?.deliveries)?info.deliveries:[];
 if(!list.length){wrapper.appendChild(el("p","muted small","尚无已交付版本。"));return}
 list.forEach(d=>{
  const x=el("div","history-item");
  x.appendChild(el("strong","","第 "+safeText(d.version)+" 版 · "+time(d.created_at)));
  x.appendChild(el("p","small muted","首次查看："+time(d.first_viewed_at)));
  if(d.image_url&&/^https:\/\//.test(d.image_url)){
   const img=el("img");img.src=d.image_url;img.alt="交付效果图";img.referrerPolicy="no-referrer";img.loading="lazy";x.appendChild(img);
  }
  if(Array.isArray(d.advice))d.advice.forEach((text,i)=>x.appendChild(el("p","small",(i+1)+"｜"+String(text))));
  wrapper.appendChild(x);
 });
}
async function selectOrder(code){
 const order=S.orders.find(x=>x.order_code===code);if(!order)return;
 S.selected=code;S.images=null;S.history=null;renderOrders();
 const d=$("orderDetail");d.replaceChildren();
 d.appendChild(el("h3","",code));
 const facts=el("div","facts");
 [["提交时间",time(order.created_at)],["客户联系方式",order.contact],["庭院面积",order.yard_size],["偏好风格",order.style],["客户需求",Array.isArray(order.needs)?order.needs.join("、"):"—"],["补充描述",order.notes],["付款状态",status(order.payment_status)],["处理状态",status(order.process_status)],["金额","¥"+safeText(order.amount_cny)]].forEach(a=>facts.appendChild(item("div",a[0],a[1])));
 d.appendChild(facts);
 const actions=el("div","block");actions.appendChild(el("h4","","操作"));
 const toolbar=el("div","filters");
 if(order.payment_status==="pending_verification"){
  toolbar.appendChild(button("核实已到账并确认收款",()=>void confirmPayment(order),"btn red small"));
 }
 if(order.process_status==="completed"&&["confirmed","paid","verified"].includes(order.payment_status)){
  toolbar.appendChild(button("生成客户专用结果链接",()=>void resultLink(order)));
 }
 if(!toolbar.children.length)toolbar.appendChild(el("p","muted small","当前没有需要执行的收款操作。"));
 actions.appendChild(toolbar);
 actions.appendChild(el("p","muted small","付款必须以实际银行/收款平台到账为准；点击订单不会自动确认付款。"));
 d.appendChild(actions);
 d.appendChild(el("hr","hrule"));
 d.appendChild(el("h4","","庭院现场照片与付款凭证"));
 const pictures=el("div","block");pictures.id="images";pictures.appendChild(el("p","muted small","正在安全读取私有图片…"));d.appendChild(pictures);
 d.appendChild(el("hr","hrule"));
 d.appendChild(el("h4","","人工交付 · 一张效果图 + 三条设计建议"));
 const form=el("form","delivery-form");form.id="deliverForm";
 const label=el("label","","选择效果图（JPG、PNG 或 WebP，≤6MB）"),file=el("input");file.type="file";file.accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp";file.required=true;label.appendChild(file);form.appendChild(label);
 const adv=[];
 for(let i=0;i<3;i++){const l=el("label","", "第 "+(i+1)+" 条设计建议"),t=el("textarea");t.required=true;t.minLength=3;t.maxLength=1200;l.appendChild(t);form.appendChild(l);adv.push(t)}
 const submit=el("button","btn","审核并交付给客户");submit.type="submit";
 submit.disabled=!["confirmed","paid","verified"].includes(order.payment_status);
 if(submit.disabled)form.appendChild(el("p","alert","收款尚未确认，不能交付。请先核实实际到账。"));
 form.appendChild(submit);
 form.addEventListener("submit",e=>void deliver(e,order,file,adv,submit));
 d.appendChild(form);
 d.appendChild(el("hr","hrule"));
 d.appendChild(el("h4","","已交付历史版本"));
 const history=el("div","block");history.id="history";history.appendChild(el("p","muted small","正在读取交付历史…"));d.appendChild(history);
 try{
  const [imgs,hist]=await Promise.allSettled([callAdmin("admin_order_images",{order_code:code}),callAdmin("admin_history",{order_code:code})]);
  if(S.selected!==code||!S.approved)return;
  renderImages(imgs.status==="fulfilled"?imgs.value:null);
  renderHistory(hist.status==="fulfilled"?hist.value:null);
  if(imgs.status==="rejected")note("订单图片暂时不可用："+imgs.reason.message,true);
 }catch(err){note("获取订单详情失败："+err.message,true)}
}
async function confirmPayment(order){
 if(!S.approved||S.selected!==order.order_code)return;
 if(!window.confirm("请先在实际收款平台确认这笔款项真实到账。\n订单："+order.order_code+"\n确认后系统可能启动生成流程，不能撤销。\n\n是否确定已经到账？"))return;
 try{await callAdmin("admin_confirm",{order_code:order.order_code});note("已提交收款确认，正在刷新订单状态。");await loadOrders();}
 catch(e){note("收款确认失败："+e.message,true)}
}
async function deliver(e,order,fileInput,adviceInputs,btn){
 e.preventDefault();if(S.selected!==order.order_code||!S.approved)return;
 const file=fileInput.files?.[0],advice=adviceInputs.map(x=>x.value.trim());
 if(!file||file.size<1||file.size>6*1024*1024){note("请上传6MB以内的图片。",true);return}
 if(!["image/jpeg","image/png","image/webp"].includes(file.type)){note("请选择JPG、PNG或WebP图片。",true);return}
 if(advice.length!==3||advice.some(x=>x.length<3||x.length>1200)){note("请写完整的三条设计建议。",true);return}
 if(!["confirmed","paid","verified"].includes(order.payment_status)){note("请先核实到账，未确认付款不能交付。",true);return}
 if(!window.confirm("确认将当前效果图和三条建议正式交付至订单 "+order.order_code+" 吗？"))return;
 btn.disabled=true;btn.textContent="正在上传并交付…";
 try{
  await callAdmin("admin_deliver",{order_code:order.order_code,advice:JSON.stringify(advice),expected_updated_at:order.updated_at||""},file);
  note("效果图与三条设计建议已通过系统正式交付。");
  await loadOrders();
 }catch(err){note("交付未成功："+err.message,true)}
 finally{btn.disabled=false;btn.textContent="审核并交付给客户"}
}
async function resultLink(order){
 if(!S.approved||S.selected!==order.order_code)return;
 try{
  const x=await callAdmin("admin_result_link",{order_code:order.order_code});
  if(!x.access_token||!/^[a-f0-9]{64}$/.test(x.access_token))throw new Error("未收到安全访问凭证");
  const link="https://dayi.homes/direction-feedback/#order="+encodeURIComponent(order.order_code)+"&key="+x.access_token;
  try{await navigator.clipboard.writeText(link);note("已复制客户专用结果链接。仅发送对应客户，不要公开分享。")}
  catch(_){window.prompt("浏览器无法自动复制，请手动复制此客户专用链接：",link)}
 }catch(err){note("生成客户结果链接失败："+err.message,true)}
}
async function boot(){
 $("loginForm").addEventListener("submit",login);
 $("forgotButton").addEventListener("click",()=>{showAuth("forgot");$("resetEmail").value=$("email").value;authMessage("输入管理员邮箱以请求重置密码。")});
 $("backLogin").addEventListener("click",()=>showAuth("login"));
 $("cancelReset").addEventListener("click",()=>showAuth("login"));
 $("forgotForm").addEventListener("submit",forgot);
 $("newPasswordForm").addEventListener("submit",changePassword);
 $("logoutSide").addEventListener("click",()=>signOut("已安全退出登录。"));
 $("logoutTop").addEventListener("click",()=>signOut("已安全退出登录。"));
 document.querySelectorAll("[data-tab]").forEach(b=>b.addEventListener("click",()=>choose(b.dataset.tab)));
 document.querySelectorAll("[data-target]").forEach(b=>b.addEventListener("click",()=>choose(b.dataset.target)));
 document.querySelectorAll("[data-business]").forEach(b=>b.addEventListener("click",()=>showBusinessModule(b.dataset.business)));
 document.querySelectorAll("[data-product]").forEach(b=>b.addEventListener("click",()=>showProductModule(b.dataset.product)));
 $("orderFilter").addEventListener("change",()=>{S.filter=$("orderFilter").value;S.offset=0;void loadOrders(false)});
 $("orderSearch").addEventListener("input",renderOrders);
 $("refreshOrders").addEventListener("click",()=>void loadOrders());
 $("prevPage").addEventListener("click",()=>{S.offset=Math.max(0,S.offset-25);void loadOrders(false)});
 $("nextPage").addEventListener("click",()=>{S.offset+=25;void loadOrders(false)});
 setInterval(()=>{if(S.approved&&S.tab==="business"&&S.businessModule==="feedback"&&!document.hidden&&!S.loading)void loadOrders()},60000);
 if(checkRecovery())return;
 const saved=storedSession();
 if(saved){remember(saved);authMessage("正在恢复管理员登录…");try{await verify();return}catch(e){clearCredentials();authMessage("请重新登录："+e.message,true)}}
 showAuth("login");
}
void boot();
})();