/** Yuanyan Engine - Approval Panel View */

import { ItemView, WorkspaceLeaf, Notice } from "obsidian";
import type { PendingItem, OutputTag, ApprovalAction } from "../data";
import { readPendingItems, updatePendingItem, appendToApprovalLog } from "../data";
import { tagLabel, tagEmoji } from "../classifier";
import { executeProduction } from "../producer";
import type YuanYanPlugin from "../main";

export const APPROVAL_VIEW_TYPE = "yuanyan-approval";

export class ApprovalView extends ItemView {
	private plugin: YuanYanPlugin;

	constructor(leaf: WorkspaceLeaf, plugin: YuanYanPlugin) {
		super(leaf);
		this.plugin = plugin;
	}

	getViewType(): string { return APPROVAL_VIEW_TYPE; }
	getDisplayText(): string { return "Yuanyan Approval"; }
	getIcon(): string { return "check-check"; }

	async onload(): Promise<void> {
		super.onload();
		this.contentEl.empty();
		this.contentEl.addClass("yuanyan-approval-view");
		await this.render();
	}

	async render(): Promise<void> {
		this.contentEl.empty();

		const h = this.contentEl.createEl("div", { cls: "yuanyan-header" });
		h.createEl("h2", { text: "元演引擎 · 审批面板" });

		const items = await readPendingItems(this.plugin.app.vault);
		const pending = items.filter(i => i.status === "pending");
		const processed = items.filter(i => i.status !== "pending");

		if (pending.length === 0) {
			this.contentEl.createEl("div", { cls: "yuanyan-empty" }).createSpan({ text: "暂无待审批项" });
		} else {
			const sec = this.contentEl.createEl("div", { cls: "yuanyan-section" });
			sec.createEl("h3", { text: `待审批 (${pending.length})` });
			for (const item of pending) {
				const card = sec.createEl("div", { cls: "yuanyan-card" });
				this.renderCard(card, item);
			}
		}

		if (processed.length > 0) {
			const sec = this.contentEl.createEl("div", { cls: "yuanyan-section" });
			sec.createEl("h3", { text: `已处理 (${processed.length})` });
			for (const item of processed.slice(0, 10)) {
				sec.createEl("div", { cls: "yuanyan-processed-entry" }).setText(
					item.title + (item.finalTag ? ` ${tagEmoji(item.finalTag)}` : "")
				);
			}
		}
	}

	private renderCard(container: HTMLElement, item: PendingItem): void {
		container.createEl("div", { text: item.title, cls: "yuanyan-card-title" });
		if (item.summary) container.createEl("div", { text: item.summary, cls: "yuanyan-card-summary" });
		if (item.classification?.rationale) {
			container.createEl("div", {
				text: `[${tagLabel(item.suggestedTag)}] ${item.classification.rationale}`,
				cls: "yuanyan-card-rationale"
			});
		}

		const actions = container.createEl("div", { cls: "yuanyan-actions" });

		// 原有按钮
		this.addBtn(actions, "✅ 通过", async () => this.approveItem(item, item.suggestedTag));
		this.addBtn(actions, "❌ 拒绝", async () => this.rejectItem(item));
		this.addBtn(actions, "📹 视频", async () => this.approveItem(item, "video"));
		this.addBtn(actions, "📝 文章", async () => this.approveItem(item, "article"));
		this.addBtn(actions, "🔧 工具", async () => this.approveItem(item, "tool"));

		// 新按钮：格式发布（不走 AI）
		this.addBtn(actions, "📢 格式发布", async () => this.approveItem(item, "publish"), "#5a8e6a");
	}

	private addBtn(
		container: HTMLElement,
		label: string,
		onClick: () => Promise<void>,
		color?: string
	): void {
		const btn = container.createEl("button", { cls: "yuanyan-btn-approve" });
		btn.setText(label);
		if (color) btn.style.borderColor = color;
		btn.onclick = async () => {
			btn.setAttr("disabled", "true");
			btn.setText("...");
			try { await onClick(); } catch (e: any) {
				new Notice(`Error: ${e.message}`);
				btn.removeAttribute("disabled");
				btn.setText(label);
			}
		};
	}

	private async approveItem(item: PendingItem, finalTag: OutputTag): Promise<void> {
		const action: ApprovalAction = finalTag === "publish" ? "publish"
			: finalTag === item.suggestedTag ? "approve" : "convert";

		await appendToApprovalLog(this.plugin.app.vault, {
			id: crypto.randomUUID(), itemId: item.id, sourceFile: item.sourceFile,
			action, originalTag: item.suggestedTag, finalTag, timestamp: new Date().toISOString(),
		});

		await executeProduction(this.plugin.app.vault, item, finalTag, {
			apiKey: this.plugin.settings.deepseekApiKey,
			model: this.plugin.settings.deepseekModel,
			wechatAppId: this.plugin.settings.wechatAppId,
			wechatAppSecret: this.plugin.settings.wechatAppSecret,
			wechatEnabled: this.plugin.settings.wechatEnabled,
			wechatCoverMediaId: this.plugin.settings.wechatCoverMediaId,
		});

		await updatePendingItem(this.plugin.app.vault, item.id, {
			status: "approved", approvedAt: new Date().toISOString(), finalTag,
		});
		await this.render();
	}

	private async rejectItem(item: PendingItem): Promise<void> {
		await appendToApprovalLog(this.plugin.app.vault, {
			id: crypto.randomUUID(), itemId: item.id, sourceFile: item.sourceFile,
			action: "reject", originalTag: item.suggestedTag, finalTag: "none", timestamp: new Date().toISOString(),
		});
		await updatePendingItem(this.plugin.app.vault, item.id, {
			status: "rejected", approvedAt: new Date().toISOString(), finalTag: "none",
		});
		new Notice(`Rejected: ${item.title}`);
		await this.render();
	}
}
