/** 元演引擎 — Obsidian 插件入口 */

import { App, Plugin, TFile, Notice, normalizePath, WorkspaceLeaf, Modal, Setting } from "obsidian";
import { ApprovalView, APPROVAL_VIEW_TYPE } from "./views/ApprovalView";
import { YuanYanSettingTab, YuanYanSettings, DEFAULT_SETTINGS } from "./settings";
import { classifyContent } from "./classifier";
import {
	isInDailyInputDir,
	readPendingItems,
	writePendingItems,
	appendToClassifyLog,
	PendingItem,
	DAILY_INPUT_DIR,
	CAPTURE_DIR,
	isInCaptureDir,
	moveFile,
} from "./data";
import { executeProduction } from "./producer";

const PROCESSED_FILES_KEY = "processedFiles";

// ========== Flomo 确认弹窗 ==========

class FlomoConfirmModal extends Modal {
	private title: string;
	private preview: string;
	private filePath: string;
	private plugin: YuanYanPlugin;
	private onConfirm: () => void;
	private onDecline: () => void;

	constructor(
		app: App,
		plugin: YuanYanPlugin,
		filePath: string,
		title: string,
		preview: string,
		onConfirm: () => void,
		onDecline: () => void
	) {
		super(app);
		this.plugin = plugin;
		this.filePath = filePath;
		this.title = title;
		this.preview = preview;
		this.onConfirm = onConfirm;
		this.onDecline = onDecline;
	}

	onOpen(): void {
		const { contentEl } = this;

		contentEl.empty();
		contentEl.addClass("flomo-confirm-modal");

		contentEl.createEl("h2", { text: "📮 检测到 Flomo 新笔记" });

		contentEl.createEl("h3", { text: this.title, cls: "flomo-note-title" });

		const previewEl = contentEl.createEl("div", { cls: "flomo-preview" });
		previewEl.createEl("p", { text: this.preview.slice(0, 200) });
		if (this.preview.length > 200) {
			previewEl.createEl("p", { text: "......", cls: "flomo-preview-more" });
		}

		new Setting(contentEl)
			.addButton(button =>
				button
					.setButtonText("❌ 留在捕获")
					.setWarning()
					.onClick(() => {
						this.close();
						this.onDecline();
					})
			)
			.addButton(button =>
				button
					.setButtonText("✅ 移入日输入")
					.setCta()
					.onClick(() => {
						this.close();
						this.onConfirm();
					})
			);
	}

	onClose(): void {
		const { contentEl } = this;
		contentEl.empty();
	}
}

export default class YuanYanPlugin extends Plugin {
	settings!: YuanYanSettings;
	engineStatus: "idle" | "running" | "error" = "idle";
	private processedFiles: Set<string> = new Set();
	private debounceTimer: number | null = null;
	private pendingChanges: Map<string, number> = new Map();
	// ── 新增 Flomo 相关 ──
	private declinedFiles: Set<string> = new Set();
	private flomoCheckTimer: number | null = null;

	async onload(): Promise<void> {
		await this.loadSettings();
		await this.loadProcessedState();
		await this.loadDeclinedState();

		this.registerView(APPROVAL_VIEW_TYPE, (leaf: WorkspaceLeaf) => new ApprovalView(leaf, this));

		const ribbonIcon = this.addRibbonIcon("list-checks", "元演引擎 · 审批面板", async () => {
			await this.openApprovalView();
		});
		ribbonIcon.addClass("yuanyan-ribbon-icon");

		this.addCommand({
			id: "open-approval-panel",
			name: "打开审批面板",
			callback: async () => { await this.openApprovalView(); },
		});

		this.addCommand({
			id: "classify-unprocessed",
			name: "分类未处理的日输入",
			callback: async () => {
				await this.processExistingFiles();
				new Notice("元演引擎: 分类完成");
			},
		});

		// 新命令：快捷格式化发布
		this.addCommand({
			id: "format-publish",
			name: "格式化发布日输入 → 公众号（跳过 AI 审批）",
			callback: async () => {
				await this.quickFormatPublish();
			},
		});

		this.addCommand({
			id: "test-api-debug",
			name: "1. 测试 API 连接（调试用）",
			callback: async () => { await this.testApiConnection(); },
		});

		this.addCommand({
			id: "show-plugin-state",
			name: "2. 查看插件状态（调试用）",
			callback: async () => { await this.showState(); },
		});

		this.addSettingTab(new YuanYanSettingTab(this.app, this));

		this.registerEvent(
			this.app.vault.on("create", (file) => {
				if (file instanceof TFile) this.onFileChange(file);
			})
		);
		this.registerEvent(
			this.app.vault.on("modify", (file) => {
				if (file instanceof TFile) this.onFileChange(file);
			})
		);

		if (this.settings.enabled && this.settings.deepseekApiKey) {
			this.engineStatus = "running";
			setTimeout(() => this.processExistingFiles(), 3000);
			// 启动 Flomo 捕获目录监控
			if (this.settings.flomoSyncEnabled) {
				this.startFlomoCaptureWatch();
			}
		}
	}

