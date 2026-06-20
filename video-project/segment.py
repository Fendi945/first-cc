#!/usr/bin/env python3
"""
逐字稿断句审查工具
==================
读取 Whisper 转录稿，按语义/气口分段，供用户审核后再跑 pipeline。

用法:
  PYTHONIOENCODING=utf-8 python segment.py              # 分段并保存
  PYTHONIOENCODING=utf-8 python segment.py --show         # 预览分段结果
"""
import json, re, sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
TRANSCRIPT_FILE = PROJECT_DIR / "transcript.json"
SEGMENTED_FILE = PROJECT_DIR / "transcript_segmented.json"

# 错字修正
CORRECTIONS = {
    "时工钱多": "施工前", "动线每一会儿": "动线没画", "时工对黑": "施工队黑",
    "守五王哪身": "手往哪伸", "红风成一三": "红枫×3", "元宝风成一二": "元宝枫×2",
    "从客厅到水井": "从客厅到水景", "踩一脚衣": "踩一脚泥", "洞个脑子": "动动脑子",
    "叶竹省": "业主审", "怎么省它": "怎么省事", "砸迟毕": "砸池壁",
    "拿枝笔": "拿支笔", "拿着笔": "拿支笔", "循环笵": "循环泵",
    "时工": "施工", "鞋俩字": "写俩字", "绿花袋": "绿化带", "厅步路": "汀步路",
    "红风": "红枫", "元宝风": "元宝枫", "贯笵": "冠幅", "笵坑": "泵坑",
    "迟毕": "池壁", "守五": "手", "数官": "树冠", "数长": "树长", "数种": "树种",
    "掌开": "长开", "兼具": "间距", "石拔": "石板", "水井": "水景",
    "挖两壳": "挖了两棵", "挖两棵": "挖了两棵", "五位书": "五位数",
    "指标了": "只标了", "管先": "管线", "交结": "胶粘", "沾死": "粘死",
    "水准": "水景", "稳资": "文字", "笵": "泵", "堆": "队", "王": "往",
    "蕾": "雷", "流": "留", "鞋": "写", "巳": "已",
    "时空对黑": "施工队黑", "时空": "施工", "图上": "图纸上",
}

# 硬断句规则：这些词后面是天然的断句点
BREAK_AFTER = {"了", "吧", "吗", "呢", "的", "？", "？", "。", "！", "!", "?", "好", "了"}
# 这些词前面应该断开
BREAK_BEFORE = {"那", "这", "但", "可", "所", "要", "如", "就", "还", "也", "并", "第", "一"}

def fix(text):
    for w, c in sorted(CORRECTIONS.items(), key=lambda x: -len(x[0])):
        text = text.replace(w, c)
    return text

ALL_PUNCT = re.compile(r'[，,。．！？、；：!?.\'\"()（）【】《》「」『』—…·]')

def clean(text):
    return ALL_PUNCT.sub('', text)

def segment_transcript():
    """读取 Whisper 转录稿，按语义/气口分为字幕段。"""
    with open(TRANSCRIPT_FILE, encoding='utf-8') as f:
        data = json.load(f)

    # 收集全部字词（去标点）
    all_words = []  # (word, start, end)
    for seg in data['segments']:
        for w in seg.get('words', []):
            t = clean(w['word'].strip())
            if t:
                all_words.append((t, w['start'], w['end']))

    # 分段
    segments = []
    group = []
    for i, (word, start, end) in enumerate(all_words):
        group.append((word, start, end))
        should_break = False

        # 规则1：词间停顿 >0.4s → 断
        if len(group) > 1 and (start - group[-2][2]) > 0.4:
            should_break = True
        # 规则2：当前词是断句标记（嗯、啊、了、吧等在末尾）
        if word in BREAK_AFTER:
            should_break = True
        # 规则3：下一个词是起始词且当前组已≥3字
        if len(group) >= 3 and i + 1 < len(all_words):
            next_word = all_words[i + 1][0]
            if next_word in BREAK_BEFORE:
                should_break = True
        # 规则4：单句最多 8 个字
        if len(group) >= 8:
            should_break = True
        # 规则5：组已经 ≥4 字且有标点停顿（利用原始转录中的标点位置）
        if len(group) >= 4:
            # 检查原始词中是否含标点（Whisper 有时标点嵌在字里）
            pass  # 标点已被 clean 去掉

        if should_break:
            combined = ''.join(w[0] for w in group).strip()
            combined = fix(combined)
            if len(combined) >= 1:
                segments.append({
                    'text': combined,
                    'start': round(group[0][1], 2),
                    'end': round(group[-1][2], 2)
                })
            group = []

    # 尾巴
    if group:
        combined = ''.join(w[0] for w in group).strip()
        combined = fix(combined)
        if len(combined) >= 1:
            segments.append({
                'text': combined,
                'start': round(group[0][1], 2),
                'end': round(group[-1][2], 2)
            })

    # 合并单字段到前一段
    merged = []
    for seg in segments:
        if len(seg['text']) <= 1 and merged:
            merged[-1]['text'] += seg['text']
            merged[-1]['end'] = seg['end']
        else:
            merged.append(seg)

    # 再次合并：如果一段太短（≤2字）且下一段开头能接上
    cleaned = []
    for seg in merged:
        if len(seg['text']) <= 2 and cleaned:
            # 判断语义上是否应该合并到前一段
            prev = cleaned[-1]
            # 如果前一段以"了"结尾，不合并（这是完整句尾）
            # 否则合并
            if not any(prev['text'].endswith(p) for p in '了吧吗呢的'):
                prev['text'] += seg['text']
                prev['end'] = seg['end']
                continue
        cleaned.append(seg)

    return cleaned


if __name__ == '__main__':
    segments = segment_transcript()
    SEGMENTED_FILE.parent.mkdir(exist_ok=True)

    # 保存
    output = {'segments': segments}
    with open(SEGMENTED_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 打印预览
    print(f"\n{'='*60}")
    print(f"  逐字稿断句方案 — {len(segments)} 段")
    print(f"{'='*60}")
    for i, seg in enumerate(segments, 1):
        dur = seg['end'] - seg['start']
        print(f"  {i:2d}. [{seg['start']:6.1f}s-{seg['end']:6.1f}s] ({dur:.1f}s) {seg['text']}")
    print(f"\n  保存至: {SEGMENTED_FILE}")
    print(f"  {'='*60}")
    print(f"  请审核断句方案。如需调整，告诉我哪些要合并/拆分。")
    print(f"  确认无误后，我跑 pipeline。")
