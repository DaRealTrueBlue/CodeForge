"""
CodeForge - A modern, customisable code editor
Author: DaRealTrueBlue
Version: 1.1.0-beta
License: MIT
Repository: https://github.com/DaRealTrueBlue/CodeForge
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font, simpledialog, colorchooser
import os
from pathlib import Path
import re
import subprocess
import threading
from PIL import Image, ImageTk
import ctypes
from functools import lru_cache
import gc
import json

version = "1.1.0-beta"

class CodeEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("CodeForge" f" - v{version}")
        self.root.geometry("1200x800")
        
        # Make window appear in taskbar even with overrideredirect
        self.root.overrideredirect(True)
        self.root.update_idletasks()
        
        # Set window to appear in taskbar (Windows-specific)
        try:
            # Get the window handle
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            # Set WS_EX_APPWINDOW style to show in taskbar
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
            style = style | 0x00040000  # WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
            # Update the window
            self.root.withdraw()
            self.root.deiconify()
        except:
            pass
        
        # Store open files
        self.open_files = {}
        self.current_file = None
        self.current_folder = None
        
        # Recent files
        self.recent_files = []
        self.max_recent_files = 10
        
        # Window dragging
        self.offset_x = 0
        self.offset_y = 0
        
        # Bracket matching
        self.matching_pairs = {'(': ')', '[': ']', '{': '}', '<': '>'}
        self.closing_pairs = {v: k for k, v in self.matching_pairs.items()}
        
        # Tracking for syntax highlighting
        self.current_language = None
        
        # Compiled regex patterns for syntax highlighting (performance)
        self.regex_cache = {}
        
        # Terminal process
        self.terminal_process = None
        
        # Auto-save
        self.auto_save_enabled = True
        self.auto_save_interval = 30000  # 30 seconds
        
        # Font size for zoom
        self.base_font_size = 11
        self.current_font_size = 11
        
        # Settings with layout customisation
        self.settings = {
            'theme': 'dark',
            'font_family': 'Consolas',
            'font_size': 11,
            'auto_save': True,
            'show_line_numbers': True,
            'show_minimap': True,
            'tab_size': 4,
            'sidebar_position': 'left',  # left or right
            'activity_bar_visible': True,
            'panel_position': 'bottom',  # bottom or right
            'layout_preset': 'default',  # default, minimal, focus
            'accent_color': '#007acc',
            'custom_theme': None
        }
        
        # Theme presets
        self.themes = {
            'dark': {
                'bg': '#1e1e1e',
                'fg': '#d4d4d4',
                'editor_bg': '#1e1e1e',
                'editor_fg': '#d4d4d4',
                'sidebar_bg': '#252526',
                'selected_bg': '#37373d',
                'titlebar_bg': '#323233',
                'accent': '#007acc',
                'border': '#454545'
            },
            'light': {
                'bg': '#ffffff',
                'fg': '#000000',
                'editor_bg': '#ffffff',
                'editor_fg': '#000000',
                'sidebar_bg': '#f3f3f3',
                'selected_bg': '#e8e8e8',
                'titlebar_bg': '#dddddd',
                'accent': '#0078d4',
                'border': '#cccccc'
            },
            'monokai': {
                'bg': '#272822',
                'fg': '#f8f8f2',
                'editor_bg': '#272822',
                'editor_fg': '#f8f8f2',
                'sidebar_bg': '#1e1f1c',
                'selected_bg': '#3e3d32',
                'titlebar_bg': '#1e1f1c',
                'accent': '#66d9ef',
                'border': '#3e3d32'
            },
            'dracula': {
                'bg': '#282a36',
                'fg': '#f8f8f2',
                'editor_bg': '#282a36',
                'editor_fg': '#f8f8f2',
                'sidebar_bg': '#21222c',
                'selected_bg': '#44475a',
                'titlebar_bg': '#21222c',
                'accent': '#bd93f9',
                'border': '#44475a'
            }
        }
        
        # Load current theme
        self.load_theme(self.settings['theme'])
        
        # Load current theme
        self.load_theme(self.settings['theme'])
        
        # Set window icon
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon", "white-transparent.png")
            icon_img = tk.PhotoImage(file=icon_path)
            self.root.iconphoto(True, icon_img)
        except:
            pass
        
        self.setup_ui()
        self.setup_bindings()
        self.configure_styles()
        self.setup_syntax_highlighting()
        
        # Start auto-save after everything is initialized
        if self.auto_save_enabled:
            self.schedule_auto_save()
    
    def load_theme(self, theme_name):
        """Load a theme and apply colours"""
        if theme_name in self.themes:
            theme = self.themes[theme_name]
        else:
            theme = self.themes['dark']  # Fallback
        
        self.bg_color = theme['bg']
        self.fg_color = theme['fg']
        self.editor_bg = theme['editor_bg']
        self.editor_fg = theme['editor_fg']
        self.sidebar_bg = theme['sidebar_bg']
        self.selected_bg = theme['selected_bg']
        self.titlebar_bg = theme.get('titlebar_bg', theme['sidebar_bg'])
        self.accent_color = theme['accent']
        self.border_color = theme['border']
    
    def apply_theme(self, theme_name):
        """Apply theme to existing UI elements"""
        self.load_theme(theme_name)
        self.settings['theme'] = theme_name
        
        # Update root
        if hasattr(self, 'root'):
            self.root.configure(bg=self.bg_color)
        
        # Update title bar
        if hasattr(self, 'title_bar'):
            self.title_bar.configure(bg=self.titlebar_bg)
            for widget in self.title_bar.winfo_children():
                self._update_widget_colours(widget)
        
        # Update text area
        if hasattr(self, 'text_area'):
            self.text_area.configure(bg=self.editor_bg, fg=self.editor_fg,
                                    insertbackground=self.fg_color,
                                    selectbackground=self.accent_color)
        
        # Update line numbers
        if hasattr(self, 'line_numbers'):
            self.line_numbers.configure(bg=self.sidebar_bg, fg=self.fg_color)
        
        # Update terminal
        if hasattr(self, 'terminal_output'):
            self.terminal_output.configure(bg=self.bg_color, fg=self.fg_color)
        
        # Reconfigure styles
        self.configure_styles()
        
        messagebox.showinfo("Theme Changed", f"Theme '{theme_name}' applied successfully!")
    
    def _update_widget_colours(self, widget):
        """Recursively update widget colours"""
        try:
            widget_type = widget.winfo_class()
            if widget_type in ['Frame', 'Label']:
                widget.configure(bg=self.titlebar_bg)
                if widget_type == 'Label':
                    widget.configure(fg=self.fg_color)
        except:
            pass
        
        for child in widget.winfo_children():
            self._update_widget_colours(child)
        
    def setup_syntax_highlighting(self):
        """Configure syntax highlighting tags"""
        # Python syntax colours (like VS Code dark theme)
        self.text_area.tag_configure("keyword", foreground="#569cd6")  # Blue
        self.text_area.tag_configure("string", foreground="#ce9178")   # Orange
        self.text_area.tag_configure("comment", foreground="#6a9955")  # Green
        self.text_area.tag_configure("function", foreground="#dcdcaa")  # Yellow
        self.text_area.tag_configure("number", foreground="#b5cea8")   # Light green
        self.text_area.tag_configure("class", foreground="#4ec9b0")    # Cyan
        self.text_area.tag_configure("operator", foreground="#d4d4d4") # White
        self.text_area.tag_configure("builtin", foreground="#4fc1ff")  # Light blue
        
        # Current line highlight
        self.text_area.tag_configure("current_line", background="#2a2a2a")
        
    def configure_styles(self):
        """Configure ttk styles for dark theme"""
        style = ttk.Style()
        
        # Configure Treeview style
        style.theme_use('default')
        style.configure("Treeview",
                       background=self.sidebar_bg,
                       foreground=self.fg_color,
                       fieldbackground=self.sidebar_bg,
                       borderwidth=0,
                       relief='flat')
        style.configure("Treeview.Heading",
                       background=self.sidebar_bg,
                       foreground=self.fg_color,
                       borderwidth=0)
        style.map("Treeview",
                 background=[('selected', self.selected_bg)],
                 foreground=[('selected', self.fg_color)])
        
        # Configure scrollbar styles for dark theme
        style.configure("Vertical.TScrollbar",
                       background="#424242",
                       darkcolor="#2d2d2d",
                       lightcolor="#4e4e4e",
                       troughcolor="#1e1e1e",
                       bordercolor="#1e1e1e",
                       arrowcolor="#858585")
        style.map("Vertical.TScrollbar",
                 background=[('active', '#4e4e4e'), ('!active', '#424242')])
        
        style.configure("Horizontal.TScrollbar",
                       background="#424242",
                       darkcolor="#2d2d2d",
                       lightcolor="#4e4e4e",
                       troughcolor="#1e1e1e",
                       bordercolor="#1e1e1e",
                       arrowcolor="#858585")
        style.map("Horizontal.TScrollbar",
                 background=[('active', '#4e4e4e'), ('!active', '#424242')])
        
        # Configure PanedWindow
        style.configure("TPanedwindow", background=self.bg_color)
        style.configure("Sash", sashthickness=3, background="#3e3e42")
        
    def setup_ui(self):
        # Configure root background
        self.root.configure(bg=self.bg_color)
        
        # Custom title bar
        self.title_bar = tk.Frame(self.root, bg="#2d2d30", height=35, relief=tk.FLAT)
        self.title_bar.pack(fill=tk.X, side=tk.TOP)
        self.title_bar.pack_propagate(False)
        
        # Bind dragging events
        self.title_bar.bind("<Button-1>", self.start_drag)
        self.title_bar.bind("<B1-Motion>", self.on_drag)
        
        # App icon and title
        title_left = tk.Frame(self.title_bar, bg="#2d2d30")
        title_left.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Load custom logo
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "icon", "white-transparent.png")
            logo_image = Image.open(logo_path)
            logo_image = logo_image.resize((20, 20), Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_image)
            logo_label = tk.Label(title_left, image=self.logo_photo, bg="#2d2d30")
            logo_label.pack(side=tk.LEFT, padx=(0, 8))
        except:
            # Fallback to emoji if image fails to load
            tk.Label(title_left, text="💻", bg="#2d2d30", fg="#ffffff",
                    font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=(0, 8))
        
        self.title_label = tk.Label(title_left, text=f"CodeForge - v{version}", bg="#2d2d30", fg="#cccccc",
                                    font=("Segoe UI", 9))
        self.title_label.pack(side=tk.LEFT)
        self.title_label.bind("<Button-1>", self.start_drag)
        self.title_label.bind("<B1-Motion>", self.on_drag)
        
        # Window controls
        controls_frame = tk.Frame(self.title_bar, bg="#2d2d30")
        controls_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Minimize button
        min_btn = tk.Label(controls_frame, text="─", bg="#2d2d30", fg="#cccccc",
                          font=("Segoe UI", 12), width=5, cursor="hand2")
        min_btn.pack(side=tk.LEFT, fill=tk.Y)
        min_btn.bind("<Button-1>", lambda e: self.root.iconify())
        min_btn.bind("<Enter>", lambda e: min_btn.config(bg="#3e3e42"))
        min_btn.bind("<Leave>", lambda e: min_btn.config(bg="#2d2d30"))
        
        # Maximize button
        self.max_btn = tk.Label(controls_frame, text="🗖", bg="#2d2d30", fg="#cccccc",
                               font=("Segoe UI", 11), width=5, cursor="hand2")
        self.max_btn.pack(side=tk.LEFT, fill=tk.Y)
        self.max_btn.bind("<Button-1>", self.toggle_maximize)
        self.max_btn.bind("<Enter>", lambda e: self.max_btn.config(bg="#3e3e42"))
        self.max_btn.bind("<Leave>", lambda e: self.max_btn.config(bg="#2d2d30"))
        
        # Close button
        close_btn = tk.Label(controls_frame, text="✕", bg="#2d2d30", fg="#cccccc",
                            font=("Segoe UI", 10), width=5, cursor="hand2")
        close_btn.pack(side=tk.LEFT, fill=tk.Y)
        close_btn.bind("<Button-1>", lambda e: self.root.quit())
        close_btn.bind("<Enter>", lambda e: close_btn.config(bg="#e81123", fg="#ffffff"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(bg="#2d2d30", fg="#cccccc"))
        
        # Main container frame
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Menu bar (below title bar) - without attaching to root
        menu_frame = tk.Frame(main_frame, bg="#2d2d30", height=22)
        menu_frame.pack(fill=tk.X, side=tk.TOP)
        menu_frame.pack_propagate(False)
        
        # Create custom menu buttons
        menu_buttons_frame = tk.Frame(menu_frame, bg="#2d2d30")
        menu_buttons_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # File menu
        file_btn = tk.Label(menu_buttons_frame, text="File", bg="#2d2d30", fg="#cccccc",
                           font=("Segoe UI", 9), padx=10, cursor="hand2")
        file_btn.pack(side=tk.LEFT)
        
        file_menu = tk.Menu(file_btn, tearoff=0, bg="#2d2d30", fg="#cccccc",
                           activebackground="#3e3e42", activeforeground="#ffffff",
                           relief=tk.FLAT, bd=0)
        file_menu.add_command(label="New File", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open File", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Open Folder", command=self.open_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As", command=self.save_file_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        
        # Recent files submenu
        self.recent_menu = tk.Menu(file_menu, tearoff=0, bg="#2d2d30", fg="#cccccc",
                                   activebackground="#3e3e42", activeforeground="#ffffff",
                                   relief=tk.FLAT, bd=0)
        file_menu.add_cascade(label="Recent Files", menu=self.recent_menu)
        self.update_recent_files_menu()
        
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        def show_file_menu(e):
            file_menu.post(e.widget.winfo_rootx(), e.widget.winfo_rooty() + e.widget.winfo_height())
        file_btn.bind("<Button-1>", show_file_menu)
        file_btn.bind("<Enter>", lambda e: file_btn.config(bg="#3e3e42"))
        file_btn.bind("<Leave>", lambda e: file_btn.config(bg="#2d2d30"))
        
        # Edit menu
        edit_btn = tk.Label(menu_buttons_frame, text="Edit", bg="#2d2d30", fg="#cccccc",
                           font=("Segoe UI", 9), padx=10, cursor="hand2")
        edit_btn.pack(side=tk.LEFT)
        
        edit_menu = tk.Menu(edit_btn, tearoff=0, bg="#2d2d30", fg="#cccccc",
                           activebackground="#3e3e42", activeforeground="#ffffff",
                           relief=tk.FLAT, bd=0)
        edit_menu.add_command(label="Undo", command=lambda: self.text_area.edit_undo(), accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=lambda: self.text_area.edit_redo(), accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=lambda: self.text_area.event_generate("<<Cut>>"), accelerator="Ctrl+X")
        edit_menu.add_command(label="Copy", command=lambda: self.text_area.event_generate("<<Copy>>"), accelerator="Ctrl+C")
        edit_menu.add_command(label="Paste", command=lambda: self.text_area.event_generate("<<Paste>>"), accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="Select All", command=lambda: self.text_area.tag_add("sel", "1.0", "end"), accelerator="Ctrl+A")
        edit_menu.add_command(label="Find", command=self.show_find_dialog, accelerator="Ctrl+F")
        
        def show_edit_menu(e):
            edit_menu.post(e.widget.winfo_rootx(), e.widget.winfo_rooty() + e.widget.winfo_height())
        edit_btn.bind("<Button-1>", show_edit_menu)
        edit_btn.bind("<Enter>", lambda e: edit_btn.config(bg="#3e3e42"))
        edit_btn.bind("<Leave>", lambda e: edit_btn.config(bg="#2d2d30"))
        
        # View menu
        view_btn = tk.Label(menu_buttons_frame, text="View", bg="#2d2d30", fg="#cccccc",
                           font=("Segoe UI", 9), padx=10, cursor="hand2")
        view_btn.pack(side=tk.LEFT)
        
        view_menu = tk.Menu(view_btn, tearoff=0, bg="#2d2d30", fg="#cccccc",
                           activebackground="#3e3e42", activeforeground="#ffffff",
                           relief=tk.FLAT, bd=0)
        view_menu.add_command(label="Toggle Terminal", command=self.toggle_terminal)
        view_menu.add_command(label="Toggle Minimap", command=self.toggle_minimap)
        view_menu.add_separator()
        
        # Theme submenu
        theme_menu = tk.Menu(view_menu, tearoff=0, bg="#2d2d30", fg="#cccccc",
                            activebackground="#3e3e42", activeforeground="#ffffff",
                            relief=tk.FLAT, bd=0)
        theme_menu.add_command(label="Dark", command=lambda: self.apply_theme('dark'))
        theme_menu.add_command(label="Light", command=lambda: self.apply_theme('light'))
        theme_menu.add_command(label="Monokai", command=lambda: self.apply_theme('monokai'))
        theme_menu.add_command(label="Dracula", command=lambda: self.apply_theme('dracula'))
        view_menu.add_cascade(label="Themes", menu=theme_menu)
        
        # Layout submenu
        layout_menu = tk.Menu(view_menu, tearoff=0, bg="#2d2d30", fg="#cccccc",
                             activebackground="#3e3e42", activeforeground="#ffffff",
                             relief=tk.FLAT, bd=0)
        layout_menu.add_command(label="Sidebar: Left", command=lambda: self.change_sidebar_position('left'))
        layout_menu.add_command(label="Sidebar: Right", command=lambda: self.change_sidebar_position('right'))
        layout_menu.add_separator()
        layout_menu.add_command(label="Save Current Layout", command=self.save_layout)
        layout_menu.add_command(label="Load Layout", command=self.load_layout)
        view_menu.add_cascade(label="Layout", menu=layout_menu)
        
        view_menu.add_separator()
        view_menu.add_command(label="Zoom In", command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="Zoom Out", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="Reset Zoom", command=self.reset_zoom, accelerator="Ctrl+0")
        
        def show_view_menu(e):
            view_menu.post(e.widget.winfo_rootx(), e.widget.winfo_rooty() + e.widget.winfo_height())
        view_btn.bind("<Button-1>", show_view_menu)
        view_btn.bind("<Enter>", lambda e: view_btn.config(bg="#3e3e42"))
        view_btn.bind("<Leave>", lambda e: view_btn.config(bg="#2d2d30"))
        
        # Help menu
        help_btn = tk.Label(menu_buttons_frame, text="Help", bg="#2d2d30", fg="#cccccc",
                           font=("Segoe UI", 9), padx=10, cursor="hand2")
        help_btn.pack(side=tk.LEFT)
        
        help_menu = tk.Menu(help_btn, tearoff=0, bg="#2d2d30", fg="#cccccc",
                           activebackground="#3e3e42", activeforeground="#ffffff",
                           relief=tk.FLAT, bd=0)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label="Settings", command=self.show_settings, accelerator="Ctrl+,")
        help_menu.add_separator()
        help_menu.add_command(label="About CodeForge", command=self.show_about)
        
        def show_help_menu(e):
            help_menu.post(e.widget.winfo_rootx(), e.widget.winfo_rooty() + e.widget.winfo_height())
        help_btn.bind("<Button-1>", show_help_menu)
        help_btn.bind("<Enter>", lambda e: help_btn.config(bg="#3e3e42"))
        help_btn.bind("<Leave>", lambda e: help_btn.config(bg="#2d2d30"))
        
        # Main paned window
        main_container = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Sidebar frame
        sidebar_frame = tk.Frame(main_container, bg=self.sidebar_bg, width=250)
        main_container.add(sidebar_frame, weight=0)
        
        # Sidebar header
        sidebar_header = tk.Frame(sidebar_frame, bg=self.sidebar_bg)
        sidebar_header.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(sidebar_header, text="EXPLORER", bg=self.sidebar_bg, fg=self.fg_color, 
                font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        
        open_folder_btn = tk.Button(sidebar_header, text="📂", command=self.open_folder, 
                 bg=self.sidebar_bg, fg=self.fg_color, relief=tk.FLAT, 
                 cursor="hand2", font=("Segoe UI", 11), bd=0, padx=5)
        open_folder_btn.pack(side=tk.RIGHT)
        open_folder_btn.bind("<Enter>", lambda e: open_folder_btn.config(bg="#2a2d2e"))
        open_folder_btn.bind("<Leave>", lambda e: open_folder_btn.config(bg=self.sidebar_bg))
        
        # File tree with autohide scrollbar
        tree_frame = tk.Frame(sidebar_frame, bg=self.sidebar_bg)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tree_scroll = ttk.Scrollbar(tree_frame, style="Vertical.TScrollbar")
        
        self.tree = ttk.Treeview(tree_frame, show="tree", 
                                 yscrollcommand=lambda *args: self.on_tree_scroll(*args))
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree_scroll.config(command=self.tree.yview)
        
        self.tree.bind("<Double-Button-1>", self.on_tree_double_click)
        self.tree.bind("<<TreeviewOpen>>", self.on_tree_expand)
        
        # Store tree frame reference
        self.tree_frame = tree_frame
        
        # Right side container
        right_frame = tk.Frame(main_container, bg=self.bg_color)
        main_container.add(right_frame, weight=1)
        
        # Tab bar
        self.tab_frame = tk.Frame(right_frame, bg="#2d2d30", height=35)
        self.tab_frame.pack(fill=tk.X)
        self.tab_frame.pack_propagate(False)
        
        # Text editor
        editor_frame = tk.Frame(right_frame, bg=self.editor_bg)
        editor_frame.pack(fill=tk.BOTH, expand=True)
        
        # Minimap frame (right side)
        minimap_frame = tk.Frame(editor_frame, bg="#1a1a1a", width=100)
        minimap_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Minimap canvas with scrollbar
        self.minimap = tk.Canvas(minimap_frame, width=100, bg="#1a1a1a", 
                                highlightthickness=0, cursor="hand2")
        self.minimap.pack(fill=tk.BOTH, expand=True)
        self.minimap.bind("<Button-1>", self.minimap_click)
        self.minimap.bind("<B1-Motion>", self.minimap_click)
        self.minimap.bind("<MouseWheel>", self.on_minimap_scroll)
        
        # Show/hide minimap toggle
        self.minimap_visible = True
        
        # Vertical scrollbar for both line numbers and text (autohide)
        self.v_scroll = ttk.Scrollbar(editor_frame, style="Vertical.TScrollbar")
        
        # Line numbers
        self.line_numbers = tk.Text(editor_frame, width=4, padx=5, takefocus=0, border=0,
                                    bg="#1e1e1e", fg="#858585", state="disabled",
                                    font=("Consolas", 11), wrap=tk.NONE,
                                    yscrollcommand=lambda *args: self.on_text_scroll(*args, 'v'))
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # Main text area
        self.text_area = tk.Text(editor_frame, wrap=tk.NONE, undo=True, maxundo=-1,
                                 bg=self.editor_bg, fg=self.editor_fg,
                                 insertbackground=self.fg_color,
                                 selectbackground="#264f78",
                                 font=("Consolas", 11),
                                 relief=tk.FLAT,
                                 yscrollcommand=lambda *args: self.on_text_scroll(*args, 'v'),
                                 xscrollcommand=lambda *args: self.on_text_scroll(*args, 'h'),
                                 padx=5, pady=5,
                                 autoseparators=True)  # Better undo/redo performance
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Horizontal scrollbar (autohide)
        self.h_scroll = ttk.Scrollbar(right_frame, orient=tk.HORIZONTAL, style="Horizontal.TScrollbar")
        self.h_scroll.config(command=self.text_area.xview)
        
        # Configure vertical scrollbar to scroll both text and line numbers
        def on_scroll(*args):
            self.text_area.yview(*args)
            self.line_numbers.yview(*args)
        
        self.v_scroll.config(command=on_scroll)
        
        # Store reference to editor frame for scrollbar management
        self.editor_frame = editor_frame
        self.right_frame = right_frame
        
        # Terminal panel (hidden by default)
        self.terminal_frame = tk.Frame(right_frame, bg="#1a1a1a", height=200)
        self.terminal_visible = False
        
        terminal_header = tk.Frame(self.terminal_frame, bg="#2d2d30", height=30)
        terminal_header.pack(fill=tk.X)
        terminal_header.pack_propagate(False)
        
        tk.Label(terminal_header, text="TERMINAL", bg="#2d2d30", fg=self.fg_color,
                font=("Segoe UI", 9, "bold"), padx=10).pack(side=tk.LEFT)
        
        tk.Button(terminal_header, text="Clear", command=self.clear_terminal,
                 bg="#2d2d30", fg=self.fg_color, relief=tk.FLAT, cursor="hand2",
                 font=("Segoe UI", 8)).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(terminal_header, text="×", command=self.toggle_terminal,
                 bg="#2d2d30", fg=self.fg_color, relief=tk.FLAT, cursor="hand2",
                 font=("Segoe UI", 12, "bold")).pack(side=tk.RIGHT)
        
        # Terminal output area
        terminal_content = tk.Frame(self.terminal_frame, bg="#1a1a1a")
        terminal_content.pack(fill=tk.BOTH, expand=True)
        
        term_scroll = ttk.Scrollbar(terminal_content, style="Vertical.TScrollbar")
        term_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.terminal_output = tk.Text(terminal_content, 
                                       bg="#1a1a1a", 
                                       fg="#cccccc",
                                       font=("Consolas", 10),
                                       relief=tk.FLAT,
                                       yscrollcommand=term_scroll.set,
                                       wrap=tk.WORD)
        self.terminal_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        term_scroll.config(command=self.terminal_output.yview)
        
        # Terminal input area
        input_frame = tk.Frame(self.terminal_frame, bg="#1a1a1a")
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(input_frame, text="$", bg="#1a1a1a", fg="#4ec9b0",
                font=("Consolas", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        
        self.terminal_input = tk.Entry(input_frame,
                                       bg="#2d2d30",
                                       fg="#cccccc",
                                       font=("Consolas", 10),
                                       insertbackground="#cccccc",
                                       relief=tk.FLAT)
        self.terminal_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.terminal_input.bind("<Return>", self.execute_command)
        self.terminal_input.bind("<Up>", self.terminal_history_up)
        self.terminal_input.bind("<Down>", self.terminal_history_down)
        
        # Command history
        self.command_history = []
        self.history_index = -1
        
        # Status bar with more info
        status_frame = tk.Frame(self.root, bg="#007acc")
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_bar = tk.Label(status_frame, text="Ready", anchor=tk.W,
                                   bg="#007acc", fg="white", padx=10, pady=3,
                                   font=("Segoe UI", 9))
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.cursor_pos = tk.Label(status_frame, text="Ln 1, Col 1", anchor=tk.E,
                                   bg="#007acc", fg="white", padx=10, pady=3,
                                   font=("Segoe UI", 9))
        self.cursor_pos.pack(side=tk.RIGHT)
        
        # Welcome message
        self.text_area.insert("1.0", "# Welcome to CodeForge\n# Press Ctrl+O to open a file or Ctrl+N for a new file")
        self.text_area.tag_add("center", "1.0", "end")
        
        # Track if window is maximized
        self.is_maximized = False
        self.restore_geometry = None
        
    def setup_bindings(self):
        # Keyboard shortcuts
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_file_as())
        self.root.bind("<Control-f>", lambda e: self.show_find_dialog())
        # Ctrl+` binding removed due to cross-platform issues - use View menu instead
        
        # New enhanced shortcuts
        self.root.bind("<Control-/>", lambda e: self.toggle_comment())  # Ctrl+/
        self.root.bind("<Control-d>", lambda e: self.duplicate_line())  # Ctrl+D
        self.root.bind("<Control-w>", lambda e: self.close_current_tab())  # Ctrl+W
        self.root.bind("<Alt-Up>", lambda e: self.move_line_up())  # Alt+Up
        self.root.bind("<Alt-Down>", lambda e: self.move_line_down())  # Alt+Down
        self.root.bind("<Control-Alt-Up>", lambda e: self.add_cursor_above())  # Ctrl+Alt+Up
        self.root.bind("<Control-Alt-Down>", lambda e: self.add_cursor_below())  # Ctrl+Alt+Down
        self.root.bind("<Control-g>", lambda e: self.show_goto_line_dialog())  # Ctrl+G
        self.root.bind("<Control-h>", lambda e: self.show_replace_dialog())  # Ctrl+H
        self.root.bind("<Control-comma>", lambda e: self.show_settings())  # Ctrl+,
        # Zoom bindings - use = key (same as +) and Shift+= for cross-platform compatibility
        self.root.bind("<Control-equal>", lambda e: self.zoom_in())  # Ctrl+=
        self.root.bind("<Control-Shift-equal>", lambda e: self.zoom_in())  # Ctrl+Shift+= (Ctrl++)
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())  # Ctrl++ (alternate)
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())  # Ctrl+-
        self.root.bind("<Control-Key-0>", lambda e: self.reset_zoom())  # Ctrl+0
        
        # Track changes
        self.text_area.bind("<<Modified>>", self.on_text_modified)
        self.text_area.bind("<KeyRelease>", lambda e: (self.update_line_numbers(), self.update_cursor_position(), self.highlight_syntax(), self.highlight_matching_bracket(), self.update_minimap(), self.highlight_current_line()))
        self.text_area.bind("<Button-1>", lambda e: (self.update_cursor_position(e), self.highlight_matching_bracket(), self.highlight_current_line()))
        self.text_area.bind("<Configure>", lambda e: (self.update_line_numbers(), self.update_minimap()))
        
        # Auto-indent on Enter
        self.text_area.bind("<Return>", self.auto_indent)
        
        # Auto-complete brackets (handle < and > separately due to tkinter event syntax)
        for opener in ['(', '[', '{']:
            self.text_area.bind(opener, lambda e, o=opener: self.auto_complete_bracket(e, o))
        self.text_area.bind("<less>", lambda e: self.auto_complete_bracket(e, '<'))
        self.text_area.bind("<greater>", lambda e: self.auto_complete_bracket(e, '>'))
        
        # Auto-close quotes
        for quote in ['"', "'"]:
            self.text_area.bind(quote, lambda e, q=quote: self.auto_complete_quote(e, q))
        
        # Backspace to remove matching bracket
        self.text_area.bind("<BackSpace>", self.smart_backspace)
        
        # Sync line numbers when scrolling
        self.text_area.bind("<MouseWheel>", self.on_mousewheel)
        self.line_numbers.bind("<MouseWheel>", self.on_mousewheel)
        
        # Update line numbers initially
        self.update_line_numbers()
        self.update_cursor_position()
    
    def auto_indent(self, event):
        """Auto-indent on Enter key"""
        # Get current line
        line_num = self.text_area.index(tk.INSERT).split('.')[0]
        line = self.text_area.get(f"{line_num}.0", f"{line_num}.end")
        
        # Calculate indentation
        indent = len(line) - len(line.lstrip())
        indent_str = line[:indent]
        
        # Check if line ends with colon (Python) or opening bracket
        stripped = line.rstrip()
        if stripped.endswith(':') or stripped.endswith('{') or stripped.endswith('[') or stripped.endswith('('):
            indent_str += "    "  # Add extra indent
        
        # Insert newline and indentation
        self.text_area.insert(tk.INSERT, f"\n{indent_str}")
        return "break"
    
    def auto_complete_bracket(self, event, opener):
        """Auto-complete matching bracket"""
        closer = self.matching_pairs[opener]
        
        # Check if there's a selection
        try:
            sel_start = self.text_area.index(tk.SEL_FIRST)
            sel_end = self.text_area.index(tk.SEL_LAST)
            selected_text = self.text_area.get(sel_start, sel_end)
            
            # Wrap selection with brackets
            self.text_area.delete(sel_start, sel_end)
            self.text_area.insert(sel_start, f"{opener}{selected_text}{closer}")
            self.text_area.mark_set(tk.INSERT, f"{sel_start}+{len(selected_text) + 1}c")
            return "break"
        except tk.TclError:
            # No selection, just insert bracket pair
            self.text_area.insert(tk.INSERT, opener + closer)
            self.text_area.mark_set(tk.INSERT, f"{tk.INSERT}-1c")
            return "break"
    
    def auto_complete_quote(self, event, quote):
        """Auto-complete matching quote"""
        # Check if there's a selection
        try:
            sel_start = self.text_area.index(tk.SEL_FIRST)
            sel_end = self.text_area.index(tk.SEL_LAST)
            selected_text = self.text_area.get(sel_start, sel_end)
            
            # Wrap selection with quotes
            self.text_area.delete(sel_start, sel_end)
            self.text_area.insert(sel_start, f"{quote}{selected_text}{quote}")
            self.text_area.mark_set(tk.INSERT, f"{sel_start}+{len(selected_text) + 1}c")
            return "break"
        except tk.TclError:
            # Check if next character is the same quote (to skip it)
            next_char = self.text_area.get(tk.INSERT, f"{tk.INSERT}+1c")
            if next_char == quote:
                self.text_area.mark_set(tk.INSERT, f"{tk.INSERT}+1c")
                return "break"
            
            # Insert quote pair
            self.text_area.insert(tk.INSERT, quote + quote)
            self.text_area.mark_set(tk.INSERT, f"{tk.INSERT}-1c")
            return "break"
    
    def smart_backspace(self, event):
        """Smart backspace to remove matching brackets/quotes"""
        # Get characters around cursor
        prev_char = self.text_area.get(f"{tk.INSERT}-1c", tk.INSERT)
        next_char = self.text_area.get(tk.INSERT, f"{tk.INSERT}+1c")
        
        # Check if we're between matching brackets or quotes
        if (prev_char in self.matching_pairs and next_char == self.matching_pairs[prev_char]) or \
           (prev_char in ['"', "'", '`'] and prev_char == next_char):
            # Delete both characters
            self.text_area.delete(f"{tk.INSERT}-1c", f"{tk.INSERT}+1c")
            return "break"
        
        return None  # Allow normal backspace
    
    def highlight_matching_bracket(self):
        """Highlight matching bracket at cursor position"""
        # Remove previous highlighting
        self.text_area.tag_remove("match_bracket", "1.0", "end")
        
        # Get character at cursor
        cursor_pos = self.text_area.index(tk.INSERT)
        char_before = self.text_area.get(f"{cursor_pos}-1c", cursor_pos)
        char_after = self.text_area.get(cursor_pos, f"{cursor_pos}+1c")
        
        # Check character before cursor
        if char_before in self.matching_pairs:
            self.find_matching_bracket(f"{cursor_pos}-1c", char_before, self.matching_pairs[char_before], 1)
        elif char_before in self.closing_pairs:
            self.find_matching_bracket(f"{cursor_pos}-1c", char_before, self.closing_pairs[char_before], -1)
        
        # Check character after cursor
        if char_after in self.matching_pairs:
            self.find_matching_bracket(cursor_pos, char_after, self.matching_pairs[char_after], 1)
        elif char_after in self.closing_pairs:
            self.find_matching_bracket(cursor_pos, char_after, self.closing_pairs[char_after], -1)
    
    def find_matching_bracket(self, start_pos, open_char, close_char, direction):
        """Find and highlight matching bracket"""
        content = self.text_area.get("1.0", "end-1c")
        start_index = len(self.text_area.get("1.0", start_pos))
        
        count = 0
        i = start_index
        
        while 0 <= i < len(content):
            if content[i] == open_char:
                count += 1
            elif content[i] == close_char:
                count -= 1
                
            if count == 0 and i != start_index:
                # Found matching bracket
                match_pos = f"1.0+{i}c"
                self.text_area.tag_add("match_bracket", start_pos, f"{start_pos}+1c")
                self.text_area.tag_add("match_bracket", match_pos, f"{match_pos}+1c")
                self.text_area.tag_config("match_bracket", background="#515c6a", foreground="#ffff00")
                break
                
            i += direction
    
    def toggle_comment(self):
        """Toggle line comment for selected lines"""
        if not self.current_file:
            return
        
        # Get comment symbol based on file extension
        ext = self.current_file.split('.')[-1].lower() if '.' in self.current_file else ''
        comment_symbols = {
            'py': '#',
            'js': '//',
            'ts': '//',
            'java': '//',
            'c': '//',
            'cpp': '//',
            'cs': '//',
            'html': '<!--',
            'css': '/*',
        }
        
        comment = comment_symbols.get(ext, '#')
        
        try:
            # Get selected range
            start_line = int(self.text_area.index(tk.SEL_FIRST).split('.')[0])
            end_line = int(self.text_area.index(tk.SEL_LAST).split('.')[0])
        except tk.TclError:
            # No selection, use current line
            start_line = end_line = int(self.text_area.index(tk.INSERT).split('.')[0])
        
        # Check if all lines are commented
        all_commented = True
        for line_num in range(start_line, end_line + 1):
            line = self.text_area.get(f"{line_num}.0", f"{line_num}.end")
            if line.strip() and not line.lstrip().startswith(comment):
                all_commented = False
                break
        
        # Toggle comments
        for line_num in range(start_line, end_line + 1):
            line = self.text_area.get(f"{line_num}.0", f"{line_num}.end")
            if all_commented:
                # Remove comment
                if line.lstrip().startswith(comment):
                    indent = len(line) - len(line.lstrip())
                    new_line = line[:indent] + line[indent:].lstrip()[len(comment):].lstrip()
                    self.text_area.delete(f"{line_num}.0", f"{line_num}.end")
                    self.text_area.insert(f"{line_num}.0", new_line)
            else:
                # Add comment
                if line.strip():  # Only comment non-empty lines
                    indent = len(line) - len(line.lstrip())
                    new_line = line[:indent] + comment + ' ' + line[indent:]
                    self.text_area.delete(f"{line_num}.0", f"{line_num}.end")
                    self.text_area.insert(f"{line_num}.0", new_line)
        
        return "break"
    
    def duplicate_line(self):
        """Duplicate current line or selection"""
        try:
            # Check if there's a selection
            sel_start = self.text_area.index(tk.SEL_FIRST)
            sel_end = self.text_area.index(tk.SEL_LAST)
            selected_text = self.text_area.get(sel_start, sel_end)
            
            # Duplicate selection
            self.text_area.insert(sel_end, selected_text)
        except tk.TclError:
            # No selection, duplicate current line
            line_num = self.text_area.index(tk.INSERT).split('.')[0]
            line = self.text_area.get(f"{line_num}.0", f"{line_num}.end")
            self.text_area.insert(f"{line_num}.end", f"\n{line}")
        
        return "break"
    
    def move_line_up(self):
        """Move current line up"""
        line_num = int(self.text_area.index(tk.INSERT).split('.')[0])
        
        if line_num > 1:
            # Get current and previous line
            current_line = self.text_area.get(f"{line_num}.0", f"{line_num}.end")
            prev_line = self.text_area.get(f"{line_num-1}.0", f"{line_num-1}.end")
            
            # Swap lines
            self.text_area.delete(f"{line_num-1}.0", f"{line_num}.end")
            self.text_area.insert(f"{line_num-1}.0", f"{current_line}\n{prev_line}")
            
            # Move cursor
            self.text_area.mark_set(tk.INSERT, f"{line_num-1}.0")
        
        return "break"
    
    def move_line_down(self):
        """Move current line down"""
        line_num = int(self.text_area.index(tk.INSERT).split('.')[0])
        last_line = int(self.text_area.index('end-1c').split('.')[0])
        
        if line_num < last_line:
            # Get current and next line
            current_line = self.text_area.get(f"{line_num}.0", f"{line_num}.end")
            next_line = self.text_area.get(f"{line_num+1}.0", f"{line_num+1}.end")
            
            # Swap lines
            self.text_area.delete(f"{line_num}.0", f"{line_num+1}.end")
            self.text_area.insert(f"{line_num}.0", f"{next_line}\n{current_line}")
            
            # Move cursor
            self.text_area.mark_set(tk.INSERT, f"{line_num+1}.0")
        
        return "break"
    
    def add_cursor_above(self):
        """Add cursor/selection above (simplified multi-cursor)"""
        # This is a simplified version - just selects the same word above
        try:
            current_word = self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            line_num = int(self.text_area.index(tk.SEL_FIRST).split('.')[0])
            
            if line_num > 1:
                # Search for same word in line above
                prev_line = self.text_area.get(f"{line_num-1}.0", f"{line_num-1}.end")
                if current_word in prev_line:
                    start_col = prev_line.index(current_word)
                    self.text_area.tag_add("sel", f"{line_num-1}.{start_col}", 
                                          f"{line_num-1}.{start_col + len(current_word)}")
        except tk.TclError:
            pass
        
        return "break"
    
    def add_cursor_below(self):
        """Add cursor/selection below (simplified multi-cursor)"""
        try:
            current_word = self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            line_num = int(self.text_area.index(tk.SEL_LAST).split('.')[0])
            last_line = int(self.text_area.index('end-1c').split('.')[0])
            
            if line_num < last_line:
                # Search for same word in line below
                next_line = self.text_area.get(f"{line_num+1}.0", f"{line_num+1}.end")
                if current_word in next_line:
                    start_col = next_line.index(current_word)
                    self.text_area.tag_add("sel", f"{line_num+1}.{start_col}", 
                                          f"{line_num+1}.{start_col + len(current_word)}")
        except tk.TclError:
            pass
        
        return "break"
    
    def schedule_auto_save(self):
        """Schedule auto-save"""
        if self.auto_save_enabled and self.current_file:
            file_info = self.open_files.get(self.current_file)
            if file_info and file_info.get("path") and file_info.get("modified"):
                self.save_file()
                self.status_bar.config(text=f"Auto-saved: {file_info['path']}")
        
        # Schedule next auto-save
        self.root.after(self.auto_save_interval, self.schedule_auto_save)
    
    def add_to_recent_files(self, filepath):
        """Add file to recent files list"""
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        self.recent_files.insert(0, filepath)
        
        # Keep only max recent files
        if len(self.recent_files) > self.max_recent_files:
            self.recent_files = self.recent_files[:self.max_recent_files]
    
    def clear_recent_files(self):
        """Clear the recent files list"""
        self.recent_files = []
        self.update_recent_files_menu()
    
    def update_minimap(self):
        """Update the minimap with code overview"""
        if not self.minimap_visible:
            return
        
        try:
            self.minimap.delete("all")
            
            content = self.text_area.get("1.0", "end-1c")
            lines = content.split('\n')
            
            if not lines:
                return
            
            # Calculate minimap dimensions
            canvas_height = self.minimap.winfo_height()
            canvas_width = self.minimap.winfo_width()
            
            if canvas_height <= 1 or canvas_width <= 1:
                return
            
            total_lines = len(lines)
            
            # Fixed 2 pixels per line + 1 pixel gap
            line_height = 2
            line_gap = 1
            pixels_per_line = line_height + line_gap
            
            # Calculate total minimap content height
            minimap_content_height = total_lines * pixels_per_line
            
            # Configure scroll region for the canvas
            self.minimap.configure(scrollregion=(0, 0, canvas_width, minimap_content_height))
            
            # Get current scroll position of text area
            first_visible_line = 1
            scroll_fraction = 0
            try:
                first_visible_line = float(self.text_area.index("@0,0").split('.')[0])
                last_line = float(self.text_area.index('end-1c').split('.')[0])
                
                # Calculate scroll position as fraction
                if last_line > 1:
                    scroll_fraction = (first_visible_line - 1) / (last_line - 1)
                
                # Scroll minimap to match text area
                if minimap_content_height > canvas_height:
                    scroll_y = scroll_fraction * (minimap_content_height - canvas_height)
                    self.minimap.yview_moveto(scroll_y / minimap_content_height)
            except:
                pass
            
            # Only draw visible lines for performance (with buffer)
            visible_start = max(0, int(first_visible_line) - 50)
            visible_end = min(total_lines, int(first_visible_line) + 200)
            
            # Draw minimap with character-level detail
            for i in range(visible_start, visible_end):
                line = lines[i]
                y = i * pixels_per_line
                
                # Skip empty lines (just leave the gap)
                if not line.strip():
                    continue
                
                # Draw background for the line based on indentation
                indent_level = len(line) - len(line.lstrip())
                
                # Determine base color based on content type
                stripped = line.lstrip()
                if stripped.startswith('#') or stripped.startswith('//'):
                    base_color = (106, 153, 85)  # Green for comments
                elif any(stripped.startswith(kw) for kw in ['def ', 'class ', 'function ', 'public ', 'private ', 'async ', 'const ', 'let ', 'var ']):
                    base_color = (220, 220, 170)  # Yellow for definitions
                elif any(kw in stripped for kw in ['import ', 'from ', 'include ', 'using ']):
                    base_color = (78, 201, 176)  # Cyan for imports
                elif any(stripped.startswith(kw) for kw in ['if ', 'else', 'for ', 'while ', 'switch ', 'case ', 'return ']):
                    base_color = (86, 156, 214)  # Blue for control flow
                else:
                    base_color = (212, 212, 212)  # Light gray for regular code
                
                # Calculate character density (how much of the line is filled)
                line_length = len(line.rstrip())
                max_line_length = 100  # Assumed max visible line length
                char_ratio = min(1.0, line_length / max_line_length)
                
                # Calculate indent offset in pixels
                indent_offset = min(canvas_width // 3, int((indent_level / 4) * (canvas_width / 15)))
                
                # Calculate line width based on content
                content_width = int(char_ratio * (canvas_width - indent_offset))
                
                if content_width > 0:
                    # Draw the line as a single smooth rectangle
                    color = "#{:02x}{:02x}{:02x}".format(
                        int(base_color[0]),
                        int(base_color[1]),
                        int(base_color[2])
                    )
                    
                    self.minimap.create_rectangle(
                        indent_offset, y, indent_offset + content_width, y + line_height,
                        fill=color, outline=""
                    )
            
            # Draw viewport indicator (scaled correctly)
            try:
                first_visible = float(self.text_area.index("@0,0").split('.')[0])
                last_visible = float(self.text_area.index(f"@0,{self.text_area.winfo_height()}").split('.')[0])
                
                viewport_start = (first_visible - 1) * pixels_per_line
                viewport_height = (last_visible - first_visible + 1) * pixels_per_line
                
                # Draw border for viewport (no fill, just outline)
                self.minimap.create_rectangle(
                    0, viewport_start, canvas_width, viewport_start + viewport_height,
                    outline="#569cd6", width=2, fill="", tags="viewport"
                )
            except:
                pass
                
        except Exception as e:
            pass
    
    def on_minimap_scroll(self, event):
        """Handle mouse wheel scrolling on minimap"""
        # Forward scroll to text area
        self.text_area.yview_scroll(int(-1*(event.delta/120)), "units")
        return "break"
    
    def minimap_click(self, event):
        """Handle minimap click to scroll to position"""
        try:
            content = self.text_area.get("1.0", "end-1c")
            lines = content.split('\n')
            
            # Use same calculation as update_minimap
            line_height = 2
            line_gap = 1
            pixels_per_line = line_height + line_gap
            
            # Get the actual y position in canvas coordinates (accounting for scroll)
            canvas_y = self.minimap.canvasy(event.y)
            
            clicked_line = int(canvas_y / pixels_per_line) + 1
            clicked_line = max(1, min(clicked_line, len(lines)))
            
            # Scroll to clicked line
            self.text_area.see(f"{clicked_line}.0")
            self.text_area.mark_set(tk.INSERT, f"{clicked_line}.0")
            self.update_minimap()
        except:
            pass
    
    def toggle_minimap(self):
        """Toggle minimap visibility"""
        self.minimap_visible = not self.minimap_visible
        if self.minimap_visible:
            self.minimap.pack(fill=tk.BOTH, expand=True)
            self.update_minimap()
        else:
            self.minimap.pack_forget()
    
    
    
    
    def on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        # Scroll the text area
        self.text_area.yview_scroll(int(-1*(event.delta/120)), "units")
        # Sync line numbers by updating them
        self.root.after_idle(self.update_line_numbers)
        return "break"
    
    def on_text_scroll(self, first, last, orientation):
        """Handle scrollbar visibility and syncing"""
        first, last = float(first), float(last)
        
        if orientation == 'v':
            # Update scrollbar
            self.v_scroll.set(first, last)
            # Show/hide vertical scrollbar
            if first == 0.0 and last == 1.0:
                self.v_scroll.pack_forget()
            else:
                self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y, in_=self.editor_frame)
                
        elif orientation == 'h':
            # Update scrollbar
            self.h_scroll.set(first, last)
            # Show/hide horizontal scrollbar
            if first == 0.0 and last == 1.0:
                self.h_scroll.pack_forget()
            else:
                self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X, before=self.editor_frame, in_=self.right_frame)
    
    def on_tree_scroll(self, first, last):
        """Handle tree scrollbar visibility"""
        first, last = float(first), float(last)
        
        # Update scrollbar
        self.tree_scroll.set(first, last)
        
        # Show/hide tree scrollbar
        if first == 0.0 and last == 1.0:
            self.tree_scroll.pack_forget()
        else:
            self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y, in_=self.tree_frame)
        
    def highlight_syntax(self):
        """Apply syntax highlighting based on file extension"""
        if not self.current_file:
            return
            
        # Detect language
        ext = self.current_file.split('.')[-1].lower() if '.' in self.current_file else ''
        
        # Remove all existing tags
        for tag in ["keyword", "string", "comment", "function", "number", "class", "builtin", "operator"]:
            self.text_area.tag_remove(tag, "1.0", "end")
        
        content = self.text_area.get("1.0", "end-1c")
        
        if ext == 'py':
            self.highlight_python(content)
        elif ext in ['js', 'ts', 'jsx', 'tsx']:
            self.highlight_javascript(content)
        elif ext in ['java', 'c', 'cpp', 'cs', 'h']:
            self.highlight_c_like(content)
        elif ext == 'html':
            self.highlight_html(content)
    
    def get_compiled_regex(self, pattern, key):
        """Get or compile regex pattern with caching"""
        if key not in self.regex_cache:
            self.regex_cache[key] = re.compile(pattern)
        return self.regex_cache[key]
    
    def highlight_python(self, content):
        """Highlight Python syntax"""
        # Keywords
        keywords = r'\b(def|class|if|elif|else|for|while|try|except|finally|with|as|import|from|return|yield|break|continue|pass|raise|assert|lambda|and|or|not|in|is|True|False|None|async|await)\b'
        pattern = self.get_compiled_regex(keywords, 'py_keywords')
        for match in pattern.finditer(content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("keyword", start, end)
        
        # Built-in functions
        builtins = r'\b(print|len|range|str|int|float|list|dict|set|tuple|open|input|isinstance|type|enumerate|zip|map|filter|sum|min|max|sorted|abs|all|any|bool|bytes|chr|ord|dir|eval|exec|format|hash|help|hex|id|iter|next|object|oct|pow|repr|reversed|round|slice|super|vars)\b'
        pattern = self.get_compiled_regex(builtins, 'py_builtins')
        for match in pattern.finditer(content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("builtin", start, end)
        
        # Strings (single and double quotes, including triple quotes)
        strings = r'(""".*?"""|\'\'\'.*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')'
        for match in re.finditer(strings, content, re.DOTALL):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("string", start, end)
        
        # Comments
        pattern = self.get_compiled_regex(r'#.*?$', 'py_comments')
        for match in pattern.finditer(content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("comment", start, end)
        
        # Numbers
        pattern = self.get_compiled_regex(r'\b\d+\.?\d*\b', 'py_numbers')
        for match in pattern.finditer(content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("number", start, end)
        
        # Function definitions
        pattern = self.get_compiled_regex(r'\bdef\s+(\w+)', 'py_functions')
        for match in pattern.finditer(content):
            start = f"1.0+{match.start(1)}c"
            end = f"1.0+{match.end(1)}c"
            self.text_area.tag_add("function", start, end)
        
        # Class definitions
        pattern = self.get_compiled_regex(r'\bclass\s+(\w+)', 'py_classes')
        for match in pattern.finditer(content):
            start = f"1.0+{match.start(1)}c"
            end = f"1.0+{match.end(1)}c"
            self.text_area.tag_add("class", start, end)
    
    def highlight_javascript(self, content):
        """Highlight JavaScript/TypeScript syntax"""
        # Keywords
        keywords = r'\b(function|const|let|var|if|else|for|while|do|switch|case|break|continue|return|try|catch|finally|throw|new|this|class|extends|import|export|from|default|async|await|yield|typeof|instanceof|delete|void|in|of)\b'
        pattern = self.get_compiled_regex(keywords, 'js_keywords')
        for match in pattern.finditer(content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("keyword", start, end)
        
        # Strings
        pattern = self.get_compiled_regex(r'(`.*?`|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')', 'js_strings')
        for match in pattern.finditer(content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("string", start, end)
        
        # Comments
        pattern = self.get_compiled_regex(r'//.*?$|/\*.*?\*/', 'js_comments')
        for match in pattern.finditer(content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("comment", start, end)
        
        # Numbers
        pattern = self.get_compiled_regex(r'\b\d+\.?\d*\b', 'js_numbers')
        for match in pattern.finditer(content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("number", start, end)
    
    def highlight_c_like(self, content):
        """Highlight C/C++/Java/C# syntax"""
        # Keywords
        keywords = r'\b(if|else|for|while|do|switch|case|break|continue|return|class|struct|enum|public|private|protected|static|void|int|float|double|char|bool|long|short|unsigned|signed|const|new|delete|try|catch|throw|virtual|override|namespace|using|include)\b'
        pattern = self.get_compiled_regex(keywords, 'c_keywords')
        for match in pattern.finditer(content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("keyword", start, end)
        
        # Strings
        pattern = self.get_compiled_regex(r'"(?:[^"\\]|\\.)*"', 'c_strings')
        for match in pattern.finditer(content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("string", start, end)
        
        # Comments
        pattern = self.get_compiled_regex(r'//.*?$|/\*.*?\*/', 'c_comments')
        for match in pattern.finditer(content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("comment", start, end)
        
        # Numbers
        pattern = self.get_compiled_regex(r'\b\d+\.?\d*\b', 'c_numbers')
        for match in pattern.finditer(content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("number", start, end)
    
    def highlight_html(self, content):
        """Highlight HTML syntax"""
        # Tags
        pattern = self.get_compiled_regex(r'</?[\w\-]+[^>]*>', 'html_tags')
        for match in pattern.finditer(content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("keyword", start, end)
        
        # Comments
        for match in re.finditer(r'<!--.*?-->', content, re.DOTALL):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("comment", start, end)
        
        # Strings in attributes
        for match in re.finditer(r'"[^"]*"|\'[^\']*\'', content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("string", start, end)
    
    def highlight_current_line(self):
        """Highlight the current line"""
        # Remove previous highlight
        self.text_area.tag_remove("current_line", "1.0", "end")
        
        # Add highlight to current line
        current_line = self.text_area.index(tk.INSERT).split('.')[0]
        self.text_area.tag_add("current_line", f"{current_line}.0", f"{current_line}.end+1c")
        
        # Make sure current_line tag has lower priority than syntax tags
        self.text_area.tag_lower("current_line")
    
    def update_cursor_position(self, event=None):
        """Update cursor position in status bar"""
        cursor_pos = self.text_area.index(tk.INSERT)
        line, col = cursor_pos.split(".")
        self.cursor_pos.config(text=f"Ln {line}, Col {int(col) + 1}")
        
    def update_line_numbers(self, event=None):
        """Update line numbers efficiently"""
        try:
            self.line_numbers.config(state="normal")
            self.line_numbers.delete("1.0", "end")
            
            # Get total line count
            line_count = int(self.text_area.index('end-1c').split('.')[0])
            
            # Create line numbers string more efficiently
            if line_count < 1000:
                line_numbers_string = "\n".join(str(i) for i in range(1, line_count + 1))
            else:
                # For large files, use list comprehension and join (faster)
                line_numbers_string = "\n".join(map(str, range(1, line_count + 1)))
            
            self.line_numbers.insert("1.0", line_numbers_string)
            
            # Scroll line numbers to match text area
            self.line_numbers.yview_moveto(self.text_area.yview()[0])
            
            self.line_numbers.config(state="disabled")
        except:
            pass
        
    def on_text_modified(self, event=None):
        if self.current_file and self.text_area.edit_modified():
            self.update_tab_modified(self.current_file, True)
            self.text_area.edit_modified(False)
    
    def close_current_tab(self):
        """Close the currently active tab"""
        if self.current_file:
            self.close_file(self.current_file)
        return "break"
            
    def new_file(self):
        count = len([f for f in self.open_files.keys() if f.startswith("Untitled")])
        filename = f"Untitled-{count + 1}" if count > 0 else "Untitled"
        
        self.open_files[filename] = {
            "path": None,
            "content": "",
            "modified": False
        }
        
        self.switch_to_file(filename)
        self.update_tabs()
        self.highlight_syntax()  # Apply syntax highlighting
        self.update_title()  # Update title bar
        
    def open_file(self):
        filetypes = (
            ("All Files", "*.*"),
            ("Text Files", "*.txt"),
            ("Python Files", "*.py"),
            ("JavaScript Files", "*.js"),
            ("Java Files", "*.java"),
            ("C/C++ Files", "*.c *.cpp *.h"),
        )
        
        filename = filedialog.askopenfilename(
            title="Open File",
            filetypes=filetypes
        )
        
        if filename:
            self.load_file(filename)
            
    def load_file(self, filepath):
        try:
            # Use buffered reading for better performance
            with open(filepath, "r", encoding="utf-8", buffering=8192) as f:
                content = f.read()
            
            filename = os.path.basename(filepath)
            self.open_files[filename] = {
                "path": filepath,
                "content": content,
                "modified": False
            }
            
            self.switch_to_file(filename)
            self.update_tabs()
            self.status_bar.config(text=f"Opened: {filepath}")
            self.highlight_syntax()  # Apply syntax highlighting
            self.update_title()  # Update title bar
            
            # Add to recent files
            self.add_to_recent_files(filepath)
            self.update_recent_files_menu()
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {str(e)}")
    
    def update_recent_files_menu(self):
        """Update the recent files menu"""
        self.recent_menu.delete(0, tk.END)
        
        if not self.recent_files:
            self.recent_menu.add_command(label="No recent files", state="disabled")
        else:
            for filepath in self.recent_files:
                display_name = os.path.basename(filepath)
                self.recent_menu.add_command(
                    label=f"{display_name} - {filepath}",
                    command=lambda p=filepath: self.load_file(p)
                )
            
            self.recent_menu.add_separator()
            self.recent_menu.add_command(label="Clear Recent Files", 
                                        command=self.clear_recent_files)
            
    def save_file(self):
        """Save file with memory optimization"""
        if not self.current_file:
            return
            
        file_info = self.open_files[self.current_file]
        
        if file_info["path"] is None:
            self.save_file_as()
            return
            
        try:
            content = self.text_area.get("1.0", "end-1c")
            with open(file_info["path"], "w", encoding="utf-8", buffering=8192) as f:
                f.write(content)
            
            file_info["content"] = content
            file_info["modified"] = False
            self.update_tab_modified(self.current_file, False)
            self.status_bar.config(text=f"Saved: {file_info['path']}")
            
            # Clear content hash to force re-highlight on next edit
            self.last_content_hash = None
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file: {str(e)}")
            
    def save_file_as(self):
        if not self.current_file:
            return
            
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=(("All Files", "*.*"), ("Text Files", "*.txt"))
        )
        
        if filepath:
            try:
                content = self.text_area.get("1.0", "end-1c")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                
                # Update file info
                old_name = self.current_file
                new_name = os.path.basename(filepath)
                
                self.open_files[new_name] = {
                    "path": filepath,
                    "content": content,
                    "modified": False
                }
                
                if old_name != new_name:
                    del self.open_files[old_name]
                
                self.current_file = new_name
                self.update_tabs()
                self.status_bar.config(text=f"Saved: {filepath}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {str(e)}")
                
    def open_folder(self):
        folder = filedialog.askdirectory(title="Open Folder")
        
        if folder:
            self.current_folder = folder
            self.populate_tree(folder)
            self.status_bar.config(text=f"Opened folder: {folder}")
            
    def populate_tree(self, path):
        self.tree.delete(*self.tree.get_children())
        
        node = self.tree.insert("", "end", text=os.path.basename(path), open=True, 
                               values=[path])
        self.populate_tree_node(node, path)
        
    def populate_tree_node(self, parent, path):
        """Populate tree node with lazy loading for better performance"""
        try:
            items = os.listdir(path)
            
            # Separate folders and files efficiently
            folders = []
            files = []
            for item in items:
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    folders.append(item)
                elif os.path.isfile(item_path):
                    files.append(item)
            
            folders.sort()
            files.sort()
            
            # Add folders first
            for item in folders:
                if item.startswith('.') or item == '__pycache__':
                    continue
                item_path = os.path.join(path, item)
                node = self.tree.insert(parent, "end", text=f"📁 {item}", values=[item_path])
                # Add dummy child to show expand arrow
                try:
                    # Check if folder has contents
                    if os.listdir(item_path):
                        self.tree.insert(node, "end", text="")  # Dummy node
                except (PermissionError, OSError):
                    pass
                
            # Then add files
            for item in files:
                if item.startswith('.'):
                    continue
                item_path = os.path.join(path, item)
                self.tree.insert(parent, "end", text=f"📄 {item}", values=[item_path])
                
        except (PermissionError, OSError) as e:
            pass
    
    def on_tree_expand(self, event):
        item = self.tree.selection()
        if not item:
            return
            
        item = item[0]
        children = self.tree.get_children(item)
        
        # Check if we need to populate
        if children and len(children) == 1:
            first_child = self.tree.item(children[0])
            if not first_child["text"]:  # It's a dummy node
                values = self.tree.item(item, "values")
                if values:
                    item_path = values[0]
                    # Remove dummy
                    self.tree.delete(children[0])
                    # Populate
                    self.populate_tree_node(item, item_path)
            
    def on_tree_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return
            
        item = selection[0]
        values = self.tree.item(item, "values")
        if not values:
            return
            
        item_path = values[0]
        
        if os.path.isfile(item_path):
            self.load_file(item_path)
        elif os.path.isdir(item_path):
            # Expand/collapse folder
            children = self.tree.get_children(item)
            if children:
                # Check if it's just the dummy node
                first_child = self.tree.item(children[0])
                if not first_child["text"]:  # It's a dummy
                    # Clear dummy and populate
                    for child in children:
                        self.tree.delete(child)
                    self.populate_tree_node(item, item_path)
                else:
                    # Already populated, just toggle
                    for child in children:
                        self.tree.delete(child)
                    # Add dummy back for next expand
                    self.tree.insert(item, "end")
                
    def switch_to_file(self, filename):
        if filename not in self.open_files:
            return
            
        # Save current file content
        if self.current_file:
            self.open_files[self.current_file]["content"] = self.text_area.get("1.0", "end-1c")
        
        # Switch to new file
        self.current_file = filename
        file_info = self.open_files[filename]
        
        # Reset content hash for new file
        self.last_content_hash = None
        
        # Disable undo/redo temporarily for better performance during file switch
        self.text_area.config(undo=False)
        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", file_info["content"])
        self.text_area.config(undo=True)
        
        self.update_tabs()
        self.update_line_numbers()
        self.highlight_syntax()  # Apply syntax highlighting
        self.update_minimap()  # Update minimap
        self.update_title()  # Update title bar
        
    def update_title(self):
        """Update the title bar with current file name"""
        if self.current_file:
            file_info = self.open_files.get(self.current_file)
            if file_info and file_info.get('path'):
                title = f"CodeForge - v{version} | {self.current_file}"
            else:
                title = f"CodeForge - v{version} | {self.current_file}"
            
            # Update status bar
            if file_info.get("path"):
                self.status_bar.config(text=file_info["path"])
            else:
                self.status_bar.config(text=self.current_file or "New File")
        else:
            title = f"CodeForge - v{version}"
            self.status_bar.config(text="Ready")
        
        self.title_label.config(text=title)
            
    def close_file(self, filename):
        """Close file with memory cleanup"""
        if filename not in self.open_files:
            return
            
        file_info = self.open_files[filename]
        
        # Check if modified
        if file_info["modified"]:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                f"Do you want to save changes to {filename}?"
            )
            if response is None:  # Cancel
                return
            elif response:  # Yes
                self.save_file()
        
        # Clean up memory
        del self.open_files[filename]
        if len(self.open_files) == 0:
            # Clear regex cache when all files closed
            self.regex_cache.clear()
            gc.collect()
        
        # Switch to another file or show welcome
        if self.open_files:
            self.switch_to_file(list(self.open_files.keys())[0])
        else:
            self.current_file = None
            self.text_area.delete("1.0", "end")
            self.text_area.insert("1.0", "# Welcome to CodeForge\n# Press Ctrl+O to open a file")
            self.status_bar.config(text="Ready")
            
        self.update_tabs()
        
    def update_tabs(self):
        # Clear existing tabs
        for widget in self.tab_frame.winfo_children():
            widget.destroy()
            
        # Create tabs for each open file
        for filename in self.open_files.keys():
            file_info = self.open_files[filename]
            
            tab = tk.Frame(self.tab_frame, bg="#2d2d30" if filename != self.current_file else "#1e1e1e")
            tab.pack(side=tk.LEFT, padx=1)
            
            # File name label
            label_text = ("● " if file_info["modified"] else "") + filename
            label = tk.Label(tab, text=label_text, bg=tab["bg"], fg=self.fg_color,
                           padx=10, pady=8, cursor="hand2")
            label.pack(side=tk.LEFT)
            label.bind("<Button-1>", lambda e, f=filename: self.switch_to_file(f))
            
            # Close button
            close_btn = tk.Label(tab, text="×", bg=tab["bg"], fg="#858585",
                                padx=5, cursor="hand2", font=("Segoe UI", 14, "bold"))
            close_btn.pack(side=tk.LEFT)
            close_btn.bind("<Button-1>", lambda e, f=filename: self.close_file(f))
            close_btn.bind("<Enter>", lambda e, btn=close_btn, t=tab: (
                btn.config(fg="#ffffff", bg="#e81123"),
                t.config(bg=t["bg"])
            ))
            close_btn.bind("<Leave>", lambda e, btn=close_btn, bg=tab["bg"]: (
                btn.config(fg="#858585", bg=bg)
            ))
            
    def update_tab_modified(self, filename, modified):
        if filename in self.open_files:
            self.open_files[filename]["modified"] = modified
            self.update_tabs()
            
    def show_find_dialog(self):
        """Show find and replace dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Find & Replace")
        dialog.geometry("450x220")
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Find entry
        tk.Label(dialog, text="Find:", bg=self.bg_color, fg=self.fg_color).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        find_entry = tk.Entry(dialog, width=35, bg=self.editor_bg, fg=self.fg_color, insertbackground=self.fg_color)
        find_entry.grid(row=0, column=1, padx=10, pady=10, columnspan=2)
        find_entry.focus()
        
        # Replace entry
        tk.Label(dialog, text="Replace:", bg=self.bg_color, fg=self.fg_color).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        replace_entry = tk.Entry(dialog, width=35, bg=self.editor_bg, fg=self.fg_color, insertbackground=self.fg_color)
        replace_entry.grid(row=1, column=1, padx=10, pady=10, columnspan=2)
        
        # Options
        options_frame = tk.Frame(dialog, bg=self.bg_color)
        options_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=5)
        
        case_sensitive_var = tk.BooleanVar(value=False)
        regex_var = tk.BooleanVar(value=False)
        whole_word_var = tk.BooleanVar(value=False)
        
        tk.Checkbutton(options_frame, text="Case sensitive", variable=case_sensitive_var,
                      bg=self.bg_color, fg=self.fg_color, selectcolor=self.sidebar_bg,
                      activebackground=self.bg_color, activeforeground=self.fg_color).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(options_frame, text="Regex", variable=regex_var,
                      bg=self.bg_color, fg=self.fg_color, selectcolor=self.sidebar_bg,
                      activebackground=self.bg_color, activeforeground=self.fg_color).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(options_frame, text="Whole word", variable=whole_word_var,
                      bg=self.bg_color, fg=self.fg_color, selectcolor=self.sidebar_bg,
                      activebackground=self.bg_color, activeforeground=self.fg_color).pack(side=tk.LEFT, padx=5)
        
        def find_next():
            search_term = find_entry.get()
            if not search_term:
                return
                
            # Remove previous highlights
            self.text_area.tag_remove("search", "1.0", "end")
            
            # Build search parameters
            nocase = not case_sensitive_var.get()
            use_regex = regex_var.get()
            
            # Find all occurrences
            start = "1.0"
            count = 0
            
            try:
                if use_regex:
                    import re
                    content = self.text_area.get("1.0", "end-1c")
                    flags = 0 if case_sensitive_var.get() else re.IGNORECASE
                    pattern = re.compile(search_term, flags)
                    
                    for match in pattern.finditer(content):
                        start_pos = f"1.0+{match.start()}c"
                        end_pos = f"1.0+{match.end()}c"
                        self.text_area.tag_add("search", start_pos, end_pos)
                        count += 1
                    
                    if count > 0:
                        first_match = pattern.search(content)
                        if first_match:
                            first_pos = f"1.0+{first_match.start()}c"
                            self.text_area.see(first_pos)
                            self.text_area.mark_set("insert", first_pos)
                else:
                    while True:
                        pos = self.text_area.search(search_term, start, stopindex="end", nocase=nocase, regexp=False)
                        if not pos:
                            break
                        end = f"{pos}+{len(search_term)}c"
                        self.text_area.tag_add("search", pos, end)
                        count += 1
                        start = end
                    
                    # Jump to first occurrence
                    if count > 0:
                        first = self.text_area.search(search_term, "1.0", stopindex="end", nocase=nocase)
                        if first:
                            self.text_area.see(first)
                            self.text_area.mark_set("insert", first)
                
                self.text_area.tag_config("search", background="#515c6a", foreground="white")
                
                if count > 0:
                    self.status_bar.config(text=f"Found {count} occurrence(s)")
                else:
                    self.status_bar.config(text="No matches found")
            except re.error as e:
                self.status_bar.config(text=f"Invalid regex: {str(e)}")
            except Exception as e:
                self.status_bar.config(text=f"Search error: {str(e)}")
        
        def replace_all():
            search_term = find_entry.get()
            replace_term = replace_entry.get()
            
            if not search_term:
                return
            
            try:
                content = self.text_area.get("1.0", "end-1c")
                
                if regex_var.get():
                    import re
                    flags = 0 if case_sensitive_var.get() else re.IGNORECASE
                    pattern = re.compile(search_term, flags)
                    new_content, count = pattern.subn(replace_term, content)
                else:
                    if case_sensitive_var.get():
                        count = content.count(search_term)
                        new_content = content.replace(search_term, replace_term)
                    else:
                        # Case-insensitive replace
                        import re
                        pattern = re.compile(re.escape(search_term), re.IGNORECASE)
                        new_content, count = pattern.subn(replace_term, content)
                
                if count > 0:
                    self.text_area.delete("1.0", "end")
                    self.text_area.insert("1.0", new_content)
                    self.status_bar.config(text=f"Replaced {count} occurrence(s)")
                else:
                    self.status_bar.config(text="No matches found")
            except Exception as e:
                self.status_bar.config(text=f"Replace error: {str(e)}")
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg=self.bg_color)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=15)
        
        tk.Button(btn_frame, text="Find All", command=find_next, bg="#0e639c", fg="white", 
                 padx=15, pady=5, relief=tk.FLAT, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Replace All", command=replace_all, bg="#0e639c", fg="white",
                 padx=15, pady=5, relief=tk.FLAT, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Close", command=dialog.destroy, bg="#3e3e42", fg="white",
                 padx=15, pady=5, relief=tk.FLAT, cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        # Bind Enter to find
        find_entry.bind("<Return>", lambda e: find_next())
    
    def show_about(self):
        """Show about dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("About CodeForge")
        dialog.geometry("400x300")
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Logo
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "icon", "white-transparent.png")
            logo_image = Image.open(logo_path)
            logo_image = logo_image.resize((80, 80), Image.Resampling.LANCZOS)
            logo_photo = ImageTk.PhotoImage(logo_image)
            logo_label = tk.Label(dialog, image=logo_photo, bg=self.bg_color)
            logo_label.image = logo_photo  # Keep reference
            logo_label.pack(pady=(20, 10))
        except:
            pass
        
        # App name
        tk.Label(dialog, text="CodeForge", bg=self.bg_color, fg=self.fg_color,
                font=("Segoe UI", 20, "bold")).pack(pady=(0, 5))
        
        # Version
        tk.Label(dialog, text=f"Version {version}", bg=self.bg_color, fg="#858585",
                font=("Segoe UI", 10)).pack(pady=(0, 15))
        
        # Description
        tk.Label(dialog, text="A modern code editor built with Python and Tkinter", 
                bg=self.bg_color, fg=self.fg_color,
                font=("Segoe UI", 9)).pack(pady=(0, 5))
        
        # Features
        features_text = "Features: Syntax highlighting, Auto-indent, Smart brackets,\nTerminal integration, Multi-file tabs, Minimap, Auto-save"
        tk.Label(dialog, text=features_text, bg=self.bg_color, fg="#858585",
                font=("Segoe UI", 9), justify=tk.CENTER).pack(pady=(0, 20))
        
        # Copyright
        tk.Label(dialog, text="© 2025 CodeForge", bg=self.bg_color, fg="#858585",
                font=("Segoe UI", 8)).pack(pady=(0, 0))
        
        # Close button
        close_btn = tk.Button(dialog, text="Close", command=dialog.destroy,
                             bg="#0e639c", fg="white", font=("Segoe UI", 9),
                             padx=30, pady=8, relief=tk.FLAT, cursor="hand2",
                             activebackground="#1177bb", activeforeground="white")
        close_btn.pack(pady=(0, 20))
    
    def show_shortcuts(self):
        """Show keyboard shortcuts dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Keyboard Shortcuts")
        dialog.geometry("500x600")
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Title
        tk.Label(dialog, text="Keyboard Shortcuts", bg=self.bg_color, fg=self.fg_color,
                font=("Segoe UI", 16, "bold")).pack(pady=(20, 20))
        
        # Shortcuts frame with scrollbar
        shortcuts_frame = tk.Frame(dialog, bg=self.bg_color)
        shortcuts_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        shortcuts = [
            ("File Operations", [
                ("Ctrl+N", "New File"),
                ("Ctrl+O", "Open File"),
                ("Ctrl+S", "Save File"),
                ("Ctrl+Shift+S", "Save As"),
            ]),
            ("Editing", [
                ("Ctrl+Z", "Undo"),
                ("Ctrl+Y", "Redo"),
                ("Ctrl+X", "Cut"),
                ("Ctrl+C", "Copy"),
                ("Ctrl+V", "Paste"),
                ("Ctrl+A", "Select All"),
                ("Ctrl+F", "Find"),
                ("Ctrl+H", "Replace"),
                ("Ctrl+G", "Go to Line"),
                ("Ctrl+/", "Toggle Comment"),
                ("Ctrl+D", "Duplicate Line"),
                ("Ctrl+W", "Close Current Tab"),
            ]),
            ("Navigation", [
                ("Alt+Up", "Move Line Up"),
                ("Alt+Down", "Move Line Down"),
                ("Ctrl+Alt+Up", "Add Cursor Above"),
                ("Ctrl+Alt+Down", "Add Cursor Below"),
            ]),
            ("View", [
                ("View Menu", "Toggle Terminal"),
                ("View Menu", "Toggle Minimap"),
                ("Ctrl++", "Zoom In"),
                ("Ctrl+-", "Zoom Out"),
                ("Ctrl+0", "Reset Zoom"),
            ]),
            ("Settings", [
                ("Ctrl+,", "Open Settings"),
            ]),
        ]
        
        for category, items in shortcuts:
            # Category header
            tk.Label(shortcuts_frame, text=category, bg=self.bg_color, fg="#569cd6",
                    font=("Segoe UI", 11, "bold"), anchor="w").pack(fill=tk.X, pady=(10, 5))
            
            # Shortcuts
            for key, description in items:
                shortcut_row = tk.Frame(shortcuts_frame, bg=self.bg_color)
                shortcut_row.pack(fill=tk.X, pady=2)
                
                tk.Label(shortcut_row, text=key, bg=self.sidebar_bg, fg=self.fg_color,
                        font=("Consolas", 9), width=20, anchor="w", padx=10, pady=3).pack(side=tk.LEFT)
                tk.Label(shortcut_row, text=description, bg=self.bg_color, fg="#858585",
                        font=("Segoe UI", 9), anchor="w", padx=10).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Close button
        close_btn = tk.Button(dialog, text="Close", command=dialog.destroy,
                             bg="#0e639c", fg="white", font=("Segoe UI", 9),
                             padx=30, pady=8, relief=tk.FLAT, cursor="hand2",
                             activebackground="#1177bb", activeforeground="white")
        close_btn.pack(pady=(10, 20))
    
    
    def toggle_terminal(self):
        """Show or hide the terminal panel"""
        if self.terminal_visible:
            self.terminal_frame.pack_forget()
            self.terminal_visible = False
        else:
            self.terminal_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, in_=self.right_frame, before=self.editor_frame)
            self.terminal_visible = True
            self.terminal_input.focus()
            # Print welcome message if terminal is empty
            if not self.terminal_output.get("1.0", "end-1c"):
                self.write_terminal("Terminal ready. Type commands here.\n", "info")
                if self.current_folder:
                    self.write_terminal(f"Working directory: {self.current_folder}\n\n", "info")
    
    def clear_terminal(self):
        """Clear terminal output"""
        self.terminal_output.config(state="normal")
        self.terminal_output.delete("1.0", "end")
        self.terminal_output.config(state="disabled")
    
    def write_terminal(self, text, tag="output"):
        """Write text to terminal output"""
        self.terminal_output.config(state="normal")
        self.terminal_output.insert("end", text, tag)
        self.terminal_output.see("end")
        self.terminal_output.config(state="disabled")
        
        # Configure tags
        self.terminal_output.tag_config("output", foreground="#cccccc")
        self.terminal_output.tag_config("error", foreground="#f48771")
        self.terminal_output.tag_config("info", foreground="#4ec9b0")
        self.terminal_output.tag_config("command", foreground="#569cd6")
    
    def execute_command(self, event=None):
        """Execute command in terminal"""
        command = self.terminal_input.get().strip()
        if not command:
            return
        
        # Add to history
        self.command_history.append(command)
        self.history_index = len(self.command_history)
        
        # Display command
        self.write_terminal(f"$ {command}\n", "command")
        self.terminal_input.delete(0, tk.END)
        
        # Handle built-in commands
        if command == "clear" or command == "cls":
            self.clear_terminal()
            return
        elif command.startswith("cd "):
            path = command[3:].strip().strip('"').strip("'")
            try:
                if os.path.isdir(path):
                    os.chdir(path)
                    self.current_folder = os.getcwd()
                    self.write_terminal(f"Changed directory to: {self.current_folder}\n", "info")
                else:
                    self.write_terminal(f"Directory not found: {path}\n", "error")
            except Exception as e:
                self.write_terminal(f"Error: {str(e)}\n", "error")
            return
        
        # Execute command in background thread
        threading.Thread(target=self.run_command, args=(command,), daemon=True).start()
    
    def run_command(self, command):
        """Run command and capture output"""
        try:
            # Set working directory
            cwd = self.current_folder if self.current_folder else os.getcwd()
            
            # Run command
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                text=True
            )
            
            # Read output
            stdout, stderr = process.communicate(timeout=30)
            
            # Display output
            if stdout:
                self.root.after(0, lambda: self.write_terminal(stdout, "output"))
            if stderr:
                self.root.after(0, lambda: self.write_terminal(stderr, "error"))
            
            if process.returncode != 0:
                self.root.after(0, lambda: self.write_terminal(f"\nProcess exited with code {process.returncode}\n", "error"))
            
        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: self.write_terminal("\nCommand timed out after 30 seconds\n", "error"))
        except Exception as e:
            self.root.after(0, lambda: self.write_terminal(f"\nError executing command: {str(e)}\n", "error"))
        
        self.root.after(0, lambda: self.write_terminal("\n", "output"))
    
    def terminal_history_up(self, event):
        """Navigate up in command history"""
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.terminal_input.delete(0, tk.END)
            self.terminal_input.insert(0, self.command_history[self.history_index])
    
    def terminal_history_down(self, event):
        """Navigate down in command history"""
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.terminal_input.delete(0, tk.END)
            self.terminal_input.insert(0, self.command_history[self.history_index])
        elif self.history_index >= len(self.command_history) - 1:
            self.history_index = len(self.command_history)
            self.terminal_input.delete(0, tk.END)
    
    def start_drag(self, event):
        """Start dragging the window"""
        self.offset_x = event.x_root - self.root.winfo_x()
        self.offset_y = event.y_root - self.root.winfo_y()
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
    
    def on_drag(self, event):
        """Drag the window"""
        if self.is_maximized:
            # If maximized and user drags, restore to normal and position under cursor
            # Calculate the relative position of the cursor in the window
            relative_x = event.x / self.root.winfo_width()
            
            # Restore to normal
            self.root.geometry(self.restore_geometry)
            self.is_maximized = False
            self.max_btn.config(text="🗖")
            
            # Position window so cursor stays in same relative position on title bar
            width = self.root.winfo_width()
            x = event.x_root - int(width * relative_x)
            y = event.y_root - event.y
            self.root.geometry(f"+{x}+{y}")
            
            # Update offsets for continued dragging
            self.offset_x = int(width * relative_x)
            self.offset_y = event.y
        else:
            x = event.x_root - self.offset_x
            y = event.y_root - self.offset_y
            self.root.geometry(f"+{x}+{y}")
            
            # Auto-maximize if dragged to top of screen
            if event.y_root <= 10:
                self.toggle_maximize()
    
    def zoom_in(self):
        """Increase font size"""
        self.current_font_size += 1
        self.update_font_size()
    
    def zoom_out(self):
        """Decrease font size"""
        if self.current_font_size > 6:
            self.current_font_size -= 1
            self.update_font_size()
    
    def reset_zoom(self):
        """Reset font size to default"""
        self.current_font_size = self.base_font_size
        self.update_font_size()
    
    def update_font_size(self):
        """Update editor font size"""
        font_family = self.settings.get('font_family', 'Consolas')
        self.text_area.config(font=(font_family, self.current_font_size))
        self.line_numbers.config(font=(font_family, self.current_font_size))
        self.terminal_output.config(font=(font_family, self.current_font_size - 1))
        self.update_line_numbers()
        self.status_bar.config(text=f"Font size: {self.current_font_size}")
    
    def show_goto_line_dialog(self):
        """Show go to line dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Go to Line")
        dialog.geometry("300x120")
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="Line number:", bg=self.bg_color, fg=self.fg_color,
                font=("Segoe UI", 10)).pack(pady=(20, 5))
        
        line_entry = tk.Entry(dialog, width=20, bg=self.editor_bg, fg=self.fg_color,
                             insertbackground=self.fg_color, font=("Segoe UI", 10))
        line_entry.pack(pady=5)
        line_entry.focus()
        
        def go_to_line():
            try:
                line_num = int(line_entry.get())
                last_line = int(self.text_area.index('end-1c').split('.')[0])
                
                if 1 <= line_num <= last_line:
                    self.text_area.mark_set(tk.INSERT, f"{line_num}.0")
                    self.text_area.see(f"{line_num}.0")
                    self.highlight_current_line()
                    self.status_bar.config(text=f"Jumped to line {line_num}")
                    dialog.destroy()
                else:
                    messagebox.showwarning("Invalid Line", f"Line number must be between 1 and {last_line}")
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid line number")
        
        btn_frame = tk.Frame(dialog, bg=self.bg_color)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Go", command=go_to_line, bg="#0e639c", fg="white",
                 padx=20, pady=5, relief=tk.FLAT, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, bg="#3e3e42", fg="white",
                 padx=20, pady=5, relief=tk.FLAT, cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        line_entry.bind("<Return>", lambda e: go_to_line())
        line_entry.bind("<Escape>", lambda e: dialog.destroy())
    
    def show_replace_dialog(self):
        """Show replace dialog (alias to find dialog)"""
        self.show_find_dialog()
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.geometry("500x400")
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Title
        tk.Label(dialog, text="Settings", bg=self.bg_color, fg=self.fg_color,
                font=("Segoe UI", 16, "bold")).pack(pady=(20, 20))
        
        # Settings frame
        settings_frame = tk.Frame(dialog, bg=self.bg_color)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=40)
        
        # Font Family
        tk.Label(settings_frame, text="Font Family:", bg=self.bg_color, fg=self.fg_color,
                font=("Segoe UI", 10), anchor="w").grid(row=0, column=0, sticky="w", pady=10)
        
        font_var = tk.StringVar(value=self.settings.get('font_family', 'Consolas'))
        font_options = ['Consolas', 'Courier New', 'Monaco', 'Menlo', 'Fira Code', 'Source Code Pro']
        font_menu = ttk.Combobox(settings_frame, textvariable=font_var, values=font_options,
                                state="readonly", width=20)
        font_menu.grid(row=0, column=1, sticky="ew", pady=10, padx=(10, 0))
        
        # Font Size
        tk.Label(settings_frame, text="Font Size:", bg=self.bg_color, fg=self.fg_color,
                font=("Segoe UI", 10), anchor="w").grid(row=1, column=0, sticky="w", pady=10)
        
        size_var = tk.IntVar(value=self.settings.get('font_size', 11))
        size_spin = tk.Spinbox(settings_frame, from_=6, to=24, textvariable=size_var,
                              width=20, bg=self.editor_bg, fg=self.fg_color,
                              buttonbackground=self.sidebar_bg)
        size_spin.grid(row=1, column=1, sticky="ew", pady=10, padx=(10, 0))
        
        # Tab Size
        tk.Label(settings_frame, text="Tab Size:", bg=self.bg_color, fg=self.fg_color,
                font=("Segoe UI", 10), anchor="w").grid(row=2, column=0, sticky="w", pady=10)
        
        tab_var = tk.IntVar(value=self.settings.get('tab_size', 4))
        tab_spin = tk.Spinbox(settings_frame, from_=2, to=8, textvariable=tab_var,
                             width=20, bg=self.editor_bg, fg=self.fg_color,
                             buttonbackground=self.sidebar_bg)
        tab_spin.grid(row=2, column=1, sticky="ew", pady=10, padx=(10, 0))
        
        # Auto-save
        auto_save_var = tk.BooleanVar(value=self.settings.get('auto_save', True))
        tk.Checkbutton(settings_frame, text="Enable auto-save (every 30s)",
                      variable=auto_save_var, bg=self.bg_color, fg=self.fg_color,
                      selectcolor=self.sidebar_bg, activebackground=self.bg_color,
                      activeforeground=self.fg_color, font=("Segoe UI", 10)).grid(
                      row=3, column=0, columnspan=2, sticky="w", pady=10)
        
        # Show line numbers
        line_numbers_var = tk.BooleanVar(value=self.settings.get('show_line_numbers', True))
        tk.Checkbutton(settings_frame, text="Show line numbers",
                      variable=line_numbers_var, bg=self.bg_color, fg=self.fg_color,
                      selectcolor=self.sidebar_bg, activebackground=self.bg_color,
                      activeforeground=self.fg_color, font=("Segoe UI", 10)).grid(
                      row=4, column=0, columnspan=2, sticky="w", pady=10)
        
        # Show minimap
        minimap_var = tk.BooleanVar(value=self.settings.get('show_minimap', True))
        tk.Checkbutton(settings_frame, text="Show minimap",
                      variable=minimap_var, bg=self.bg_color, fg=self.fg_color,
                      selectcolor=self.sidebar_bg, activebackground=self.bg_color,
                      activeforeground=self.fg_color, font=("Segoe UI", 10)).grid(
                      row=5, column=0, columnspan=2, sticky="w", pady=10)
        
        settings_frame.columnconfigure(1, weight=1)
        
        def save_settings():
            # Update settings
            self.settings['font_family'] = font_var.get()
            self.settings['font_size'] = size_var.get()
            self.settings['tab_size'] = tab_var.get()
            self.settings['auto_save'] = auto_save_var.get()
            self.settings['show_line_numbers'] = line_numbers_var.get()
            self.settings['show_minimap'] = minimap_var.get()
            
            # Apply settings
            self.base_font_size = self.settings['font_size']
            self.current_font_size = self.settings['font_size']
            self.auto_save_enabled = self.settings['auto_save']
            
            # Update font
            self.text_area.config(font=(self.settings['font_family'], self.current_font_size))
            self.line_numbers.config(font=(self.settings['font_family'], self.current_font_size))
            
            # Toggle line numbers
            if self.settings['show_line_numbers']:
                self.line_numbers.pack(side=tk.LEFT, fill=tk.Y, before=self.text_area)
            else:
                self.line_numbers.pack_forget()
            
            # Toggle minimap
            if not self.settings['show_minimap'] and self.minimap_visible:
                self.toggle_minimap()
            elif self.settings['show_minimap'] and not self.minimap_visible:
                self.toggle_minimap()
            
            self.status_bar.config(text="Settings saved")
            dialog.destroy()
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg=self.bg_color)
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="Save", command=save_settings, bg="#0e639c", fg="white",
                 font=("Segoe UI", 9), padx=30, pady=8, relief=tk.FLAT, cursor="hand2",
                 activebackground="#1177bb", activeforeground="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, bg="#3e3e42", fg="white",
                 font=("Segoe UI", 9), padx=30, pady=8, relief=tk.FLAT, cursor="hand2",
                 activebackground="#4e4e52", activeforeground="white").pack(side=tk.LEFT, padx=5)
    
    def change_sidebar_position(self, position):
        """Change sidebar position (left or right)"""
        self.settings['sidebar_position'] = position
        messagebox.showinfo("Layout Changed", 
                           f"Sidebar position set to {position}.\nRestart the application to apply changes.")
    
    def save_layout(self):
        """Save current layout configuration to file"""
        layout_config = {
            'sidebar_position': self.settings['sidebar_position'],
            'activity_bar_visible': self.settings['activity_bar_visible'],
            'panel_position': self.settings['panel_position'],
            'show_minimap': self.settings['show_minimap'],
            'show_line_numbers': self.settings['show_line_numbers'],
            'theme': self.settings['theme'],
            'font_family': self.settings['font_family'],
            'font_size': self.settings['font_size']
        }
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Save Layout"
        )
        
        if filepath:
            try:
                with open(filepath, 'w') as f:
                    json.dump(layout_config, f, indent=2)
                messagebox.showinfo("Success", f"Layout saved to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save layout:\n{str(e)}")
    
    def load_layout(self):
        """Load layout configuration from file"""
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Load Layout"
        )
        
        if filepath:
            try:
                with open(filepath, 'r') as f:
                    layout_config = json.load(f)
                
                # Apply loaded settings
                for key, value in layout_config.items():
                    if key in self.settings:
                        self.settings[key] = value
                
                # Apply theme
                if 'theme' in layout_config:
                    self.apply_theme(layout_config['theme'])
                
                # Update font
                if 'font_size' in layout_config:
                    self.current_font_size = layout_config['font_size']
                    self.update_font_size()
                
                messagebox.showinfo("Success", 
                                   "Layout loaded successfully!\nSome changes may require restart.")
            except Exception as e:
                messagebox.showerror("Error", f"Could not load layout:\n{str(e)}")
    
    def toggle_maximize(self, event=None):
        """Toggle between maximized and normal window state"""
        if self.is_maximized:
            # Restore to normal
            self.root.geometry(self.restore_geometry)
            self.is_maximized = False
            self.max_btn.config(text="🗖")
        else:
            # Maximize
            self.restore_geometry = self.root.geometry()
            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            self.root.geometry(f"{screen_width}x{screen_height}+0+0")
            self.is_maximized = True
            self.max_btn.config(text="🗗")

def main():
    root = tk.Tk()
    app = CodeEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
