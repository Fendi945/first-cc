"""Obsidian 

/ Obsidian  + 
 .md  vault 

:
    python engine/dashboard_gen.py

:
    {VAULT_PATH}/.md
"""
import json
import re
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

#  engine
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.config import VAULT_PATH, KANBAN_DIR, DATA_DIR, PROJECT_ROOT
from engine.feishu_client import FeishuClient

OUTPUT_FILE = VAULT_PATH / ".md"
STATE_FILE = PROJECT_ROOT / "feishu_bitable_state.json"

#   

def read_feishu_table(app_token, table_id, page_size=100):
    """"""
    try:
        client = FeishuClient()
        records = client.list_bitable_records(app_token, table_id, page_size=page_size)
        result = []
        for rec in records:
            fields = rec.get("fields", {})
            result.append(fields)
        return result
    except Exception as e:
        return [{"_error": str(e)}]


def get_feishu_state():
    """ feishu_bitable_state.json"""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


#   

def get_today_tasks(state):
    """"""
    info = state.get("bitables", {}).get("", {})
    app_token = info.get("app_token", "")
    if not app_token:
        return [], ""

    table_id = list(info.get("table_map", {}).values())[0] if info.get("table_map") else ""
    if not table_id:
        return [], "ID"

    records = read_feishu_table(app_token, table_id)
    today_str = date.today().isoformat()
    today_ts_tmp = int(datetime.now().timestamp())
    today_start = int(datetime.today().timestamp())
    today_end = int(datetime.today().timestamp()) + 86400

    tasks = []
    for r in records:
        status = r.get("", "")
        name = r.get("", "")
        if not name:
            continue
        plan_date = r.get("", 0)
        if isinstance(plan_date, (int, float)):
            plan_date_str = datetime.fromtimestamp(plan_date).strftime("%Y-%m-%d")
        else:
            plan_date_str = str(plan_date)[:10] if plan_date else ""

        # 
        if status in ("", "") and plan_date_str:
            tasks.append((plan_date_str, status, name))
        elif status in ("",) and not plan_date_str:
            tasks.append(("", status, name))

    # 
    tasks.sort(key=lambda x: x[0])
    # 
    tasks = [t for t in tasks if t[0] <= today_str or t[0] == ""]
    return tasks, None


