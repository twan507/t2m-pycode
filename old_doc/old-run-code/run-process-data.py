import subprocess
import os

try:
    path = os.getcwd()
    subprocess.run(["python", path + "\\t2m-process-data.py"], check=True)

except subprocess.CalledProcessError as e:
    print(f"Error: {type(e).__name__}")