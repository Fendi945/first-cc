#!/bin/bash
# 语音播报：用 edge-tts 生成并播放英文男声
# 用法: bash speak.sh "要说的文字" [voice_name]

TEXT="${1:-Hello boss, I have already finish the task. Please check.}"
VOICE="${2:-en-US-ChristopherNeural}"
TMPFILE="/tmp/tts_output.mp3"

# 构建命令
CMD="edge-tts --voice \"$VOICE\" --text \"$TEXT\" --write-media \"$TMPFILE\""

# 如果传了语速参数就加上
if [ -n "$3" ]; then
  CMD="$CMD --rate \"$3\""
fi

# 生成语音
eval $CMD 2>/dev/null

if [ $? -eq 0 ] && [ -f "$TMPFILE" ]; then
  # 播放
  ffplay -nodisp -autoexit "$TMPFILE" 2>/dev/null
  rm -f "$TMPFILE"
else
  echo "语音生成失败"
fi
