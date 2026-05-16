$base = Split-Path -Parent $MyInvocation.MyCommand.Path

$limit = (Get-Date).AddDays(-7)

$expired = Get-ChildItem -LiteralPath $base -Directory |
    Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}$' -and [datetime]$_.Name -lt $limit }

if ($expired) {
    $expired | ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
        Write-Host "已清除: $($_.Name)"
    }
    Write-Host "清理完成: 移除 $($expired.Count) 个过期目录"
} else {
    Write-Host "无过期数据"
}
