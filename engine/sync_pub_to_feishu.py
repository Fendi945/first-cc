""" Obsidian  CLI """
import json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.config import VAULT_PATH

BASE_TOKEN = "J5kob4zpLau5L4sFTSFcOegnnCh"
TABLE_ID = "tblaCnSv10loAQGZ"

# 
CATEGORY_MAP = {
    "": {
        "dir": VAULT_PATH / " " / "",
        "default_cat": "",
        "title_prefix": ""
    },
    "": {
        "dir": VAULT_PATH / " " / "",
        "default_cat": "",
        "title_prefix": ""
    },
    "": {
        "dir": VAULT_PATH / " " / "",
        "default_cat": "",
        "title_prefix": ""
    },
}

def read_md(file_path):
    """ md """
    content = file_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    title = file_path.stem
    body = content
    #  #  
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith("# ") and not line_stripped.startswith("##"):
            title = line_stripped[2:].strip()
            break
    return title, body

LARK_CLI = r"C:\Users\Administrator\nodejs\node-v20.18.0-win-x64\lark-cli.cmd"

import tempfile, os

LARK_CLI = r"C:\Users\Administrator\nodejs\node-v20.18.0-win-x64\lark-cli.cmd"

def cli(*args):
    """ CLI GBK """
    my_env = dict(os.environ)
    my_env["PYTHONIOENCODING"] = "utf-8"
    cmd = [LARK_CLI] + list(args) + ["--as", "user", "--format", "json"]
    tmp = tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False, encoding="utf-8")
    tmp.close()
    try:
        with open(tmp.name, "w", encoding="utf-8") as fout:
            r = subprocess.run(cmd, stdout=fout, stderr=subprocess.PIPE, env=my_env)
        if r.returncode != 0:
            err = r.stderr.decode("utf-8", errors="replace")[:200]
            return {"_error": f"exit {r.returncode}: {err}"}
        with open(tmp.name, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"_error": str(e)[:200]}
    finally:
        try: os.unlink(tmp.name)
        except: pass
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout) if result.stdout else {}

print(" Obsidian  -> ...")

synced = 0
skipped = 0

for cat_name, cfg in CATEGORY_MAP.items():
    d = cfg["dir"]
    if not d.exists():
        print(f"  SKIP: {d.name} ")
        continue
    for f in sorted(d.glob("*.md")):
        title, body = read_md(f)

        # 
        cat = cfg["default_cat"]
        if "" in str(f.stem):
            cat = ""
        elif "" in str(f.stem):
            cat = ""

        #  JSON 
        record_data = {
            "": title[:50],
            "": cat,
        }
        result = cli("base", "+record-upsert",
                     "--base-token", BASE_TOKEN,
                     "--table-id", TABLE_ID,
                     "--json", json.dumps(record_data, ensure_ascii=False))
        if result.get("ok"):
            synced += 1
            print(f"  OK: [{cat}] {title[:30]}")
        else:
            print(f"  FAIL: {title[:30]} - {result}")

print(f"\n {synced}  {skipped} ")
