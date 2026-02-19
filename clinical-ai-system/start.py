import subprocess
import sys

python = sys.executable  # current venv python

subprocess.Popen([python, "api_service.py"])
subprocess.Popen([python, "followup_service.py"])

print("Both API and Follow-up services started.")
print("Dashboard: http://127.0.0.1:9000/login")
print("API:       http://127.0.0.1:9001/api/health")

input("Press ENTER to stop servers...")
