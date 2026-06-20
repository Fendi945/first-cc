$ws = New-Object -ComObject WScript.Shell

$s1 = $ws.CreateShortcut("D:\Documents\Desktop\要事第一.lnk")
$s1.TargetPath = "C:\Users\Administrator\Documents\trae_projects\first cc\four-quadrants\node_modules\electron\dist\electron.exe"
$s1.Arguments = "."
$s1.WorkingDirectory = "C:\Users\Administrator\Documents\trae_projects\first cc\four-quadrants"
$s1.IconLocation = "D:\Documents\Desktop\要事第一抠图.ico, 0"
$s1.Save()

$s2 = $ws.CreateShortcut("D:\Documents\Desktop\fq.lnk")
$s2.TargetPath = "C:\Users\Administrator\Documents\trae_projects\first cc\pomodoro-timer\node_modules\electron\dist\electron.exe"
$s2.Arguments = "."
$s2.WorkingDirectory = "C:\Users\Administrator\Documents\trae_projects\first cc\pomodoro-timer"
$s2.IconLocation = "D:\Documents\Desktop\番茄抠图.ico, 0"
$s2.Save()

Write-Host "OK"
