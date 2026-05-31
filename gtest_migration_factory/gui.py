import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os
import io
from .orchestrator.pipeline import run_pipeline

# Color Palette (Catppuccin Mocha theme inspired for a premium dark mode)
BG_COLOR = "#1e1e2e"
SURFACE_COLOR = "#181825"
INPUT_BG = "#313244"
TEXT_COLOR = "#cdd6f4"
ACCENT_COLOR = "#89b4fa"      # Pastel blue
SUCCESS_COLOR = "#a6e3a1"     # Pastel green
ERROR_COLOR = "#f38ba8"       # Pastel red
BORDER_COLOR = "#45475a"

class ConsoleRedirector(io.StringIO):
    """Redirects stdout/stderr to a Tkinter Text widget."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')
        # Also print to standard console
        sys.__stdout__.write(string)

    def flush(self):
        sys.__stdout__.flush()

class GTestMigrationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GTest Unit Test Migration Factory")
        self.root.geometry("1140x660")
        self.root.configure(bg=BG_COLOR)
        
        # Configure Styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Style mappings for Dark Mode
        self.style.configure('.', bg=BG_COLOR, fg=TEXT_COLOR)
        self.style.configure('TLabel', background=BG_COLOR, foreground=TEXT_COLOR, font=('Arial', 10))
        self.style.configure('TFrame', background=BG_COLOR)
        self.style.configure('TLabelframe', background=BG_COLOR, foreground=TEXT_COLOR)
        self.style.configure('TLabelframe.Label', background=BG_COLOR, foreground=ACCENT_COLOR, font=('Arial', 10, 'bold'))
        
        self.style.configure('TButton', 
            background=INPUT_BG, 
            foreground=TEXT_COLOR, 
            borderwidth=1, 
            bordercolor=BORDER_COLOR, 
            font=('Arial', 9, 'bold'),
            padding=5
        )
        self.style.map('TButton',
            background=[('active', ACCENT_COLOR), ('pressed', '#b4befe')],
            foreground=[('active', SURFACE_COLOR), ('pressed', SURFACE_COLOR)]
        )

        self.style.configure('Run.TButton', 
            background=SUCCESS_COLOR, 
            foreground=SURFACE_COLOR, 
            font=('Arial', 11, 'bold'),
            padding=8
        )
        self.style.map('Run.TButton',
            background=[('active', '#a6e3a1'), ('pressed', '#89dceb')],
            foreground=[('active', SURFACE_COLOR), ('pressed', SURFACE_COLOR)]
        )

        self.style.configure('TCheckbutton', background=BG_COLOR, foreground=TEXT_COLOR, font=('Arial', 9))
        self.style.configure('TRadiobutton', background=BG_COLOR, foreground=TEXT_COLOR, font=('Arial', 9))
        self.style.configure('TCombobox', fieldbackground=INPUT_BG, background=INPUT_BG, foreground=TEXT_COLOR)
        
        # Notebook style (dark tabs)
        self.style.configure('TNotebook', background=BG_COLOR, borderwidth=0)
        self.style.configure('TNotebook.Tab', background=SURFACE_COLOR, foreground=TEXT_COLOR, font=('Arial', 9, 'bold'), padding=(10, 4))
        self.style.map('TNotebook.Tab', background=[('selected', ACCENT_COLOR)], foreground=[('selected', SURFACE_COLOR)])
        
        self.setup_ui()
        self.load_config()             # Load saved config if it exists
        self.on_target_mode_changed()  # Trigger initial toggle state
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        # Main Title Header
        title_frame = tk.Frame(self.root, bg=SURFACE_COLOR, height=50)
        title_frame.pack(fill=tk.X, side=tk.TOP)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame, 
            text="AI Unit Test Migration Factory", 
            font=("Arial", 14, "bold"), 
            bg=SURFACE_COLOR, 
            fg=ACCENT_COLOR
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=10)
        
        subtitle_label = tk.Label(
            title_frame, 
            text="Steps 0 - 4 + Orchestrated Feedback Loop", 
            font=("Arial", 9, "italic"), 
            bg=SURFACE_COLOR, 
            fg="#a6adc8"
        )
        subtitle_label.pack(side=tk.RIGHT, padx=20, pady=15)

        # Main Layout Container (Side-by-Side Panels)
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Left Column: Configuration & Controls Panel
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))

        # Right Column: Console Logs & Code Preview Notebook
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        # ----------------------------------------------------
        # 1. PATHS SECTION PANEL (LEFT PANEL)
        # ----------------------------------------------------
        paths_frame = ttk.LabelFrame(left_panel, text=" Configuration & Paths ")
        paths_frame.pack(fill=tk.X, pady=2, padx=2)

        # Project Root Selection
        ttk.Label(paths_frame, text="Project Root:").grid(row=0, column=0, sticky=tk.W, padx=8, pady=2)
        self.project_root_var = tk.StringVar(value=os.getcwd())
        self.project_root_entry = tk.Entry(paths_frame, textvariable=self.project_root_var, bg=INPUT_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief=tk.FLAT, width=32)
        self.project_root_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(paths_frame, text="Browse...", command=self.browse_project_root).grid(row=0, column=2, padx=8, pady=2)

        # Output Directory Selection
        ttk.Label(paths_frame, text="Output Dir:").grid(row=1, column=0, sticky=tk.W, padx=8, pady=2)
        self.output_dir_var = tk.StringVar(value=os.path.join(os.getcwd(), "tests", "generated_mocks"))
        self.output_dir_entry = tk.Entry(paths_frame, textvariable=self.output_dir_var, bg=INPUT_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief=tk.FLAT, width=32)
        self.output_dir_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(paths_frame, text="Browse...", command=self.browse_output_dir).grid(row=1, column=2, padx=8, pady=2)

        # Specific Header File (Optional)
        ttk.Label(paths_frame, text="Specific Header:").grid(row=2, column=0, sticky=tk.W, padx=8, pady=2)
        self.file_path_var = tk.StringVar()
        self.file_path_entry = tk.Entry(paths_frame, textvariable=self.file_path_var, bg=INPUT_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief=tk.FLAT, width=32)
        self.file_path_entry.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        
        self.btn_frame = ttk.Frame(paths_frame)
        self.btn_frame.grid(row=2, column=2, padx=8, pady=2, sticky=tk.W)
        self.browse_file_btn = ttk.Button(self.btn_frame, text="Browse...", command=self.browse_file)
        self.browse_file_btn.pack(side=tk.LEFT, padx=(0, 2))
        self.clear_file_btn = ttk.Button(self.btn_frame, text="Clear", command=self.clear_file)
        self.clear_file_btn.pack(side=tk.LEFT)

        paths_frame.columnconfigure(1, weight=1)

        # ----------------------------------------------------
        # 2. TARGET MODE SECTION (LEFT PANEL)
        # ----------------------------------------------------
        target_frame = ttk.LabelFrame(left_panel, text=" Target Selection Mode ")
        target_frame.pack(fill=tk.X, pady=2, padx=2)

        self.target_mode_var = tk.StringVar(value="git")
        
        self.radio_git = ttk.Radiobutton(
            target_frame, 
            text="Git Change Detection (changed headers)", 
            variable=self.target_mode_var, 
            value="git",
            command=self.on_target_mode_changed
        )
        self.radio_git.pack(anchor=tk.W, padx=15, pady=2)

        self.radio_all = ttk.Radiobutton(
            target_frame, 
            text="Process All Recursively (--all)", 
            variable=self.target_mode_var, 
            value="all",
            command=self.on_target_mode_changed
        )
        self.radio_all.pack(anchor=tk.W, padx=15, pady=2)

        self.radio_file = ttk.Radiobutton(
            target_frame, 
            text="Specific Header File Only", 
            variable=self.target_mode_var, 
            value="file",
            command=self.on_target_mode_changed
        )
        self.radio_file.pack(anchor=tk.W, padx=15, pady=2)

        # ----------------------------------------------------
        # 3. ADVANCED OPTIONS SECTION (LEFT PANEL - COMPACTED GRID)
        # ----------------------------------------------------
        advanced_frame = ttk.LabelFrame(left_panel, text=" Advanced Customizations ")
        advanced_frame.pack(fill=tk.X, pady=2, padx=2)

        # Row 0: Exclude patterns (Takes whole width)
        ttk.Label(advanced_frame, text="Exclude Patterns:").grid(row=0, column=0, sticky=tk.W, padx=8, pady=2)
        self.exclude_patterns_var = tk.StringVar(value="")
        self.exclude_patterns_entry = tk.Entry(advanced_frame, textvariable=self.exclude_patterns_var, bg=INPUT_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief=tk.FLAT)
        self.exclude_patterns_entry.grid(row=0, column=1, columnspan=3, sticky=tk.EW, padx=5, pady=2)

        # Row 1: C++ Standard & Mock Prefix
        ttk.Label(advanced_frame, text="C++ Standard:").grid(row=1, column=0, sticky=tk.W, padx=8, pady=2)
        self.cxx_standard_var = tk.StringVar(value="Auto-detect")
        cxx_dropdown = ttk.Combobox(
            advanced_frame, 
            textvariable=self.cxx_standard_var, 
            values=["Auto-detect", "11", "14", "17", "20"],
            state="readonly",
            width=10
        )
        cxx_dropdown.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(advanced_frame, text="Mock Prefix:").grid(row=1, column=2, sticky=tk.W, padx=10, pady=2)
        self.mock_prefix_var = tk.StringVar(value="Mock")
        self.mock_prefix_entry = tk.Entry(advanced_frame, textvariable=self.mock_prefix_var, bg=INPUT_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief=tk.FLAT, width=12)
        self.mock_prefix_entry.grid(row=1, column=3, sticky=tk.EW, padx=5, pady=2)

        # Row 2: Mock Suffix & Namespace Filter
        ttk.Label(advanced_frame, text="Mock Suffix:").grid(row=2, column=0, sticky=tk.W, padx=8, pady=2)
        self.mock_suffix_var = tk.StringVar(value="")
        self.mock_suffix_entry = tk.Entry(advanced_frame, textvariable=self.mock_suffix_var, bg=INPUT_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief=tk.FLAT, width=12)
        self.mock_suffix_entry.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)

        ttk.Label(advanced_frame, text="Namespace Filter:").grid(row=2, column=2, sticky=tk.W, padx=10, pady=2)
        self.namespace_filter_var = tk.StringVar(value="")
        self.namespace_filter_entry = tk.Entry(advanced_frame, textvariable=self.namespace_filter_var, bg=INPUT_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief=tk.FLAT, width=12)
        self.namespace_filter_entry.grid(row=2, column=3, sticky=tk.EW, padx=5, pady=2)

        # Row 3: Custom Includes
        ttk.Label(advanced_frame, text="Custom Includes:").grid(row=3, column=0, sticky=tk.W, padx=8, pady=2)
        self.custom_includes_var = tk.StringVar(value="")
        self.custom_includes_entry = tk.Entry(advanced_frame, textvariable=self.custom_includes_var, bg=INPUT_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief=tk.FLAT)
        self.custom_includes_entry.grid(row=3, column=1, columnspan=3, sticky=tk.EW, padx=5, pady=2)

        # Row 4: Compile Commands
        ttk.Label(advanced_frame, text="Compile Cmds:").grid(row=4, column=0, sticky=tk.W, padx=8, pady=2)
        self.compile_commands_var = tk.StringVar(value="")
        self.compile_commands_entry = tk.Entry(advanced_frame, textvariable=self.compile_commands_var, bg=INPUT_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief=tk.FLAT)
        self.compile_commands_entry.grid(row=4, column=1, columnspan=3, sticky=tk.EW, padx=5, pady=2)

        advanced_frame.columnconfigure(1, weight=1)
        advanced_frame.columnconfigure(3, weight=1)

        # ----------------------------------------------------
        # 4. ACTION TOGGLES PANEL (LEFT PANEL - GRID)
        # ----------------------------------------------------
        toggles_frame = ttk.LabelFrame(left_panel, text=" Action Flags ")
        toggles_frame.pack(fill=tk.X, pady=2, padx=2)

        self.keep_class_name_var = tk.BooleanVar(value=False)
        self.keep_class_name_cb = ttk.Checkbutton(
            toggles_frame, 
            text="Keep Class Name (swap)", 
            variable=self.keep_class_name_var
        )
        self.keep_class_name_cb.grid(row=0, column=0, sticky=tk.W, padx=10, pady=2)

        self.no_override_var = tk.BooleanVar(value=False)
        self.no_override_cb = ttk.Checkbutton(
            toggles_frame, 
            text="Omit Override Keyword", 
            variable=self.no_override_var
        )
        self.no_override_cb.grid(row=0, column=1, sticky=tk.W, padx=10, pady=2)

        self.clang_format_var = tk.BooleanVar(value=False)
        self.clang_format_cb = ttk.Checkbutton(
            toggles_frame, 
            text="Run Clang-Format", 
            variable=self.clang_format_var
        )
        self.clang_format_cb.grid(row=1, column=0, sticky=tk.W, padx=10, pady=2)

        self.verify_compile_var = tk.BooleanVar(value=False)
        self.verify_compile_cb = ttk.Checkbutton(
            toggles_frame, 
            text="Verify Compile Check", 
            variable=self.verify_compile_var
        )
        self.verify_compile_cb.grid(row=1, column=1, sticky=tk.W, padx=10, pady=2)

        self.dry_run_var = tk.BooleanVar(value=False)
        self.dry_run_cb = ttk.Checkbutton(
            toggles_frame, 
            text="Dry Run Mode", 
            variable=self.dry_run_var
        )
        self.dry_run_cb.grid(row=2, column=0, sticky=tk.W, padx=10, pady=2)

        self.verbose_var = tk.BooleanVar(value=True)
        self.verbose_cb = ttk.Checkbutton(
            toggles_frame, 
            text="Verbose Logs", 
            variable=self.verbose_var
        )
        self.verbose_cb.grid(row=2, column=1, sticky=tk.W, padx=10, pady=2)

        for col in range(2):
            toggles_frame.columnconfigure(col, weight=1)

        # ----------------------------------------------------
        # 5. CONTROL & RUN ACTION PANEL (LEFT PANEL - AT THE BOTTOM)
        # ----------------------------------------------------
        control_frame = ttk.LabelFrame(left_panel, text=" Execution & Dashboard ")
        control_frame.pack(fill=tk.BOTH, expand=True, pady=4, padx=2)

        # Help / Instructions label
        instructions_text = (
            "👉 **How to execute migration:**\n"
            "1. Choose a target mode (Git status, All, or Specific file)\n"
            "2. Enable 'Verify Compile Check' to validate & auto-heal stubs.\n"
            "3. Click 'Execute Migration' below to run!"
        )
        self.instructions_lbl = tk.Label(
            control_frame, 
            text=instructions_text, 
            bg=BG_COLOR, 
            fg="#a6adc8", 
            justify=tk.LEFT,
            font=("Arial", 9, "italic"),
            anchor=tk.W
        )
        self.instructions_lbl.pack(fill=tk.X, padx=10, pady=(5, 10))

        # Status Panel
        status_subframe = ttk.Frame(control_frame)
        status_subframe.pack(fill=tk.X, padx=10, pady=2)
        
        self.status_label = tk.Label(
            status_subframe, 
            text="Status: Ready ●", 
            bg=BG_COLOR, 
            fg=SUCCESS_COLOR,
            font=("Arial", 10, "bold")
        )
        self.status_label.pack(side=tk.LEFT)

        # Run Buttons Frame
        btns_subframe = ttk.Frame(control_frame)
        btns_subframe.pack(fill=tk.X, padx=10, pady=(10, 5))

        self.run_button = ttk.Button(
            btns_subframe, 
            text="Execute Migration", 
            style="Run.TButton",
            command=self.execute_pipeline
        )
        self.run_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        self.preview_button = ttk.Button(
            btns_subframe,
            text="Preview Mock",
            command=self.preview_mock
        )
        self.preview_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 2))

        self.open_output_button = ttk.Button(
            btns_subframe,
            text="Open Folder 📁",
            command=self.open_output_folder,
            state="disabled"
        )
        self.open_output_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        # ----------------------------------------------------
        # 6. DUAL-TAB CONSOLE & CODE PREVIEW (RIGHT PANEL)
        # ----------------------------------------------------
        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Execution Console Frame
        console_frame = ttk.Frame(self.notebook)
        self.notebook.add(console_frame, text=" Execution Console ")

        self.console_text = tk.Text(
            console_frame, 
            bg=SURFACE_COLOR, 
            fg=TEXT_COLOR, 
            insertbackground=TEXT_COLOR,
            relief=tk.FLAT,
            state='disabled',
            font=("Consolas", 10),
            padx=10,
            pady=10
        )
        self.console_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        console_scrollbar = ttk.Scrollbar(console_frame, command=self.console_text.yview)
        console_scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.console_text.configure(yscrollcommand=console_scrollbar.set)

        # Tab 2: Mock Code Preview Frame
        preview_frame = ttk.Frame(self.notebook)
        self.notebook.add(preview_frame, text=" Mock Code Preview ")

        self.preview_text = tk.Text(
            preview_frame, 
            bg=SURFACE_COLOR, 
            fg=TEXT_COLOR, 
            insertbackground=TEXT_COLOR,
            relief=tk.FLAT,
            state='disabled',
            font=("Consolas", 10),
            padx=10,
            pady=10
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        preview_scrollbar = ttk.Scrollbar(preview_frame, command=self.preview_text.yview)
        preview_scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.preview_text.configure(yscrollcommand=preview_scrollbar.set)

        # ----------------------------------------------------
        # 6. RUN BUTTONS & STATUS
        # ----------------------------------------------------
        bottom_frame = ttk.Frame(main_container)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=4)

        self.status_label = tk.Label(
            bottom_frame, 
            text="Status: Ready", 
            bg=BG_COLOR, 
            fg=TEXT_COLOR,
            font=("Arial", 10, "bold")
        )
        self.status_label.pack(side=tk.LEFT, padx=10)

        # Execute Migration Button
        self.run_button = ttk.Button(
            bottom_frame, 
            text="Execute Migration", 
            style="Run.TButton",
            command=self.execute_pipeline
        )
        self.run_button.pack(side=tk.RIGHT, padx=5)

        # Preview Mock Button
        self.preview_button = ttk.Button(
            bottom_frame,
            text="Preview Mock",
            command=self.preview_mock
        )
        self.preview_button.pack(side=tk.RIGHT, padx=5)

    def on_target_mode_changed(self):
        mode = self.target_mode_var.get()
        if mode == "file":
            # Enable Specific Header inputs
            self.file_path_entry.configure(state="normal")
            self.browse_file_btn.configure(state="normal")
            self.clear_file_btn.configure(state="normal")
            # Excludes are not applicable to file mode
            self.exclude_patterns_entry.configure(state="disabled")
        elif mode == "all":
            # Disable file inputs
            self.file_path_entry.configure(state="disabled")
            self.browse_file_btn.configure(state="disabled")
            self.clear_file_btn.configure(state="disabled")
            # Enable excludes
            self.exclude_patterns_entry.configure(state="normal")
        else:  # Git change detection
            # Disable file inputs
            self.file_path_entry.configure(state="disabled")
            self.browse_file_btn.configure(state="disabled")
            self.clear_file_btn.configure(state="disabled")
            # Enable excludes
            self.exclude_patterns_entry.configure(state="normal")

    # ----------------------------------------------------
    # BROWSE ACTIONS
    # ----------------------------------------------------
    def browse_project_root(self):
        path = filedialog.askdirectory(initialdir=self.project_root_var.get())
        if path:
            self.project_root_var.set(os.path.abspath(path))
            self.output_dir_var.set(os.path.abspath(os.path.join(path, "tests", "generated_mocks")))

    def browse_output_dir(self):
        path = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if path:
            self.output_dir_var.set(os.path.abspath(path))

    def browse_file(self):
        path = filedialog.askopenfilename(
            initialdir=self.project_root_var.get(),
            filetypes=[("C++ Header Files", "*.h *.hpp *.hh *.h++"), ("All Files", "*.*")]
        )
        if path:
            self.file_path_var.set(os.path.abspath(path))

    def clear_file(self):
        self.file_path_var.set("")

    # ----------------------------------------------------
    # PREVIEW ACTION
    # ----------------------------------------------------
    def preview_mock(self):
        target_file = self.file_path_var.get()
        if not target_file:
            messagebox.showwarning("No File Selected", "Please select a specific header file to generate a preview.")
            return

        # Switch to Preview Tab
        self.notebook.select(1)
        
        self.preview_text.configure(state='normal')
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(tk.END, "Parsing C++ structure and generating Mock preview...\n")
        self.preview_text.configure(state='disabled')
        self.root.update_idletasks()

        try:
            from .parser.cpp_parser import parse_header
            from .generator.mock_generator import generate_mock_header_from_ast

            ast = parse_header(target_file)
            
            keep_class = self.keep_class_name_var.get()
            no_override = self.no_override_var.get()
            mock_prefix = self.mock_prefix_var.get().strip()
            mock_suffix = self.mock_suffix_var.get().strip()
            namespace_filter = self.namespace_filter_var.get().strip() or None
            custom_inc = self.custom_includes_var.get().strip() or None

            mock_content = generate_mock_header_from_ast(
                ast,
                os.path.basename(target_file),
                keep_class_name=keep_class,
                mock_prefix=mock_prefix,
                mock_suffix=mock_suffix,
                no_override=no_override,
                custom_includes=custom_inc,
                namespace_filter=namespace_filter
            )

            self.preview_text.configure(state='normal')
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, mock_content)
            self.preview_text.configure(state='disabled')
            
        except Exception as e:
            self.preview_text.configure(state='normal')
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, f"Failed to generate preview: {e}")
            self.preview_text.configure(state='disabled')

    # ----------------------------------------------------
    # EXECUTION PIPELINE
    # ----------------------------------------------------
    def execute_pipeline(self):
        # Switch to Console Tab
        self.notebook.select(0)
        
        # Reset console
        self.console_text.configure(state='normal')
        self.console_text.delete(1.0, tk.END)
        self.console_text.configure(state='disabled')
        
        self.status_label.configure(text="Status: Executing... ●", fg=ACCENT_COLOR)
        self.open_output_button.configure(state="disabled")
        self.root.update_idletasks()

        # Capture print outputs
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirector = ConsoleRedirector(self.console_text)
        sys.stdout = redirector
        sys.stderr = redirector

        try:
            # Extract arguments
            proj_root = self.project_root_var.get()
            out_dir = self.output_dir_var.get()
            target_mode = self.target_mode_var.get()
            
            target_file = None
            process_all = False
            if target_mode == "file":
                target_file = self.file_path_var.get()
                if not target_file:
                    raise ValueError("Specific file mode selected but no header file was specified.")
            elif target_mode == "all":
                process_all = True

            cxx_std = self.cxx_standard_var.get()
            if cxx_std == "Auto-detect":
                cxx_std = None
                
            keep_class = self.keep_class_name_var.get()
            no_override = self.no_override_var.get()
            clang_format = self.clang_format_var.get()
            verify_compile = self.verify_compile_var.get()
            dry_run = self.dry_run_var.get()
            verbose = self.verbose_var.get()
            
            exclude_pats = self.exclude_patterns_var.get().strip() or None
            mock_prefix = self.mock_prefix_var.get().strip()
            mock_suffix = self.mock_suffix_var.get().strip()
            namespace_filter = self.namespace_filter_var.get().strip() or None
            custom_inc = self.custom_includes_var.get().strip() or None
            compile_cmds = self.compile_commands_var.get().strip() or None

            # Run orchestrator
            print(f"=== GTest Migration GUI Launch ===")
            print(f"Project Root:     {proj_root}")
            print(f"Output Dir:       {out_dir}")
            print(f"Target Selection: {target_mode.upper()} mode")
            if target_file:
                print(f"Target File:      {target_file}")
            print(f"Class Name:       {'Preserved (Stub swap)' if keep_class else 'Custom naming prefix/suffix'}")
            if not keep_class:
                print(f"Naming Pattern:   {mock_prefix}<Class>{mock_suffix}")
            if namespace_filter:
                print(f"Namespace Filter: {namespace_filter}")
            if compile_cmds:
                print(f"Compile Commands: {compile_cmds}")
            if dry_run:
                print(f"Mode:             DRY RUN (no files will be written)")
            print(f"==================================\n")

            result = run_pipeline(
                project_root=proj_root,
                output_dir=out_dir,
                file_path=target_file,
                cxx_standard=cxx_std,
                keep_class_name=keep_class,
                verbose=verbose,
                process_all=process_all,
                exclude_patterns=exclude_pats,
                mock_prefix=mock_prefix,
                mock_suffix=mock_suffix,
                no_override=no_override,
                dry_run=dry_run,
                clang_format=clang_format,
                custom_includes=custom_inc,
                namespace_filter=namespace_filter,
                compile_commands=compile_cmds,
                verify_compile=verify_compile
            )

            if result["status"] == "success":
                if dry_run:
                    self.status_label.configure(text="Status: Dry Run Done! ●", fg=SUCCESS_COLOR)
                    print(f"\nDry run complete. {len(result['generated_files'])} files would be processed/written.")
                else:
                    self.status_label.configure(text="Status: Success! ●", fg=SUCCESS_COLOR)
                    self.open_output_button.configure(state="normal")
                    print(f"\nGenerated {len(result['generated_files'])} files successfully!")
                self.save_config()
            else:
                self.status_label.configure(text=f"Status: Error - {result.get('error')} ●", fg=ERROR_COLOR)
                print(f"\n[Error] Pipeline failed: {result.get('error')}")

        except Exception as e:
            self.status_label.configure(text="Status: Exception occurred! ●", fg=ERROR_COLOR)
            print(f"\n[Exception occurred during execution]:\n{e}")
            import traceback
            traceback.print_exc()

        finally:
            # Restore stdout/stderr streams
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def open_output_folder(self):
        out_dir = self.output_dir_var.get()
        if os.path.exists(out_dir):
            if sys.platform == "win32":
                os.startfile(out_dir)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.run(["open", out_dir])
            else:
                import subprocess
                subprocess.run(["xdg-open", out_dir])

    def save_config(self):
        import json
        config_path = os.path.join(os.getcwd(), ".gtest_factory_config.json")
        try:
            config = {
                "project_root": self.project_root_var.get(),
                "output_dir": self.output_dir_var.get(),
                "file_path": self.file_path_var.get(),
                "target_mode": self.target_mode_var.get(),
                "exclude_patterns": self.exclude_patterns_var.get(),
                "cxx_standard": self.cxx_standard_var.get(),
                "mock_prefix": self.mock_prefix_var.get(),
                "mock_suffix": self.mock_suffix_var.get(),
                "namespace_filter": self.namespace_filter_var.get(),
                "custom_includes": self.custom_includes_var.get(),
                "compile_commands": self.compile_commands_var.get(),
                "keep_class_name": self.keep_class_name_var.get(),
                "no_override": self.no_override_var.get(),
                "clang_format": self.clang_format_var.get(),
                "verify_compile": self.verify_compile_var.get(),
                "dry_run": self.dry_run_var.get(),
                "verbose": self.verbose_var.get()
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception:
            pass

    def load_config(self):
        import json
        config_path = os.path.join(os.getcwd(), ".gtest_factory_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                # Check for each value and set it if present in config
                if "project_root" in config: self.project_root_var.set(config["project_root"])
                if "output_dir" in config: self.output_dir_var.set(config["output_dir"])
                if "file_path" in config: self.file_path_var.set(config["file_path"])
                if "target_mode" in config: self.target_mode_var.set(config["target_mode"])
                if "exclude_patterns" in config: self.exclude_patterns_var.set(config["exclude_patterns"])
                if "cxx_standard" in config: self.cxx_standard_var.set(config["cxx_standard"])
                if "mock_prefix" in config: self.mock_prefix_var.set(config["mock_prefix"])
                if "mock_suffix" in config: self.mock_suffix_var.set(config["mock_suffix"])
                if "namespace_filter" in config: self.namespace_filter_var.set(config["namespace_filter"])
                if "custom_includes" in config: self.custom_includes_var.set(config["custom_includes"])
                if "compile_commands" in config: self.compile_commands_var.set(config["compile_commands"])
                if "keep_class_name" in config: self.keep_class_name_var.set(config["keep_class_name"])
                if "no_override" in config: self.no_override_var.set(config["no_override"])
                if "clang_format" in config: self.clang_format_var.set(config["clang_format"])
                if "verify_compile" in config: self.verify_compile_var.set(config["verify_compile"])
                if "dry_run" in config: self.dry_run_var.set(config["dry_run"])
                if "verbose" in config: self.verbose_var.set(config["verbose"])
            except Exception:
                pass

    def on_closing(self):
        try:
            self.save_config()
        except Exception:
            pass
        self.root.destroy()

def launch_gui():
    root = tk.Tk()
    app = GTestMigrationGUI(root)
    root.mainloop()

if __name__ == "__main__":
    launch_gui()
