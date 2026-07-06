# -*- coding: utf-8 -*-
"""Register daily_generate.py as a Windows scheduled task at 08:00 US Eastern."""
import os, pathlib, subprocess, sys

ENGINE = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ENGINE / "scripts" / "daily_generate.py"
PYTHON = sys.executable
TASK_NAME = "TKHJTools-DailyContent"

xml = (
    '<?xml version="1.0" encoding="UTF-16"?>\n'
    '<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
    '  <RegistrationInfo>\n'
    '    <Description>Daily exam article + AI news check for TKHJ Tools</Description>\n'
    '    <Author>TKHJ Tools</Author>\n'
    '  </RegistrationInfo>\n'
    '  <Triggers>\n'
    '    <CalendarTrigger>\n'
    '      <StartBoundary>2025-01-01T08:00:00</StartBoundary>\n'
    '      <Enabled>true</Enabled>\n'
    '      <ScheduleByDay>\n'
    '        <DaysInterval>1</DaysInterval>\n'
    '      </ScheduleByDay>\n'
    '    </CalendarTrigger>\n'
    '  </Triggers>\n'
    '  <Principals>\n'
    '    <Principal id="Author">\n'
    '      <LogonType>InteractiveToken</LogonType>\n'
    '      <RunLevel>LeastPrivilege</RunLevel>\n'
    '    </Principal>\n'
    '  </Principals>\n'
    '  <Settings>\n'
    '    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n'
    '    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n'
    '    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n'
    '    <AllowHardTerminate>true</AllowHardTerminate>\n'
    '    <StartWhenAvailable>true</StartWhenAvailable>\n'
    '    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>\n'
    '    <ExecutionTimeLimit>PT60M</ExecutionTimeLimit>\n'
    '    <Priority>7</Priority>\n'
    '    <Settings>\n'
    '        <IdleSettings>\n'
    '            <StopOnIdleEnd>false</StopOnIdleEnd>\n'
    '            <RestartOnIdle>false</RestartOnIdle>\n'
    '        </IdleSettings>\n'
    '    </Settings>\n'
    '  </Settings>\n'
    '  <Actions Context="Author">\n'
    '    <Exec>\n'
    '      <Command>' + PYTHON + '</Command>\n'
    '      <Arguments>"' + str(SCRIPT) + '"</Arguments>\n'
    '      <WorkingDirectory>' + str(ENGINE) + '</WorkingDirectory>\n'
    '    </Exec>\n'
    '  </Actions>\n'
    '</Task>\n'
)

def main():
    if sys.platform != "win32":
        print("Windows only.")
        return 1
    xml_path = ENGINE / "_task_def.xml"
    xml_path.write_text(xml, encoding="utf-16")
    print("Wrote task XML: " + str(xml_path))
    cmd = ["schtasks.exe", "/Create", "/TN", TASK_NAME, "/XML", str(xml_path), "/F"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        print("STDERR:", r.stderr)
    if r.returncode == 0:
        print("Task '" + TASK_NAME + "' registered. Runs daily at 08:00 US Eastern.")
    else:
        print("Failed (exit " + str(r.returncode) + "). Run as Administrator.")
    try:
        xml_path.unlink()
    except:
        pass
    return 0

if __name__ == "__main__":
    sys.exit(main())
