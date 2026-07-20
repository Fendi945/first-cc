""" base  4  base"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.feishu_client import FeishuClient
import requests as req
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

client = FeishuClient()
token = client.get_tenant_access_token()
headers = {"Authorization": f"Bearer {token}"}
BASE = "https://open.feishu.cn/open-apis"

# 1.  base 
print("===  base  ===")
try:
    r = req.post(f"{BASE}/bitable/v1/apps", headers=headers,
                json={"name": "__"}, timeout=10)
    d = r.json()
    print(json.dumps(d, ensure_ascii=False, indent=2)[:500])
    test_token = d.get("data", {}).get("app", {}).get("app_token", "")
    if test_token:
        print(f"\n: app_token={test_token}")

        #  drive 
        r2 = req.get(f"{BASE}/drive/v1/files", headers=headers,
                    params={"page_size": 100}, timeout=10)
        for item in r2.json().get("data", {}).get("files", []):
            if item.get("token") == test_token:
                print(f"Drive : parent={item.get('parent_token')} name={item.get('name')}")
                break
except Exception as e:
    print(f"Error: {e}")

# 2.  RasN base 
print("\n===  RasN base  ===")
r3 = req.get(f"{BASE}/drive/v1/files", headers=headers,
            params={"page_size": 100}, timeout=10)
for item in r3.json().get("data", {}).get("files", []):
    t = item.get("token", "")
    name = item.get("name", "")
    parent = item.get("parent_token", "")
    typ = item.get("type", "")
    if t == "RasNbFNK0anDMysbcX2cgr9Snoh" or t == "S4S0bXtB4adQkLsBbHmclNOfn0N":
        print(f"  [{typ}] {name}  token={t}  parent={parent}")

# 3.   (/base)
print("\n=== / ===")
# 
# 
r4 = req.get(f"{BASE}/drive/v1/files", headers=headers,
            params={"page_size": 100}, timeout=10)

#  all folders
all_folders = {}
all_bitables = {}
for item in r4.json().get("data", {}).get("files", []):
    if item.get("type") == "folder":
        all_folders[item.get("token")] = item.get("name")
    elif item.get("type") == "bitable":
        all_bitables[item.get("token")] = item.get("name")

print(f": {len(all_folders)}")
for ft, fn in all_folders.items():
    print(f"  : {fn}  token={ft}")

print(f"\n bitables : {len(all_bitables)}")
for bt, bn in all_bitables.items():
    print(f"  bitable: {bn}  token={bt}")
