param(
    [string]$OutDir = "./models"
)

# Attempts to download a default yolov8n.pt model into the local models folder.
# If the primary URL fails, it will instruct the user how to download manually.

if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$outPath = Join-Path $OutDir "yolov8n.pt"

Write-Host "Downloading default model to $outPath ..."

# Primary candidate URL (GitHub assets release). If this fails, try the second.
$urls = @(
    'https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt',
    'https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt'
)

$success = $false
foreach ($u in $urls) {
    try {
        Invoke-WebRequest -Uri $u -OutFile $outPath -UseBasicParsing -ErrorAction Stop
        Write-Host "Downloaded from $u"
        $success = $true
        break
    } catch {
        Write-Host "Failed to download from $u : $_"
    }
}

if (-not $success) {
    Write-Host "Automatic download failed. Please download yolov8n.pt manually and place it into $OutDir." -ForegroundColor Yellow
    Write-Host "Suggested source: https://ultralytics.com/ (or search 'yolov8n.pt ultralytics assets')"
    exit 1
}

Write-Host "Model saved to $outPath"
exit 0
