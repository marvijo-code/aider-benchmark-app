import os
import sys
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, ttk
from git import Repo
import subprocess
import datetime
import shutil
from pathlib import Path
from dotenv import load_dotenv
import threading
from tqdm import tqdm
import locale
import git
from pygments import highlight
from pygments.lexers import PythonLexer, guess_lexer
from pygments.formatters import HtmlFormatter
import re

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    os.environ["PYTHONIOENCODING"] = "utf-8"

class SyntaxHighlightingText(ctk.CTkFrame):
    def __init__(self, *args, text_wrap="none", **kwargs):
        frame_kwargs = {k: v for k, v in kwargs.items() if k not in ["wrap"]}
        super().__init__(*args, **frame_kwargs)
        
        # Create the text widget
        self.text = tk.Text(self, wrap=text_wrap,
                           bg="#2d2d2d", fg="#ffffff",
                           insertbackground="#ffffff",
                           font=("Consolas", 18))
        
        # Create and configure scrollbar
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack widgets
        self.scrollbar.pack(side="right", fill="y")
        self.text.pack(expand=True, fill="both")

        # Configure tags for syntax highlighting
        self.text.tag_configure("error", foreground="#ff5555")
        self.text.tag_configure("success", foreground="#50fa7b")
        self.text.tag_configure("info", foreground="#8be9fd")
        self.text.tag_configure("warning", foreground="#ffb86c")
        self.text.tag_configure("code", foreground="#f1fa8c")

        # Configure tags for syntax highlighting
        self.formatter = HtmlFormatter(style='monokai')
        self.python_lexer = PythonLexer()
        
        for token, style in self.formatter.style:
            foreground = str(style['color']) if style['color'] else None
            background = str(style['bgcolor']) if style['bgcolor'] else None
            font = "Consolas" if "Consolas" in tk.font.families() else "Courier"
            
            if foreground or background:
                self.text.tag_configure(
                    str(token),
                    foreground=f"#{foreground}" if foreground else None,
                    background=f"#{background}" if background else None,
                    font=(font, 20)
                )
    
    def configure(self, **kwargs):
        # Separate text widget kwargs from frame kwargs
        text_kwargs = {}
        frame_kwargs = {}
        
        for key, value in kwargs.items():
            if key in ['bg', 'fg', 'font', 'text_color']:
                text_kwargs[key] = value
            else:
                frame_kwargs[key] = value
        
        # Configure the text widget
        if text_kwargs:
            self.text.configure(**text_kwargs)
            
        # Configure the frame
        if frame_kwargs:
            super().configure(**frame_kwargs)

    def highlight_text(self, text):
        try:
            lexer = guess_lexer(text)
        except:
            lexer = self.python_lexer
        
        tokens = lexer.get_tokens(text)
        
        for token, content in tokens:
            start = self.text.index("end-1c")
            self.text.insert("end", content)
            end = self.text.index("end-1c")
            self.text.tag_add(str(token), start, end)
    
    def insert_with_highlighting(self, text):
        if text.lower().startswith(("error:", "exception:")):
            self.text.insert("end", text, "error")
        elif "success" in text.lower() or "completed" in text.lower():
            self.text.insert("end", text, "success")
        elif text.lower().startswith(("info:", "running:")):
            self.text.insert("end", text, "info")
        elif text.lower().startswith(("warning:", "warn:")):
            self.text.insert("end", text, "warning")
        else:
            if re.search(r'[{}\[\]()=]', text):
                self.highlight_text(text)
            else:
                self.text.insert("end", text)
        
        self.text.insert("end", "\n")
        self.text.see("end")
    
    def see(self, *args, **kwargs):
        self.text.see(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        self.text.delete(*args, **kwargs)
    
    def get(self, *args, **kwargs):
        return self.text.get(*args, **kwargs)

class BenchmarkGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("Benchmark Runner")
        self.geometry("800x600")
        
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Create frames
        self.create_input_frame()
        self.create_options_frame()
        self.create_output_frame()
        self.create_control_frame()

        # Initialize variables
        self.running = False
        self.process = None

    def create_input_frame(self):
        input_frame = ctk.CTkFrame(self)
        input_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        # Test Path input
        ctk.CTkLabel(input_frame, text="Test Path:").grid(row=0, column=0, padx=5, pady=5)
        self.test_path = ctk.CTkEntry(input_frame, placeholder_text="all or specific test path")
        self.test_path.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.test_path.insert(0, "say")
        
        input_frame.grid_columnconfigure(1, weight=1)

    def create_options_frame(self):
        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        options_frame.grid_columnconfigure(1, weight=1)
        options_frame.grid_columnconfigure(3, weight=1)

        # Conda Environment
        ctk.CTkLabel(options_frame, text="Conda Env:").grid(row=0, column=0, padx=5, pady=5)
        self.conda_env = ctk.CTkEntry(options_frame)
        self.conda_env.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.conda_env.insert(0, "aider-dev")

        # Model
        ctk.CTkLabel(options_frame, text="Model:").grid(row=0, column=2, padx=5, pady=5)
        self.model = ctk.CTkEntry(options_frame)
        self.model.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self.model.insert(0, "openai/Qwen/Qwen2.5-Coder-32B-Instruct")

        # Edit Format
        ctk.CTkLabel(options_frame, text="Edit Format:").grid(row=1, column=0, padx=5, pady=5)
        self.edit_format = ctk.CTkEntry(options_frame)
        self.edit_format.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.edit_format.insert(0, "diff")

        # Threads
        ctk.CTkLabel(options_frame, text="Threads:").grid(row=1, column=2, padx=5, pady=5)
        self.threads = ctk.CTkEntry(options_frame)
        self.threads.grid(row=1, column=3, padx=5, pady=5, sticky="ew")
        self.threads.insert(0, "1")

    def create_output_frame(self):
        self.output_frame = ctk.CTkFrame(self)
        self.output_frame.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="nsew")

        self.output_text = SyntaxHighlightingText(self, text_wrap="word")
        self.output_text.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="nsew")
        
        # Set frame and text colors
        self.output_text.configure(fg_color="#2d2d2d")

    def create_control_frame(self):
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=4, column=0, padx=10, pady=(5, 10), sticky="ew")
        
        button_frame = ctk.CTkFrame(control_frame)
        button_frame.grid(row=0, column=0, sticky="ew")
        button_frame.grid_columnconfigure((0,1,2,3), weight=1)
        
        # Run button
        self.run_button = ctk.CTkButton(button_frame, text="Run Benchmark", command=self.run_benchmark)
        self.run_button.grid(row=0, column=0, padx=5, pady=5)
        
        # Stop button
        self.stop_button = ctk.CTkButton(button_frame, text="Stop", command=self.stop_benchmark, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5, pady=5)
        
        # Re-run Latest button
        self.rerun_button = ctk.CTkButton(button_frame, text="Re-run Latest", command=self.rerun_latest)
        self.rerun_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Clear button
        self.clear_button = ctk.CTkButton(button_frame, text="Clear", command=self.clear_output)
        self.clear_button.grid(row=0, column=3, padx=5, pady=5)

    def validate_inputs(self):
        if not os.path.exists(".env"):
            self.log_output(".env file not found. Please create a .env file with your API keys.")
            return False
        
        # Check if benchmark script exists
        benchmark_script = os.path.join(os.path.dirname(__file__), "..", "benchmark", "benchmark.py")
        if not os.path.exists(benchmark_script):
            self.log_output(f"Benchmark script not found at: {benchmark_script}")
            self.log_output("Please make sure the benchmark directory is in the correct location.")
            return False

        # Check for exercism-python repository
        benchmark_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp.benchmarks")
        exercism_dir = os.path.join(benchmark_dir, "exercism-python")
        
        if not os.path.exists(exercism_dir):
            if messagebox.askyesno("Repository Not Found", 
                                 "The exercism-python repository is not found.\nWould you like to clone it now?"):
                if not os.path.exists(benchmark_dir):
                    os.makedirs(benchmark_dir)
                try:
                    self.log_output("Cloning exercism-python repository...")
                    git.Repo.clone_from(
                        "https://github.com/exercism/python.git",
                        exercism_dir,
                        progress=git.remote.RemoteProgress()
                    )
                    self.log_output("Repository cloned successfully!")
                except Exception as e:
                    self.log_output(f"Error cloning repository: {str(e)}")
                    return False
            else:
                self.log_output("exercism-python repository is required to run benchmarks.")
                return False
        
        if not self.test_path.get():
            self.log_output("Test path is required.")
            return False

        if not self.model.get():
            self.log_output("Model is required.")
            return False

        return True

    def log_output(self, message):
        self.output_text.insert_with_highlighting(message)

    def run_benchmark(self):
        if not self.validate_inputs():
            return

        self.running = True
        self.run_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        
        # Clear previous output
        self.output_text.delete("1.0", "end")
        
        # Start benchmark in a separate thread
        thread = threading.Thread(target=self.run_benchmark_thread)
        thread.daemon = True
        thread.start()

    def run_benchmark_thread(self):
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            test_path = self.test_path.get()
            model = self.model.get()
            edit_format = self.edit_format.get()
            
            if test_path == "all":
                run_name = f"{timestamp}--{model}-{edit_format}"
            else:
                test_name = os.path.basename(test_path)
                run_name = f"{timestamp}--{test_name}-{model}-{edit_format}"

            self.log_output(f"Running benchmark...\n")
            self.log_output(f"Using model: {model}")
            self.log_output(f"Edit format: {edit_format}")
            self.log_output(f"Threads: {self.threads.get()}\n")

            # Load environment variables
            load_dotenv()
            
            # Set up environment variables for the subprocess
            env = os.environ.copy()
            env["AIDER_BENCHMARK_DIR"] = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp.benchmarks")
            env["AIDER_RUN_LOCALLY"] = "true"
            
            # Set encoding for Windows
            if sys.platform == "win32":
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONUTF8"] = "1"

            # Get the path to the benchmark script
            benchmark_script = os.path.join(os.path.dirname(__file__), "..", "benchmark", "benchmark.py")
            
            if not os.path.exists(benchmark_script):
                raise FileNotFoundError(f"Benchmark script not found at: {benchmark_script}")

            # Prepare command
            cmd = [
                sys.executable,
                benchmark_script,
                run_name,
                "--model", model,
                "--edit-format", edit_format,
                "--threads", self.threads.get()
            ]
            
            if test_path != "all":
                cmd.extend(["--keywords", os.path.basename(test_path)])

            # Run benchmark
            self.process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8'
            )

            # Read output
            while self.running and self.process:
                line = self.process.stdout.readline()
                if not line and self.process.poll() is not None:
                    break
                if line:
                    self.log_output(line.strip())

            if self.running:
                # Generate stats
                self.log_output("\nGenerating benchmark stats...")
                stats_cmd = [
                    sys.executable,
                    benchmark_script,
                    "--stats",
                    f"tmp.benchmarks/{run_name}"
                ]
                
                subprocess.run(stats_cmd, env=env, check=True)
                
                self.log_output(f"\nBenchmark complete! Results are in tmp.benchmarks/{run_name}")
                self.log_output(f"You can view the stats by running: python benchmark/benchmark.py --stats tmp.benchmarks/{run_name}")

        except Exception as e:
            self.log_output(f"\nError: {str(e)}")
        finally:
            self.running = False
            self.process = None
            self.run_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

    def stop_benchmark(self):
        self.running = False
        if self.process:
            self.process.terminate()
            self.log_output("\nBenchmark stopped by user.")

    def rerun_latest(self):
        # Find the latest benchmark directory
        benchmark_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp.benchmarks")
        if not os.path.exists(benchmark_dir):
            self.log_output("No previous benchmarks found")
            return
            
        # Get all directories and sort by creation time
        dirs = [(d, os.path.getctime(os.path.join(benchmark_dir, d))) 
                for d in os.listdir(benchmark_dir) if os.path.isdir(os.path.join(benchmark_dir, d))]
        if not dirs:
            self.log_output("No previous benchmarks found")
            return
            
        latest_dir = max(dirs, key=lambda x: x[1])[0]
        latest_path = os.path.join(benchmark_dir, latest_dir)
        
        # Find the model directory
        model_dirs = [d for d in os.listdir(latest_path) if os.path.isdir(os.path.join(latest_path, d))]
        if not model_dirs:
            self.log_output("No model directories found")
            return
            
        model_path = os.path.join(latest_path, model_dirs[0])
        test_dirs = [d for d in os.listdir(model_path) if os.path.isdir(os.path.join(model_path, d))]
        if not test_dirs:
            self.log_output("No test directories found")
            return
            
        test_path = os.path.join(model_path, test_dirs[0])
        
        self.log_output(f"Re-running tests in: {test_path}")
        
        # Disable buttons while running
        self.run_button.configure(state="disabled")
        self.rerun_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        
        try:
            # Run the tests using unittest directly
            cmd = [sys.executable, "-m", "unittest", "discover", "-s", test_path, "-t", test_path, "-p", "*_test.py"]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read output in real-time
            while self.running and self.process:
                line = self.process.stdout.readline()
                if not line and self.process.poll() is not None:
                    break
                if line:
                    self.log_output(line.strip())
                    
        except Exception as e:
            self.log_output(f"Error running tests: {str(e)}")
            
        finally:
            self.running = False
            self.process = None
            # Re-enable buttons
            self.run_button.configure(state="normal")
            self.rerun_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

    def clear_output(self):
        self.output_text.delete("1.0", "end")

if __name__ == "__main__":
    app = BenchmarkGUI()
    app.mainloop()
