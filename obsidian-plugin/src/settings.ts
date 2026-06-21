/** 元演引擎 — 设置面板 */

import { PluginSettingTab, Setting, App } from "obsidian";
import type YuanYanPlugin from "./main";

export interface YuanYanSettings {
	deepseekApiKey: string;
	deepseekModel: string;
	enabled: boolean;
	wechatAppId: string;
	wechatAppSecret: string;
	wechatEnabled: boolean;
	wechatCoverMediaId: string;
	flomoApiKey: string;
	flomoSyncEnabled: boolean;
}

export const DEFAULT_SETTINGS: YuanYanSettings = {
	deepseekApiKey: "",
	deepseekModel: "deepseek-chat",
	enabled: true,
	wechatAppId: "",
	wechatAppSecret: "",
	wechatEnabled: false,
	wechatCoverMediaId: "",
	flomoApiKey: "",
	flomoSyncEnabled: false,
};

export class YuanYanSettingTab extends PluginSettingTab {
	private plugin: YuanYanPlugin;

	constructor(app: App, plugin: YuanYanPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const { containerEl } = this;
		containerEl.empty();

		containerEl.createEl("h2", { text: "元演引擎设置" });

		// ── 引擎开关 ──
		new Setting(containerEl)
			.setName("启用引擎")
			.setDesc("开启/关闭自动分类和生产功能")
			.addToggle(toggle =>
				toggle
					.setValue(this.plugin.settings.enabled)
					.onChange(async value => {
						this.plugin.settings.enabled = value;
						await this.plugin.saveSettings();
					})
			);

		// ── DeepSeek 配置 ──
		containerEl.createEl("h3", { text: "DeepSeek API 配置" });

		new Setting(containerEl)
			.setName("API Key")
			.setDesc("用于分类和文章生成的 DeepSeek API 密钥")
			.addText(text =>
				text
					.setPlaceholder("sk-...")
					.setValue(this.plugin.settings.deepseekApiKey)
					.onChange(async value => {
						this.plugin.settings.deepseekApiKey = value.trim();
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("模型")
			.setDesc("模型名称，如 deepseek-v4-flash")
			.addText(text =>
				text
					.setPlaceholder("deepseek-v4-flash")
					.setValue(this.plugin.settings.deepseekModel)
					.onChange(async value => {
						this.plugin.settings.deepseekModel = value.trim() || "deepseek-v4-flash";
						await this.plugin.saveSettings();
					})
			);

		// ── 公众号配置 ──
		containerEl.createEl("h3", { text: "微信公众号配置" });

		new Setting(containerEl)
			.setName("启用公众号推送")
			.setDesc("审批通过文章后自动推送到公众号草稿箱")
			.addToggle(toggle =>
				toggle
					.setValue(this.plugin.settings.wechatEnabled)
					.onChange(async value => {
						this.plugin.settings.wechatEnabled = value;
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("AppID")
			.setDesc("公众号开发信息中的 AppID")
			.addText(text =>
				text
					.setPlaceholder("wx...")
					.setValue(this.plugin.settings.wechatAppId)
					.onChange(async value => {
						this.plugin.settings.wechatAppId = value.trim();
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("AppSecret")
			.setDesc("公众号开发信息中的 AppSecret")
			.addText(text =>
				text
					.setPlaceholder("...")
					.setValue(this.plugin.settings.wechatAppSecret)
					.onChange(async value => {
						this.plugin.settings.wechatAppSecret = value.trim();
						await this.plugin.saveSettings();
					})
			);

		// ── Flomo 同步配置 ──
		containerEl.createEl("h3", { text: "Flomo 同步配置" });

		new Setting(containerEl)
			.setName("启用 Flomo 同步")
			.setDesc("定时从 Flomo 拉取笔记到捕获目录")
			.addToggle(toggle =>
				toggle
					.setValue(this.plugin.settings.flomoSyncEnabled)
					.onChange(async value => {
						this.plugin.settings.flomoSyncEnabled = value;
						await this.plugin.saveSettings();
						if (value) {
							this.plugin.startFlomoSync();
						} else {
							this.plugin.stopFlomoSync();
						}
					})
			);

		new Setting(containerEl)
			.setName("Flomo API Key")
			.setDesc("Flomo Pro 用户的 API 密钥（设置 → API → 复制）")
			.addText(text =>
				text
					.setPlaceholder("输入 Flomo API Key")
					.setValue(this.plugin.settings.flomoApiKey)
					.onChange(async value => {
						this.plugin.settings.flomoApiKey = value.trim();
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("立即同步")
			.setDesc("手动触发一次 Flomo 笔记同步")
			.addButton(button =>
				button
					.setButtonText("🔄 同步")
					.setCta()
					.onClick(async () => {
						button.setDisabled(true);
						button.setButtonText("同步中...");
						await this.plugin.triggerFlomoSync();
						button.setButtonText("✅ 完成");
						setTimeout(() => {
							button.setButtonText("🔄 同步");
							button.setDisabled(false);
						}, 2000);
					})
			);
	}
}
