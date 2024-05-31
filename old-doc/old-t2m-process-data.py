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


def get_current_time(start_time_am, end_time_am, start_time_pm, end_time_pm):
    if (dt.datetime.now()).weekday() <= 4:
        current_time = dt.datetime.now().time()
        if current_time < start_time_am:
            current_time = end_time_pm
        elif (current_time >= start_time_am) & (current_time < end_time_am):
            current_time = current_time
        elif (current_time >= end_time_am) & (current_time < start_time_pm):
            current_time = end_time_am
        elif (current_time >= start_time_pm) & (current_time < end_time_pm):
            current_time = current_time
        elif current_time >= end_time_pm:
            current_time = end_time_pm
        return current_time
    if (dt.datetime.now()).weekday() > 4:
        return end_time_pm

def run_notebook(path):
    # Đọc file notebook
    with open(path + "\\t2m-process-data.ipynb", "r", encoding="utf-8") as f:
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

        current_time = get_current_time(
            dt.time(9, 00), dt.time(11, 30), dt.time(13, 00), dt.time(15, 00)
        )
        date_series = pd.read_csv(
            "D:\\t2m-project\\ami-data\\ami_eod_data\\VNINDEX.csv"
        ).iloc[-1]
        date_series["date"] = pd.to_datetime(
            date_series["date"].astype(str), format="%y%m%d"
        )

        end_time = time.time()

        print(
            f"Updated: {datetime.combine(date_series['date'].date(), current_time).strftime('%d/%m/%Y %H:%M:%S')}, Completed in: {int(end_time - start_time)}s"
        )

    except Exception as e:
        print(f"Error: {type(e).__name__}")
