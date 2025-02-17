import subprocess
import os

try:
    path = os.getcwd()
    subprocess.run(["python", path + "\\run-notebook-cts.py"], check=True)

except subprocess.CalledProcessError as e:
    print(f"Error: {type(e).__name__}")

# pyinstaller --onefile run-cts-data.py