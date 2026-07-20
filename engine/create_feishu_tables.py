""" + Agent """
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.feishu_client import FeishuClient

client = FeishuClient()
state_file = Path(__file__).resolve().parent.parent / "feishu_bitable_state.json"

state = {}
if state_file.exists():
    state = json.loads(state_file.read_text(encoding="utf-8"))
bitables = state.setdefault("bitables", {})

TOPIC_DEF = {
    "name": "",
    "fields": [
        {"field_name": "", "type": 1},
        {"field_name": "", "type": 3,
         "property": {"options": [{"name": ""}, {"name": ""}, {"name": ""}, {"name": ""}]}},
        {"field_name": "", "type": 3,
         "property": {"options": [{"name": "P0"}, {"name": "P1"}, {"name": "P2"}]}},
        {"field_name": "", "type": 5},
        {"field_name": "", "type": 5},
        {"field_name": "", "type": 5},
        {"field_name": "", "type": 1},
        {"field_name": "", "type": 2},
        {"field_name": "", "type": 1},
    ],
}

AGENT_DEF = {
    "name": "Agent ",
    "fields": [
        {"field_name": "", "type": 1},
        {"field_name": "", "type": 3,
         "property": {"options": [{"name": ""}, {"name": "Claude"}, {"name": "Agent"}]}},
        {"field_name": "", "type": 3,
         "property": {"options": [{"name": ""}, {"name": ""}, {"name": ""}, {"name": ""}]}},
        {"field_name": "", "type": 3,
         "property": {"options": [{"name": "P0"}, {"name": "P1"}, {"name": "P2"}]}},
        {"field_name": "", "type": 1},
        {"field_name": "", "type": 5},
        {"field_name": "", "type": 5},
        {"field_name": "", "type": 1},
    ],
}

def create_table(name, table_def):
    print("\n=== %s ===" % name)
    data = client.create_bitable(name)
    app_token = data.get("app_token", "")
    if not app_token:
        print("  FAIL: no app_token")
        return None
    print("  OK: app_token=%s" % app_token)

    tables = client.list_tables(app_token)
    table_id = data.get("default_table_id", "")
    for t in tables:
        if t.get("table_id") == table_id:
            break
    if not table_id and tables:
        table_id = tables[0]["table_id"]
    if not table_id:
        print("  FAIL: no table_id")
        return None

    for field in table_def["fields"]:
        try:
            client.create_field(app_token, table_id,
                                field_name=field["field_name"],
                                field_type=field["type"],
                                property=field.get("property"))
            print("  + %s" % field["field_name"])
        except Exception as e:
            print("  ~ %s: %s" % (field["field_name"], e))

    tables_after = client.list_tables(app_token)
    table_map = {t["name"]: t["table_id"] for t in tables_after}
    return {"app_token": app_token, "table_map": table_map}

if "" not in bitables:
    r = create_table("", TOPIC_DEF)
    if r:
        bitables[""] = r
else:
    print("SKIP:  exists")

if "Agent " not in bitables:
    r = create_table("Agent ", AGENT_DEF)
    if r:
        bitables["Agent "] = r
else:
    print("SKIP: Agent  exists")

state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nDONE. State saved.")

for name, info in bitables.items():
    if name in ("", "Agent "):
        token = info.get("app_token", "")
        print("  https://bcn9k7tysatb.feishu.cn/base/%s  <- %s" % (token, name))
