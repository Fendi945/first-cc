/** 元演引擎 — DeepSeek API 分类引擎 */

import type { OutputTag } from "./data";

const DEEPSEEK_BASE = "https://api.deepseek.com/v1";

export interface ClassifyResponse {
	title: string;
	summary: string;
	ontology: string;
	ability: string;
	rule: string;
	event: string;
	rationale: string;
	tag: OutputTag;
}

/**
 * 调用 DeepSeek API 对日输入进行分类
 */
export async function classifyContent(
	apiKey: string,
	content: string,
	fileName: string,
	model: string = "deepseek-chat"
): Promise<ClassifyResponse> {
	const systemPrompt = `你是一个认知分类引擎，负责对用户的日输入内容进行「元演心智」四层分类。

## 元演心智系统简介
这是一个个人认知管理系统，帮助用户把每天的想法、待办、灵感转化为结构化知识产品。

## 四层分类框架
1. **本体 (Ontology)** — 这是什么性质的内容？
   - 自我觉察 / 知识学习 / 问题解决 / 灵感创意 / 情绪记录 / 日常事务 / 目标规划
2. **能力 (Ability)** — 这个内容涉及什么能力？
   - 元认知 / 逻辑推理 / 知识迁移 / 情绪管理 / 行动执行 / 创造力 / 信息整理
3. **规则 (Rule)** — 什么规则/原则在起作用？
   - 第一性原理 / 系统思维 / 复利效应 / 二八法则 / 奥卡姆剃刀 / 反馈循环 / 注意力管理
4. **事件 (Event)** — 什么事件触发了这个内容？
   - 阅读/观影 / 工作经历 / 人际交流 / 自我反思 / 计划决策 / 外部信息 / 灵感闪现

## 产出标签
- **article** — 适合写公众号文章（有完整观点、结构清晰）
- **video** — 适合做口播视频（有故事性、适合视觉表达）
- **tool** — 适合做工具/模板（有方法论、可操作性强）
- **explore** — 值得深入研究（有开放性、值得探索）
- **none** — 不适合生产，仅记录

## 输出格式
必须返回 JSON，格式如下：
{
  "title": "提炼的标题",
  "summary": "一句话摘要（20字内）",
  "ontology": "本体分类",
  "ability": "能力分类",
  "rule": "规则分类",
  "event": "事件分类",
  "rationale": "分类理由简述",
  "tag": "产出标签 (article/video/tool/explore/none)"
}`;

	const userPrompt = `请对以下日输入内容进行分类：

文件名：${fileName}

内容：
${content}`;

	const requestBody = JSON.stringify({
		model: model,
		messages: [
			{ role: "system", content: systemPrompt },
			{ role: "user", content: userPrompt },
		],
		temperature: 0.3,
		max_tokens: 2000,
	});

	const https = require("https");

	const responseData = await new Promise<string>((resolve, reject) => {
		let respData = "";

		const req = https.request(
			{
				hostname: "api.deepseek.com",
				path: "/v1/chat/completions",
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					"Authorization": `Bearer ${apiKey}`,
					"Content-Length": Buffer.byteLength(requestBody),
				},
			},
			(res: any) => {
				res.on("data", (chunk: string) => {
					respData += chunk;
				});
				res.on("end", () => {
					if (res.statusCode !== 200) {
						reject(new Error(`HTTP ${res.statusCode}: ${respData.slice(0, 300)}`));
					} else {
						resolve(respData);
					}
				});
			}
		);

		req.on("error", (e: Error) => {
			reject(new Error(`网络请求失败: ${e.message}`));
		});

		req.write(requestBody);
		req.end();
	});

	let parsedResponse: any;
	try {
		parsedResponse = JSON.parse(responseData);
	} catch (e) {
		throw new Error(`JSON解析失败: ${responseData.slice(0, 300)}`);
	}

	const replyText = parsedResponse.choices?.[0]?.message?.content || "";
	if (!replyText) {
		throw new Error(`API返回空内容: ${responseData.slice(0, 300)}`);
	}

	const jsonMatch = replyText.match(/\{[\s\S]*\}/);
	if (!jsonMatch) {
		throw new Error(`DeepSeek返回格式异常: ${replyText.slice(0, 300)}`);
	}

	let parsed: any;
	try {
		parsed = JSON.parse(jsonMatch[0]);
	} catch (e) {
		throw new Error(`JSON解析失败: ${jsonMatch[0].slice(0, 300)}`);
	}

	return {
		title: parsed.title || fileName.replace(/\.md$/, ""),
		summary: parsed.summary || "",
		ontology: parsed.ontology || "未分类",
		ability: parsed.ability || "未分类",
		rule: parsed.rule || "未分类",
		event: parsed.event || "未分类",
		rationale: parsed.rationale || "",
		tag: validateTag(parsed.tag),
	};
}

/**
 * 根据日输入内容生成一篇完整的公众号文章
 */