	onunload(): void {
		console.log("元演引擎: 插件卸载");
	}

	async loadSettings(): Promise<void> {
		const data = await this.loadData();
		this.settings = Object.assign({}, DEFAULT_SETTINGS, data);
	}

	async saveSettings(): Promise<void> {
		await this.saveData(this.settings);
	}

	private async loadProcessedState(): Promise<void> {
		const data = await this.loadData();
		if (data?.[PROCESSED_FILES_KEY]) {
			this.processedFiles = new Set(data[PROCESSED_FILES_KEY]);
		}
	}

	private async saveProcessedState(): Promise<void> {
		const data = (await this.loadData()) || {};
		data[PROCESSED_FILES_KEY] = Array.from(this.processedFiles);
		await this.saveData(data);
	}

	// ========== 快捷格式化发布（跳过 AI 审批） ==========

	async quickFormatPublish(): Promise<void> {
		if (!this.settings.wechatEnabled || !this.settings.wechatAppId || !this.settings.wechatAppSecret) {
			new Notice("请先在设置中配置公众号信息（AppID + AppSecret）");
			return;
		}

		const inputDir = normalizePath(DAILY_INPUT_DIR);
		if (!(await this.app.vault.adapter.exists(inputDir))) {
			new Notice("日输入目录不存在");
			return;
		}

		const files = this.app.vault.getFiles().filter(f =>
			isInDailyInputDir(f.path) && !this.processedFiles.has(f.path)
		);

		if (files.length === 0) {
			new Notice("没有未处理的日输入文件");
			return;
		}

		new Notice(`正在格式化发布 ${files.length} 个文件...`);

		for (const file of files) {
			try {
				const content = await this.app.vault.read(file);
				if (!content.trim()) continue;

				const title = file.name.replace(/\.md$/, "");
				const itemId = `yy-pub-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

				// 创建占位的 pending item
				const pendingItems = await readPendingItems(this.app.vault);
				const newItem: PendingItem = {
					id: itemId,
					sourceFile: file.path,
					title: title,
					summary: "",
					classification: { ontology: "日常输出", ability: "写作", rule: "知行合一", event: "创作", rationale: "格式化发布" },
					suggestedTag: "publish",
					status: "pending",
					createdAt: new Date().toISOString(),
				};
				pendingItems.unshift(newItem);
				await writePendingItems(this.app.vault, pendingItems);

				// 直接执行发布
				await executeProduction(this.app.vault, newItem, "publish", {
					apiKey: this.settings.deepseekApiKey,
					model: this.settings.deepseekModel,
					wechatAppId: this.settings.wechatAppId,
					wechatAppSecret: this.settings.wechatAppSecret,
					wechatEnabled: this.settings.wechatEnabled,
					wechatCoverMediaId: this.settings.wechatCoverMediaId || "",
				});

				// 标记已处理
				this.processedFiles.add(file.path);
				await this.saveProcessedState();

			} catch (e: any) {
				new Notice(`「${file.name}」发布失败: ${e.message}`);
			}
		}

		new Notice("格式化发布完成");
		this.refreshApprovalView();
	}

	private async showState(): Promise<void> {
		const data = await this.loadData();
		const msg =
			`启用: ${this.settings.enabled}` +
			`\nAPI Key: ${this.settings.deepseekApiKey ? this.settings.deepseekApiKey.slice(0, 10) + "..." : "未设置"}` +
			`\n模型: ${this.settings.deepseekModel}` +
			`\n状态: ${this.engineStatus}` +
			`\n已处理文件: ${this.processedFiles.size}个`;
		new Notice(msg, 8000);
	}

	private async testApiConnection(): Promise<void> {
		if (!this.settings.deepseekApiKey) {
			new Notice("请先在设置中配置 API Key");
			return;
		}

		try {
			const files = this.app.vault.getFiles().filter(f => isInDailyInputDir(f.path));
			if (files.length === 0) {
				new Notice("未找到日输入文件");
				return;
			}
			const file = files[0];
			const content = await this.app.vault.read(file);

			const https = require("https");
			const systemPrompt = `你是一个分类引擎。请对以下日输入内容进行四层分类（本体/能力/规则/事件），判断产出标签（article/video/tool/explore/none）。返回JSON。`;

			const body = JSON.stringify({
				model: this.settings.deepseekModel,
				messages: [
					{ role: "system", content: systemPrompt },
					{ role: "user", content: `文件：${file.name}\n内容：${content}` }
				],
				temperature: 0.3,
				max_tokens: 2000,
			});

			const result = await new Promise<string>((resolve, reject) => {
				const req = https.request({
					hostname: "api.deepseek.com",
					path: "/v1/chat/completions",
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						"Authorization": `Bearer ${this.settings.deepseekApiKey}`,
						"Content-Length": Buffer.byteLength(body),
					},
				}, (res: any) => {
					let data = "";
					res.on("data", (chunk: string) => { data += chunk; });
					res.on("end", () => {
						resolve(`状态=${res.statusCode} | 数据=${data.slice(0, 500)}`);
					});
				});
				req.on("error", (e: Error) => reject(e.message));
				req.write(body);
				req.end();
			});

			new Notice(`完整分类测试:\n${result}`, 10000);
		} catch (e: any) {
			new Notice(`测试失败:\n${e.message}`, 8000);
		}
	}

	// ========== 文件变化处理 ==========

	private onFileChange(file: TFile): void {
		if (!this.settings.enabled || !this.settings.deepseekApiKey) return;
		// 捕获目录的文件由 checkCaptureDir 处理，不走 AI 分类
		if (isInCaptureDir(file.path)) return;
		if (!isInDailyInputDir(file.path)) return;

		const now = Date.now();
		this.pendingChanges.set(file.path, now);

		if (this.debounceTimer !== null) {
			window.clearTimeout(this.debounceTimer);
		}

		this.debounceTimer = window.setTimeout(async () => {
			const toProcess: string[] = [];
			for (const [path, time] of this.pendingChanges) {
				if (Date.now() - time >= 2500) {
					toProcess.push(path);
				}
			}
			this.pendingChanges.clear();
			for (const path of toProcess) {
				await this.processFile(path);
			}
		}, 3000);
	}

	/** 处理单个文件（走 AI 分类） */
	private async processFile(filePath: string): Promise<void> {
		if (this.processedFiles.has(filePath)) return;

		const file = this.app.vault.getAbstractFileByPath(normalizePath(filePath));
		if (!(file instanceof TFile)) return;

		try {
			this.engineStatus = "running";
			const content = await this.app.vault.read(file);
			if (!content.trim()) return;

			const fileName = file.name;
			const result = await classifyContent(
				this.settings.deepseekApiKey,
				content,
				fileName,
				this.settings.deepseekModel
			);

			const itemId = `yy-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

			const pendingItems = await readPendingItems(this.app.vault);
			const newItem: PendingItem = {
				id: itemId,
				sourceFile: filePath,
				title: result.title,
				summary: result.summary,
				classification: {
					ontology: result.ontology,
					ability: result.ability,
					rule: result.rule,
					event: result.event,
					rationale: result.rationale,
				},
				suggestedTag: result.tag,
				status: "pending",
				createdAt: new Date().toISOString(),
			};
			pendingItems.unshift(newItem);
			await writePendingItems(this.app.vault, pendingItems);

			await appendToClassifyLog(this.app.vault, {
				id: itemId,
				sourceFile: filePath,
				title: result.title,
				classification: {
					ontology: result.ontology,
					ability: result.ability,
					rule: result.rule,
					event: result.event,
					rationale: result.rationale,
				},
				tag: result.tag,
				timestamp: new Date().toISOString(),
			});

			this.processedFiles.add(filePath);
			await this.saveProcessedState();

			new Notice(`元演引擎: 已分类「${result.title}」→ ${result.tag}`);
			this.refreshApprovalView();
		} catch (e: any) {
			this.engineStatus = "error";
			const errMsg = e.message || String(e);
			const errStack = e.stack || "";
			console.error("元演引擎错误:", filePath, errMsg, errStack);
			new Notice(`元演引擎: 分类失败 — ${errMsg}`, 10000);
		}
	}

	/** 处理所有未分类的日输入文件 */
	private async processExistingFiles(): Promise<void> {
		if (!this.settings.enabled || !this.settings.deepseekApiKey) {
			new Notice("元演引擎: 请先在设置中配置 API Key");
			return;
		}

		const inputDir = normalizePath(DAILY_INPUT_DIR);
		if (!(await this.app.vault.adapter.exists(inputDir))) {
			return;
		}

		const files = this.app.vault.getFiles().filter((f) => {
			return isInDailyInputDir(f.path) && !this.processedFiles.has(f.path);
		});

		if (files.length === 0) return;

		new Notice(`元演引擎: 正在分类 ${files.length} 个文件...`);

		for (const file of files) {
			await this.processFile(file.path);
			await new Promise((r) => setTimeout(r, 500));
		}
	}

	// ========== Flomo 同步管理 ==========

	async startFlomoSync(): Promise<void> {
		// 通过引擎 API 触发（引擎后台运行）
		try {
			const resp = await fetch("http://127.0.0.1:8765/api/flomo/sync", { method: "POST" });
			if (resp.ok) {
				new Notice("Flomo 同步已启用（引擎后台定时运行）");
			}
		} catch {
			new Notice("Flomo 同步：引擎未运行，仅监控捕获目录");
		}
		this.startFlomoCaptureWatch();
	}

	stopFlomoSync(): void {
		if (this.flomoCheckTimer !== null) {
			window.clearInterval(this.flomoCheckTimer);
			this.flomoCheckTimer = null;
		}
		new Notice("Flomo 同步已停用");
	}

	async triggerFlomoSync(): Promise<void> {
		try {
			const resp = await fetch("http://127.0.0.1:8765/api/flomo/sync", { method: "POST" });
			if (resp.ok) {
				const data = await resp.json();
				new Notice(`Flomo 同步完成: 导入 ${data.imported || 0} 条`);
			} else {
				new Notice("Flomo 同步失败: 引擎未运行？");
			}
		} catch {
			new Notice("Flomo 同步失败: 无法连接引擎");
		}
	}

	// ========== 捕获目录监控 ==========

	private startFlomoCaptureWatch(): void {
		// 每 30 秒检查一次捕获目录的新文件
		if (this.flomoCheckTimer !== null) {
			window.clearInterval(this.flomoCheckTimer);
		}
		this.flomoCheckTimer = window.setInterval(() => {
			this.checkCaptureDir();
		}, 30000);
	}

	private async checkCaptureDir(): Promise<void> {
		const captureDir = normalizePath(CAPTURE_DIR);
		if (!(await this.app.vault.adapter.exists(captureDir))) {
			return;
		}

		const files = this.app.vault.getFiles().filter(f =>
			isInCaptureDir(f.path) &&
			!this.declinedFiles.has(f.path)
		);

		for (const file of files) {
			await this.promptFlomoConfirm(file);
			return; // 每次只处理一个，避免弹窗堆积
		}
	}

	private async promptFlomoConfirm(file: TFile): Promise<void> {
		const content = await this.app.vault.read(file);
		const title = file.name.replace(/\.md$/, "");

		return new Promise((resolve) => {
			const modal = new FlomoConfirmModal(
				this.app,
				this,
				file.path,
				title,
				content.replace(/^---[\s\S]*?---\n/, ""),  // 去掉 frontmatter
				async () => {
					// 确认：移入日输入
					const targetDir = normalizePath(DAILY_INPUT_DIR);
					const result = await moveFile(this.app.vault, file.path, targetDir);
					if (result) {
						new Notice(`已移入日输入: ${title}`);
						// 立即触发分类
						await this.processFile(result);
					} else {
						new Notice(`移动失败: ${title}`, 5000);
					}
					resolve();
				},
				() => {
					// 拒绝：记录 declined
					this.declinedFiles.add(file.path);
					this.saveDeclinedState();
					new Notice(`留在捕获: ${title}`);
					resolve();
				}
			);
			modal.open();
		});
	}

	// ========== Declined 持久化 ==========

	private async loadDeclinedState(): Promise<void> {
		const data = await this.loadData();
		if (data?.declinedFiles) {
			this.declinedFiles = new Set(data.declinedFiles);
		}
	}

	private async saveDeclinedState(): Promise<void> {
		const data = (await this.loadData()) || {};
		data.declinedFiles = Array.from(this.declinedFiles);
		await this.saveData(data);
	}

	// ========== 视图管理 ==========

	async openApprovalView(): Promise<void> {
		const { workspace } = this.app;
		let leaf = workspace.getLeavesOfType(APPROVAL_VIEW_TYPE).first();
		if (!leaf) {
			leaf = workspace.getRightLeaf(false);
			if (leaf) {
				await leaf.setViewState({ type: APPROVAL_VIEW_TYPE, active: true });
			}
		}
		if (leaf) {
			workspace.revealLeaf(leaf);
		}
	}

	private refreshApprovalView(): void {
		const leaves = this.app.workspace.getLeavesOfType(APPROVAL_VIEW_TYPE);
		for (const leaf of leaves) {
			if (leaf.view instanceof ApprovalView) {
				leaf.view.render();
			}
		}
	}
}
