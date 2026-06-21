/** 元演引擎 — 生产执行器 */

import { Vault, Notice, normalizePath } from "obsidian";
import { exec } from "child_process";
import * as path from "path";
import type { PendingItem, OutputTag } from "./data";
import {
	OUTPUT_ARTICLE_DIR,
	OUTPUT_VIDEO_DIR,
	OUTPUT_TOOL_DIR,
	OUTPUT_EXPLORE_DIR,
	PROCESSING_DIR,
	YUANYAN_DIR,
} from "./data";
import { tagLabel, generateArticle, generateScript } from "./classifier";
import { pushToWechatDraft, uploadWechatImage, uploadWechatInlineImage } from "./wechat";

export interface ProductionContext {
	apiKey?: string;
	model?: string;
	wechatAppId?: string;
	wechatAppSecret?: string;
	wechatEnabled?: boolean;
	wechatCoverMediaId?: string;
}

export async function executeProduction(
	vault: Vault,
	item: PendingItem,
	finalTag: OutputTag,
	ctx?: ProductionContext
): Promise<string> {
	const msg = `[${tagLabel(finalTag)}] ${item.title}`;

	switch (finalTag) {
		case "article":
			await produceArticle(vault, item, ctx);
			break;
		case "publish":
			await produceFormatPublish(vault, item, ctx);
			break;
		case "video":
			await produceVideo(vault, item);
			break;
		case "tool":
			await produceTool(vault, item);
			break;
		case "explore":
			await produceExplore(vault, item);
			break;
		default:
			return `${msg} -> skip`;
	}

	new Notice(`Production done: ${msg}`);
	return `${msg} -> done`;
}