export async function generateArticle(
	apiKey: string,
	model: string,
	title: string,
	sourceContent: string,
	summary: string
): Promise<string> {
	const systemPrompt = `你是一个公众号文章作者，专写有深度、接地气的认知提升类文章。

## 写作风格
- 标题抓人，开头有场景感（让读者觉得"这说的就是我"）
- 正文分小标题，每段300-500字，语言口语化、生动
- 适当用「你」来增强对话感
- 有具体案例、可操作的方法，不空谈
- 结尾有总结升华 + 互动引导

## 长度要求
- 全文 1500-2500 字
- 5-7 个小标题段落
- 每段配一个简短案例或比喻`;

	const userPrompt = `请根据以下素材，写一篇完整的公众号文章。

原标题：${title}
摘要：${summary}

素材内容：
${sourceContent}

要求：直接用文章正文输出，不要 JSON 包裹。`;

	const https = require("https");
	const body = JSON.stringify({
		model: model,
		messages: [
			{ role: "system", content: systemPrompt },
			{ role: "user", content: userPrompt },
		],
		temperature: 0.7,
		max_tokens: 4000,
	});

	return await new Promise<string>((resolve, reject) => {
		const req = https.request({
			hostname: "api.deepseek.com",
			path: "/v1/chat/completions",
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"Authorization": `Bearer ${apiKey}`,
				"Content-Length": Buffer.byteLength(body),
			},
		}, (res: any) => {
			let data = "";
			res.on("data", (chunk: string) => { data += chunk; });
			res.on("end", () => {
				if (res.statusCode !== 200) {
					reject(new Error(`HTTP ${res.statusCode}`));
					return;
				}
				try {
					const parsed = JSON.parse(data);
					const text = parsed.choices?.[0]?.message?.content || "";
					if (!text) reject(new Error("返回为空"));
					else resolve(text);
				} catch (e: any) {
					reject(new Error(`解析失败: ${e.message}`));
				}
			});
		});
		req.on("error", (e: Error) => reject(e.message));
		req.write(body);
		req.end();
	});
}

/**
 * 根据文章内容生成口播文案（630字以内，短句、换行、金句）
 */
export async function generateScript(
	apiKey: string,
	model: string,
	title: string,
	sourceContent: string
): Promise<string> {
	const systemPrompt = `你是一个口播文案撰稿人，擅长把文章改成适合口播的短文案。

## 格式要求
- 全文控制在 600-630 字之间
- 用短句，每句话尽量不超过 20 字
- 重要的观点单独一行，形成节奏感
- 适当使用金句，金句前后留空行
- 不用标题，不用编号，从头到尾是一段流畅的口播稿
- 语言口语化，像在跟一个人聊天
- 不用配图说明，不需要开场白和结束语

## 示例风格
好设计不是做加法做到极致。
是减到不能再减，还能好看。
很多院子不是小，是乱。
不是缺东西，是东西太多。`;

	const userPrompt = `请根据以下文章内容，生成一段口播文案（600-630字）：

原标题：${title}

内容：
${sourceContent}

要求：短句、换行、金句、口语化、630字以内。直接用文案输出，不要 JSON。`;

	const https = require("https");
	const body = JSON.stringify({
		model: model,
		messages: [
			{ role: "system", content: systemPrompt },
			{ role: "user", content: userPrompt },
		],
		temperature: 0.7,
		max_tokens: 2000,
	});

	return await new Promise<string>((resolve, reject) => {
		const req = https.request({
			hostname: "api.deepseek.com",
			path: "/v1/chat/completions",
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"Authorization": `Bearer ${apiKey}`,
				"Content-Length": Buffer.byteLength(body),
			},
		}, (res: any) => {
			let data = "";
			res.on("data", (chunk: string) => { data += chunk; });
			res.on("end", () => {
				if (res.statusCode !== 200) {
					reject(new Error(`HTTP ${res.statusCode}`));
					return;
				}
				try {
					const parsed = JSON.parse(data);
					const text = parsed.choices?.[0]?.message?.content || "";
					if (!text) reject(new Error("返回为空"));
					else resolve(text);
				} catch (e: any) {
					reject(new Error(`解析失败: ${e.message}`));
				}
			});
		});
		req.on("error", (e: Error) => reject(e.message));
		req.write(body);
		req.end();
	});
}


function validateTag(tag: string): OutputTag {
	const validTags: OutputTag[] = ["none", "video", "article", "tool", "explore", "publish"];
	if (validTags.includes(tag as OutputTag)) {
		return tag as OutputTag;
	}
	return "none";
}

/** 产出标签 -> 中文名 */
export function tagLabel(tag: OutputTag): string {
	const map: Record<OutputTag, string> = {
		none: "不生产",
		video: "视频",
		article: "文章",
		tool: "工具",
		explore: "攻坚",
		publish: "格式发布",
	};
	return map[tag] || "未知";
}

/** 产出标签 -> 显示 emoji */
export function tagEmoji(tag: OutputTag): string {
	const map: Record<OutputTag, string> = {
		none: "📋",
		video: "📹",
		article: "📝",
		tool: "🔧",
		explore: "🔬",
		publish: "📢",
	};
	return map[tag] || "❓";
}
