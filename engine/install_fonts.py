#!/usr/bin/env python3
"""Install fonts into Windows user fonts directory."""
import os, shutil, subprocess, ctypes, sys
from pathlib import Path

FONTS = [
    ("得意黑", r"D:\Documents\Downloads\得意黑2.0.1_猫啃网\得意黑2.0.0\SmileySans-Oblique.ttf"),
    ("冠黑体", r"D:\Documents\Downloads\字体圈欣意冠黑体4.009_猫啃网\字体圈欣意冠黑体4.009\FontquanXinYiGuanHeiTi-Regular.ttf"),
    ("LOGO体", r"D:\Documents\Downloads\字体圈欣意LOGO体_猫啃网\字体圈欣意LOGO体\字体圈欣意LOGO体.ttf"),
]

user_fonts = Path(os.environ['LOCALAPPDATA']) / "Microsoft" / "Windows" / "Fonts"
user_fonts.mkdir(parents=True, exist_ok=True)

for name, src_path in FONTS:
    src = Path(src_path)
    if not src.exists():
        print(f"❌ {name}: 文件不存在 -> {src}")
        continue

    dest = user_fonts / src.name
    shutil.copy2(src, dest)
    print(f"✅ {name}: 已复制到 {dest}")

    # Register via registry (user-level)
    ps_cmd = f'''
    $regPath = "HKCU:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts"
    Set-ItemProperty -Path $regPath -Name "{name}" -Value "{src.name}" -Force
    Write-Host "Registry OK"
    '''
    result = subprocess.run(["powershell.exe", "-Command", ps_cmd], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"   {name}: 注册表 OK")
    else:
        print(f"   {name}: 注册表错误: {result.stderr.strip()}")

    # Notify system
    ctypes.windll.gdi32.AddFontResourceW(str(dest))
    print(f"   {name}: 系统通知完成")

print("\n=== 全部完成 ===")
print(f"字体位置: {user_fonts}")
print("重启剪映后即可在字体列表中找到这三款字体")
