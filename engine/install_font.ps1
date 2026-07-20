# Install 得意黑 (SmileySans) font
$fontSrc = "D:\Documents\Downloads\字体圈欣意冠黑体4.009_猫啃网\字体圈欣意冠黑体4.009\FontquanXinYiGuanHeiTi-Regular.ttf"
$fontDest = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts\"
$fontFile = "FontquanXinYiGuanHeiTi-Regular.ttf"
$regName = "字体圈欣意冠黑体 (TrueType)"

# Ensure destination exists
if (-not (Test-Path $fontDest)) {
    New-Item -ItemType Directory -Force -Path $fontDest | Out-Null
}

# Copy font
Copy-Item $fontSrc "$fontDest$fontFile" -Force
Write-Host "✅ Font copied to: $fontDest$fontFile"

# Register font via registry (user-level)
$regPath = "HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
Set-ItemProperty -Path $regPath -Name $regName -Value $fontFile
Write-Host "✅ Font registered in registry: $regName"

# Notify system
Add-Type @"
[DllImport("gdi32.dll")]
public static extern int AddFontResource(string lpszFilename);
"@ -Name FontHelper -Namespace Win32

[Win32.FontHelper]::AddFontResource("$fontDest$fontFile") | Out-Null
Write-Host "✅ Font resource added to system"

Write-Host ""
Write-Host "=== 安装完成 ==="
Write-Host "字体名称: 得意黑 / SmileySans-Oblique"
Write-Host "路径: $fontDest$fontFile"
Write-Host ""
Write-Host "Restart Jianying (CapCut) to see the font in the font list."
