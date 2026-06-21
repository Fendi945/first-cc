$WshShell = New-Object -ComObject WScript.Shell

$Shortcut = $WshShell.CreateShortcut("D:\Documents\Desktop\Obsidian.lnk")
$Shortcut.TargetPath = "C:\Users\Administrator\Documents\trae_projects\first cc\engine\run-bg.bat"
$Shortcut.WorkingDirectory = "C:\Users\Administrator\Documents\trae_projects\first cc"
$Shortcut.Description = "Obsidian + YuanYan AI Engine"
$Shortcut.Save()
Write-Output "Shortcut updated"
