import subprocess, os, sys

os.chdir(r"D:\codex\content-engine")

# Set env to disable schannel and use openssl
env = os.environ.copy()
env["GIT_SSL_NO_VERIFY"] = "1"
env["GCM_INTERACTIVE"] = "0"
env["GIT_TERMINAL_PROMPT"] = "0"

# Try with openssl backend instead of schannel
env["GIT_CONFIG_COUNT"] = "1"
env["GIT_CONFIG_KEY_0"] = "http.sslBackend"
env["GIT_CONFIG_VALUE_0"] = "openssl"

token = "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"
remote = f"https://bxlh009:{token}@github.com/bxlh009/tkjh-tools.git"

result = subprocess.run(
    ["git", "push", remote, "main"],
    capture_output=True, text=True, env=env
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[:500])