function safeName(title: string): string {
	return title.replace(/[<>:"/\\|?*]/g, "_").replace(/\s+/g, "_").slice(0, 60);
}

function frontmatter(item: PendingItem): string {
	return `---
title: ${item.title}
source: ${item.sourceFile}
classified: ${item.createdAt}
ontology: ${item.classification.ontology}
ability: ${item.classification.ability}
rule: ${item.classification.rule}
event: ${item.classification.event}
status: full-article
---
`;
}

// ========== Format & Publish：双管道输出 ==========

async function produceFormatPublish(
	vault: Vault,
	item: PendingItem,
	ctx?: ProductionContext
): Promise<void> {
	let rawContent = "";
	try {
		const sourcePath = normalizePath(item.sourceFile);
		if (await vault.adapter.exists(sourcePath)) {
			rawContent = await vault.adapter.read(sourcePath);
		}
	} catch (e: any) {
		rawContent = `# ${item.title}\n\n${item.summary || ""}`;
	}

	const title = item.title || path.basename(item.sourceFile || "", ".md");
	const today = new Date().toISOString().slice(0, 10);
	const outputDir = normalizePath(`${PROCESSING_DIR}/常驻`);
	await ensureDir(vault, outputDir);
	const name = safeName(title);

	// === 提取图片 ===
	const images = extractImages(rawContent);
	const imagePaths = resolveImagePaths(images, vault, item.sourceFile);

	// ═══════════════════════════════════════════
	// 管道一：公众号文章（正文嵌入图片 + 封面）
	// ═══════════════════════════════════════════
	if (ctx?.wechatEnabled && ctx?.wechatAppId && ctx?.wechatAppSecret) {
		try {
			// 上传封面（第一张图）
			let coverMediaId = ctx.wechatCoverMediaId || "";
			if (imagePaths.length > 0 && !coverMediaId) {
				coverMediaId = await uploadWechatImage(
					ctx.wechatAppId, ctx.wechatAppSecret, imagePaths[0]
				);
			}

			// 上传正文图片，替换 markdown 引用为 WeChat CDN 地址
			let wechatContent = rawContent;
			const inlineUrls: string[] = [];
			for (const imgPath of imagePaths) {
				try {
					const url = await uploadWechatInlineImage(
						ctx.wechatAppId, ctx.wechatAppSecret, imgPath
					);
					inlineUrls.push(url);
				} catch (e: any) {
					console.warn("图片上传失败（跳过）:", imgPath, e.message);
				}
			}

			// 替换图片引用：![[xxx.png]] → <img src="CDN_URL">
			let imgIdx = 0;
			wechatContent = wechatContent
				.replace(/!\[\[([^\]]+\.(png|jpg|jpeg|gif|webp))\]\]/gi, () => {
					const url = imgIdx < inlineUrls.length ? inlineUrls[imgIdx++] : "";
					return url ? `<img src="${url}" style="width:100%;margin:16px 0" alt="庭院示意图"/>` : "";
				})
				.replace(/!\[.*?\]\(([^)]+\.(png|jpg|jpeg|gif|webp))\)/gi, () => {
					const url = imgIdx < inlineUrls.length ? inlineUrls[imgIdx++] : "";
					return url ? `<img src="${url}" style="width:100%;margin:16px 0" alt="庭院示意图"/>` : "";
				});

			// 转 HTML
			const html = markdownToWechatHtml(wechatContent);

			const mediaId = await pushToWechatDraft(
				ctx.wechatAppId, ctx.wechatAppSecret,
				title, html, coverMediaId, "大一", title
			);
			if (mediaId) {
				new Notice(`公众号文章已推送: ${title}`);
			}
		} catch (e: any) {
			new Notice(`公众号推送失败: ${e.message}`);
		}
	}

	// ═══════════════════════════════════════════
	// 管道二：口播文案（AI 生成，630字以内）
	// ═══════════════════════════════════════════
	let scriptText = "";
	if (ctx?.apiKey) {
		try {
			scriptText = await generateScript(
				ctx.apiKey,
				ctx.model || "deepseek-v4-flash",
				title,
				rawContent
			);
		} catch (e: any) {
			scriptText = `（口播文案生成失败: ${e.message}）`;
		}
	} else {
		scriptText = "（请先配置 DeepSeek API Key 以生成口播文案）";
	}

	// 保存口播文案
	const scriptPath = normalizePath(`${outputDir}/口播-${name}.md`);
	const scriptFm = `---
title: ${title}（口播版）
created: ${today}
tags: [口播, 脚本]
status: published
words: ${scriptText.length}
source: ${item.sourceFile}
---

`;
	const scriptFull = scriptFm + scriptText + `\n\n---\n\n> 口播文案 ${scriptText.length} 字，自动生成于 ${today}`;

	try {
		await vault.create(scriptPath, scriptFull);
	} catch {
		const ts = Date.now().toString(36);
		await vault.create(normalizePath(`${outputDir}/口播-${name}_${ts}.md`), scriptFull);
	}
	new Notice(`口播文案已保存（${scriptText.length}字）`);

	// === 也保存原文到常驻 ===
	const rawFm = `---
title: ${title}
created: ${today}
tags: [publish, 整理发布]
status: published
source: ${item.sourceFile}
---

`;
	const rawPath = normalizePath(`${outputDir}/原文-${name}.md`);
	try {
		await vault.create(rawPath, rawFm + rawContent);
	} catch {}
}


// ========== 图片相关工具函数 ==========

function extractImages(content: string): string[] {
	const results: string[] = [];
	const wikiRe = /!\[\[([^\]]+\.(png|jpg|jpeg|gif|webp))\]\]/gi;
	const mdRe = /!\[.*?\]\(([^)]+\.(png|jpg|jpeg|gif|webp))\)/gi;
	let m;
	while ((m = wikiRe.exec(content)) !== null) results.push(m[1]);
	while ((m = mdRe.exec(content)) !== null) results.push(m[1]);
	return results;
}

