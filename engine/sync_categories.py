""" Obsidian  4 """
import json, subprocess, tempfile, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.config import VAULT_PATH

LARK_CLI = r"C:\Users\Administrator\nodejs\node-v20.18.0-win-x64\lark-cli.cmd"

TABLES = {
    "": {
        "base": "P5szbKkrEarkfFsQEBDcsjzanld",
        "table": "tbl7XNWsbHGnqPYv",
        "dir": VAULT_PATH / " " / "",
        "filter": lambda f: "" in f.stem,
    },
    "": {
        "base": "QhpRb0IoOakSXfsPe7Ic2TJRnBg",
        "table": "tbltiP4IsxNC3X69",
        "dir": VAULT_PATH / " " / "",
        "filter": lambda f: "" in f.stem,
    },
    "": {
        "base": "WoGrbsdSBaIDw4sQoGOc3n9Knpb",
        "table": "tblZIXHRTsCo3UHN",
        "dir": VAULT_PATH / " " / "",
        "filter": lambda f: f.stem not in ("",),
    },
    "": {
        "base": "QtGqbzoIMaTu25s0z6pc4DTJnvd",
        "table": "tblcY7iT99e4qsJD",
        "dir": VAULT_PATH / " " / "",
        "filter": lambda f: "" in f.stem,
    },
}

def read_md(file_path):
    content = file_path.read_text(encoding="utf-8")
    title = file_path.stem
    for line in content.split("\n"):
        s = line.strip()
        if s.startswith("# ") and not s.startswith("##"):
            title = s[2:].strip()
            break
    return title, content[:5000]

def cli_upsert(base_token, table_id, data):
    """JSON  stdin """
    my_env = dict(os.environ)
    my_env["PYTHONIOENCODING"] = "utf-8"
    cmd = [LARK_CLI, "base", "+record-upsert",
           "--base-token", base_token,
           "--table-id", table_id,
           "--json", json.dumps(data, ensure_ascii=False),
           "--as", "user", "--format", "json"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=my_env)
        if r.returncode != 0:
            return {"_error": f"exit {r.returncode}: {r.stderr[:100]}"}
        return json.loads(r.stdout)
    except Exception as e:
        return {"_error": str(e)[:200]}

total = 0
for cat, cfg in TABLES.items():
    d = cfg["dir"]
    if not d.exists():
        print(f"  SKIP {cat}")
        continue
    files = [f for f in sorted(d.glob("*.md")) if cfg["filter"](f)]
    print(f"\n=== {cat}{len(files)} ===")
    for f in files:
        title, body = read_md(f)
        result = cli_upsert(cfg["base"], cfg["table"],
                            {"": title, "": body})
        if result.get("ok"):
            total += 1
            print(f"  OK: {title[:28]}")
        else:
            print(f"  ~ {title[:28]}: {result.get('_error','')[:60]}")

print(f"\nOK{total} ")
for cat, cfg in TABLES.items():
    print(f"  {cat}: https://bcn9k7tysatb.feishu.cn/base/{cfg['base']}")
