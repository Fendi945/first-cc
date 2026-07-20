import https from "https";
import fs from "fs";

// 优先从环境变量读取，避免硬编码凭据
const APP_ID = process.env.WECHAT_APP_ID || "wxa965a1f564142049";
const APP_SECRET = process.env.WECHAT_APP_SECRET || "a8b1e6dce37e3994884722538c6d76b3";
const AUTHOR = "大一";

function httpsGet(url) {
  return new Promise((resolve, reject) => {
    https.get(url, res => {
      let d = "";
      res.on("data", c => d += c);
      res.on("end", () => resolve(JSON.parse(d)));
    }).on("error", reject);
  });
}

function httpsPost(url, data, contentType) {
  const u = new URL(url);
  const body = typeof data === "string" ? data : JSON.stringify(data);
  const headers = { "Content-Length": Buffer.byteLength(body) };
  if (contentType) headers["Content-Type"] = contentType;
  else headers["Content-Type"] = "application/json";

  return new Promise((resolve, reject) => {
    const req = https.request({ hostname: u.hostname, path: u.pathname + u.search, method: "POST", headers }, res => {
      let d = "";
      res.on("data", c => d += c);
      res.on("end", () => resolve(JSON.parse(d)));
    });
    req.on("error", reject);
    req.write(body);
    req.end();
  });
}

// multipart upload for image
function uploadImage(token, filePath) {
  const boundary = "----FormBoundary" + Date.now().toString(36);
  const fileName = "cover.png";
  const imgData = fs.readFileSync(filePath);
  const parts = [
    `--${boundary}\r\nContent-Disposition: form-data; name="media"; filename="${fileName}"\r\nContent-Type: image/png\r\n\r\n`,
    imgData,
    `\r\n--${boundary}--\r\n`
  ];
  const body = Buffer.concat(parts.map(p => Buffer.isBuffer(p) ? p : Buffer.from(p)));

  return new Promise((resolve, reject) => {
    const u = new URL(`https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=${token}&type=image`);
    const req = https.request({
      hostname: u.hostname, path: u.pathname + u.search, method: "POST",
      headers: {
        "Content-Type": `multipart/form-data; boundary=${boundary}`,
        "Content-Length": body.length
      }
    }, res => {
      let d = "";
      res.on("data", c => d += c);
      res.on("end", () => resolve(JSON.parse(d)));
    });
    req.on("error", reject);
    req.write(body);
    req.end();
  });
}

async function main() {
  console.log("=== WeChat draft push ===\n");

  // 1. get token
  const tokenData = await httpsGet(
    `https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${APP_ID}&secret=${APP_SECRET}`
  );
  if (!tokenData.access_token) throw new Error("Token failed: " + JSON.stringify(tokenData));
  const token = tokenData.access_token;
  console.log("[OK] Token acquired");

  // 2. upload cover image
  const imgRes = await uploadImage(token, "D:\\Documents\\Desktop\\庭院产品卡片\\微信图片_20260621215330_52_123.png");
  if (!imgRes.media_id) throw new Error("Upload failed: " + JSON.stringify(imgRes));
  const thumbId = imgRes.media_id;
  console.log("[OK] Cover uploaded -> " + thumbId.slice(0, 20) + "...");

  // 3. push draft
  const bodyHtml = `<div class="rich_media_content">
<p style="font-size:16px;line-height:2;color:#3a2a1a">很多院子不是小，是乱。不是缺东西，是东西太多。</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a"><strong>一个院子丑，99%是这三个问题：</strong></p>
<p style="font-size:16px;line-height:2;color:#3a2a1a"><strong>第一个：没有主景。</strong> 进院子扫一眼，视线不知道停在哪。左边种棵桂花，右边放个陶罐，中间铺块草坪——每个都好看，合在一起没有焦点。</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a"><strong>第二个：没有停留。</strong> 走一圈全是景，但没一个地方能坐下来。客人来了站门口聊两句就走了——因为你没给他一个“留下来”的理由。</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a"><strong>第三个：元素太满。</strong> 恨不得把小红书上好看的全搬进自己家。水景、凉亭、汀步、灯带、假山——最后像个公园，不像院子。</p>
<hr style="border:0;height:1px;background:#e0d5c8;margin:24px 0">
<p style="font-size:16px;line-height:2;color:#3a2a1a"><strong>高级院子的底层逻辑就三句话。</strong></p>
<p style="font-size:18px;line-height:2;color:#1a1008;font-weight:bold;margin:20px 0 8px">一、定主景——让视线有归宿</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">一个院子只准有一个主角。可以是一棵树、一面景墙、或者一个水景。其他都是配角。</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">选主景的诀窍：从室内最常待的那个位置往外看，视线自然落到的那个点，就是主景位置。</p>
<p style="font-size:16px;line-height:2;color:#8a6a4a;margin:8px 0">好院子不是什么都种了，是走进来第一眼知道看哪。</p>
<p style="font-size:18px;line-height:2;color:#1a1008;font-weight:bold;margin:20px 0 8px">二、设停留——让人想坐下</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">院子不是展览馆，是生活的地方。你需要在院子里放一两处可以坐下来喝茶、看书、发呆的地方。</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">停留点的位置：跟着太阳走。上午有阳光的位置放把椅子，下午有阴凉的地方搭个坐台。</p>
<p style="font-size:16px;line-height:2;color:#8a6a4a;margin:8px 0">好停留不是堆了个亭子，是你不自觉地想在那坐下来。</p>
<p style="font-size:18px;line-height:2;color:#1a1008;font-weight:bold;margin:20px 0 8px">三、留白——让空间喘口气</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">留白不是空着不用，是给眼睛休息的地方。</p>
<p style="font-size:16px;line-height:2;color:#8a6a4a;margin:8px 0">好设计不是做加法做到极致，是减到不能再减，还能好看。</p>
<hr style="border:0;height:1px;background:#e0d5c8;margin:24px 0">
<p style="font-size:16px;line-height:2;color:#3a2a1a"><strong>普通院子变高级的实操步骤：</strong></p>
<p style="font-size:16px;line-height:2;color:#3a2a1a"><strong>第一步：</strong> 清空。把你院子里所有能搬的东西全部搬走。</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a"><strong>第二步：</strong> 定主角。</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a"><strong>第三步：</strong> 添配角。</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a"><strong>第四步：</strong> 检查每个角度。</p>
<p style="font-size:16px;line-height:2;color:#8a6a4a;margin:20px 0">好设计不是做加法做到极致，是减到不能再减，还能好看。</p>
</div>`;

  const draftRes = await httpsPost(
    `https://api.weixin.qq.com/cgi-bin/draft/add?access_token=${token}`,
    {
      articles: [{
        title: "院子想高级，先别急着买树",
        thumb_media_id: thumbId,
        author: AUTHOR,
        digest: "很多院子不是小，是乱。不是缺东西，是东西太多。三招让你的院子变高级。",
        content: bodyHtml,
        need_open_comment: 1,
        only_fans_can_comment: 0,
        show_cover_pic: 1,
      }]
    }
  );
  if (!draftRes.media_id) throw new Error("Draft failed: " + JSON.stringify(draftRes));
  console.log("[OK] Draft pushed -> " + draftRes.media_id.slice(0, 20) + "...");
  console.log("\nDone! media_id: " + draftRes.media_id);
}

main().catch(e => { console.error(e.message); process.exit(1); });
