import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os

class ZendellConfigUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Zendell Configuration")
        self.root.geometry("650x450")
        self.root.resizable(False, False)
        
        # Create a themed style
        self.style = ttk.Style()
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")  # Use clam theme for a modern look if available
        
        # Configure styles
        self.style.configure("Title.TLabel", font=("Helvetica", 18, "bold"))
        self.style.configure("Subtitle.TLabel", font=("Helvetica", 10, "italic"))
        self.style.configure("Accent.TButton", font=("Helvetica", 12, "bold"))
        
        # Main container frame with padding
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header frame
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Title and subtitle
        title_label = ttk.Label(
            header_frame, 
            text="Zendell Multi-Agent System", 
            style="Title.TLabel"
        )
        title_label.pack(pady=(0, 5))
        
        subtitle_label = ttk.Label(
            header_frame, 
            text="Configuration Interface", 
            style="Subtitle.TLabel"
        )
        subtitle_label.pack()
        
        # Description frame
        desc_frame = ttk.Frame(self.main_frame)
        desc_frame.pack(fill=tk.X, pady=(0, 20))
        
        desc_text = (
            "Zendell is a proactive multi-agent system designed to assist users "
            "with various tasks. Configure your preferences below before starting the system."
        )
        
        desc_label = ttk.Label(
            desc_frame, 
            text=desc_text,
            wraplength=600,
            justify=tk.CENTER
        )
        desc_label.pack()
        
        # Configuration options frame
        config_frame = ttk.LabelFrame(self.main_frame, text="System Configuration", padding="15")
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # LLM Selection
        llm_frame = ttk.Frame(config_frame)
        llm_frame.pack(fill=tk.X, pady=8)
        
        llm_label = ttk.Label(llm_frame, text="LLM Model:", width=20)
        llm_label.pack(side=tk.LEFT, padx=5)
        
        self.llm_var = tk.StringVar(value="gpt-4o")
        llm_options = ["gpt-3.5-turbo", "gpt-4o", "gpt-4-turbo", "claude-3-opus", "llama-3-70b"]
        llm_dropdown = ttk.Combobox(llm_frame, textvariable=self.llm_var, values=llm_options, state="readonly", width=30)
        llm_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Proactivity Time
        time_frame = ttk.Frame(config_frame)
        time_frame.pack(fill=tk.X, pady=8)
        
        time_label = ttk.Label(time_frame, text="Proactivity Interval:", width=20)
        time_label.pack(side=tk.LEFT, padx=5)
        
        self.time_var = tk.StringVar(value="60 minutes")
        time_options = ["5 minutes", "15 minutes", "30 minutes", "60 minutes", "120 minutes"]
        time_dropdown = ttk.Combobox(time_frame, textvariable=self.time_var, values=time_options, state="readonly", width=30)
        time_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Button frame
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        # Start button
        self.start_button = ttk.Button(
            button_frame, 
            text="Start Zendell System", 
            command=self.start_system,
            style="Accent.TButton",
            width=25
        )
        self.start_button.pack(pady=10)
        
        # Status frame
        status_frame = ttk.Frame(self.main_frame)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready to start")
        status_label = ttk.Label(
            status_frame, 
            textvariable=self.status_var, 
            font=("Helvetica", 10, "italic")
        )
        status_label.pack()
    
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os

class ZendellConfigUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Zendell Configuration")
        self.root.geometry("650x450")
        self.root.resizable(False, False)
        
        # Create a themed style
        self.style = ttk.Style()
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")  # Use clam theme for a modern look if available
        
        # Configure styles
        self.style.configure("Title.TLabel", font=("Helvetica", 18, "bold"))
        self.style.configure("Subtitle.TLabel", font=("Helvetica", 10, "italic"))
        self.style.configure("Accent.TButton", font=("Helvetica", 12, "bold"))
        
        # Main container frame with padding
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header frame
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Title and subtitle
        title_label = ttk.Label(
            header_frame, 
            text="Zendell Multi-Agent System", 
            style="Title.TLabel"
        )
        title_label.pack(pady=(0, 5))
        
        subtitle_label = ttk.Label(
            header_frame, 
            text="Configuration Interface", 
            style="Subtitle.TLabel"
        )
        subtitle_label.pack()
        
        # Description frame
        desc_frame = ttk.Frame(self.main_frame)
        desc_frame.pack(fill=tk.X, pady=(0, 20))
        
        desc_text = (
            "Zendell is a proactive multi-agent system designed to assist users "
            "with various tasks. Configure your preferences below before starting the system."
        )
        
        desc_label = ttk.Label(
            desc_frame, 
            text=desc_text,
            wraplength=600,
            justify=tk.CENTER
        )
        desc_label.pack()
        
        # Configuration options frame
        config_frame = ttk.LabelFrame(self.main_frame, text="System Configuration", padding="15")
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # LLM Selection
        llm_frame = ttk.Frame(config_frame)
        llm_frame.pack(fill=tk.X, pady=8)
        
        llm_label = ttk.Label(llm_frame, text="LLM Model:", width=20)
        llm_label.pack(side=tk.LEFT, padx=5)
        
        self.llm_var = tk.StringVar(value="gpt-4o")
        llm_options = ["gpt-3.5-turbo", "gpt-4o", "gpt-4-turbo", "claude-3-opus", "llama-3-70b"]
        llm_dropdown = ttk.Combobox(llm_frame, textvariable=self.llm_var, values=llm_options, state="readonly", width=30)
        llm_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Proactivity Time
        time_frame = ttk.Frame(config_frame)
        time_frame.pack(fill=tk.X, pady=8)
        
        time_label = ttk.Label(time_frame, text="Proactivity Interval:", width=20)
        time_label.pack(side=tk.LEFT, padx=5)
        
        self.time_var = tk.StringVar(value="60 minutes")
        time_options = ["5 minutes", "15 minutes", "30 minutes", "60 minutes", "120 minutes"]
        time_dropdown = ttk.Combobox(time_frame, textvariable=self.time_var, values=time_options, state="readonly", width=30)
        time_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Button frame
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        # Start button
        self.start_button = ttk.Button(
            button_frame, 
            text="Start Zendell System", 
            command=self.start_system,
            style="Accent.TButton",
            width=25
        )
        self.start_button.pack(pady=10)
        
        # Status frame
        status_frame = ttk.Frame(self.main_frame)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready to start")
        status_label = ttk.Label(
            status_frame, 
            textvariable=self.status_var, 
            font=("Helvetica", 10, "italic")
        )
        status_label.pack()
    
    def start_system(self):
        """Start the Zendell system with the selected configuration."""
        self.status_var.set("Starting Zendell system...")
        self.root.update()
        
        try:
            # Find the main.py script - try multiple possible locations
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Possible locations for main.py
            possible_paths = [
                os.path.join(current_dir, "main.py"),                    # Same directory
                os.path.join(current_dir, "zendell", "main.py"),         # zendell subdirectory
                os.path.join(os.path.dirname(current_dir), "main.py"),   # Parent directory
                os.path.join(os.path.dirname(current_dir), "zendell", "main.py")  # Parent's zendell dir
            ]
            
            main_script = None
            for path in possible_paths:
                if os.path.exists(path):
                    main_script = path
                    break
            
            # Check if the main script was found
            if not main_script:
                error_msg = "Could not find main.py in any expected location"
                self.status_var.set(f"Error: {error_msg}")
                messagebox.showerror("Error", error_msg)
                return
                
            # Print selected options (for now, as they won't be passed to the main script)
            selected_llm = self.llm_var.get()
            selected_time = self.time_var.get()
            print(f"Starting Zendell with LLM: {selected_llm}, Proactivity Interval: {selected_time}")
            
            # Execute the main script
            process = subprocess.Popen([sys.executable, main_script])
            
            # Close the configuration window
            self.root.destroy()
            
        except Exception as e:
            error_message = f"Error starting system: {str(e)}"
            self.status_var.set(error_message)
            messagebox.showerror("Error", error_message)

def main():
    root = tk.Tk()
    app = ZendellConfigUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()