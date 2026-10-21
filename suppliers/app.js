/* DAY1 Supplier Portal v1.0 — invitation bearer can only access its own submissions.
 * No access to order APIs or the workbench. */
(function(){
"use strict";
const API="https://fhvhnibznphatfnbvvnb.supabase.co/functions/v1/dayi-supplier-api";
const PUB="sb_publishable_8_ElUXtWKbEM9Of37zdYug_mdWjcV4B";
const KEY="dayi-supplier-invite-v1";
const $=id=>document.getElementById(id);
let token=null, profile=null, busy=false;
const dictionary={pending:"待大一审核",approved:"审核通过",rejected:"未通过"};
function status(msg,error=false){$("status").textContent=msg;$("status").classList.toggle("error",error)}
function saved(){try{const t=localStorage.getItem(KEY);return /^[a-f0-9]{64}$/.test(t||"")?t:null}catch{return null}}
function persist(t){try{localStorage.setItem(KEY,t);return localStorage.getItem(KEY)===t}catch{return false}}
function clearHash(){
 if(window.location.hash)try{history.replaceState(null,"",location.pathname+location.search)}catch{}
}
async function api(action,fields={},files=null){
 const headers={apikey:PUB};let body;
 if(files){
  const d=new FormData();
  d.append("action",action);d.append("invite_token",token);
  Object.entries(fields).forEach(([key,value])=>d.append(key,value));
  files.forEach(([kind,file])=>{if(file)d.append(kind,file,file.name)});
  body=d;
 }else{
  headers["Content-Type"]="application/json";
  body=JSON.stringify({action,invite_token:token,...fields});
 }
 let r=await fetch(API,{method:"POST",headers,body,cache:"no-store",signal:AbortSignal.timeout(60000)});
 let data;try{data=await r.json()}catch{data={}};
 if(!r.ok)throw new Error(({invitation_required:"需要有效邀请",invitation_expired_or_revoked:"邀请已过期或撤销，请联系大一重新邀请",supplier_disabled:"此供应商已停止授权",rate_limited:"操作较频繁，请稍后重试",photo_required:"请补充真实物料照片",missing_material_information:"请填写名称并选择正确品类",image_too_large:"图片不得超过6MB",invalid_image_format:"图片格式应为 JPG、PNG 或 WebP",image_usage_permission_required:"请勾选图片授权确认",service_unavailable:"连接暂时中断，请稍后重试",storage_or_database_unavailable:"服务器暂时无法保存，请稍后重试"})[data.error]||"提交失败（"+(data.error||r.status)+"）");
 return data;
}
async function profileAndList(){
 try{
  const r=await api("vendor_profile");
  profile=r.supplier;
  if(!profile||!profile.id)throw new Error("无法识别供应商");
  $("workspace").hidden=false;$("needInvite").hidden=true;
  $("companyName").textContent=profile.company_name||"供应商";
  $("companyMeta").textContent="供应商已通过独立邀请验证 · 您提交的物料需由大一审核，其他供应商无法访问这些内容。";
  status("邀请验证成功。您现在可以上传本公司的材料与图片。");
  await reload();
 }catch(e){
  $("workspace").hidden=true;$("needInvite").hidden=false;
  status(e.message,true);
 }
}
async function reload(){
 const e=$("myMaterials");e.replaceChildren();
 e.appendChild(Object.assign(document.createElement("p"),{className:"hint",textContent:"正在读取本公司提交记录…"}));
 try{
  const res=await api("vendor_materials"); e.replaceChildren();
  if(!res.materials?.length){e.appendChild(Object.assign(document.createElement("p"),{className:"hint",textContent:"尚未提交物料。请从上方新增一项材料。"}));return}
  res.materials.forEach(item=>{
   const row=document.createElement("div");row.className="material";
   const info=document.createElement("div");
   const name=document.createElement("strong");name.textContent=item.name;
   const date=document.createElement("div");date.className="hint";date.textContent=new Date(item.created_at).toLocaleDateString("zh-CN")+(item.review_notes?" · 审核意见："+item.review_notes:"");
   info.append(name,date);
   const tag=document.createElement("span");tag.className="pill "+item.approval_status;tag.textContent=dictionary[item.approval_status]||"已提交";
   row.append(info,tag);e.appendChild(row);
  });
 }catch(e){e.replaceChildren(); const msg=document.createElement("p");msg.className="hint";msg.textContent=e.message;e.appendChild(msg)}
}
const previews=new Map();
function preview(fileInput,viewId){
 const img=$(viewId),file=fileInput.files?.[0];
 if(previews.has(viewId)){URL.revokeObjectURL(previews.get(viewId));previews.delete(viewId)}
 img.hidden=true;img.removeAttribute("src");
 if(!file)return;
 if(!["image/jpeg","image/png","image/webp"].includes(file.type)||file.size>6*1024*1024){
  fileInput.value="";status("仅支持6MB以内的 JPG/PNG/WebP 图片。",true);return;
 }
 const url=URL.createObjectURL(file);previews.set(viewId,url);img.src=url;img.hidden=false;
}
async function submit(e){
 e.preventDefault();if(busy||!token||!profile)return;
 const form=e.currentTarget,photo=$("photo").files?.[0],texture=$("texture").files?.[0];
 if(!photo){status("请选择一张物料真实照片。",true);return}
 if(!$("permission").checked){status("请确认拥有图片使用授权。",true);return}
 const fd=new FormData(form);
 const data=Object.fromEntries(fd.entries());delete data.name_dummy;
 data.permission=true;
 if(!data.name||String(data.name).trim().length<2||!data.category){status("请输入物料名称并选择品类。",true);return}
 const btn=$("submitButton");busy=true;btn.disabled=true;btn.textContent="正在安全上传，请稍候…";
 try{
  const response=await api("vendor_submit",{metadata:JSON.stringify(data)},[["photo",photo],["texture",texture]]);
  if(!response.saved)throw new Error("提交结果无法确认，请联系管理员");
  status("提交成功，材料已进入大一的待审核列表。您可以继续提交下一种材料。");
  form.reset();
  previews.forEach((url,id)=>{URL.revokeObjectURL(url);$(id).hidden=true;$(id).removeAttribute("src")});previews.clear();
  await reload();
  window.scrollTo({top:0,behavior:"smooth"});
 }catch(err){status(err.message,true)}
 finally{busy=false;btn.disabled=false;btn.textContent="提交物料，等待大一审核 →"}
}
function init(){
 const params=new URLSearchParams(location.hash.replace(/^#/,""));
 const hash=params.get("invite");
 const fromUrl=/^[0-9a-f]{64}$/.test(hash||"")?hash:null;
 token=fromUrl||saved();
 if(fromUrl&&persist(fromUrl))clearHash();
 if(!token){$("needInvite").hidden=false;status("尚未提供有效的供应商邀请，请使用大一发送给您的专属链接。",true);return}
 $("materialForm").addEventListener("submit",submit);
 $("photo").addEventListener("change",()=>preview($("photo"),"photoPreview"));
 $("texture").addEventListener("change",()=>preview($("texture"),"texturePreview"));
 $("reloadMaterials").addEventListener("click",reload);
 void profileAndList();
}
init();
})();