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
            run_state = 1 #Trước giờ giao dịch buổi sáng
        elif start_time_am <= current_time < end_time_am:
            run_state = 0 #Trong giờ giao dịch buổi sáng
        elif end_time_am <= current_time < start_time_pm:
            run_state = 0 #Giờ nghỉ trưa
        elif start_time_pm <= current_time < end_time_pm:
            run_state = 0 #Trong giờ giao dịch buổi chiều
        elif end_time_pm <= current_time < start_time_ev:
            run_state = 2 #Ngoài giờ giao dịch buổi chiều
            current_time = end_time_pm #Giữ nguyên thời gian là thời gian kết phiên giao dịch
        elif start_time_ev <= current_time < end_time_ev:
            run_state = 0 #Thời gian cập nhật dữ liệu tự doanh buổi tối
            current_time = end_time_pm #Giữ nguyên thời gian là thời gian kết phiên giao dịch
        elif current_time >= end_time_ev:
            run_state = 4 #Ngoài giờ cập nhật dữ liệu tự doanh buổi tối
            current_time = end_time_pm #Giữ nguyên thời gian là thời gian kết phiên giao dịch
    else:  
        run_state = 3 #Các ngày cuối tuần không giao dịch

    return current_time, run_state  # Trả về giá trị đã được xác định hoặc None nếu không vào nhánh nào

def run_period_data():
    current_time, _ = get_current_time(dt.time(9, 00), dt.time(11, 30), dt.time(13, 00), dt.time(15, 10), dt.time(19, 00), dt.time(21, 00))

    start_time = time.time()
    current_date = pd.to_datetime(dt.datetime.now().date(), format="%Y-%m-%d")
    current_path = (os.path.dirname(os.getcwd()))

    with open(current_path + "\\t2m_period_data.ipynb", "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)
    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
    ep.preprocess(nb, {"metadata": {"path": current_path}})

    end_time = time.time()

    print(f"Update time: {datetime.combine(current_date, current_time).strftime('%d/%m/%Y %H:%M:%S')}, Completed in: {int(end_time - start_time)}s\n")

def run_current_data():
    current_time, _ = get_current_time(dt.time(9, 00), dt.time(11, 30), dt.time(13, 00), dt.time(15, 10), dt.time(19, 00), dt.time(21, 00))

    start_time = time.time()
    current_date = pd.to_datetime(dt.datetime.now().date(), format="%Y-%m-%d")
    current_path = (os.path.dirname(os.getcwd()))

    with open(current_path + "\\t2m_current_data.ipynb", "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)
    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
    ep.preprocess(nb, {"metadata": {"path": current_path}})

    end_time = time.time()

    print(f"Update time: {datetime.combine(current_date, current_time).strftime('%d/%m/%Y %H:%M:%S')}, Completed in: {int(end_time - start_time)}s")



#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#Tính toán thời gian và trạng thái phiên giao dịch
_, run_state = get_current_time(dt.time(9, 00), dt.time(11, 30), dt.time(13, 00), dt.time(15, 10), dt.time(19, 00), dt.time(21, 00))

#Kiểm tra xem nếu trạng thái là 1 thì sẽ chạy period data
if run_state == 1:
    try:
        print("Running period data...")
        run_period_data()
    except Exception as e:
        print(f"Error: {type(e).__name__}")

#Nếu không trong giờ giao dịch thì chạy test 1 lần
if run_state != 0:
    try:
        print("Running test current data ...")
        run_current_data()
    except Exception as e:
            print(f"Error: {type(e).__name__}")

#Tạo vòng lặp để chạy dữ liệu liên tục trong giờ giao dịch
print("Running current data ...")
while True:
    try:
        if run_state == 1:
            print("Chưa tới thời gian giao dịch: ",dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            time.sleep(60)
            continue
        elif run_state == 2:
            print("Đã hết thời gian giao dịch: ",dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            time.sleep(14000)
            continue
        elif run_state == 3:
            print("Cuối tuần không giao dịch: ",dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            time.sleep(14000)
            continue
        elif run_state == 4:
            break
        else:
            run_current_data()
    except Exception as e:
        print(f"Error: {type(e).__name__}")
    