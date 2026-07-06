# ============================================================
# 一次性配置 Windows 计划任务（每天美东时间 09:00 运行）
# 美东 09:00 = 北京时间 22:00（冬令时）/ 21:00（夏令时）
# 调整 -DailyAt 后面的时间匹配你的本地时间
# ============================================================

$action  = New-ScheduledTaskAction `
    -Execute "python.exe" `
    -Argument "$PSScriptRoot\ai_news_monitor.py --auto-generate" `
    -WorkingDirectory $PSScriptRoot

$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "22:00"   # 美东 09:00（北京 22:00）

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask `
    -TaskName "tkhjtools-ai-news-monitor" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "每天美东 9 点抓取 AI 新闻并生成草稿" `
    -Force

Write-Output "计划任务创建成功。用下面命令测试："
Write-Output "  Start-ScheduledTask -TaskName tkhjtools-ai-news-monitor"
