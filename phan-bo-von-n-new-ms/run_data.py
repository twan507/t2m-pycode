import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import os
import datetime as dt
from datetime import datetime
import pandas as pd
import time
import asyncio
import platform

# Set environment variables for debugger
os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"

# Set the event loop policy for Windows
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def run_notebook(path):
    # Đọc file notebook
    with open(path + "\\t2m-notebook.ipynb", "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    # Tạo một executor để chạy notebook
    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")

    # Sử dụng đường dẫn của notebook để chạy các cells trong cùng thư mục đó
    ep.preprocess(nb, {"metadata": {"path": path}})

while True:
    try:
        start_time = time.time()
        current_path = os.getcwd()
        run_notebook(current_path)

        end_time = time.time()

        print(
            f"Completed in: {int(end_time - start_time)}s"
        )
        time.sleep(60)

    except Exception as e:
        print(f"Error: {type(e).__name__}")
        time.sleep(60)
