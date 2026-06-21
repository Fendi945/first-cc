/** 元演引擎 — 数据结构定义与文件读写 */

import { Vault, normalizePath } from "obsidian";

// ========== 目录常量 ==========
/** 相对于 vault 根目录 */
export const VAULT_ROOT = ""; // vault root
export const YUANYAN_DIR = "🧠 元演心智";
export const DAILY_INPUT_DIR = `${YUANYAN_DIR}/🌱 原料库/日输入`;
export const CAPTURE_DIR = `${YUANYAN_DIR}/🌱 原料库/捕获`;
export const KANBAN_DIR = `${YUANYAN_DIR}/⚙️ 反哺弧/看板`;
export const PROCESSING_DIR = `${YUANYAN_DIR}/🌿 加工间`;
export const OUTPUT_ARTICLE_DIR = `${PROCESSING_DIR}/文章草稿`;
export const OUTPUT_VIDEO_DIR = `${PROCESSING_DIR}/视频脚本`;
export const OUTPUT_TOOL_DIR = `${PROCESSING_DIR}/工具雏形`;
export const OUTPUT_EXPLORE_DIR = `${PROCESSING_DIR}/攻坚`;

export const PENDING_FILE = `${KANBAN_DIR}/待审批.json`;
export const APPROVAL_LOG_FILE = `${KANBAN_DIR}/审批日志.json`;
export const CLASSIFY_LOG_FILE = `${KANBAN_DIR}/分类日志.json`;

// ========== 类型定义 ==========

export type OutputTag = "none" | "video" | "article" | "tool" | "explore" | "publish";
export type ItemStatus = "pending" | "approved" | "rejected";
export type ApprovalAction = "approve" | "reject" | "convert" | "publish";

export interface ClassificationResult {
	ontology: string;
	ability: string;
	rule: string;
	event: string;
	rationale: string;
}

export interface PendingItem {
	id: string;
	sourceFile: string;
	title: string;
	summary: string;
	classification: ClassificationResult;
	suggestedTag: OutputTag;
	status: ItemStatus;
	createdAt: string;
	approvedAt?: string;
	finalTag?: OutputTag;
}

export interface ApprovalLogEntry {
	id: string;
	itemId: string;
	sourceFile: string;
	action: ApprovalAction;
	originalTag: OutputTag;
	finalTag: OutputTag;
	timestamp: string;
}

export interface ClassifyLogEntry {
	id: string;
	sourceFile: string;
	title: string;
	classification: ClassificationResult;
	tag: OutputTag;
	timestamp: string;
}

// ========== 文件读写 ==========

/**
 * 从 vault 读取 JSON 文件，不存在则返回默认值
 */
export async function readJson<T>(vault: Vault, filePath: string, defaultValue: T): Promise<T> {
	const normalPath = normalizePath(filePath);
	if (await vault.adapter.exists(normalPath)) {
		const content = await vault.adapter.read(normalPath);
		try {
			return JSON.parse(content) as T;
		} catch {
			console.error(`元演引擎: JSON 解析失败 ${normalPath}`);
			return defaultValue;
		}
	}
	return defaultValue;
}

/**
 * 写入 JSON 文件到 vault
 */
export async function writeJson<T>(vault: Vault, filePath: string, data: T): Promise<void> {
	const normalPath = normalizePath(filePath);
	await vault.adapter.write(normalPath, JSON.stringify(data, null, 2));
}

// ========== 便捷方法 ==========

export async function readPendingItems(vault: Vault): Promise<PendingItem[]> {
	return readJson<PendingItem[]>(vault, PENDING_FILE, []);
}

export async function writePendingItems(vault: Vault, items: PendingItem[]): Promise<void> {
	return writeJson(vault, PENDING_FILE, items);
}

export async function readApprovalLog(vault: Vault): Promise<ApprovalLogEntry[]> {
	return readJson<ApprovalLogEntry[]>(vault, APPROVAL_LOG_FILE, []);
}

export async function writeApprovalLog(vault: Vault, entries: ApprovalLogEntry[]): Promise<void> {
	return writeJson(vault, APPROVAL_LOG_FILE, entries);
}

export async function readClassifyLog(vault: Vault): Promise<ClassifyLogEntry[]> {
	return readJson<ClassifyLogEntry[]>(vault, CLASSIFY_LOG_FILE, []);
}

export async function appendToApprovalLog(vault: Vault, entry: ApprovalLogEntry): Promise<void> {
	const log = await readApprovalLog(vault);
	log.push(entry);
	await writeApprovalLog(vault, log);
}

export async function appendToClassifyLog(vault: Vault, entry: ClassifyLogEntry): Promise<void> {
	const log = await readClassifyLog(vault);
	log.push(entry);
	await writeClassifyLog(vault, log);
}

/**
 * 标记 pending item 为已处理
 */
export async function updatePendingItem(
	vault: Vault,
	itemId: string,
	updates: Partial<PendingItem>
): Promise<PendingItem | null> {
	const items = await readPendingItems(vault);
	const idx = items.findIndex(i => i.id === itemId);
	if (idx === -1) return null;
	items[idx] = { ...items[idx], ...updates };
	await writePendingItems(vault, items);
	return items[idx];
}

/**
 * 检查文件是否在日输入目录内
 */
export function isInDailyInputDir(filePath: string): boolean {
	const normalPath = normalizePath(filePath);
	const inputDir = normalizePath(DAILY_INPUT_DIR);
	return normalPath.startsWith(inputDir) && normalPath.endsWith(".md");
}

/**
 * 检查文件是否在捕获目录内
 */
export function isInCaptureDir(filePath: string): boolean {
	const normalPath = normalizePath(filePath);
	const captureDir = normalizePath(CAPTURE_DIR);
	return normalPath.startsWith(captureDir) && normalPath.endsWith(".md");
}

/**
 * 移动文件到目标目录（使用 vault.adapter 跨平台实现）
 * 如果目标文件已存在则自动加数字后缀
 */
export async function moveFile(
	vault: Vault,
	sourcePath: string,
	targetDir: string
): Promise<string | null> {
	const sourceNormal = normalizePath(sourcePath);
	const fileName = sourceNormal.split("/").pop() || "";
	const baseName = fileName.replace(/\.md$/, "");
	const targetBase = normalizePath(`${targetDir}/${fileName}`);

	// 检查目标是否已存在
	let targetPath = targetBase;
	let counter = 1;
	while (await vault.adapter.exists(normalizePath(targetPath))) {
		targetPath = normalizePath(`${targetDir}/${baseName}_${counter}.md`);
		counter++;
	}

	try {
		await vault.adapter.rename(sourceNormal, targetPath);
		return targetPath;
	} catch (e) {
		console.error("元演引擎: 文件移动失败", sourceNormal, "→", targetPath, e);
		return null;
	}
}
