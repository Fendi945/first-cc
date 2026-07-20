# 用脚本所在目录推导路径，避免硬编码
$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
$DistDir = Join-Path $ProjectRoot "dist" "审批面板"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "元演审批面板.lnk"
$ExePath = Join-Path $DistDir "审批面板.exe"

if (-not (Test-Path $ExePath)) {
    Write-Error "EXE not found: $ExePath"
    Write-Output "Run scripts/build_exe.py first, or specify a custom path."
    exit 1
}

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = $DistDir
$Shortcut.Description = "YuanYan Approval Panel"
$Shortcut.Save()
Write-Output "Shortcut created: $ShortcutPath"
