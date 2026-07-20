$src = "C:\Users\Administrator\AppData\Local\Microsoft\Windows\Fonts\FontquanXinYiGuanHeiTi-Regular.ttf"
$dst = "C:\Users\Administrator\AppData\Local\JianyingPro\User Data\Resources\Font\FontquanXinYiGuanHeiTi-Regular.ttf"

# Read raw bytes and change "FontquanXinYiGuanHeiTi" to shorten it
# Actually, let's just copy a fresh copy and verify
Write-Host "Source exists: $(Test-Path $src)"
Write-Host "Dest exists: $(Test-Path $dst)"

# Copy fresh
Copy-Item $src $dst -Force
Write-Host "Fresh copy done"