function resolveImagePaths(refs: string[], vault: Vault, sourceFile: string): string[] {
	const results: string[] = [];
	const vaultRoot = vault.getRoot()?.path || "";
	const sourceDir = path.dirname(sourceFile);

	for (const ref of refs) {
		// 尝试各路径
		const candidates = [
			ref,                                          // 原始
			`assets/images/${ref}`,                       // assets/images/
			`${YUANYAN_DIR}/assets/images/${ref}`,         // 元演心智/assets/images/
			`${sourceDir}/${ref}`,                         // 同目录
			normalizePath(`${vaultRoot}/${ref}`),          // vault 根
		];
		// 拿第一个能找到的
		results.push(normalizePath(candidates[0]));
	}
	return results;
}


// ========== Markdown → 微信公众号 HTML ==========

function markdownToWechatHtml(md: string): string {
	// 移除图片引用（已被替换）
	let text = md
		.replace(/!\[\[([^\]]+)\]\]/g, "")
		.replace(/!\[.*?\]\(.*?\)/g, "");

	const parts: string[] = [];
	const lines = text.split("\n");
	let inBlockquote = false;

	for (const line of lines) {
		const trimmed = line.trim();

		if (trimmed.startsWith("> ")) {
			if (!inBlockquote) {
				parts.push('<blockquote style="border-left:3px solid #e8753a;padding:10px 16px;margin:12px 0;color:#5a4a3a;background:#f8f4ec;font-size:15px;line-height:1.8">');
				inBlockquote = true;
			}
			parts.push(trimmed.slice(2));
			continue;
		} else if (inBlockquote) {
			parts.push("</blockquote>");
			inBlockquote = false;
		}

		if (!trimmed) {
			parts.push("</p><p style='font-size:15px;line-height:1.9;color:#3a2a1a;margin:10px 0'>");
			continue;
		}

		if (trimmed.startsWith("### ")) {
			parts.push(`<h3 style="font-size:17px;font-weight:700;margin:20px 0 8px;color:#1a1008">${trimmed.slice(4)}</h3>`);
			continue;
		}
		if (trimmed.startsWith("## ")) {
			parts.push(`<h2 style="font-size:19px;font-weight:700;margin:24px 0 8px;color:#1a1008">${trimmed.slice(3)}</h2>`);
			continue;
		}
		if (trimmed.startsWith("# ")) {
			parts.push(`<h1 style="font-size:22px;font-weight:700;margin:24px 0 8px;color:#1a1008">${trimmed.slice(2)}</h1>`);
			continue;
		}

		if (trimmed === "---") {
			parts.push('<hr style="border:0;height:1px;background:#e0d5c8;margin:24px 0">');
			continue;
		}

		let txt = trimmed
			.replace(/\*\*(.+?)\*\*/g, '<strong style="color:#e8753a">$1</strong>')
			.replace(/__(.+?)__/g, '<strong style="color:#e8753a">$1</strong>');
		parts.push(txt);
	}

	if (inBlockquote) parts.push("</blockquote>");

	let html = parts.join("");
	html = `<div class="rich_media_content"><p style="font-size:15px;line-height:1.9;color:#3a2a1a;margin:10px 0">${html}</p></div>`;
	return html;
}


// ========== Article production ==========

