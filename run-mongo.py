import subprocess
import threading

def run_script(script_name):
    # Đặt đường dẫn tới thư mục chứa script
    script_path = f"py-mongo/{script_name}"
    while True:
        subprocess.run(["python", script_path])

# Tên các script
scripts1 = [ "list1.py","list2.py","list3.py","list4.py","list5.py"]

# Tạo và khởi chạy các thread cho mỗi script
threads = []
for script in scripts1:
    thread = threading.Thread(target=run_script, args=(script,))
    thread.start()
    threads.append(thread)

# Chờ tất cả các thread hoàn thành
for thread in threads:
    thread.join()