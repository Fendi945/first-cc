#!/bin/bash
FONT="C:/Windows/Fonts/msyh.ttc"
DIR="C:/Users/Administrator/Documents/trae_projects/first cc"

# 1 动线设计
ffmpeg -y -f lavfi -i "color=c=#2d5a27:s=800x450:d=1" \
  -vf "drawbox=x=0:y=0:w=800:h=450:c=white@0.03:t=fill,drawtext=fontfile=${FONT}:text='\xE5\x8A\xA8\xE7\xBA\xBF\xE8\xAE\xBE\xE8\xAE\xA1':fontsize=44:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-25,drawtext=fontfile=${FONT}:text='\xE5\xB0\x8F\xE9\x99\xA2\xE5\xAD\x90\xE5\x8F\x98\xE5\xA4\xA7\xE7\x9A\x84\xE7\xA7\x98\xE5\xAF\x86':fontsize=24:fontcolor=#c0d0c0:x=(w-text_w)/2:y=(h-text_h)/2+25" \
  -frames:v 1 "${DIR}/cover_1.png" 2>&1 | tail -1 &

# 2 水景
ffmpeg -y -f lavfi -i "color=c=#1a4a5a:s=800x450:d=1" \
  -vf "drawbox=x=0:y=0:w=800:h=450:c=white@0.03:t=fill,drawtext=fontfile=${FONT}:text='\xE4\xB8\x8D\xE5\x90\x8C\xE9\x9D\xA2\xE7\xA7\xAF\xE6\xB0\xB4\xE6\x99\xAF\xE6\x96\xB9\xE6\xA1\x88':fontsize=40:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-25,drawtext=fontfile=${FONT}:text='\xE4\xBD\xA0\xE7\x9A\x84\xE9\x99\xA2\xE5\xAD\x90\xE9\x80\x82\xE5\x90\x88\xE4\xBB\x80\xE4\xB9\x88\xE6\xB0\xB4\xE6\x99\xAF':fontsize=22:fontcolor=#a0c0d0:x=(w-text_w)/2:y=(h-text_h)/2+25" \
  -frames:v 1 "${DIR}/cover_2.png" 2>&1 | tail -1 &

# 3 锦鲤池
ffmpeg -y -f lavfi -i "color=c=#2a4a3a:s=800x450:d=1" \
  -vf "drawbox=x=0:y=0:w=800:h=450:c=white@0.03:t=fill,drawtext=fontfile=${FONT}:text='\xE9\x94\xA6\xE9\xB2\xA4\xE6\xB1\xA0\xE5\x8A\x9D\xE9\x80\x80\xE7\xAF\x87':fontsize=44:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-25,drawtext=fontfile=${FONT}:text='\xE5\x85\x88\xE6\x83\xB3\xE6\xB8\x85\xE6\xA5\x9A\xE5\x86\x8D\xE6\x8C\x96':fontsize=22:fontcolor=#a0c0a0:x=(w-text_w)/2:y=(h-text_h)/2+25" \
  -frames:v 1 "${DIR}/cover_3.png" 2>&1 | tail -1 &

# 4 园林底层逻辑
ffmpeg -y -f lavfi -i "color=c=#3a3020:s=800x450:d=1" \
  -vf "drawbox=x=0:y=0:w=800:h=450:c=white@0.03:t=fill,drawtext=fontfile=${FONT}:text='\xE5\x9B\xAD\xE6\x9E\x97\xE5\xBA\x95\xE5\xB1\x82\xE9\x80\xBB\xE8\xBE\x91':fontsize=44:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-25,drawtext=fontfile=${FONT}:text='\xE4\xB8\xBA\xE4\xBB\x80\xE4\xB9\x88\xE6\x80\xBB\xE8\xA7\x89\xE5\xBE\x97\xE5\x88\xAB\xE6\x89\xAD':fontsize=22:fontcolor=#c0b090:x=(w-text_w)/2:y=(h-text_h)/2+25" \
  -frames:v 1 "${DIR}/cover_4.png" 2>&1 | tail -1 &

# 5 图纸三个坑
ffmpeg -y -f lavfi -i "color=c=#4a2020:s=800x450:d=1" \
  -vf "drawbox=x=0:y=0:w=800:h=450:c=white@0.03:t=fill,drawtext=fontfile=${FONT}:text='\xE4\xB8\x80\xE5\xBC\xA0\xE5\x9B\xBE\xE7\xBA\xB8\xE4\xB8\x89\xE4\xB8\xAA\xE5\x9D\x91':fontsize=40:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-25,drawtext=fontfile=${FONT}:text='\xE5\xBA\xAD\xE9\x99\xA2\xE9\x80\xA0\xE4\xBB\xB7\xE7\xBF\xBB\xE5\x80\x8D\xE7\x9A\x84\xE7\xA7\x98\xE5\xAF\x86':fontsize=22:fontcolor=#d0a0a0:x=(w-text_w)/2:y=(h-text_h)/2+25" \
  -frames:v 1 "${DIR}/cover_5.png" 2>&1 | tail -1 &

# 6 施工图纸细节
ffmpeg -y -f lavfi -i "color=c=#2a3040:s=800x450:d=1" \
  -vf "drawbox=x=0:y=0:w=800:h=450:c=white@0.03:t=fill,drawtext=fontfile=${FONT}:text='\xE6\x96\xBD\xE5\xB7\xA5\xE5\x9B\xBE\xE7\xBA\xB8\xE7\xBB\x86\xE8\x8A\x82':fontsize=44:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-25,drawtext=fontfile=${FONT}:text='\xE9\x98\x9F\xE6\x9C\x80\xE6\x80\x95\xE4\xBD\xA0\xE7\x9C\x8B\xE6\x87\x82\xE7\x9A\x84':fontsize=22:fontcolor=#90a0c0:x=(w-text_w)/2:y=(h-text_h)/2+25" \
  -frames:v 1 "${DIR}/cover_6.png" 2>&1 | tail -1 &

# 7 从0到1
ffmpeg -y -f lavfi -i "color=c=#2a4a30:s=800x450:d=1" \
  -vf "drawbox=x=0:y=0:w=800:h=450:c=white@0.03:t=fill,drawtext=fontfile=${FONT}:text='\xE5\xBA\xAD\xE9\x99\xA2\xE8\xAE\xBE\xE8\xAE\xA1\xE5\x85\xA8\xE6\x8C\x87\xE5\x8D\x97':fontsize=44:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-25,drawtext=fontfile=${FONT}:text='\xE4\xBB\x8E0\xE5\x88\xB01\xE7\x9A\x84\xE9\x81\xBF\xE5\x9D\x91\xE6\xB8\x85\xE5\x8D\x95':fontsize=22:fontcolor=#a0d0a0:x=(w-text_w)/2:y=(h-text_h)/2+25" \
  -frames:v 1 "${DIR}/cover_7.png" 2>&1 | tail -1 &

wait
echo "All covers generated"
