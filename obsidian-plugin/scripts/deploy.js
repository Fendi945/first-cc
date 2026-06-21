/**
 * Deploy plugin to vault .obsidian/plugins/yuanyan-engine/
 */
const fs = require("fs");
const path = require("path");

const VAULT_PLUGIN_DIR = path.join(
	"D:\\Documents\\Documents\\Obsidian Vault",
	".obsidian",
	"plugins",
	"yuanyan-engine"
);

const files = ["main.js", "manifest.json", "styles.css"];

if (!fs.existsSync(VAULT_PLUGIN_DIR)) {
	fs.mkdirSync(VAULT_PLUGIN_DIR, { recursive: true });
}

for (const file of files) {
	const src = path.join(__dirname, "..", file);
	const dest = path.join(VAULT_PLUGIN_DIR, file);
	if (fs.existsSync(src)) {
		fs.copyFileSync(src, dest);
		console.log(`  ✓ ${file}`);
	} else {
		console.log(`  - ${file} (not found, skipping)`);
	}
}

console.log(`\nDeployed to: ${VAULT_PLUGIN_DIR}`);
