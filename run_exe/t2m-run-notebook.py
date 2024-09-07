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
    
def get_current_time(start_time_am, end_time_am, start_time_pm, end_time_pm, start_time_ev, end_time_ev):
    current_time = dt.datetime.now().time()  # Khai báo trước để tránh UnboundLocalError
    run_state = None  # Mặc định là None để xử lý trường hợp không vào bất kỳ nhánh nào

    # Xác định thứ trong tuần là ngày làm việc hay cuối tuần
    if dt.datetime.now().weekday() <= 4:  # Ngày làm việc
        if current_time < start_time_am:
            run_state = 1
        elif start_time_am <= current_time < end_time_am:
            run_state = 0
        elif end_time_am <= current_time < start_time_pm:
            run_state = 0
        elif start_time_pm <= current_time < end_time_pm:
            run_state = 0
        elif end_time_pm <= current_time < start_time_ev:
            current_time = end_time_pm  # Cập nhật current_time để phản ánh thời điểm chuyển giao
            run_state = 2
        elif start_time_ev <= current_time < end_time_ev:
            current_time = end_time_pm  # Giữ nguyên
            run_state = 0
        elif current_time >= end_time_ev:
            current_time = end_time_pm  # Giữ nguyên
            run_state = 4
    else:  # Cuối tuần
        run_state = 3

    return current_time, run_state  # Trả về giá trị đã được xác định hoặc None nếu không vào nhánh nào

def run_current_data(path):
    with open(path + "\\process_current_data.ipynb", "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)
    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
    ep.preprocess(nb, {"metadata": {"path": path}})

def run_period_data(current_time):
    start_time = time.time()

    date_series = pd.read_csv("D:\\t2m-project\\ami-data\\ami_eod_data\\VNINDEX.csv").iloc[-1]
    date_series["date"] = pd.to_datetime(date_series["date"].astype(str), format="%y%m%d")

    current_path = (os.path.dirname(os.getcwd()))

    with open(current_path + "\\process_period_data.ipynb", "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)
    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
    ep.preprocess(nb, {"metadata": {"path": current_path}})

    end_time = time.time()

    print(f"Update time: {datetime.combine(date_series['date'].date(), current_time).strftime('%d/%m/%Y %H:%M:%S')}, Real time: {dt.datetime.now().time().strftime('%H:%M:%S')}, Completed in: {int(end_time - start_time)}s \n")

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

current_time, run_state = get_current_time(dt.time(9, 00), dt.time(11, 30), dt.time(13, 00), dt.time(15, 10), dt.time(19, 00), dt.time(21, 00))
if run_state == 1:
    try:
        print("Running period data...")
        run_period_data(current_time)
    except Exception as e:
        print(f"Error: {type(e).__name__}")
    
print("Running current data ...")

#Lấy ra ngày hiện tại
date_series = pd.read_csv("D:\\t2m-project\\ami-data\\ami_eod_data\\VNINDEX.csv").iloc[-1]
date_series["date"] = pd.to_datetime(date_series["date"].astype(str), format="%y%m%d")
current_path = (os.path.dirname(os.getcwd()))

#Chạy test 1 lần trước
start_time = time.time()
current_time, run_state = get_current_time(dt.time(9, 00), dt.time(11, 30), dt.time(13, 00), dt.time(15, 10), dt.time(19, 00), dt.time(21, 00))
run_current_data(current_path)

end_time = time.time()
print(f"Update time: {datetime.combine(date_series['date'].date(), current_time).strftime('%d/%m/%Y %H:%M:%S')}, Real time: {dt.datetime.now().time().strftime('%H:%M:%S')}, Completed in: {int(end_time - start_time)}s")

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
            pass
        elif run_state == 4:
            break

        run_current_data(current_path)

        end_time = time.time()

        print(f"Update time: {datetime.combine(date_series['date'].date(), current_time).strftime('%d/%m/%Y %H:%M:%S')}, Real time: {dt.datetime.now().time().strftime('%H:%M:%S')}, Completed in: {int(end_time - start_time)}s")
    except Exception as e:
        print(f"Error: {type(e).__name__}")
    