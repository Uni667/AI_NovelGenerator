# ─── Railway Backend Deploy on Boot ───────────────────────────────
# 此脚本由 Windows Startup 文件夹的 .bat 文件在用户登录时触发
# 执行完成后会自动删除启动快捷方式
# 脚本本身保留在 scripts/ 目录，可重复启用
# ──────────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"
$ProjectDir = "D:\Personal\Desktop\plan\AI_NovelGenerator"
$LogFile = Join-Path $ProjectDir "logs\deploy-boot.log"

# 确保日志目录存在
$LogDir = Join-Path $ProjectDir "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Message" | Out-File -Append -FilePath $LogFile -Encoding utf8
    Write-Host "$timestamp - $Message"
}

Write-Log "=== Railway boot deploy started ==="

# 等待网络可用 (最多等 60 秒)
Write-Log "Waiting for network..."
$networkReady = $false
for ($i = 0; $i -lt 12; $i++) {
    try {
        $connection = Test-Connection -ComputerName "backboard.railway.com" -Count 1 -Quiet -ErrorAction SilentlyContinue
        if ($connection) {
            $networkReady = $true
            Write-Log "Network is ready after $($i * 5)s"
            break
        }
    } catch { }
    Start-Sleep -Seconds 5
}

if (-not $networkReady) {
    Write-Log "WARNING: Network may not be fully ready, proceeding anyway..."
}

# 进入项目目录并部署
try {
    Set-Location $ProjectDir
    Write-Log "Running: railway up"
    $output = & railway up 2>&1
    Write-Log "Railway output:"
    $output | ForEach-Object { Write-Log $_ }

    if ($LASTEXITCODE -eq 0) {
        Write-Log "SUCCESS: Railway deploy completed successfully."
    } else {
        # 检查是否是 peak hours 限流
        $outputStr = $output -join "`n"
        if ($outputStr -match "peak hours|Free-tier") {
            Write-Log "DEFERRED: Railway free-tier peak hours restriction. Will retry on next boot."
            # 不删除计划任务，下次开机自动重试
            exit 0
        }
        Write-Log "FAILED: Railway deploy exited with code $LASTEXITCODE"
    }
} catch {
    Write-Log "ERROR: $_"
    exit 1
} finally {
    Write-Log "=== Railway boot deploy finished ==="
}

# 部署成功后删除启动快捷方式，下次开机不再自动运行
$StartupBat = Join-Path ([Environment]::GetFolderPath('Startup')) "RailwayDeployBackend.bat"
if (Test-Path $StartupBat) {
    Write-Log "Removing startup script: $StartupBat"
    Remove-Item -LiteralPath $StartupBat -Force -ErrorAction SilentlyContinue
    Write-Log "Startup script removed. Will not run on next boot."
}
Write-Log "Script completed. Re-enable by copying startup bat to Startup folder."
