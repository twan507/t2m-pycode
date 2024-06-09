import subprocess
import os
import time

path = os.getcwd()

try:
    subprocess.run(['python', path + '\\t2m-tele-bot.py'], check=True)
except subprocess.CalledProcessError as e:
    print(f"Error: {type(e).__name__}")
    time.sleep(30)