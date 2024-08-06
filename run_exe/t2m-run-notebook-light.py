import asyncio
import datetime as dt
import os
import platform
import time
from datetime import datetime

import nbformat
import pandas as pd
from nbconvert.preprocessors import ExecutePreprocessor

# Set environment variables for debugger
os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"

# Set the event loop policy for Windows
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def run_notebook(path):
    with open(path + "\\t2m-notebook-light.ipynb", "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)
    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
    ep.preprocess(nb, {"metadata": {"path": path}})

def get_current_time(start_time_am, end_time_am, start_time_pm, end_time_pm, start_time_ev, end_time_ev):
    if (dt.datetime.now()).weekday() <= 4:
        current_time = dt.datetime.now().time()
        if current_time < start_time_am:
            current_time = start_time_am
            run_state = 1
        elif (current_time >= start_time_am) & (current_time < end_time_am):
            current_time = current_time
            run_state = 0
        elif (current_time >= end_time_am) & (current_time < start_time_pm):
            current_time = end_time_am
            run_state = 0
        elif (current_time >= start_time_pm) & (current_time < end_time_pm):
            current_time = current_time
            run_state = 0
        elif (current_time >= end_time_pm) & (current_time < start_time_ev):
            current_time = end_time_pm
            run_state = 2
        elif (current_time >= start_time_ev) & (current_time < end_time_ev):
            current_time = end_time_pm
            run_state = 0
        elif current_time >= end_time_ev:
            current_time = end_time_pm
            run_state = 4
    if (dt.datetime.now()).weekday() > 4:
        run_state = 3

    return current_time, run_state

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def run_test():
    start_time = time.time()
    current_time, run_state = get_current_time(dt.time(8, 30), dt.time(11, 30), dt.time(13, 00), dt.time(15, 10), dt.time(19, 00), dt.time(21, 00))

    date_series = pd.read_csv("D:\\t2m-project\\ami-data\\ami_eod_data\\VNINDEX.csv").iloc[-1]
    date_series["date"] = pd.to_datetime(date_series["date"].astype(str), format="%y%m%d")

    current_path = (os.path.dirname(os.getcwd()))
    run_notebook(current_path)

    end_time = time.time()

    print(f"Updated: {datetime.combine(date_series['date'].date(), current_time).strftime('%d/%m/%Y %H:%M:%S')}, Completed in: {int(end_time - start_time)}s")

try:
    print("Runing data light test...")
    run_test()
except Exception as e:
    print(f"Error: {type(e).__name__}")
    
print("Runing data light data ...")
while True:
    try:
        start_time = time.time()
        current_time, run_state = get_current_time(dt.time(9, 00), dt.time(11, 30), dt.time(13, 00), dt.time(15, 10), dt.time(19, 00), dt.time(21, 00))

        if run_state == 1:
            print("Chưa tới thời gian giao dịch: ",dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            time.sleep(60)
            continue
        elif run_state == 2:
            print("Đã hết thời gian giao dịch: ",dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            time.sleep(14000)
            continue
        elif run_state == 3:
            print("Ngày nghỉ không giao dịch: ",dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            time.sleep(86400)
            continue
        elif run_state == 4:
            print("Ngoài thời gian giao dịch: ",dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            time.sleep(42000)
            continue

        date_series = pd.read_csv("D:\\t2m-project\\ami-data\\ami_eod_data\\VNINDEX.csv").iloc[-1]
        date_series["date"] = pd.to_datetime(date_series["date"].astype(str), format="%y%m%d")

        current_path = (os.path.dirname(os.getcwd()))
        run_notebook(current_path)

        end_time = time.time()

        print(f"Updated: {datetime.combine(date_series['date'].date(), current_time).strftime('%d/%m/%Y %H:%M:%S')}, Completed in: {int(end_time - start_time)}s")
    except Exception as e:
        print(f"Error: {type(e).__name__}")