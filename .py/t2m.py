import subprocess
import os

try:
    path = os.getcwd()
    main_path = path + "\\.py\\main.py"
    # main_path = os.path.join(path, ".py", "main.py")
    subprocess.Popen(
        ["pythonw", main_path],
        creationflags=subprocess.DETACHED_PROCESS
    )

except subprocess.CalledProcessError as e:
    print(f"Error: {type(e).__name__}")

# pyinstaller --noconsole --onefile --icon=t2m.ico t2m.py