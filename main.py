import subprocess
import threading

def run_script(script_name):
    while True:
        subprocess.run(["python", script_name])

# Tên các script
scripts = ["script1.py", "script2.py", "script3.py"]

# Tạo và khởi chạy các thread cho mỗi script
threads = []
for script in scripts:
    thread = threading.Thread(target=run_script, args=(script,))
    thread.start()
    threads.append(thread)

# Chờ tất cả các thread hoàn thành
for thread in threads:
    thread.join()
