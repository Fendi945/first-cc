$reg = 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'

# Register missing font (冠黑体)
$fontFile = 'FontquanXinYiGuanHeiTi-Regular.ttf'
$fontName = '字体圈欣意冠黑体 (TrueType)'
Set-ItemProperty -Path $reg -Name $fontName -Value $fontFile -Force
Write-Host "Registered: $fontName"

# Also register the other fonts with proper names
$others = @{
    '得意黑 (TrueType)' = 'SmileySans-Oblique.ttf'
    '字体圈欣意LOGO体 (TrueType)' = '字体圈欣意LOGO体.ttf'
}
foreach ($n in $others.Keys) {
    Set-ItemProperty -Path $reg -Name $n -Value $others[$n] -Force
    Write-Host "OK: $n"
}

Write-Host "`nDone. Restart apps to see fonts."