def get_pending_count():
    """.json """
    pending_file = KANBAN_DIR / ".json"
    if not pending_file.exists():
        return 0
    try:
        data = json.loads(pending_file.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return len(data)
        return 0
    except Exception:
        return 0


def get_tools():
    """// """
    tools_dir = VAULT_PATH / " " / ""
    if not tools_dir.exists():
        return []
    tools = []
    for f in sorted(tools_dir.iterdir()):
        if f.suffix == ".md":
            name = f.stem
            if len(name) > 20:
                name = name[:20] + "…"
            tools.append(name)
    return tools


def get_rules():
    """// """
    rules_dir = VAULT_PATH / " " / ""
    if not rules_dir.exists():
        return []
    rules = []
    for f in sorted(rules_dir.iterdir()):
        if f.suffix == ".md":
            rules.append(f.stem)
    return rules


def get_capture_stats():
    """"""
    capture_dir = VAULT_PATH / " " / ""
    if not capture_dir.exists():
        return 0, 0
    files = [f for f in capture_dir.iterdir() if f.suffix == ".md"]
    today_count = 0
    week_count = 0
    today_str = date.today().isoformat()
    week_ago = date.today() - timedelta(days=7)
    for f in files:
        #  YYYY-MM-DD xxx.md
        match = re.match(r"(\d{4}-\d{2}-\d{2})", f.stem)
        if match:
            fdate_str = match.group(1)
            if fdate_str == today_str:
                today_count += 1
            if fdate_str >= week_ago.isoformat():
                week_count += 1
    return today_count, week_count


def get_latest_video_data():
    """&"""
    state = get_feishu_state()
    info = state.get("bitables", {}).get("&", {})
    app_token = info.get("app_token", "")
    if not app_token:
        #  dashboard-data.json 
        dash_file = KANBAN_DIR / "dashboard-data.json"
        if dash_file.exists():
            try:
                data = json.loads(dash_file.read_text(encoding="utf-8"))
                return data.get("data", []), None
            except Exception:
                pass
        return [], ""

    table_id = list(info.get("table_map", {}).values())[0] if info.get("table_map") else ""
    if not table_id:
        return [], "ID"

    records = read_feishu_table(app_token, table_id)
    return records, None


def get_analysis_insight():
    """.md """
    analysis_file = DATA_DIR / ".md"
    if not analysis_file.exists():
        return None
    try:
        content = analysis_file.read_text(encoding="utf-8")
        # """"
        lines = content.split("\n")
        insight_lines = []
        in_insight = False
        in_suggestions = False
        for line in lines:
            if "" in line or "" in line:
                in_insight = True
                continue
            if in_insight and line.startswith("##"):
                break
            if in_insight and line.strip():
                #  markdown 
                clean = line.strip().strip("- ").strip()
                if clean:
                    insight_lines.append(clean)
        return " ".join(insight_lines[:3]) if insight_lines else None
    except Exception:
        return None


#   

def build_dashboard(state):
    """"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    today_weekday = ["", "", "", "", "", "", ""][datetime.now().weekday()]

    # 
    tasks, tasks_err = get_today_tasks(state)
    pending_count = get_pending_count()
    tools = get_tools()
    rules = get_rules()
    today_cap, week_cap = get_capture_stats()
    video_data, v_err = get_latest_video_data()
    insight = get_analysis_insight()

    #   
    lines = []
    lines.append("---")
    lines.append("created: " + now)
    lines.append("tags: [dashboard, home, auto-gen]")
    lines.append("updated: auto")
    lines.append("---")
    lines.append("")
    lines.append("#   · ")
    lines.append("")
    lines.append("> " + today_weekday + " · " + now)
    lines.append("")
    lines.append("---")
    lines.append("")

    #   
    lines.append("##  ")
    lines.append("")

    has_todo = False
    if tasks:
        for plan_date, status, name in tasks:
            icon = "" if "" in status else ""
            lines.append(f"- {icon} **{status}**{name}{plan_date}")
            has_todo = True
    if pending_count > 0:
        lines.append(f"-  ****{pending_count} ")
        has_todo = True
    if not has_todo:
        lines.append("_ _")
    lines.append("")

    #   
    lines.append("##  ")
    lines.append("")
    if video_data and not v_err:
        # 
        sorted_data = sorted(
            [v for v in video_data if v.get("") or v.get("")],
            key=lambda x: x.get("", 0) if isinstance(x.get(""), (int, float)) else 0,
            reverse=True,
        )
        if sorted_data:
            latest = sorted_data[0]
            title = latest.get("") or latest.get("", "")
            plays = latest.get("/") or latest.get("", 0)
            likes = latest.get("", 0)
            comments = latest.get("", 0)
            shares = latest.get("/", 0)
            lines.append(f"|  |  |  |  |  |")
            lines.append(f"|------|------|----|----|----|")
            title_short = title[:16] + "…" if len(title) > 16 else title
            lines.append(f"| {title_short} | {plays} | {likes} | {comments} | {shares} |")
            lines.append("")
        else:
            lines.append("_ _")
            lines.append("")
    else:
        lines.append("_ _")
        lines.append("")

    if insight:
        lines.append(f">  ****{insight}")
        lines.append("")

    #   
    lines.append("##  ")
    lines.append("")
    if tools:
        # 4
        for i in range(0, len(tools), 5):
            chunk = tools[i:i + 5]
            lines.append("| " + " | ".join(chunk) + " |")
        lines.append("")
    else:
        lines.append("__")
        lines.append("")

    #   
    lines.append("##  ")
    lines.append("")
    if rules:
        for r in rules:
            # .md/
            clean_name = re.sub(r"^[\d\s\-_\.]+", "", r)
            lines.append(f"- {clean_name}")
        lines.append("")
    else:
        lines.append("__")
        lines.append("")

    #   
    lines.append("##  ")
    lines.append("")
    lines.append(f"-  +{today_cap} ")
    lines.append(f"-  {week_cap} ")
    lines.append("")

    #   
    lines.append("---")
    lines.append("")
    lines.append(f"_  {now} ·  + Obsidian_")

    return "\n".join(lines)


def main():
    state = get_feishu_state()
    content = build_dashboard(state)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(content, encoding="utf-8")
    print(f"[OK]  -> {OUTPUT_FILE}")
    print()
    # 
    for line in content.split("\n")[:5]:
        print(line)


if __name__ == "__main__":
    main()
