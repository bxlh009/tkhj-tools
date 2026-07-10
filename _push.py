import subprocess, os
os.chdir(r"D:\codex\content-engine")
token = "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"
remote = f"https://bxlh009:{token}@github.com/bxlh009/tkjh-tools.git"
result = subprocess.run(["git", "push", remote, "main"], capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)