#!/usr/bin/env python3
"""读取用户画好斜线的逐字稿，按 / 拆分、删除标记的重复，输出分段文件。"""
import json, re
from pathlib import Path

PROJECT_DIR = Path(r"C:\Users\Administrator\Documents\trae_projects\first cc\video-project")
USER_FILE = Path(r"D:\Documents\Desktop\逐字稿-待断句.txt")
OUTPUT = PROJECT_DIR / "transcript_segmented.json"

with open(USER_FILE, encoding='utf-8') as f:
    text = f.read()

# ===== 手动处理标记 =====

# 1. "（这句重复删掉）" 出现在第9行：前面三句"如果画图的时候多想一步/五年后修泵的人怎么站/手往哪伸"是重复
#    直接删掉 "如果画图的时候多想一步/五年后修泵的人怎么站/手往哪伸/（这句重复删掉）"
text = text.replace(
    '如果画图的时候多想一步/五年后修泵的人怎么站/手往哪伸/（这句重复删掉）',
    ''
)

# 2. "（重复的删掉）" x2 都在第15行
#    a) "好图纸不是（重复的删掉）好图纸不只是告诉你做什么" → "好图纸不只是告诉你做什么"
text = text.replace(
    '好图纸不是（重复的删掉）好图纸不只是告诉你做什么',
    '好图纸不只是告诉你做什么'
)
#    b) "觉得有用吗收藏这一期做图纸之前（重复的删掉）觉得有用吗/收藏这一期/做院子之前翻出来看眼"
#       → "觉得有用吗/收藏这一期/做院子之前翻出来看眼"
text = text.replace(
    '觉得有用吗收藏这一期做图纸之前（重复的删掉）觉得有用吗/收藏这一期/做院子之前翻出来看眼',
    '觉得有用吗/收藏这一期/做院子之前翻出来看眼'
)

# ===== 按 / 拆分 =====
# 先按行切，每行再按 / 切
raw_lines = text.strip().split('\n')
segments = []
for raw_line in raw_lines:
    parts = [p.strip() for p in raw_line.strip().split('/') if p.strip()]
    segments.extend(parts)

# ===== 修正拆分错误 =====
fixes = {
    '红枫×3元': '红枫×3',
    '宝枫×2': '元宝枫×2',
}
segments = [fixes.get(s, s) for s in segments]

# ===== 修正错字 =====
segments = [s.replace('穿个拖写', '穿个拖鞋') for s in segments]

# ===== 去重相邻重复 =====
deduped = []
for s in segments:
    if deduped and deduped[-1] == s:
        continue
    deduped.append(s)

# ===== 输出 =====
print(f"\n{'='*60}")
print(f"  最终断句方案 — {len(deduped)} 条字幕")
print(f"{'='*60}")
for i, line in enumerate(deduped, 1):
    print(f"  {i:2d}. {line}")
print(f"\n{'='*60}")

# 保存 JSON
output = {'segments': [{'index': i, 'text': line} for i, line in enumerate(deduped, 1)]}
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n  已保存: {OUTPUT}")
