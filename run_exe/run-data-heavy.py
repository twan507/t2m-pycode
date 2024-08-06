import subprocess
import os

try:
    path = os.getcwd()
    subprocess.run(["python", path + "\\t2m-run-notebook-heavy.py"], check=True)

except subprocess.CalledProcessError as e:
    print(f"Error: {type(e).__name__}")