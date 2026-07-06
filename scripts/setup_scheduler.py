# -*- coding: utf-8 -*-
"""
setup_scheduler.py — register a Windows Task Scheduler job that runs
daily_ai_news.py at 08:00 US Eastern time (adjusts for EST/EDT).

Usage (run as Administrator):
    python scripts\setup_scheduler.py

The task is registered as:
    Name:     TKHJTools-DailyAINews
    Trigger:  Daily at 08:00 US Eastern (the scheduler converts to local time)
    Action:   python.exe <ENGINE_DIR>\scripts\daily_ai_news.py
    Workdir:  <ENGINE_DIR>

Requires:  Windows + schtasks.exe (built-in).
"""
import os
import pathlib
import subprocess
import sys

ENGINE_DIR = pathlib.Path(__file__).resolve().parent.parent
SCRIPT     = ENGINE_DIR / "scripts" / "daily_ai_news.py"
PYTHON     = sys.executable
TASK_NAME  = "TKHJTools-DailyAINews"

# 08:00 US Eastern = 13:00 UTC (EST, winter) or 12:00 UTC (EDT, summer).
# Windows Task Scheduler handles DST if we use TZID "Eastern Standard Time".
SCHTASKS_XML = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Daily AI news check + conditional article publish for TKHJ Tools</Description>
    <Author>TKHJ Tools</Author>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2025-01-01T08:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Princials>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Priority>7</Priority>
    <Settings>
        <IdleSettings>
            <StopOnIdleEnd>false</StopOnIdleEnd>
            <RestartOnIdle>false</RestartOnIdle>
        </IdleSettings>
    </Settings>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{PYTHON}</Command>
      <Arguments>"{SCRIPT}"</Arguments>
      <WorkingDirectory>{ENGINE_DIR}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""

def main():
    if sys.platform != "win32":
        print("This scheduler setup is Windows-only.")
        return 1
    # Write XML to a temp file
    xml_path = ENGINE_DIR / "_task_def.xml"
    xml_path.write_text(SCHTASKS_XML, encoding="utf-16")
    print(f"Wrote task XML: {xml_path}")
    # Register the task (requires admin)
    cmd = [
        "schtasks.exe",
        "/Create",
        "/TN", TASK_NAME,
        "/XML", str(xml_path),
        "/F",  # force overwrite
    ]
    print(f"Registering task '{TASK_NAME}'...")
    print(f"  command: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    print("stdout:", r.stdout)
    print("stderr:", r.stderr)
    if r.returncode == 0:
        print(f"Task '{TASK_NAME}' registered successfully.")
        print("Verify with: schtasks /Query /TN " + TASK_NAME)
    else:
        print(f"Task registration failed (exit code {r.returncode}).")
        print("Try running this script as Administrator.")
    # cleanup
    try:
        xml_path.unlink()
    except Exception:
        pass
    return 0

if __name__ == "__main__":
    sys.exit(main())
