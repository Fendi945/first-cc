#!/bin/bash
# ============================================
# Agnes-2.0-Flash 调用助手
# 用法: bash call-agnes.sh "你的提示词"
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

get_env() {
  grep -E "^$1=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r\n'
}

API_KEY="$(get_env AGNES_API_KEY)"
BASE_URL="$(get_env AGNES_BASE_URL)"
MODEL="$(get_env AGNES_MODEL)"

BASE_URL="${BASE_URL:-https://apihub.agnes-ai.com/v1}"
MODEL="${MODEL:-agnes-2.0-flash}"

if [ -z "$API_KEY" ]; then
  echo "Error: AGNES_API_KEY not set in .env" >&2
  exit 1
fi

PROMPT="$*"
if [ -z "$PROMPT" ]; then
  echo "Usage: bash call-agnes.sh <prompt>" >&2
  exit 1
fi

# 写 prompt 到临时文件，Python 读文件，彻底避免转义问题
TMPFILE=$(mktemp)
echo "$PROMPT" > "$TMPFILE"

export API_KEY BASE_URL MODEL TMPFILE

python << 'PYEOF'
import json, urllib.request, os

api_key = os.environ['API_KEY']
base_url = os.environ['BASE_URL']
model = os.environ['MODEL']

with open(os.environ['TMPFILE'], 'r', encoding='utf-8') as f:
    prompt = f.read()

system_prompt = (
    "Top expert. Accuracy beats approval. Blunt, argumentative. "
    "No disclaimers or praise. Lead with counterarguments. "
    "TAG every claim: [KNOWN] [COMPUTED] [INFERRED] [COMMON] [FRAME] [GUESS]. "
    "No untagged disease, statute, citation, or named entity. "
    "FRAME→REALITY FORBIDDEN: symbolic frames stay in source frame. "
    "CONFIDENCE: HIGH≥80% MED 50-80% LOW 20-50% VERY LOW<20%. "
    "UNKNOWN: [FRAME]+[GUESS] cap at LOW. "
    "DON'T KNOW: first line 'I don't know.' "
    "ANTI-SYCOPHANCY: cut specifics, add [GUESS], or say you don't know. "
    "POST-HOC: can't predict without outcome → [INFERRED, post-hoc]. "
    "Never fabricate citations. "
    "End with: [RULES I BROKE]: which, where, why."
)

payload = json.dumps({
    "model": model,
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.3,
    "max_tokens": 8192
}).encode('utf-8')

req = urllib.request.Request(
    f"{base_url}/chat/completions",
    data=payload,
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
)

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
        if 'choices' in data and len(data['choices']) > 0:
            content = data['choices'][0]['message']['content']
            # Windows 终端 UTF-8 适配
            import sys
            sys.stdout.reconfigure(encoding='utf-8')
            print(content)
        elif 'error' in data:
            print(f"Error: {data['error']}", file=sys.stderr)
        else:
            print(f"Unknown: {json.dumps(data, ensure_ascii=False)[:500]}", file=sys.stderr)
except Exception as e:
    print(f"Request failed: {e}", file=sys.stderr)
finally:
    os.remove(os.environ['TMPFILE'])
PYEOF