async function produceArticle(vault: Vault, item: PendingItem, ctx?: ProductionContext): Promise<void> {
	let articleBody = "";

	if (ctx?.apiKey) {
		try {
			let sourceContent = item.summary;
			try {
				const sourcePath = normalizePath(item.sourceFile);
				if (await vault.adapter.exists(sourcePath)) {
					sourceContent = await vault.adapter.read(sourcePath);
				}
			} catch {}

			articleBody = await generateArticle(
				ctx.apiKey,
				ctx.model || "deepseek-v4-flash",
				item.title,
				sourceContent,
				item.summary
			);
		} catch (e: any) {
			articleBody = `> ${item.summary}\n\n> *(AI generation failed: ${e.message})*\n\n---\n\n## Body\n\n`;
		}
	}

	if (!articleBody) {
		articleBody = `> ${item.summary}\n\n## Body\n\n(To be completed)\n`;
	}

	const name = safeName(item.title);
	const filePath = normalizePath(`${OUTPUT_ARTICLE_DIR}/${name}.md`);
	const content = `${frontmatter(item)}${articleBody}\n\n---\n\n*Generated at ${new Date().toISOString().slice(0, 10)}*\n`;

	await ensureDir(vault, OUTPUT_ARTICLE_DIR);
	try { await vault.create(filePath, content); } catch {
		const ts = Date.now().toString(36);
		await vault.create(normalizePath(`${OUTPUT_ARTICLE_DIR}/${name}_${ts}.md`), content);
	}

	if (ctx?.wechatEnabled && ctx?.wechatAppId && ctx?.wechatAppSecret && ctx?.wechatCoverMediaId) {
		try {
			const mediaId = await pushToWechatDraft(
				ctx.wechatAppId, ctx.wechatAppSecret,
				item.title, articleBody,
				ctx.wechatCoverMediaId, "大一",
				item.summary || item.title
			);
			if (mediaId) new Notice(`WeChat draft pushed: ${mediaId.slice(0, 10)}...`);
			else new Notice(`WeChat push failed, check console`);
		} catch (e: any) { new Notice(`WeChat push error: ${e.message}`); }
	}
}

// ========== Video production ==========

async function produceVideo(vault: Vault, item: PendingItem): Promise<void> {
	const name = safeName(item.title);
	const filePath = normalizePath(`${OUTPUT_VIDEO_DIR}/${name}.md`);
	const content = `${frontmatter(item)}# Video script: ${item.title}

Source: [[${item.sourceFile.replace(/\.md$/, "")}]]

## Core idea
${item.summary}

## Script

(To be completed)
`;

	await ensureDir(vault, OUTPUT_VIDEO_DIR);
	try { await vault.create(filePath, content); } catch {
		await vault.create(normalizePath(`${OUTPUT_VIDEO_DIR}/${name}_${Date.now().toString(36)}.md`), content);
	}
}

// ========== Tool production ==========

async function produceTool(vault: Vault, item: PendingItem): Promise<void> {
	const name = safeName(item.title);
	const filePath = normalizePath(`${OUTPUT_TOOL_DIR}/${name}.md`);
	const content = `${frontmatter(item)}# Tool: ${item.title}

Background: ${item.classification.rationale}
`;

	await ensureDir(vault, OUTPUT_TOOL_DIR);
	try { await vault.create(filePath, content); } catch {
		await vault.create(normalizePath(`${OUTPUT_TOOL_DIR}/${name}_${Date.now().toString(36)}.md`), content);
	}
}

// ========== Explore production ==========

async function produceExplore(vault: Vault, item: PendingItem): Promise<void> {
	const name = safeName(item.title);
	const filePath = normalizePath(`${OUTPUT_EXPLORE_DIR}/${name}.md`);
	const content = `${frontmatter(item)}# Explore: ${item.title}

Source: [[${item.sourceFile.replace(/\.md$/, "")}]]

## Questions

1.
2.
`;

	await ensureDir(vault, OUTPUT_EXPLORE_DIR);
	try { await vault.create(filePath, content); } catch {
		await vault.create(normalizePath(`${OUTPUT_EXPLORE_DIR}/${name}_${Date.now().toString(36)}.md`), content);
	}
}

async function ensureDir(vault: Vault, dirPath: string): Promise<void> {
	const normalPath = normalizePath(dirPath);
	if (!(await vault.adapter.exists(normalPath))) {
		await vault.adapter.mkdir(normalPath);
	}
}

export function callPythonScript(scriptName: string, args: string[]): Promise<string> {
	return new Promise((resolve, reject) => {
		const projectDir = path.join(__dirname, "..", "..");
		const scriptPath = path.join(projectDir, "engine", scriptName);
		const child = exec(
			`python "${scriptPath}" ${args.map(a => `"${a}"`).join(" ")}`,
			{ cwd: projectDir },
			(error, stdout, stderr) => {
				if (error) reject(new Error(stderr || error.message));
				else resolve(stdout.trim());
			}
		);
	});
}
