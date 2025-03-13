import os
import sys
import subprocess
import argparse
import time
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
import asyncio

# Set environment variables for debugger
os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"

try:
    from asyncio import WindowsSelectorEventLoopPolicy
    # Chỉ áp dụng trên Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
except ImportError:
    pass

def install_requirements():
    """Cài đặt các thư viện từ file requirements.txt"""
    requirements_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'requirements.txt')
    
    if not os.path.exists(requirements_path):
        print(f"Không tìm thấy file requirements.txt tại: {requirements_path}")
        return False
    
    print("Đang kiểm tra và cài đặt các thư viện cần thiết...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_path])
        print("✓ Đã cài đặt thành công tất cả các thư viện.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Lỗi khi cài đặt thư viện: {str(e)}")
        return False

def get_notebooks(directory=None):
    """Tìm kiếm tất cả các file .ipynb trong thư mục được chỉ định"""
    if directory is None:
        # Tìm trong thư mục .ipynb mặc định
        directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../.ipynb')
    
    if not os.path.exists(directory):
        print(f"Không tìm thấy thư mục notebook: {directory}")
        return []
    
    ipynb_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.ipynb'):
                ipynb_files.append(os.path.join(root, file))
    
    return ipynb_files

def execute_notebook(notebook_path, output_dir=None):
    # Tạo thư mục đầu ra nếu được chỉ định và chưa tồn tại
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, os.path.basename(notebook_path))
    else:
        output_path = None
    
    # Đọc notebook
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = nbformat.read(f, as_version=4)
    except Exception as e:
        # print(f"Lỗi khi đọc notebook: {str(e)}")
        return False, ""
    
    # Cấu hình quá trình thực thi notebook
    ep = ExecutePreprocessor(timeout=3600, kernel_name='python3')
    
    try:
        # Thực thi notebook
        start_time = datetime.now()
        sys.stdout.flush()
        
        ep.preprocess(notebook, {'metadata': {'path': os.path.dirname(notebook_path)}})
        
        end_time = datetime.now()
        execution_time = end_time - start_time
        total_seconds = execution_time.total_seconds()
        rounded_seconds = round(total_seconds, 1)
        
        # Định dạng lại thời gian: phút:giây.phần thập phân
        minutes = int(rounded_seconds // 60)
        seconds = rounded_seconds % 60
        formatted_time = f"{minutes}m:{seconds:.1f}s"
        
        # Thay vì print, ta trả về kết quả
        return True, formatted_time
    except Exception as e:
        return False, "Lỗi, chạy lại."

def find_notebook_by_name(name, notebooks):
    """Tìm notebook theo tên (có thể không chỉ định đường dẫn đầy đủ)"""
    # Kiểm tra đường dẫn trực tiếp
    if os.path.exists(name) and name.endswith('.ipynb'):
        return name
    
    # Tìm theo tên file
    for notebook in notebooks:
        if os.path.basename(notebook) == name:
            return notebook
        if os.path.basename(notebook) == name + '.ipynb':
            return notebook
    
    return None

class NotebookRunnerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Notebook Runner")
        
        # Set window size
        window_width = 900
        window_height = 950
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate position coordinates for center of screen
        x = (screen_width - window_width) // 2
        y = (screen_height-100 - window_height) // 2
        
        # Set window size and position
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.iconbitmap(r".py/logo.ico")
        
        # Variables
        self.notebooks = []
        self.filtered_notebooks = []  # Add this line to initialize the list
        self.selected_notebooks = []
        self.running_notebooks = {}  # Store running notebook information {path: {'thread': thread, 'time': 0.0, 'status': 'running', 'controls': {...}}}
        self.timer_running = False  # Flag to control the timer thread
        
        self.create_widgets()
        self.refresh_notebooks()

    def check_auto_run_time(self):
        """Check if it's time to auto-run notebooks sequentially"""
        if hasattr(self, 'root') and self.root.winfo_exists():
            # Get current time
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            
            try:
                # Get selected time
                selected_hour = int(self.auto_run_hour.get())
                selected_minute = int(self.auto_run_minute.get())
                
                # Update countdown display
                if self.auto_run_enabled.get():
                    if (current_hour < selected_hour or 
                        (current_hour == selected_hour and current_minute < selected_minute)):
                        # Calculate time remaining
                        target_time = now.replace(hour=selected_hour, minute=selected_minute, second=0)
                        time_diff = target_time - now
                        hours, remainder = divmod(time_diff.seconds, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        
                        if hours > 0:
                            countdown = f"Còn {hours} giờ {minutes} phút"
                        else:
                            countdown = f"Còn {minutes} phút {seconds} giây"
                        
                        self.auto_run_timer_label.config(text=countdown, foreground="blue")
                    elif (current_hour == selected_hour and current_minute == selected_minute):
                        # Time matched - run notebooks sequentially!
                        self.auto_run_timer_label.config(text="Đang chạy...", foreground="green")
                        
                        # Run notebooks sequentially
                        sorted_notebooks = self.get_notebooks_by_ui_order()
                        if sorted_notebooks:
                            self.log(f"Tự động chạy lần lượt {len(sorted_notebooks)} notebooks vào lúc {selected_hour:02d}:{selected_minute:02d}")
                            sequence_thread = Thread(target=self.execute_notebooks_sequence, args=(sorted_notebooks,))
                            sequence_thread.daemon = True
                            sequence_thread.start()
                            
                            # Disable auto-run after triggering
                            self.auto_run_enabled.set(False)
                        else:
                            self.auto_run_timer_label.config(text="Không có notebooks", foreground="red")
                            self.auto_run_enabled.set(False)

                    else:
                        # Time already passed
                        self.auto_run_timer_label.config(text="Thời gian đã qua", foreground="orange")
                else:
                    self.auto_run_timer_label.config(text="")
                    
            except (ValueError, TypeError) as e:
                self.auto_run_timer_label.config(text="Lỗi định dạng thời gian", foreground="red")
            
            # Check again after 1 second
            self.root.after(1000, self.check_auto_run_time)

    def _is_time_passed(self, hour, minute):
        """Check if the current time has passed the given hour:minute"""
        now = datetime.now()
        return now.hour > hour or (now.hour == hour and now.minute >= minute)

    def start_notebook(self, notebook_path):
        """Start running a notebook, no waiting for auto-start time"""
        info = self.running_notebooks[notebook_path]
        
        # Already running or waiting, don't do anything
        if info['status'] == 'running' or info['status'] == 'waiting':
            return
        
        # Start immediately - no more waiting for auto-start time
        self._start_notebook_immediately(notebook_path)

    def run_all_notebooks_parallel(self):
        """Run all notebooks in the running list simultaneously"""
        if not self.running_notebooks:
            messagebox.showwarning("Chú ý", "Không có notebook nào trong danh sách chạy.")
            return
        
        # Count how many notebooks will be started
        start_count = 0
        
        # Start all notebooks that aren't already running
        for notebook_path, info in list(self.running_notebooks.items()):
            if info['status'] != 'running':
                self.start_notebook(notebook_path)
                start_count += 1
        
        if start_count > 0:
            self.log(f"Đã bắt đầu chạy đồng thời {start_count} notebooks")
        else:
            self.log("Tất cả notebooks đã đang chạy")

    def _start_notebook_immediately(self, notebook_path):
        """Actually start the notebook without any delay checks"""
        info = self.running_notebooks[notebook_path]
        
        # Reset UI and status
        info['status'] = 'running'
        info['stop_flag'] = False
        info['time'] = 0.0
        info['time_label'].config(text="00:00.0")
        info['status_label'].config(text="Đang chạy", foreground="blue")
        
        # Update controls
        info['controls']['start_btn'].config(state=tk.DISABLED)
        info['controls']['stop_btn'].config(state=tk.NORMAL)
        
        # Create and start the thread
        thread = Thread(target=self.run_notebook_continuously, args=(notebook_path,))
        thread.daemon = True
        thread.start()
        
        info['thread'] = thread
        # self.log(f"Bắt đầu chạy: {os.path.basename(notebook_path)}")

    def check_stop_time(self):
        """Start a periodic check for the auto-stop time"""
        if hasattr(self, 'root') and self.root.winfo_exists():
            # Get current time
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            
            try:
                # Get selected time
                selected_hour = int(self.hour_var.get())
                selected_minute = int(self.minute_var.get())
                
                # Update countdown display
                if self.auto_stop_enabled.get():
                    if (current_hour < selected_hour or 
                        (current_hour == selected_hour and current_minute < selected_minute)):
                        # Calculate time remaining
                        target_time = now.replace(hour=selected_hour, minute=selected_minute, second=0)
                        time_diff = target_time - now
                        hours, remainder = divmod(time_diff.seconds, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        
                        if hours > 0:
                            countdown = f"Còn {hours} giờ {minutes} phút"
                        else:
                            countdown = f"Còn {minutes} phút {seconds} giây"
                        
                        self.stop_timer_label.config(text=countdown, foreground="blue")
                    elif (current_hour == selected_hour and current_minute == selected_minute):
                        # Time matched - stop all notebooks!
                        stopped_count = self.stop_all_notebooks()
                        self.stop_timer_label.config(text=f"Đã dừng {stopped_count} notebooks", foreground="green")
                        self.log(f"Đã tự động dừng {stopped_count} notebooks vào lúc {selected_hour:02d}:{selected_minute:02d}")
                        # Disable auto-stop after triggering
                        self.auto_stop_enabled.set(False)

                    else:
                        # Time already passed
                        self.stop_timer_label.config(text="Thời gian đã qua", foreground="orange")
                else:
                    self.stop_timer_label.config(text="")
            except (ValueError, TypeError) as e:
                self.stop_timer_label.config(text="Lỗi định dạng thời gian", foreground="red")
            
            # Check again after 1 second
            self.root.after(1000, self.check_stop_time)

    def run_notebooks_sequentially(self):
        """Run all notebooks in the running list sequentially from top to bottom"""
        if not self.running_notebooks:
            messagebox.showwarning("Chú ý", "Không có notebook nào trong danh sách chạy.")
            return
        
        # Get notebooks sorted by their position in the UI
        sorted_notebooks = self.get_notebooks_by_ui_order()
        if not sorted_notebooks:
            return
        
        # Start the sequential run in a separate thread
        sequence_thread = Thread(target=self.execute_notebooks_sequence, args=(sorted_notebooks,))
        sequence_thread.daemon = True
        sequence_thread.start()
        
        self.log(f"Bắt đầu chạy lần lượt {len(sorted_notebooks)} notebooks")

    def get_notebooks_by_ui_order(self):
        """Get notebooks sorted by their vertical position in the UI"""
        notebook_positions = []
        
        # Get each notebook's frame position
        for notebook_path, info in self.running_notebooks.items():
            if 'frame' in info and info['frame'].winfo_exists():
                y_position = info['frame'].winfo_y()
                notebook_positions.append((y_position, notebook_path))
        
        # Sort by Y position (top to bottom)
        notebook_positions.sort()
        
        # Return just the sorted notebook paths
        return [path for _, path in notebook_positions]

    def execute_notebooks_sequence(self, notebook_paths):
        """Execute a sequence of notebooks one after another, respecting loop settings"""
        for notebook_path in notebook_paths:
            # Skip if notebook was removed from the running list
            if notebook_path not in self.running_notebooks:
                continue
                    
            info = self.running_notebooks[notebook_path]
            
            # Skip ONLY if currently running, not if stopped/completed
            if info['status'] == 'running':
                self.log(f"Bỏ qua {os.path.basename(notebook_path)} vì đang chạy")
                continue
                
            # Ensure thread is properly cleaned up
            if 'thread' in info and info['thread'] is not None and info['thread'].is_alive():
                self.log(f"Đợi thread cũ kết thúc cho {os.path.basename(notebook_path)}")
                info['stop_flag'] = True
                time.sleep(0.5)  # Brief pause to let thread respond to stop flag
            
            # Reset notebook state to prepare for new run
            info['thread'] = None
            info['stop_flag'] = False
                
            # Update UI to show we're starting this notebook
            notebook_name = os.path.basename(notebook_path)
            
            # Determine if this notebook should run in loop mode
            is_loop_mode = info['loop_var'].get()
            
            if is_loop_mode:
                # For loop mode notebooks, start them in their own thread
                self.log(f"Chạy lặp lại: {notebook_name}")
                # Use the existing start_notebook method which creates a background thread
                self._start_notebook_immediately(notebook_path)
                
                # Wait for 60 seconds before proceeding to the next notebook
                self.log(f"Đợi 60 giây trước khi chạy notebook tiếp theo...")
                
                # Wait in small increments to keep UI responsive
                wait_start = time.time()
                while time.time() - wait_start < 60:
                    time.sleep(0.1)
                    try:
                        self.root.update_idletasks()  # Keep UI responsive
                    except:
                        pass
                        
            else:
                # For non-loop mode notebooks, run them the specified number of times
                try:
                    runs_count = int(info['runs_var'].get())
                except ValueError:
                    runs_count = 2  # Default to 2 if value is invalid
                
                # Ensure valid runs count
                if runs_count < 1:
                    runs_count = 1
                
                self.log(f"Chạy {notebook_name} {runs_count} lần")
                
                # Update status and UI
                info['status'] = 'running'
                info['time'] = 0.0
                
                try:
                    # Update UI elements
                    info['time_label'].config(text="00m:00.0s")
                    info['status_label'].config(text="Đang chạy", foreground="blue")
                    info['controls']['start_btn'].config(state=tk.DISABLED)
                    info['controls']['stop_btn'].config(state=tk.NORMAL)
                    
                    # Run notebook the specified number of times
                    for run_num in range(1, runs_count + 1):
                        # Check stop flag
                        if info['stop_flag'] or notebook_path not in self.running_notebooks:
                            break
                        
                        # Log the execution
                        current_time = datetime.now().strftime("%H:%M:%S")
                        info['log_text'].insert(tk.END, f"\n--- Chạy lần lượt lần {run_num}/{runs_count} ({current_time}): ")
                        info['log_text'].see(tk.END)
                        
                        # Execute notebook
                        self.execute_notebook_with_log(notebook_path, info['log_text'], info['status_label'])
                        
                        # If it's not the last run and we haven't been stopped, wait briefly
                        if run_num < runs_count and not info['stop_flag']:
                            try:
                                # Show waiting status
                                if info['status_label'].winfo_exists():
                                    info['status_label'].config(text=f"Đợi lần {run_num+1}/{runs_count}", foreground="blue")
                                
                                # Wait in small increments to keep UI responsive and check stop flag
                                for _ in range(10):  # 10 x 0.1s = 1s
                                    if info['stop_flag']:
                                        break
                                    time.sleep(0.1)
                                    try:
                                        self.root.update_idletasks()  # Keep UI responsive
                                    except:
                                        pass
                                
                                # Update status back to running
                                if not info['stop_flag'] and info['status_label'].winfo_exists():
                                    info['status_label'].config(text="Đang chạy", foreground="blue")
                            except tk.TclError:
                                pass
                    
                    # Update status after completion if not stopped
                    if not info['stop_flag'] and notebook_path in self.running_notebooks:
                        info['status'] = 'completed'
                        info['status_label'].config(text="Hoàn thành", foreground="green")
                        info['controls']['start_btn'].config(state=tk.NORMAL)
                        info['controls']['stop_btn'].config(state=tk.DISABLED)
                        
                except Exception as e:
                    self.log(f"Lỗi khi chạy lần lượt {notebook_name}: {str(e)}")
                    if notebook_path in self.running_notebooks:
                        info['status'] = 'error'
                        if 'status_label' in info and info['status_label'].winfo_exists():
                            info['status_label'].config(text="Lỗi", foreground="red")
                        if 'controls' in info and 'start_btn' in info['controls'] and info['controls']['start_btn'].winfo_exists():
                            info['controls']['start_btn'].config(state=tk.NORMAL)
                        if 'controls' in info and 'stop_btn' in info['controls'] and info['controls']['stop_btn'].winfo_exists():
                            info['controls']['stop_btn'].config(state=tk.DISABLED)
        
        self.log("Đã hoàn thành chạy lần lượt tất cả notebooks")

    def stop_all_notebooks(self):
        """Stop all running notebooks"""
        stopped_count = 0
        for notebook_path, info in list(self.running_notebooks.items()):
            if info['status'] == 'running':
                self.stop_notebook(notebook_path)
                stopped_count += 1
        
        if stopped_count > 0:
            self.log(f"Đã tự động dừng {stopped_count} notebooks vào lúc {self.hour_var.get()}:{self.minute_var.get()}")
        
        return stopped_count
    
    def clear_all_logs(self):
        """Clear logs for all notebooks in the running list"""
        # Count how many notebook logs were cleared
        cleared_count = 0
        
        # Clear each notebook's log
        for notebook_path, info in self.running_notebooks.items():
            if 'log_text' in info and info['log_text'].winfo_exists():
                info['log_text'].delete(1.0, tk.END)
                cleared_count += 1
        
        # Log the action
        if cleared_count > 0:
            self.log(f"Đã xóa log của {cleared_count} notebooks")
        else:
            self.log("Không có log nào để xóa")

    def clear_notebook_selection(self):
        """Clear the selection in the notebook listbox"""
        # Reset display for all items (remove any selection numbers)
        for i in range(self.notebook_listbox.size()):
            notebook_name = os.path.basename(self.filtered_notebooks[i])
            self.notebook_listbox.delete(i)
            self.notebook_listbox.insert(i, f"    | {notebook_name}")
        
        self.notebook_listbox.selection_clear(0, tk.END)  # Clear all selections
        self.selected_notebooks = []  # Clear the selected_notebooks list
        self.selection_order = []     # Clear the selection order list
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top actions
        actions_frame = ttk.Frame(main_frame)
        actions_frame.pack(fill=tk.X, pady=5)
        
        install_btn = ttk.Button(actions_frame, text="Cài đặt thư viện", command=self.install_requirements_thread)
        install_btn.pack(side=tk.LEFT, padx=5)
        
        refresh_btn = ttk.Button(actions_frame, text="Làm mới danh sách", command=self.refresh_notebooks)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(actions_frame, text="Sẵn sàng")
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
        # Notebooks list section
        notebook_frame = ttk.LabelFrame(main_frame, text="Notebooks có sẵn")
        notebook_frame.pack(fill=tk.X, pady=10)
        
        list_frame = ttk.Frame(notebook_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Change selection mode from MULTIPLE to EXTENDED
        self.notebook_listbox = tk.Listbox(list_frame, height=6, selectmode=tk.EXTENDED)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.notebook_listbox.yview)
        self.notebook_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.notebook_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add instance variable to track selection order
        self.selection_order = []
        
        # Modify the binding to use our custom selection handler
        self.notebook_listbox.bind('<<ListboxSelect>>', self.on_notebook_select)
        
        # Create a button frame to organize buttons better
        button_frame = ttk.Frame(notebook_frame)
        button_frame.pack(side=tk.RIGHT, padx=5, pady=5)

        # Add "Thêm Notebooks" button with improved styling
        add_btn = ttk.Button(button_frame, text="Thêm Notebooks", 
                        command=self.add_selected_notebooks,
                        width=20)
        add_btn.pack(side=tk.RIGHT, padx=3)

        # Add "Bỏ chọn" button with consistent styling
        clear_select_btn = ttk.Button(button_frame, text="Bỏ chọn", 
                                    command=self.clear_notebook_selection,
                                    width=20)
        clear_select_btn.pack(side=tk.RIGHT, padx=3)
        
        # --- Auto-action container with simplified design ---
        auto_container = ttk.Frame(main_frame)
        auto_container.pack(fill=tk.X, pady=5)
        
        # Simplified auto-run frame
        auto_run_frame = ttk.LabelFrame(auto_container, text="Tự động chạy lần lượt")
        auto_run_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        auto_run_content = ttk.Frame(auto_run_frame)
        auto_run_content.pack(fill=tk.X, padx=5, pady=10)
        
        self.auto_run_enabled = tk.BooleanVar(value=False)
        auto_run_check = ttk.Checkbutton(auto_run_content, text="Chạy lần lượt lúc:", variable=self.auto_run_enabled)
        auto_run_check.pack(side=tk.LEFT, padx=5)
        
        time_frame = ttk.Frame(auto_run_content)
        time_frame.pack(side=tk.LEFT, padx=5)
        
        self.auto_run_hour = tk.StringVar(value="08")
        hour_spin = ttk.Spinbox(time_frame, from_=0, to=23, width=4, format="%02.0f", textvariable=self.auto_run_hour)
        hour_spin.pack(side=tk.LEFT, padx=2)
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT)
        
        self.auto_run_minute = tk.StringVar(value="30")
        minute_spin = ttk.Spinbox(time_frame, from_=0, to=59, width=4, format="%02.0f", textvariable=self.auto_run_minute)
        minute_spin.pack(side=tk.LEFT, padx=2)
        
        self.auto_run_timer_label = ttk.Label(auto_run_content, text="")
        self.auto_run_timer_label.pack(side=tk.LEFT, padx=10)
        
        # Auto-stop frame (unchanged)
        auto_stop_frame = ttk.LabelFrame(auto_container, text="Ngừng tự động")
        auto_stop_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        auto_stop_content = ttk.Frame(auto_stop_frame)
        auto_stop_content.pack(fill=tk.X, padx=5, pady=10)
        
        self.auto_stop_enabled = tk.BooleanVar(value=False)
        auto_stop_check = ttk.Checkbutton(auto_stop_content, text="Ngừng tất cả lúc:", variable=self.auto_stop_enabled)
        auto_stop_check.pack(side=tk.LEFT, padx=5)
        
        time_frame = ttk.Frame(auto_stop_content)
        time_frame.pack(side=tk.LEFT, padx=5)
        
        self.hour_var = tk.StringVar(value="15")
        hour_spin = ttk.Spinbox(time_frame, from_=0, to=23, width=4, format="%02.0f", textvariable=self.hour_var)
        hour_spin.pack(side=tk.LEFT, padx=2)
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT)
        
        self.minute_var = tk.StringVar(value="10")
        minute_spin = ttk.Spinbox(time_frame, from_=0, to=59, width=4, format="%02.0f", textvariable=self.minute_var)
        minute_spin.pack(side=tk.LEFT, padx=2)
        
        self.stop_timer_label = ttk.Label(auto_stop_content, text="")
        self.stop_timer_label.pack(side=tk.LEFT, padx=10)
        
        # Start timer checks
        self.check_auto_run_time()
        self.check_stop_time()

        # ADD NEW CONTROL BUTTONS FRAME HERE
        notebooks_control_frame = ttk.Frame(main_frame)
        notebooks_control_frame.pack(fill=tk.X, pady=5)

        # Add "Chạy lần lượt" button to new location
        run_sequential_btn = ttk.Button(notebooks_control_frame, text="Chạy lần lượt", 
                                    command=self.run_notebooks_sequentially, 
                                    width=20)
        run_sequential_btn.pack(side=tk.LEFT, padx=5, pady=5)

        # Add new "Chạy đồng thời" button
        run_parallel_btn = ttk.Button(notebooks_control_frame, text="Chạy đồng thời", 
                                command=self.run_all_notebooks_parallel, 
                                width=20)
        run_parallel_btn.pack(side=tk.LEFT, padx=5, pady=5)

        # Add "Xóa tất cả" button between the other buttons
        remove_all_btn = ttk.Button(notebooks_control_frame, text="Xóa tất cả", 
                                command=self.remove_all_notebooks, 
                                width=20)
        remove_all_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        # Add "Dừng tất cả" button next to it
        stop_all_btn = ttk.Button(notebooks_control_frame, text="Dừng tất cả", 
                                command=self.stop_all_notebooks, 
                                width=20)
        stop_all_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        # Add new "Xóa tất cả Log" button
        clear_all_logs_btn = ttk.Button(notebooks_control_frame, text="Xóa tất cả Log", 
                                command=self.clear_all_logs, 
                                width=20)
        clear_all_logs_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        # Running notebooks frame
        self.running_frame = ttk.LabelFrame(main_frame, text="Notebooks đang chạy")
        self.running_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Create canvas with scrollbar for running notebooks
        self.running_canvas = tk.Canvas(self.running_frame)
        running_scrollbar = ttk.Scrollbar(self.running_frame, orient="vertical", command=self.running_canvas.yview)

        # Configure canvas to resize with frame
        self.running_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        running_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.running_canvas.configure(yscrollcommand=running_scrollbar.set)

        # Create container frame inside canvas
        self.running_container = ttk.Frame(self.running_canvas)
        self.running_container_id = self.running_canvas.create_window((0, 0), window=self.running_container, anchor="nw", width=self.running_frame.winfo_width()-20)

        # Update scroll region when container changes
        def update_scroll_region(event):
            self.running_canvas.configure(scrollregion=self.running_canvas.bbox("all"))
        self.running_container.bind("<Configure>", update_scroll_region)

        # Make sure canvas resizes when running_frame changes size
        def configure_canvas(event):
            # Update canvas width when frame resizes
            canvas_width = event.width - 30  # Adjust for scrollbar width
            self.running_canvas.configure(width=canvas_width)
            # Also update the width of the container window
            self.running_canvas.itemconfig(self.running_container_id, width=canvas_width)
        self.running_frame.bind("<Configure>", configure_canvas)

        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Log chung")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Add button to clear log
        log_action_frame = ttk.Frame(log_frame)
        log_action_frame.pack(fill=tk.X, side=tk.TOP)
        
        clear_log_btn = ttk.Button(log_action_frame, text="Xóa Log", command=self.clear_main_log)
        clear_log_btn.pack(side=tk.RIGHT, padx=5, pady=2)
        
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(log_frame, height=8, yscrollcommand=log_scroll.set)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        log_scroll.config(command=self.log_text.yview)

    def log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def clear_main_log(self):
        """Clear the main log window"""
        self.log_text.delete(1.0, tk.END)

    def clear_notebook_log(self, notebook_path, log_text):
        """Clear the log for a specific notebook"""
        log_text.delete(1.0, tk.END)
        notebook_name = os.path.basename(notebook_path)
        self.log(f"Đã xóa log của notebook: {notebook_name}")
        
    def refresh_notebooks(self):
        # Lấy danh sách notebook và chuẩn hóa đường dẫn
        raw_notebooks = get_notebooks()
        self.notebooks = [os.path.abspath(nb) for nb in raw_notebooks]
        
        self.notebook_listbox.delete(0, tk.END)
        self.selected_notebooks = []
        self.selection_order = []  # Reset selection order
        self.filtered_notebooks = []  # Reset filtered notebooks list
        
        # So sánh danh sách bằng đường dẫn chuẩn (absolute path)
        running_paths = set(os.path.abspath(path) for path in self.running_notebooks.keys())
        
        if self.notebooks:
            for nb in self.notebooks:
                if nb not in running_paths:
                    self.notebook_listbox.insert(tk.END, f"    | {os.path.basename(nb)}")
                    self.filtered_notebooks.append(nb)
        else:
            self.log("Không tìm thấy notebook nào.")

    # First, add the new function to the NotebookRunnerApp class
    def remove_all_notebooks(self):
        """Remove all notebooks from the running list"""
        # First stop all running notebooks
        self.stop_all_notebooks()
        
        # Count how many notebooks were removed
        notebook_count = len(self.running_notebooks)
        
        # Remove all notebook frames from UI
        for notebook_path, info in list(self.running_notebooks.items()):
            if 'frame' in info and info['frame'].winfo_exists():
                info['frame'].destroy()
        
        # Clear the running notebooks dictionary
        self.running_notebooks.clear()
        
        # Log the action
        if notebook_count > 0:
            self.log(f"Đã xóa tất cả {notebook_count} notebooks khỏi danh sách")
        
        # Refresh the notebook list to show all notebooks again
        self.refresh_notebooks()

    def on_notebook_select(self, event):
        """Handle notebook selection and show selection order based on click sequence"""
        # Get current selection and previous selection
        selected_indices = self.notebook_listbox.curselection()
        
        # Determine what changed since last selection event
        if not hasattr(self, 'previous_selection'):
            self.previous_selection = []
        
        newly_selected = [idx for idx in selected_indices if idx not in self.previous_selection]
        newly_deselected = [idx for idx in self.previous_selection if idx not in selected_indices]
        
        # Update our selection order:
        # 1. Add newly selected items to the end of our order
        # 2. Remove items that were deselected
        for idx in newly_selected:
            if idx not in self.selection_order:
                self.selection_order.append(idx)
        
        # Remove deselected items
        self.selection_order = [idx for idx in self.selection_order if idx in selected_indices]
        
        # Reset display for all items first (remove any selection numbers)
        for i in range(self.notebook_listbox.size()):
            notebook_name = os.path.basename(self.filtered_notebooks[i])
            self.notebook_listbox.delete(i)
            self.notebook_listbox.insert(i, f"    | {notebook_name}")
        
        # Update selected_notebooks based on the current selection order
        self.selected_notebooks = []
        for index in self.selection_order:
            notebook = self.filtered_notebooks[index]
            self.selected_notebooks.append(notebook)
        
        # Display selection order numbers
        for i, index in enumerate(self.selection_order):
            order_num = i + 1  # Selection order number (1-based)
            notebook_name = os.path.basename(self.filtered_notebooks[index])
            display_text = f"{order_num:2d} | {notebook_name}"
            
            # Update the listbox display
            self.notebook_listbox.delete(index)
            self.notebook_listbox.insert(index, display_text)
        
        # Restore selection highlighting
        for idx in selected_indices:
            self.notebook_listbox.selection_set(idx)
        
        # Save current selection for next comparison
        self.previous_selection = list(selected_indices)
    
    def browse_output_dir(self):
        # This method is no longer needed but we'll keep it for compatibility
        pass
    
    def install_requirements_thread(self):
        def task():
            self.status_label.config(text="Đang cài đặt thư viện...")
            
            # Capture output to log
            class LogRedirector:
                def __init__(self, log_func):
                    self.log_func = log_func
                    
                def write(self, message):
                    if message.strip():
                        self.log_func(message.strip())
                    
                def flush(self):
                    pass
            
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = LogRedirector(self.log)
            sys.stderr = LogRedirector(self.log)
            
            success = install_requirements()
            
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
            if success:
                self.log("✓ Đã cài đặt thành công tất cả các thư viện.")
            else:
                self.log("✗ Lỗi khi cài đặt thư viện.")
            self.status_label.config(text="Sẵn sàng")
        
        Thread(target=task).start()
    
    def update_timers(self):
        """Update timers for all running notebooks with enhanced reliability"""
        while self.timer_running and hasattr(self, 'root') and self.root.winfo_exists():
            try:
                for notebook_path, info in list(self.running_notebooks.items()):
                    if info['status'] == 'running':
                        try:
                            info['time'] += 0.1
                            elapsed = round(info['time'], 1)
                            minutes = int(elapsed // 60)
                            seconds = elapsed % 60
                            time_str = f"{minutes:02d}m:{seconds:04.1f}s"
                            
                            # Cập nhật thời gian đồng hồ được cập nhật gần nhất
                            info['last_timer_update'] = time.time()
                            
                            # Chỉ cập nhật UI nếu widget còn tồn tại
                            if 'time_label' in info and info['time_label'].winfo_exists():
                                info['time_label'].config(text=time_str)
                        except tk.TclError:
                            # Bỏ qua lỗi widget không tồn tại
                            pass
                        except Exception as e:
                            # Ghi log lỗi nhưng vẫn tiếp tục
                            print(f"Lỗi cập nhật timer cho {os.path.basename(notebook_path)}: {e}")
            except Exception as e:
                # Xử lý lỗi chung nhưng không dừng vòng lặp
                print(f"Lỗi cập nhật timer: {e}")

            # Nghỉ 0.1 giây trước chu kỳ tiếp theo
            time.sleep(0.1)
            
            # Cập nhật UI nhưng bảo vệ tránh lỗi
            try:
                if hasattr(self, 'root') and self.root.winfo_exists():
                    self.root.update_idletasks()
            except Exception:
                pass
        
        print("Timer thread đã kết thúc!")
        # Đánh dấu timer đã dừng để có thể khởi động lại khi cần
        self.timer_running = False
    
    def stop_execution(self):
        """Stop continuous execution of notebooks"""
        self.continuous_execution = False
        self.log("Đã dừng chạy liên tục")
        self.run_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Đã dừng")
        
    def run_selected_notebooks(self):
        """Start running all selected notebooks - replaced by add_selected_notebooks"""
        self.add_selected_notebooks()
        
        # Start all added notebooks automatically
        for notebook_path in self.selected_notebooks:
            if notebook_path in self.running_notebooks:
                self.start_notebook(notebook_path)
    
    def add_selected_notebooks(self):
        """Add selected notebooks to the running list"""
        if not self.selected_notebooks:
            messagebox.showwarning("Chú ý", "Vui lòng chọn ít nhất một notebook.")
            return
        
        # Start timer thread if not already running
        if not self.timer_running:
            self.timer_running = True
            timer_thread = Thread(target=self.update_timers, daemon=True)
            timer_thread.start()
        
        # Add each selected notebook to running list
        for notebook_path in self.selected_notebooks:
            if notebook_path in self.running_notebooks:
                self.log(f"Notebook {os.path.basename(notebook_path)} đã trong danh sách đang chạy")
                continue
                
            self.add_notebook_to_running(notebook_path)
        
        # Clear the selection after adding notebooks
        self.clear_notebook_selection()
        self.refresh_notebooks()

    def move_notebook_up(self, notebook_path, frame):
        """Move a notebook up in the UI order"""
        # Get all frames in order
        ordered_frames = self.get_notebook_frames_ordered()
        
        # Find current frame position
        current_index = ordered_frames.index(frame)
        
        # Can't move up if already at the top
        if current_index == 0:
            return
        
        # Swap with the frame above
        frame.pack_forget()
        frame.pack(before=ordered_frames[current_index-1], fill=tk.X, expand=True, pady=5, padx=5)
        
        self.log(f"Đã di chuyển notebook {os.path.basename(notebook_path)} lên trên")
    
    def move_notebook_down(self, notebook_path, frame):
        """Move a notebook down in the UI order"""
        # Get all frames in order
        ordered_frames = self.get_notebook_frames_ordered()
        
        # Find current frame position
        current_index = ordered_frames.index(frame)
        
        # Can't move down if already at the bottom
        if current_index >= len(ordered_frames)-1:
            return
        
        # Get the frame below
        below_frame = ordered_frames[current_index+1]
        
        # Swap positions
        frame.pack_forget()
        frame.pack(after=below_frame, fill=tk.X, expand=True, pady=5, padx=5)
        
        self.log(f"Đã di chuyển notebook {os.path.basename(notebook_path)} xuống dưới")
        
    def get_notebook_frames_ordered(self):
        """Get all notebook frames in their current UI order"""
        frames = []
        
        for widget in self.running_container.winfo_children():
            if isinstance(widget, ttk.Frame):
                frames.append(widget)
        
        # Sort frames by their Y position
        frames.sort(key=lambda f: f.winfo_y())
        return frames
    
    def add_notebook_to_running(self, notebook_path):
        """Add a single notebook to the running list and create UI elements for it"""
        # Create UI elements for this notebook - set width to match canvas width
        frame = ttk.Frame(self.running_container)
        frame.pack(fill=tk.X, expand=True, pady=5, padx=5)
        
        # Upper part: name and controls
        upper_frame = ttk.Frame(frame)
        upper_frame.pack(fill=tk.X, expand=True, pady=2)

        # Order control buttons (Up/Down)
        order_frame = ttk.Frame(upper_frame)
        order_frame.pack(side=tk.LEFT, padx=2)
        
        # Up button
        up_btn = ttk.Button(order_frame, text="↑", width=2, 
                        command=lambda p=notebook_path, f=frame: self.move_notebook_up(p, f))
        up_btn.pack(side=tk.LEFT, pady=1)
        
        # Down button
        down_btn = ttk.Button(order_frame, text="↓", width=2,
                            command=lambda p=notebook_path, f=frame: self.move_notebook_down(p, f))
        down_btn.pack(side=tk.LEFT, pady=1)
        
        # Name label with reduced width to move everything left
        name_label = ttk.Label(upper_frame, text=os.path.basename(notebook_path), width=30)
        name_label.pack(side=tk.LEFT, padx=(0, 8))
        
        # Timer label with smaller padding
        time_label = ttk.Label(upper_frame, text="00:00.0")
        time_label.pack(side=tk.LEFT, padx=2)
        
        # Status label with smaller padding
        status_label = ttk.Label(upper_frame, text="Sẵn sàng", foreground="blue")
        status_label.pack(side=tk.LEFT, padx=3)

       # Loop settings group
        loop_frame = ttk.Frame(upper_frame)
        loop_frame.pack(side=tk.LEFT, padx=5)

        # Sleep frame - we'll handle the visibility of this
        sleep_frame = ttk.Frame(loop_frame)

        # New: Run count frame for non-loop mode
        runs_frame = ttk.Frame(loop_frame)

        # Loop checkbox with callback to show/hide sleep settings
        loop_var = tk.BooleanVar(value=True)  # Default to True (continuous execution)

        # Create a function to toggle settings visibility based on loop mode
        def toggle_sleep_visibility(*args):
            if loop_var.get():
                sleep_frame.pack(side=tk.LEFT, padx=(5, 0))
                runs_frame.pack_forget()
            else:
                sleep_frame.pack_forget()
                runs_frame.pack(side=tk.LEFT, padx=(5, 0))

        # Setup the loop checkbox with the toggle callback
        loop_check = ttk.Checkbutton(loop_frame, text="Lặp lại", variable=loop_var, 
                                command=toggle_sleep_visibility)
        loop_check.pack(side=tk.LEFT, padx=(0, 5))

        # Sleep time label and spinbox - in a separate frame for visibility control
        ttk.Label(sleep_frame, text="Nghỉ: ").pack(side=tk.LEFT, padx=(0, 0))
        sleep_var = tk.StringVar(value="1")
        sleep_spin = ttk.Spinbox(sleep_frame, from_=0, to=3600, width=4, textvariable=sleep_var)
        sleep_spin.pack(side=tk.LEFT, padx=(0, 0))
        ttk.Label(sleep_frame, text=" giây").pack(side=tk.LEFT, padx=(0, 0))
        
        # New: Run count controls for non-loop mode
        ttk.Label(runs_frame, text="Số lần: ").pack(side=tk.LEFT, padx=(0, 0))
        runs_var = tk.StringVar(value="2")  # Default to 2 runs
        runs_spin = ttk.Spinbox(runs_frame, from_=1, to=100, width=4, textvariable=runs_var)
        runs_spin.pack(side=tk.LEFT, padx=(0, 0))
        ttk.Label(runs_frame, text=" lần").pack(side=tk.LEFT, padx=(0, 0))

        # Initialize visibility based on initial loop state
        if loop_var.get():
            sleep_frame.pack(side=tk.LEFT, padx=(5, 0))
        else:
            runs_frame.pack(side=tk.LEFT, padx=(5, 0))
        
        # Lower part: log display
        log_frame = ttk.Frame(frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        log_text = tk.Text(log_frame, height=1, yscrollcommand=log_scroll.set)
        log_text.pack(fill=tk.BOTH, expand=True)
        log_scroll.config(command=log_text.yview)
        
        # Control buttons
        btn_frame = ttk.Frame(upper_frame)
        btn_frame.pack(side=tk.RIGHT, padx=5)
        
        start_btn = ttk.Button(btn_frame, text="Chạy", width=8,
                              command=lambda p=notebook_path: self.start_notebook(p))
        start_btn.pack(side=tk.LEFT, padx=2)
        
        stop_btn = ttk.Button(btn_frame, text="Dừng", width=8, state=tk.DISABLED,
                             command=lambda p=notebook_path: self.stop_notebook(p))
        stop_btn.pack(side=tk.LEFT, padx=2)

        clear_btn = ttk.Button(btn_frame, text="Xóa Log", width=8,
                            command=lambda p=notebook_path, t=log_text: self.clear_notebook_log(p, t))
        clear_btn.pack(side=tk.LEFT, padx=2)
        
        remove_btn = ttk.Button(btn_frame, text="Xóa Notebook", width=16,
                               command=lambda p=notebook_path, f=frame: self.remove_notebook(p, f))
        remove_btn.pack(side=tk.LEFT, padx=2)
        
        # Lưu thông tin notebook vào dictionary
        self.running_notebooks[notebook_path] = {
            'frame': frame,
            'time': 0.0,
            'status': 'ready',
            'iteration': 0,
            'time_label': time_label,
            'status_label': status_label,
            'thread': None,
            'stop_flag': False,
            'log_text': log_text,
            'loop_var': loop_var,
            'sleep_var': sleep_var,
            'runs_var': runs_var,  # Add the runs_var to track the number of runs
            'controls': {
                'start_btn': start_btn,
                'stop_btn': stop_btn,
                'clear_btn': clear_btn,
                'remove_btn': remove_btn,
                'loop_check': loop_check,
                'sleep_spin': sleep_spin,
                'runs_spin': runs_spin,  # Also add reference to the runs spinbox
                'up_btn': up_btn,
                'down_btn': down_btn
            }
        }
        
        self.log(f"Đã thêm notebook: {os.path.basename(notebook_path)}")
    
    def start_notebook(self, notebook_path):
        """Start running a notebook in a continuous loop"""
        info = self.running_notebooks[notebook_path]
        
        # Already running or if thread still exists, don't do anything
        if info['status'] == 'running' or (info.get('thread') is not None and info['thread'].is_alive()):
            return
        
        # Reset UI and status
        info['status'] = 'running'
        info['stop_flag'] = False
        info['time'] = 0.0
        info['time_label'].config(text="00:00.0")
        info['status_label'].config(text="Đang chạy", foreground="blue")
        
        # Update controls
        info['controls']['start_btn'].config(state=tk.DISABLED)
        info['controls']['stop_btn'].config(state=tk.NORMAL)
        
        # Create and start the thread
        thread = Thread(target=self.run_notebook_continuously, args=(notebook_path,))
        thread.daemon = True
        thread.start()
        
        info['thread'] = thread
        # self.log(f"Bắt đầu chạy: {os.path.basename(notebook_path)}")
    
    def stop_notebook(self, notebook_path):
        """Stop a running or waiting notebook"""
        info = self.running_notebooks[notebook_path]
        
        if info['status'] != 'running' and info['status'] != 'waiting':
            return
            
        # Set the stop flag to signal the thread to exit
        info['stop_flag'] = True
        info['status'] = 'stopping'  # Intermediate state to show we're in the process of stopping
        info['status_label'].config(text="Đang dừng...", foreground="orange")
        
        # Give the thread a chance to exit gracefully
        if 'thread' in info and info['thread'] is not None:
            # Create a separate thread to handle the stopping process without freezing UI
            def terminate_thread():
                try:
                    # Wait for a short time for the thread to respond to stop flag
                    stop_timeout = 2.0  # seconds to wait for graceful exit
                    start_time = time.time()
                    
                    while time.time() - start_time < stop_timeout and info['thread'].is_alive():
                        time.sleep(0.1)
                        
                    # Update UI after timeout or thread completion
                    if notebook_path in self.running_notebooks:
                        self.running_notebooks[notebook_path]['status'] = 'stopped'
                        self.running_notebooks[notebook_path]['thread'] = None  # Clear the thread reference

                        info['controls']['stop_btn'].config(state=tk.DISABLED)
                        info['controls']['start_btn'].config(state=tk.NORMAL)
                        info['status_label'].config(text="Đã dừng", foreground="red")
                        
                        self.log(f"Đã dừng chạy: {os.path.basename(notebook_path)}")
                except Exception as e:
                    self.log(f"Lỗi khi dừng notebook {os.path.basename(notebook_path)}: {str(e)}")
            
            # Start the termination handler thread
            terminator = Thread(target=terminate_thread)
            terminator.daemon = True
            terminator.start()
        else:
            # No thread to terminate, just update the UI
            info['status'] = 'stopped'
            info['thread'] = None  # Clear the thread reference
            info['controls']['stop_btn'].config(state=tk.DISABLED)
            info['controls']['start_btn'].config(state=tk.NORMAL)
            info['status_label'].config(text="Đã dừng", foreground="red")
            self.log(f"Đã dừng chạy: {os.path.basename(notebook_path)}")
    
    def remove_notebook(self, notebook_path, frame):
        """Remove a notebook from the running list"""
        # Stop the notebook if it's running
        if notebook_path in self.running_notebooks and self.running_notebooks[notebook_path]['status'] == 'running':
            self.stop_notebook(notebook_path)
        
        # Remove the frame from UI
        frame.destroy()
        
        # Remove from running notebooks dict
        if notebook_path in self.running_notebooks:
            del self.running_notebooks[notebook_path]
        
        self.log(f"Đã xóa notebook: {os.path.basename(notebook_path)}")
        self.refresh_notebooks()

    def run_notebook_continuously(self, notebook_path):
        """Thread function to continuously run a specific notebook"""
        info = self.running_notebooks[notebook_path]
        log_text = info['log_text']
        
        iteration = 1
        while not info['stop_flag']:
            if info['loop_var'].get():
                # Reset iteration counter in the info dictionary
                info['iteration'] = iteration
                
                # Reset the timer for each iteration and mark the last reset time
                info['time'] = 0.0
                info['last_timer_reset'] = time.time()
                try:
                    # Cập nhật UI an toàn
                    if 'time_label' in info and info['time_label'].winfo_exists():
                        info['time_label'].config(text="00m:00.0s")
                except tk.TclError:
                    print(f"Lỗi reset timer UI cho {os.path.basename(notebook_path)}")
                    
                # Kiểm tra và khởi động lại timer nếu nó đã dừng
                if not self.timer_running:
                    self.timer_running = True
                    timer_thread = Thread(target=self.update_timers, daemon=True)
                    timer_thread.start()
                
                # Clear log and add iteration header with timestamp
                current_time = datetime.now().strftime("%H:%M:%S")
                try:
                    log_text.insert(tk.END, f"\n--- Chạy lặp lại lần thứ {iteration} ({current_time}): ")
                    log_text.see(tk.END)
                except tk.TclError:
                    pass
                
                # Execute notebook
                self.execute_notebook_with_log(notebook_path, log_text, info['status_label'])

                # Check if we've been stopped during execution
                if info['stop_flag']:
                    break
                    
                # Sleep between runs if needed
                try:
                    sleep_time = int(info['sleep_var'].get())
                    if sleep_time > 0:
                        # Show sleeping status
                        try:
                            if info['status_label'].winfo_exists():
                                info['status_label'].config(text=f"Nghỉ {sleep_time}s", foreground="blue")
                        except tk.TclError:
                            pass
                        
                        # Sleep in small increments to check stop_flag
                        sleep_start = time.time()
                        while time.time() - sleep_start < sleep_time:
                            if info['stop_flag']:
                                break
                            time.sleep(0.1)
                            
                        # Reset status if not stopped
                        if not info['stop_flag']:
                            try:
                                if info['status_label'].winfo_exists():
                                    info['status_label'].config(text="Đang chạy", foreground="blue")
                            except tk.TclError:
                                pass
                except ValueError:
                    pass

                iteration += 1
            else:
                # Chạy số lần xác định (thay vì chạy một lần)
                try:
                    runs_count = int(info['runs_var'].get())
                except ValueError:
                    runs_count = 2  # Mặc định là 2 nếu giá trị không hợp lệ
                
                # Đảm bảo số lần chạy hợp lệ
                if runs_count < 1:
                    runs_count = 1
                
                # Chạy notebook theo số lần đã chọn
                for run_num in range(1, runs_count + 1):
                    # Kiểm tra cờ dừng
                    if info['stop_flag']:
                        break
                    
                    # Reset thời gian cho mỗi lần chạy
                    info['time'] = 0.0
                    try:
                        if info['time_label'].winfo_exists():
                            info['time_label'].config(text="00m:00.0s")
                    except tk.TclError:
                        pass
                    
                    # Hiển thị thông tin lần chạy hiện tại
                    current_time = datetime.now().strftime("%H:%M:%S")
                    try:
                        # Hiển thị số lần chạy hiện tại / tổng số lần chạy
                        log_text.insert(tk.END, f"\n--- Chạy lần {run_num}/{runs_count} ({current_time}): ")
                        log_text.see(tk.END)
                    except tk.TclError:
                        pass
                    
                    # Thực thi notebook
                    self.execute_notebook_with_log(notebook_path, log_text, info['status_label'])
                    
                    # Kiểm tra cờ dừng sau khi chạy
                    if info['stop_flag']:
                        break
                    
                    # Chờ giữa các lần chạy (nếu không phải lần cuối)
                    if run_num < runs_count and not info['stop_flag']:
                        try:
                            # Hiển thị trạng thái chờ
                            if info['status_label'].winfo_exists():
                                info['status_label'].config(text=f"Đợi lần {run_num+1}", foreground="blue")
                            
                            # Chờ 1 giây giữa các lần chạy (nhưng vẫn kiểm tra cờ dừng)
                            for _ in range(10):  # 10 x 0.1s = 1s
                                if info['stop_flag']:
                                    break
                                time.sleep(0.1)
                            
                            # Cập nhật lại trạng thái
                            if not info['stop_flag'] and info['status_label'].winfo_exists():
                                info['status_label'].config(text="Đang chạy", foreground="blue")
                        except tk.TclError:
                            pass

                # Cập nhật UI sau khi hoàn thành hoặc dừng
                if not info['stop_flag']:
                    info['status'] = 'completed'
                    try:
                        if info['status_label'].winfo_exists():
                            info['status_label'].config(text="Hoàn thành", foreground="green")
                        if info['controls']['start_btn'].winfo_exists():
                            info['controls']['start_btn'].config(state=tk.NORMAL)
                        if info['controls']['stop_btn'].winfo_exists():
                            info['controls']['stop_btn'].config(state=tk.DISABLED)
                    except tk.TclError:
                        pass
                break
                
    
    def execute_notebook_with_log(self, notebook_path, log_text, status_label):
        """Execute a notebook and redirect output to the specified log widget"""
        try:
            # Check if notebook has been flagged to stop
            if self.running_notebooks[notebook_path]['stop_flag']:
                return False
                    
            # Create a custom output redirector for this notebook's log
            class NotebookLogRedirector:
                def __init__(self, log_widget, main_log_func, notebook_path, app):
                    self.log_widget = log_widget
                    self.main_log_func = main_log_func
                    self.notebook_path = notebook_path
                    self.app = app
                    
                def write(self, message):
                    msg = message.strip()
                    if msg:
                        try:
                            # Check if widget still exists before accessing it
                            if hasattr(self.app, 'root') and self.app.root.winfo_exists():
                                if self.log_widget.winfo_exists():
                                    self.log_widget.insert(tk.END, f"{msg}\n")
                                    self.log_widget.see(tk.END)
                        except (tk.TclError, RuntimeError, AttributeError):
                            # Safely handle any widget-related errors
                            pass
                            
                        try:
                            # Also safely log to the main log
                            self.main_log_func(f"[{os.path.basename(self.notebook_path)}] {msg}")
                        except (tk.TclError, RuntimeError):
                            pass
                    
                def flush(self):
                    pass
            
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            
            redirector = NotebookLogRedirector(log_text, self.log, notebook_path, self)
            sys.stdout = redirector
            sys.stderr = redirector
            
            try:
                # Execute the notebook
                success, exec_time = execute_notebook(notebook_path, None)
                
                # Check if we've been stopped during execution
                if notebook_path not in self.running_notebooks or self.running_notebooks[notebook_path]['stop_flag']:
                    return False
                
                # Safely update UI
                try:
                    if status_label.winfo_exists() and log_text.winfo_exists():
                        if success:
                            status_label.config(text="Thành công", foreground="green")
                            log_text.insert(tk.END, f"Thành công {exec_time}")
                            log_text.see(tk.END)
                        else:
                            status_label.config(text="Lỗi", foreground="red")
                            log_text.insert(tk.END, f"{exec_time}")
                            log_text.see(tk.END)
                except (tk.TclError, RuntimeError):
                    pass
                
                return success
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                    
        except Exception as e:
            # Safely handle errors and update UI
            try:
                if notebook_path in self.running_notebooks:
                    self.log(f"Lỗi khi thực thi {os.path.basename(notebook_path)}: {str(e)}")
                    
                    if log_text.winfo_exists():
                        log_text.insert(tk.END, f"Lỗi: {str(e)}\n")
                        
                    if status_label.winfo_exists():
                        status_label.config(text="Lỗi", foreground="red")
                        
                    self.running_notebooks[notebook_path]['status'] = 'error'
            except (tk.TclError, RuntimeError, AttributeError):
                pass
                
            return False

def main():
    parser = argparse.ArgumentParser(description='Cài đặt thư viện và chạy notebooks IPython')
    parser.add_argument('--install', action='store_true', help='Cài đặt các thư viện từ requirements.txt')
    parser.add_argument('--list', action='store_true', help='Liệt kê tất cả các notebook có sẵn')
    parser.add_argument('--notebook', type=str, help='Tên hoặc đường dẫn của notebook cần chạy')
    parser.add_argument('--continuous', action='store_true', help='Chạy notebook liên tục')
    
    args = parser.parse_args()
    
    # Launch GUI if no command-line arguments are provided
    if len(sys.argv) == 1:
        root = tk.Tk()
        app = NotebookRunnerApp(root)
        root.mainloop()
        return
    
    # Cài đặt thư viện nếu được yêu cầu
    if args.install:
        if not install_requirements():
            print("Không thể cài đặt các thư viện cần thiết. Vui lòng kiểm tra lại.")
            return
    
    # Tìm tất cả notebooks
    notebooks = get_notebooks()
    
    # Liệt kê notebooks nếu được yêu cầu
    if args.list:
        if notebooks:
            print("Các notebook có sẵn:")
            for i, notebook in enumerate(notebooks, 1):
                print(f"{i}. {os.path.basename(notebook)}")
        else:
            print("Không tìm thấy notebook nào.")
        return
    
    # Tìm notebook cần chạy
    target_notebook = find_notebook_by_name(args.notebook, notebooks)
    
    # Thực thi notebook
    execute_notebook(target_notebook, args.output_dir)

if __name__ == "__main__":
    main()
