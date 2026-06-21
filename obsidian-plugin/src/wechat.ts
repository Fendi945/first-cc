/** 元演引擎 — 微信公众号草稿箱推送 */

import * as fs from "fs";
import * as path from "path";

let _tokenCache: { token: string; expiresAt: number } = { token: "", expiresAt: 0 };

async function getAccessToken(appId: string, appSecret: string): Promise<string> {
	const now = Date.now() / 1000;
	if (_tokenCache.token && now < _tokenCache.expiresAt) {
		return _tokenCache.token;
	}

	const https = require("https");
	const url = `https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${appId}&secret=${appSecret}`;

	const data = await new Promise<string>((resolve, reject) => {
		https.get(url, (res: any) => {
			let d = "";
			res.on("data", (chunk: string) => (d += chunk));
			res.on("end", () => resolve(d));
		}).on("error", (e: Error) => reject(e.message));
	});

	const parsed = JSON.parse(data);
	if (parsed.access_token) {
		_tokenCache = {
			token: parsed.access_token,
			expiresAt: now + parsed.expires_in - 300,
		};
		return parsed.access_token;
	}

	throw new Error(`微信 token 获取失败: ${JSON.stringify(parsed)}`);
}

/**
 * 上传图片为永久素材，返回 media_id（用于封面）
 */
export async function uploadWechatImage(
	appId: string,
	appSecret: string,
	imagePath: string
): Promise<string> {
	const token = await getAccessToken(appId, appSecret);

	const https = require("https");
	const boundary = "----FormBoundary" + Date.now().toString(36);
	const imgData = fs.readFileSync(imagePath);

	const parts = [
		`--${boundary}\r\nContent-Disposition: form-data; name="media"; filename="cover.png"\r\nContent-Type: image/png\r\n\r\n`,
		imgData,
		`\r\n--${boundary}--\r\n`,
	];
	const body = Buffer.concat(parts.map((p: any) => (Buffer.isBuffer(p) ? p : Buffer.from(p))));

	const urlObj = new URL(
		`https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=${token}&type=image`
	);

	const result = await new Promise<string>((resolve, reject) => {
		const req = https.request(
			{
				hostname: urlObj.hostname,
				path: urlObj.pathname + urlObj.search,
				method: "POST",
				headers: {
					"Content-Type": `multipart/form-data; boundary=${boundary}`,
					"Content-Length": body.length,
				},
			},
			(res: any) => {
				let d = "";
				res.on("data", (c: string) => (d += c));
				res.on("end", () => resolve(d));
			}
		);
		req.on("error", (e: Error) => reject(e.message));
		req.write(body);
		req.end();
	});

	const parsed = JSON.parse(result);
	if (parsed.media_id) return parsed.media_id;

	throw new Error(`封面图片上传失败: ${JSON.stringify(parsed)}`);
}

/**
 * 上传图片作为正文可用的素材，返回可嵌入 <img> 的 URL
 */
export async function uploadWechatInlineImage(
	appId: string,
	appSecret: string,
	imagePath: string
): Promise<string> {
	const token = await getAccessToken(appId, appSecret);

	const https = require("https");
	const boundary = "----FormBoundary" + Date.now().toString(36);
	const ext = path.extname(imagePath).toLowerCase() || ".png";
	const mime = ext === ".jpg" || ext === ".jpeg" ? "image/jpeg" : "image/png";
	const imgData = fs.readFileSync(imagePath);

	const parts = [
		`--${boundary}\r\nContent-Disposition: form-data; name="media"; filename="img${ext}"\r\nContent-Type: ${mime}\r\n\r\n`,
		imgData,
		`\r\n--${boundary}--\r\n`,
	];
	const body = Buffer.concat(parts.map((p: any) => (Buffer.isBuffer(p) ? p : Buffer.from(p))));

	const urlObj = new URL(
		`https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token=${token}`
	);

	const result = await new Promise<string>((resolve, reject) => {
		const req = https.request(
			{
				hostname: urlObj.hostname,
				path: urlObj.pathname + urlObj.search,
				method: "POST",
				headers: {
					"Content-Type": `multipart/form-data; boundary=${boundary}`,
					"Content-Length": body.length,
				},
			},
			(res: any) => {
				let d = "";
				res.on("data", (c: string) => (d += c));
				res.on("end", () => resolve(d));
			}
		);
		req.on("error", (e: Error) => reject(e.message));
		req.write(body);
		req.end();
	});

	const parsed = JSON.parse(result);
	if (parsed.url) return parsed.url;

	throw new Error(`正文图片上传失败: ${JSON.stringify(parsed)}`);
}

/**
 * 推送文章到公众号草稿箱
 * @param thumbMediaId 封面图永久素材 media_id（必填）
 * @returns media_id（成功）或 null（失败）
 */
export async function pushToWechatDraft(
	appId: string,
	appSecret: string,
	title: string,
	contentMarkdown: string,
	thumbMediaId: string,
	author: string = "大一",
	digest?: string
): Promise<string | null> {
	try {
		const token = await getAccessToken(appId, appSecret);

		const bodyHtml = `<div class="rich_media_content">${
			contentMarkdown
				.replace(/^### (.+)$/gm, "<h3>$1</h3>")
				.replace(/^## (.+)$/gm, "<h2>$1</h2>")
				.replace(/^# (.+)$/gm, "<h1>$1</h1>")
				.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
				.replace(/^- (.+)$/gm, "<li>$1</li>")
				.replace(/\n\n/g, "</p><p>")
				.replace(/\n/g, "<br/>")
		}</div>`;

		const payload = JSON.stringify({
			articles: [
				{
					title: title,
					thumb_media_id: thumbMediaId,
					author: author,
					digest: digest || title,
					content: bodyHtml,
					need_open_comment: 1,
					only_fans_can_comment: 0,
					show_cover_pic: 1,
				},
			],
		});

		const https = require("https");
		const urlObj = new URL(`https://api.weixin.qq.com/cgi-bin/draft/add?access_token=${token}`);

		const result = await new Promise<string>((resolve, reject) => {
			const req = https.request(
				{
					hostname: urlObj.hostname,
					path: urlObj.pathname + urlObj.search,
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						"Content-Length": Buffer.byteLength(payload),
					},
				},
				(res: any) => {
					let data = "";
					res.on("data", (chunk: string) => (data += chunk));
					res.on("end", () => resolve(data));
				}
			);
			req.on("error", (e: Error) => reject(e.message));
			req.write(payload);
			req.end();
		});

		const parsed = JSON.parse(result);
		if (parsed.media_id) {
			return parsed.media_id;
		}

		console.error("微信推送失败:", JSON.stringify(parsed));
		return null;
	} catch (e: any) {
		console.error("微信推送异常:", e.message);
		return null;
	}
}
