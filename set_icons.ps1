$ws = New-Object -ComObject WScript.Shell

# ===== 要事第一 =====
$s1 = $ws.CreateShortcut("D:\Documents\Desktop\🎯 要事第一.lnk")
$s1.TargetPath = "D:\Documents\Desktop\🎯 要事第一.bat"
$s1.WorkingDirectory = "C:\Users\Administrator\Documents\trae_projects\first cc\four-quadrants"
$s1.IconLocation = "C:\Users\Administrator\Documents\trae_projects\first cc\four-quadrants\icon.ico, 0"
$s1.Save()
Write-Host "1/2 要事第一 done"

# ===== 番茄钟 =====
$s2 = $ws.CreateShortcut("D:\Documents\Desktop\🍅 番茄钟.lnk")
$s2.TargetPath = "D:\Documents\Desktop\🍅 番茄钟.bat"
$s2.WorkingDirectory = "C:\Users\Administrator\Documents\trae_projects\first cc\pomodoro-timer"
$s2.IconLocation = "C:\Users\Administrator\Documents\trae_projects\first cc\pomodoro-timer\icon.ico, 0"
$s2.Save()
Write-Host "2/2 番茄钟 done"

Write-Host "All done!"
