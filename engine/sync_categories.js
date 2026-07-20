// 用 Node.js 直接调用飞书 CLI SDK，绕过 cmd.exe 编码问题
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const LARK_CLI = "C:\\Users\\Administrator\\nodejs\\node-v20.18.0-win-x64\\lark-cli.cmd";
const VAULT = "D:\\Documents\\Documents\\Obsidian Vault\\🧠 元演心智";

const NEW_BASE = "S4S0bXtB4adQkLsBbHmclNOfn0N"; // Obsidian 知识库
const TABLES = [
  { name: "口播", base: NEW_BASE, table: "tblQs29hF8MKcZQb", dir: "🍎 成品区/发布物", filter: (s) => s.includes("口播") },
  { name: "渔樵问对", base: NEW_BASE, table: "tbl22LHTQCExWW8L", dir: "🍎 成品区/发布物", filter: (s) => s.includes("渔樵") },
  { name: "工具", base: NEW_BASE, table: "tblaLyr4POoDkme7", dir: "🍎 成品区/工具", filter: (s) => !s.includes("去主观") },
  { name: "认知心法", base: NEW_BASE, table: "tblF26ZOig8jWIZT", dir: "🍎 成品区/工具", filter: (s) => s.includes("去主观") },
];

function readMD(filePath) {
  const content = fs.readFileSync(filePath, "utf-8");
  let title = path.basename(filePath, ".md");
  for (const line of content.split("\n")) {
    const s = line.trim();
    if (s.startsWith("# ") && !s.startsWith("## ")) {
      title = s.slice(2).trim();
      break;
    }
  }
  return { title, body: content.slice(0, 5000) };
}

function runCLI(base, table, data) {
  const tmpFile = path.join(__dirname, ".tmp_sync.json");
  fs.writeFileSync(tmpFile, JSON.stringify(data), "utf-8");
  const relPath = "./.tmp_sync.json";
  const cmd = `"${LARK_CLI}" base +record-upsert --base-token ${base} --table-id ${table} --json "@${relPath}" --as user --format json`;
  try {
    const out = execSync(cmd, { encoding: "utf-8", timeout: 15000, cwd: __dirname });
    fs.unlinkSync(tmpFile);
    return JSON.parse(out);
  } catch (e) {
    try { fs.unlinkSync(tmpFile); } catch(_) {}
    return { _error: e.message.slice(0, 100) };
  }
}

let total = 0;
for (const t of TABLES) {
  const dirPath = path.join(VAULT, t.dir);
  if (!fs.existsSync(dirPath)) { console.log(`SKIP ${t.name}`); continue; }
  const files = fs.readdirSync(dirPath)
    .filter((f) => f.endsWith(".md") && t.filter(f))
    .sort();
  console.log(`\n=== ${t.name} (${files.length}) ===`);
  for (const f of files) {
    const { title, body } = readMD(path.join(dirPath, f));
    const r = runCLI(t.base, t.table, { 标题: title, 正文: body });
    if (r.ok) { total++; console.log(`  OK: ${title.slice(0, 28)}`); }
    else console.log(`  ~ ${title.slice(0, 28)}: ${(r._error || "").slice(0, 60)}`);
  }
}

console.log(`\nOK, ${total} written`);
TABLES.forEach((t) => console.log(`  ${t.name}: https://bcn9k7tysatb.feishu.cn/base/${t.base}`));
