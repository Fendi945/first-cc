""" base """
import subprocess, tempfile, os, json, sys
from pathlib import Path
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

LARK_CLI = r"C:\Users\Administrator\nodejs\node-v20.18.0-win-x64\lark-cli.cmd"
OLD_BASE = "S4S0bXtB4adQkLsBbHmclNOfn0N"
NEW_BASE = "RasNbFNK0anDMysbcX2cgr9Snoh"

def cli(*args):
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

# 1.  base 
print("===  base  ===")
r = cli("base", "+table-list", "--base-token", OLD_BASE)
tables = r.get("data", {}).get("tables", [])
for t in tables:
    print(f"  {t.get('name')} - {t.get('id')}")

# 2.  4 
print("\n===  base  4  ===")
del_targets = {
    "tblQs29hF8MKcZQb": "",
    "tbl22LHTQCExWW8L": "",
    "tblaLyr4POoDkme7": "",
    "tblF26ZOig8jWIZT": "",
}
for tid, tname in del_targets.items():
    print(f" {tname} ({tid})...")
    r = cli("base", "+table-delete", "--base-token", OLD_BASE, "--table-id", tid)
    if r.get("ok"):
        print(f"   ")
    else:
        print(f"   {json.dumps(r, ensure_ascii=False)[:200]}")

# 3.  state 
print("\n===  ===")
state_file = Path(__file__).resolve().parent.parent / "feishu_bitable_state.json"
if state_file.exists():
    state = json.loads(state_file.read_text(encoding="utf-8"))
    state.setdefault("bitables", {})
    state["bitables"][""] = {"app_token": NEW_BASE, "table_map": {}}
    state["bitables"][""] = {"app_token": NEW_BASE, "table_map": {}}
    state["bitables"][""] = {"app_token": NEW_BASE, "table_map": {}}
    state["bitables"][""] = {"app_token": NEW_BASE, "table_map": {}}
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(" ")
else:
    print(" ")

# 4. 
print("\n===  base  ===")
r = cli("base", "+table-list", "--base-token", NEW_BASE)
tables = r.get("data", {}).get("tables", [])
for t in tables:
    print(f"   {t.get('name')} - {t.get('id')}")

print(f"\n base : https://bcn9k7tysatb.feishu.cn/base/{NEW_BASE}")
