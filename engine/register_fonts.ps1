$fonts = @{}
$fonts['SmileySans (TrueType)'] = 'SmileySans-Oblique.ttf'
$fonts['FontquanXinYiGuanHeiTi (TrueType)'] = 'FontquanXinYiGuanHeiTi-Regular.ttf'
$fonts['XinYiLOGO (TrueType)'] = '字体圈欣意LOGO体.ttf'

$regPath = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'
foreach ($name in $fonts.Keys) {
    try {
        Set-ItemProperty -Path $regPath -Name $name -Value $fonts[$name] -ErrorAction Stop
        Write-Host "OK: $name"
    } catch {
        Write-Host "FAIL: $name"
    }
}
