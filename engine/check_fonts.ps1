$reg = 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'
Write-Host "=== User Registry Fonts ==="
Get-ItemProperty -Path $reg | Select-Object -Property *得意*, *冠黑*, *LOGO*, *Smiley*, *Caveat*, *Huiwen*, *Mincho*, *Noto*

Write-Host "=== Files in User Fonts Dir ==="
$dir = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts"
Get-ChildItem $dir | Select-Object Name, Length

Write-Host "=== Files in System Fonts Dir ==="
Get-ChildItem "C:\Windows\Fonts\*.ttf" | Where-Object { $_.Name -match 'Smiley|GuanHei|LOGO|得意|冠黑' } | Select-Object Name, Length
