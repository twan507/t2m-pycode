import subprocess
import os

try:
    path = os.getcwd()
    subprocess.run(["python", path + "\\t2m-capital-allocation.py"], check=True)

except subprocess.CalledProcessError as e:
    print(f"Error: {type(e).__name__}")

# pyinstaller --onefile run-capital-allocation.py