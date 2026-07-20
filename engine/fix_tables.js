// 在 Obsidian 知识库内创建 4 张表，然后迁移数据
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const LARK_CLI = "C:\\Users\\Administrator\\nodejs\\node-v20.18.0-win-x64\\lark-cli.cmd";
const BASE = "S4S0bXtB4adQkLsBbHmclNOfn0N"; // Obsidian 知识库

function cli(...args) {
  const tmpFile = path.join(__dirname, ".tmp_cli.json");
  const cmd = `"${LARK_CLI}" ${args.join(" ")} --as user --format json`;
  try {
    const out = execSync(cmd, { encoding: "utf-8", timeout: 30000, cwd: __dirname });
    return JSON.parse(out);
  } catch (e) {
    try {
      const out = e.stdout || "";
      return JSON.parse(out);
    } catch {
      return { _error: e.message.slice(0, 200) };
    }
  }
}

function cliWithFile(base_token, table_id, data) {
  const tmpFile = path.join(__dirname, ".tmp_data.json");
  fs.writeFileSync(tmpFile, JSON.stringify(data), "utf-8");
  const cmd = `"${LARK_CLI}" base +record-upsert --base-token ${base_token} --table-id ${table_id} --json "./.tmp_data.json" --as user --format json`;
  try {
    const out = execSync(cmd, { encoding: "utf-8", timeout: 30000, cwd: __dirname });
    return JSON.parse(out);
  } catch (e) {
    try { return JSON.parse(e.stdout || "{}"); }
    catch { return { _error: e.message.slice(0, 100) }; }
  } finally {
    try { fs.unlinkSync(tmpFile); } catch {}
  }
}

// 1. 获取旧 4 张表的数据
const OLD_BASES = {
  "口播": { base: "P5szbKkrEarkfFsQEBDcsjzanld", table: "tbl7XNWsbHGnqPYv" },
  "渔樵问对": { base: "QhpRb0IoOakSXfsPe7Ic2TJRnBg", table: "tbltiP4IsxNC3X69" },
  "工具": { base: "WoGrbsdSBaIDw4sQoGOc3n9Knpb", table: "tblZIXHRTsCo3UHN" },
  "认知心法": { base: "QtGqbzoIMaTu25s0z6pc4DTJnvd", table: "tblcY7iT99e4qsJD" },
};

// 收集旧数据
const tableData = {};
for (const [name, cfg] of Object.entries(OLD_BASES)) {
  const r = cli("base", "+record-list", "--base-token", cfg.base, "--table-id", cfg.table);
  const records = [];
  if (r.ok && r.data && r.data.data) {
    // 解析表格格式
    const headers = r.data.field_id_list || [];
    for (const row of r.data.data) {
      const rec = {};
      for (let i = 0; i < headers.length && i < row.length; i++) {
        const h = r.data.fields[i] || `col${i}`;
        let val = row[i];
        if (Array.isArray(val)) val = val.join(",");
        if (typeof val === "string") val = val.trim();
        if (val) rec[h] = val;
      }
      if (rec["标题"]) records.push(rec);
    }
  }
  tableData[name] = records;
  console.log(`  ${name}: ${records.length} records`);
}

// 2. 在新基表里创建 4 张表
const TABLE_NAMES = ["口播", "渔樵问对", "工具", "认知心法"];
const NEW_TABLES = {};

for (const name of TABLE_NAMES) {
  // 检查是否已存在
  const list = cli("base", "+table-list", "--base-token", BASE);
  let existing = null;
  if (list.ok && list.data && list.data.tables) {
    existing = list.data.tables.find(t => t.name === name);
  }
  if (existing) {
    NEW_TABLES[name] = existing.id;
    console.log(`  ${name}: 已存在 (${existing.id})`);
  } else {
    // 创建表和字段
    const r = cli("base", "+table-create", "--base-token", BASE, "--name", `"${name}"`,
                  "--fields", JSON.stringify([
                    { name: "标题", type: "text" },
                    { name: "正文", type: "text" },
                  ]));
    if (r.ok && r.data && r.data.table) {
      NEW_TABLES[name] = r.data.table.id;
      console.log(`  ${name}: 新建 (${r.data.table.id})`);
    } else {
      console.log(`  ${name}: FAIL - ${JSON.stringify(r.error || r)}`);
    }
  }
}

console.log("\n创建结果:", JSON.stringify(NEW_TABLES));

// 3. 写入数据
let total = 0;
for (const name of TABLE_NAMES) {
  const records = tableData[name] || [];
  const tableId = NEW_TABLES[name];
  if (!tableId) continue;
  console.log(`\n=== 写入 ${name} (${records.length} 条) ===`);
  for (const rec of records) {
    const r = cliWithFile(BASE, tableId, rec);
    if (r.ok) {
      total++;
      console.log(`  OK: ${(rec["标题"]||"").slice(0, 28)}`);
    } else {
      console.log(`  ~: ${(r._error||"").slice(0, 60)}`);
    }
  }
}

console.log(`\nOK, ${total} 条已写入 Obsidian 知识库`);

// 4. 输出链接
for (const name of TABLE_NAMES) {
  const tid = NEW_TABLES[name];
  if (tid) console.log(`  ${name}: https://bcn9k7tysatb.feishu.cn/base/${BASE}?table=${tid}`);
}
