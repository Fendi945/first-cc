$ws = New-Object -ComObject WScript.Shell

$old = @("D:\Documents\Desktop\yaoshidiyi.lnk", "D:\Documents\Desktop\fanqiezhong.lnk",
         "D:\Documents\Desktop\yaoshidiyi.bat", "D:\Documents\Desktop\fanqiezhong.bat")
foreach ($f in $old) { if (Test-Path $f) { Remove-Item $f -Force } }

# 要事第一 - point to electron directly
$e1 = "C:\Users\Administrator\Documents\trae_projects\first cc\four-quadrants\node_modules\electron\dist\electron.exe"
$d1 = "C:\Users\Administrator\Documents\trae_projects\first cc\four-quadrants"
$i1 = "$d1\icon.ico"
$s1 = $ws.CreateShortcut("D:\Documents\Desktop\yaoshidiyi.lnk")
$s1.TargetPath = $e1
$s1.Arguments = "."
$s1.WorkingDirectory = $d1
$s1.IconLocation = "$i1, 0"
$s1.Save()

# 番茄钟 - point to electron directly
$e2 = "C:\Users\Administrator\Documents\trae_projects\first cc\pomodoro-timer\node_modules\electron\dist\electron.exe"
$d2 = "C:\Users\Administrator\Documents\trae_projects\first cc\pomodoro-timer"
$i2 = "$d2\icon.ico"
$s2 = $ws.CreateShortcut("D:\Documents\Desktop\fanqiezhong.lnk")
$s2.TargetPath = $e2
$s2.Arguments = "."
$s2.WorkingDirectory = $d2
$s2.IconLocation = "$i2, 0"
$s2.Save()

Write-Host "All done"
