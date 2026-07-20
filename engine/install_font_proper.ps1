$shell = New-Object -ComObject Shell.Application
$fontsFolder = $shell.NameSpace(0x14)  # 0x14 = Windows Fonts folder

# Install 冠黑体 via Windows shell (same as double-click → Install)
$fontPath = "D:\Documents\Downloads\字体圈欣意冠黑体-v4.009\FontquanXinYiGuanHeiTi-Regular.ttf"
$fontsFolder.CopyHere($fontPath, 16)  # 16 = no progress dialog

Write-Host "Install attempted. Check C:\Windows\Fonts for 'Fontquan' or '冠黑'"

# Also try installing 得意黑 the same way to be safe
$smileyPath = "D:\Documents\Downloads\得意黑2.0.1_猫啃网\得意黑2.0.0\SmileySans-Oblique.ttf"
if (Test-Path $smileyPath) {
    $fontsFolder.CopyHere($smileyPath, 16)
    Write-Host "得意黑 re-installed"
}
