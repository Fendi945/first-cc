// 从旧 4 表读取数据，写入 Obsidian 知识库新表
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const LARK_CLI = "C:\\Users\\Administrator\\nodejs\\node-v20.18.0-win-x64\\lark-cli.cmd";
const NEW_BASE = "S4S0bXtB4adQkLsBbHmclNOfn0N";

const TABLES = [
  { name: "口播", oldBase: "P5szbKkrEarkfFsQEBDcsjzanld", oldTable: "tbl7XNWsbHGnqPYv", newTable: "tblQs29hF8MKcZQb" },
  { name: "渔樵问对", oldBase: "QhpRb0IoOakSXfsPe7Ic2TJRnBg", oldTable: "tbltiP4IsxNC3X69", newTable: "tbl22LHTQCExWW8L" },
  { name: "工具", oldBase: "WoGrbsdSBaIDw4sQoGOc3n9Knpb", oldTable: "tblZIXHRTsCo3UHN", newTable: "tblaLyr4POoDkme7" },
  { name: "认知心法", oldBase: "QtGqbzoIMaTu25s0z6pc4DTJnvd", oldTable: "tblcY7iT99e4qsJD", newTable: "tblF26ZOig8jWIZT" },
];

function cliWithFile(base, table, data) {
  const tmp = path.join(__dirname, ".tmp_data.json");
  fs.writeFileSync(tmp, JSON.stringify(data), "utf-8");
  const cmd = `"${LARK_CLI}" base +record-upsert --base-token ${base} --table-id ${table} --json "./.tmp_data.json" --as user --format json`;
  try {
    const out = execSync(cmd, { encoding: "utf-8", timeout: 15000, cwd: __dirname });
    return JSON.parse(out);
  } catch(e) {
    try { return JSON.parse(e.stdout || "{}"); }
    catch { return { _error: e.message.slice(0,100) }; }
  } finally {
    try { fs.unlinkSync(tmp); } catch {}
  }
}

function getRecords(base, table) {
  const tmp = path.join(__dirname, ".tmp_out.json");
  const cmd = `"${LARK_CLI}" base +record-list --base-token ${base} --table-id ${table} --as user --format json > "${tmp}"`;
  try {
    execSync(cmd, { encoding: "utf-8", timeout: 15000, cwd: __dirname });
    const raw = JSON.parse(fs.readFileSync(tmp, "utf-8"));
    if (!raw.ok || !raw.data) return [];
    const fields = raw.data.fields || [];
    const data = raw.data.data || [];
    const records = [];
    for (const row of data) {
      if (!Array.isArray(row)) continue;
      const rec = {};
      for (let i = 0; i < fields.length && i < row.length; i++) {
        let val = row[i];
        if (Array.isArray(val)) val = val.map(v => typeof v === 'string' ? v : JSON.stringify(v)).join(" ");
        if (typeof val === "string") val = val.trim();
        if (val) rec[fields[i]] = val;
      }
      if (rec["标题"]) records.push(rec);
    }
    return records;
  } catch(e) {
    console.log(`  ERROR reading: ${e.message.slice(0,80)}`);
    return [];
  } finally {
    try { fs.unlinkSync(tmp); } catch {}
  }
}

let total = 0;
for (const t of TABLES) {
  console.log(`\n=== ${t.name} ===`);
  const records = getRecords(t.oldBase, t.oldTable);
  console.log(`  读取到 ${records.length} 条`);
  for (const rec of records) {
    const r = cliWithFile(NEW_BASE, t.newTable, rec);
    if (r.ok) {
      total++;
      console.log(`  OK: ${(rec["标题"]||"").slice(0,26)}`);
    } else {
      console.log(`  ~: ${(r._error||"")}`);
    }
  }
}

console.log(`\nOK, 共同步 ${total} 条`);
console.log(`\n新位置（Obsidian 知识库基表内）:`);
for (const t of TABLES) {
  console.log(`  ${t.name}: https://bcn9k7tysatb.feishu.cn/base/${NEW_BASE}?table=${t.newTable}`);
}
