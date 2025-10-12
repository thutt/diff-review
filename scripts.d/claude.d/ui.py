#!/usr/bin/env python3
import sys
from typing import List, Tuple, Optional

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    print("Error: tkinter must be installed to use this program",
          file=sys.stderr)
    sys.exit(1)

class DiffViewer:
    def __init__(self, base_file: str, modified_file: str,
                 note_file: Optional[str] = None):
        self.base_file = base_file
        self.modified_file = modified_file
        self.note_file = note_file
        self.note_count = 0
        
        # Track which lines have been noted
        self.base_noted_lines = set()
        self.modified_noted_lines = set()
        
        # Read files
        with open(base_file, 'r') as f:
            self.base_lines = f.readlines()
        with open(modified_file, 'r') as f:
            self.modified_lines = f.readlines()
        
        # Initialize data structures that will be populated by external API
        self.base_display = []
        self.modified_display = []
        self.base_line_nums = []
        self.modified_line_nums = []
        self.change_regions = []
        
        # Setup GUI
        self.root = tk.Tk()
        self.root.title(f"Diff Viewer: {base_file} vs {modified_file}")
        
        # Current selection
        self.current_region = 0
        self.selected_line = None
        
        # Don't setup GUI yet - wait for finalize()
        self.gui_initialized = False
    
    def add_line(self, base, modi):
        """Add a line pair from base and modified files.
        
        Args:
            base: Line object for base file (or NotPresent variant)
            modi: Line object for modified file (or NotPresent variant)
        """
        # Extract text and line numbers from Line objects
        base_text = base.line_.rstrip('\n') if hasattr(base, 'line_') else ''
        modi_text = modi.line_.rstrip('\n') if hasattr(modi, 'line_') else ''
        
        # Get line numbers (None if line doesn't exist in that file)
        base_num = base.line_num_ if base.show_line_number() else None
        modi_num = modi.line_num_ if modi.show_line_number() else None
        
        # Add to display lists
        self.base_display.append(base_text)
        self.modified_display.append(modi_text)
        self.base_line_nums.append(base_num)
        self.modified_line_nums.append(modi_num)
        
        # Store Line objects for later use in highlighting
        if not hasattr(self, 'base_line_objects'):
            self.base_line_objects = []
            self.modified_line_objects = []
        self.base_line_objects.append(base)
        self.modified_line_objects.append(modi)
    
    def finalize(self):
        """Call this after all lines have been added to populate the UI."""
        # Assert finalize is only called once
        assert not hasattr(self, 'content_populated'), "finalize() called more than once"
        
        if not self.gui_initialized:
            self.setup_gui()
            self.bind_keys()
            self.gui_initialized = True
        
        # Build change regions before populating content
        self.build_change_regions()
        
        self.populate_content()
        self.apply_diff_highlighting_from_runs()
        self.update_status()
        
        self.content_populated = True
    
    def build_change_regions(self):
        """Build change regions by analyzing the added lines."""
        if not hasattr(self, 'base_line_objects'):
            return
        
        self.change_regions = []
        region_start = None
        region_tag = None
        
        for i, (base_line, modi_line) in enumerate(zip(self.base_line_objects,
                                                        self.modified_line_objects)):
            # Determine if this line represents a change
            base_present = base_line.show_line_number()
            modi_present = modi_line.show_line_number()
            
            # Determine line type
            if base_present and modi_present:
                # Both present - check if changed
                is_changed = self.line_has_changes(base_line) or self.line_has_changes(modi_line)
                current_tag = 'replace' if is_changed else None
            elif base_present and not modi_present:
                # Line deleted
                current_tag = 'delete'
            elif not base_present and modi_present:
                # Line inserted
                current_tag = 'insert'
            else:
                # Both absent - shouldn't happen
                current_tag = None
            
            # Track region boundaries
            if current_tag is not None:
                if region_start is None:
                    # Start new region
                    region_start = i
                    region_tag = current_tag
                elif region_tag != current_tag:
                    # End previous region, start new one
                    self.change_regions.append((region_tag, region_start, i, 0, 0, 0, 0))
                    region_start = i
                    region_tag = current_tag
            else:
                # No change - end any active region
                if region_start is not None:
                    self.change_regions.append((region_tag, region_start, i, 0, 0, 0, 0))
                    region_start = None
                    region_tag = None
        
        # Close any remaining region
        if region_start is not None:
            self.change_regions.append((region_tag, region_start, len(self.base_line_objects), 0, 0, 0, 0))
    
    def line_has_changes(self, line_obj):
        """Check if a line has any changed runs."""
        if not hasattr(line_obj, 'runs_'):
            return False
        
        for run in line_obj.runs_:
            if run.changed_:
                return True
        return False
    
    def setup_gui(self):
        """Setup GUI components"""
        # Main frame
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Content frame for canvases and diff map
        self.content_frame = tk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # File name labels row
        self.filename_frame = tk.Frame(self.content_frame)
        self.filename_frame.grid(row=0, column=0, columnspan=4, sticky='ew')
        
        # Base file name label
        self.base_filename_label = tk.Label(self.filename_frame, 
                                           text=self.base_file,
                                           relief=tk.SUNKEN, bd=1,
                                           anchor=tk.W, padx=5)
        self.base_filename_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Spacer for diff map
        spacer = tk.Label(self.filename_frame, text="", width=4)
        spacer.pack(side=tk.LEFT)
        
        # Modified file name label
        self.modified_filename_label = tk.Label(self.filename_frame,
                                               text=self.modified_file,
                                               relief=tk.SUNKEN, bd=1,
                                               anchor=tk.W, padx=5)
        self.modified_filename_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Base frame (left) - contains line numbers and content
        self.base_frame = tk.Frame(self.content_frame)
        self.base_frame.grid(row=1, column=0, sticky='nsew')
        
        # Diff map (center)
        self.diff_map = tk.Canvas(self.content_frame, width=30, bg='white')
        self.diff_map.grid(row=1, column=1, sticky='ns')
        
        # Modified frame (right) - contains line numbers and content
        self.modified_frame = tk.Frame(self.content_frame)
        self.modified_frame.grid(row=1, column=2, sticky='nsew')
        
        # Vertical scrollbar
        self.v_scrollbar = tk.Scrollbar(self.content_frame, orient=tk.VERTICAL, command=self.on_v_scroll)
        self.v_scrollbar.grid(row=1, column=3, sticky='ns')
        
        # Configure grid weights
        self.content_frame.grid_rowconfigure(1, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(2, weight=1)
        
        # Horizontal scrollbar
        self.h_scrollbar = tk.Scrollbar(self.main_frame, orient=tk.HORIZONTAL, command=self.on_h_scroll)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Status bar
        self.status_frame = tk.Frame(self.main_frame, relief=tk.SUNKEN, bd=1)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.region_label = tk.Label(self.status_frame, text="Region: 0 of 0", anchor=tk.W)
        self.region_label.pack(side=tk.LEFT, padx=5)
        
        self.notes_label = tk.Label(self.status_frame, text="Notes: 0", anchor=tk.E)
        self.notes_label.pack(side=tk.RIGHT, padx=5)
        
        # Create text widgets
        self.setup_text_widgets()
        
        # Setup diff map
        self.setup_diff_map()
        
        # Setup context menu
        self.setup_context_menu()
        
        # Set initial window size
        self.set_initial_size()
        
    def setup_text_widgets(self):
        """Create text widgets for line numbers and content"""
        font = ('Courier', 12, 'bold')
        
        # Base line numbers - width for 6 digits + space + arrow
        self.base_line_text = tk.Text(self.base_frame, width=9, font=font, 
                                      state=tk.DISABLED, wrap=tk.NONE, 
                                      takefocus=False, cursor='arrow')
        self.base_line_text.pack(side=tk.LEFT, fill=tk.Y)
        
        # Base content
        self.base_content_text = tk.Text(self.base_frame, font=font, 
                                         bg='white', wrap=tk.NONE)
        self.base_content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Modified line numbers - width for 6 digits + space + arrow
        self.modified_line_text = tk.Text(self.modified_frame, width=9, font=font,
                                          state=tk.DISABLED, wrap=tk.NONE,
                                          takefocus=False, cursor='arrow')
        self.modified_line_text.pack(side=tk.LEFT, fill=tk.Y)
        
        # Modified content
        self.modified_content_text = tk.Text(self.modified_frame, font=font,
                                             bg='white', wrap=tk.NONE)
        self.modified_content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Make content text widgets read-only by blocking modifications
        def block_modify(event):
            return "break"
        
        for widget in [self.base_content_text, self.modified_content_text]:
            widget.bind('<Key>', block_modify)
            widget.bind('<<Cut>>', block_modify)
            widget.bind('<<Paste>>', block_modify)
            widget.bind('<<Clear>>', block_modify)
        
        # Configure selection colors to be visible
        self.base_content_text.config(selectbackground='blue', 
                                      selectforeground='white')
        self.modified_content_text.config(selectbackground='blue',
                                         selectforeground='white')
        
        # Bind scrolling
        self.base_content_text.config(yscrollcommand=self.update_scrollbar,
                                      xscrollcommand=self.update_h_scrollbar)
        self.modified_content_text.config(yscrollcommand=lambda *args: None,
                                          xscrollcommand=lambda *args: None)
        
        # Bind events
        self.base_content_text.bind('<Button-1>', lambda e: self.on_line_click(e, 'base'))
        self.modified_content_text.bind('<Button-1>', lambda e: self.on_line_click(e, 'modified'))
        self.base_content_text.bind('<Double-Button-1>', lambda e: self.on_double_click(e, 'base'))
        self.modified_content_text.bind('<Double-Button-1>', lambda e: self.on_double_click(e, 'modified'))
        
        # Right-click menu
        self.base_content_text.bind('<Button-3>', lambda e: self.show_context_menu(e, 'base'))
        self.modified_content_text.bind('<Button-3>', lambda e: self.show_context_menu(e, 'modified'))
        
        # Mouse wheel
        for widget in [self.base_frame, self.modified_frame, self.diff_map,
                      self.base_content_text, self.modified_content_text,
                      self.base_line_text, self.modified_line_text]:
            widget.bind('<MouseWheel>', self.on_mouse_wheel)
            widget.bind('<Button-4>', self.on_mouse_wheel)
            widget.bind('<Button-5>', self.on_mouse_wheel)
    
    def populate_content(self):
        """Populate text widgets with content"""
        # Configure tags based on TextRun color() return values
        for text_widget in [self.base_content_text, self.modified_content_text]:
            text_widget.tag_config('NORMAL', background='white', foreground='black')
            text_widget.tag_config('ADD', background='lightgreen', foreground='black')
            text_widget.tag_config('DELETE', background='red', foreground='black')
            text_widget.tag_config('INTRALINE', background='yellow', foreground='black')
            text_widget.tag_config('UNKNOWN', background='white', foreground='red')
            text_widget.tag_config('NOTPRESENT', background='darkgrey')
            # Tag for current region selection box
            text_widget.tag_config('current_region', borderwidth=2, relief='solid')
            
            # CRITICAL FIX: Raise selection tag above all other tags
            # This ensures text selection is always visible over background colors
            text_widget.tag_raise('sel')
        
        # Populate base
        self.base_line_text.config(state=tk.NORMAL)
        self.base_content_text.config(state=tk.NORMAL)
        for i, (line_num, content) in enumerate(zip(self.base_line_nums, self.base_display)):
            line_idx = f"{i+1}.0"
            if line_num is None:
                self.base_line_text.insert(tk.END, '\n')
                self.base_line_text.tag_add(f'blank_{i}', line_idx, f"{i+1}.end")
                self.base_line_text.tag_config(f'blank_{i}', background='darkgrey')
            else:
                self.base_line_text.insert(tk.END, f"{line_num:6d}  \n")
            
            self.base_content_text.insert(tk.END, content + '\n')
        self.base_line_text.config(state=tk.DISABLED)
        # Keep base_content_text in NORMAL state for selection
        
        # Populate modified
        self.modified_line_text.config(state=tk.NORMAL)
        self.modified_content_text.config(state=tk.NORMAL)
        for i, (line_num, content) in enumerate(zip(self.modified_line_nums, self.modified_display)):
            line_idx = f"{i+1}.0"
            if line_num is None:
                self.modified_line_text.insert(tk.END, '\n')
                self.modified_line_text.tag_add(f'blank_{i}', line_idx, f"{i+1}.end")
                self.modified_line_text.tag_config(f'blank_{i}', background='darkgrey')
            else:
                self.modified_line_text.insert(tk.END, f"{line_num:6d}  \n")
            
            self.modified_content_text.insert(tk.END, content + '\n')
        self.modified_line_text.config(state=tk.DISABLED)
        # Keep modified_content_text in NORMAL state for selection
    
    def apply_diff_highlighting_from_runs(self):
        """Apply highlighting based on TextRun information in Line objects."""
        if not hasattr(self, 'base_line_objects'):
            return
        
        for i, (base_line, modi_line) in enumerate(zip(self.base_line_objects, 
                                                        self.modified_line_objects)):
            # Check if line is NotPresent type and apply full line background
            base_not_present = not base_line.show_line_number()
            modi_not_present = not modi_line.show_line_number()
            
            if base_not_present:
                # Apply dark grey background to entire line in base
                self.base_content_text.tag_add('NOTPRESENT', 
                                              f"{i+1}.0", 
                                              f"{i+2}.0")
            else:
                # Apply highlighting based on runs
                self.apply_runs_to_line(self.base_content_text, i, base_line)
                
                # Check if this line has any changes and highlight line number
                if self.line_has_changes(base_line):
                    self.base_line_text.config(state=tk.NORMAL)
                    self.base_line_text.tag_add(f'changed_linenum_{i}', f"{i+1}.0", f"{i+1}.end")
                    self.base_line_text.tag_config(f'changed_linenum_{i}', background='#ffeeee')
                    self.base_line_text.config(state=tk.DISABLED)
            
            if modi_not_present:
                # Apply dark grey background to entire line in modified
                self.modified_content_text.tag_add('NOTPRESENT',
                                                  f"{i+1}.0",
                                                  f"{i+2}.0")
            else:
                # Apply highlighting based on runs
                self.apply_runs_to_line(self.modified_content_text, i, modi_line)
                
                # Check if this line has any changes and highlight line number
                if self.line_has_changes(modi_line):
                    self.modified_line_text.config(state=tk.NORMAL)
                    self.modified_line_text.tag_add(f'changed_linenum_{i}', f"{i+1}.0", f"{i+1}.end")
                    self.modified_line_text.tag_config(f'changed_linenum_{i}', background='#eeffee')
                    self.modified_line_text.config(state=tk.DISABLED)
        
        # CRITICAL: Re-raise selection tag after all highlighting is applied
        self.base_content_text.tag_raise('sel')
        self.modified_content_text.tag_raise('sel')
    
    def apply_runs_to_line(self, text_widget, line_idx, line_obj):
        """Apply TextRun highlighting to a specific line."""
        if not hasattr(line_obj, 'runs_'):
            return
        
        for run in line_obj.runs_:
            start_pos = f"{line_idx+1}.{run.start_}"
            end_pos = f"{line_idx+1}.{run.start_ + run.len_}"
            
            # Use the color() return value directly as the tag name
            tag_name = run.color()
            text_widget.tag_add(tag_name, start_pos, end_pos)
    
    def setup_diff_map(self):
        """Setup the diff map visualization"""
        self.diff_map.bind('<Button-1>', self.on_diff_map_click)
        self.root.after(100, self.update_diff_map)
    
    def update_diff_map(self):
        """Update diff map visualization"""
        self.diff_map.delete('all')
        
        total_lines = len(self.base_display)
        if total_lines == 0:
            return
        
        canvas_height = self.diff_map.winfo_height()
        canvas_width = self.diff_map.winfo_width()
        
        # Draw change regions
        for tag, display_start, display_end, i1, i2, j1, j2 in self.change_regions:
            y1 = (display_start / total_lines) * canvas_height
            y2 = (display_end / total_lines) * canvas_height
            
            if tag == 'insert':
                color = 'green'
            elif tag == 'delete':
                color = 'red'
            else:
                color = 'salmon'
            
            self.diff_map.create_rectangle(0, y1, canvas_width, y2, fill=color, outline='')
        
        # Draw viewport indicator
        first_visible = float(self.base_content_text.index('@0,0').split('.')[0]) - 1
        last_visible_y = self.base_content_text.winfo_height()
        last_visible = float(self.base_content_text.index(f'@0,{last_visible_y}').split('.')[0]) - 1
        
        viewport_y1 = (first_visible / total_lines) * canvas_height
        viewport_y2 = (last_visible / total_lines) * canvas_height
        
        self.diff_map.create_rectangle(0, viewport_y1, canvas_width, viewport_y2,
                                       fill='grey', stipple='gray50', outline='')
    
    def setup_context_menu(self):
        """Setup right-click context menu"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu_side = None
        
        if self.note_file:
            self.context_menu.add_command(label='Take Note', command=self.take_note_from_menu)
        else:
            self.context_menu.add_command(label='Take Note (no file supplied)', state=tk.DISABLED)
    
    def show_context_menu(self, event, side):
        """Show context menu on right-click"""
        self.context_menu_side = side
        
        # Check if text is selected
        text_widget = self.base_content_text if side == 'base' else self.modified_content_text
        try:
            selection = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            if self.note_file and selection:
                self.context_menu.entryconfig(0, state=tk.NORMAL)
            else:
                if self.note_file:
                    self.context_menu.entryconfig(0, state=tk.DISABLED)
        except:
            if self.note_file:
                self.context_menu.entryconfig(0, state=tk.DISABLED)
        
        self.context_menu.post(event.x_root, event.y_root)
    
    def mark_noted_line(self, side, line_num):
        """Mark a line as having a note taken"""
        line_text = self.base_line_text if side == 'base' else self.modified_line_text
        line_nums = self.base_line_nums if side == 'base' else self.modified_line_nums
        noted_set = self.base_noted_lines if side == 'base' else self.modified_noted_lines
        
        # Add to noted set
        noted_set.add(line_num)
        
        # Find display line index for this line number
        for i, num in enumerate(line_nums):
            if num == line_num:
                # Add arrow marker
                line_text.config(state=tk.NORMAL)
                line_text.delete(f"{i+1}.6", f"{i+1}.8")
                line_text.insert(f"{i+1}.6", " ►")
                line_text.tag_add(f'noted_{i}', f"{i+1}.7", f"{i+1}.8")
                line_text.tag_config(f'noted_{i}', foreground='red')
                line_text.config(state=tk.DISABLED)
                break
    
    def take_note_from_menu(self):
        """Take note from selected text"""
        if not self.note_file or not self.context_menu_side:
            return
        
        text_widget = self.base_content_text if self.context_menu_side == 'base' else self.modified_content_text
        line_nums = self.base_line_nums if self.context_menu_side == 'base' else self.modified_line_nums
        display_lines = self.base_display if self.context_menu_side == 'base' else self.modified_display
        filename = self.base_file if self.context_menu_side == 'base' else self.modified_file
        
        try:
            sel_start = text_widget.index(tk.SEL_FIRST)
            sel_end = text_widget.index(tk.SEL_LAST)
            
            start_line = int(sel_start.split('.')[0]) - 1
            end_line = int(sel_end.split('.')[0]) - 1
            
            # If selection ends at column 0, don't include that line
            end_col = int(sel_end.split('.')[1])
            if end_col == 0 and end_line > start_line:
                end_line -= 1
            
            with open(self.note_file, 'a') as f:
                prefix = '(base): ' if self.context_menu_side == 'base' else '(modi): '
                f.write(f"{prefix}{filename}\n")
                
                for i in range(start_line, end_line + 1):
                    if line_nums[i] is not None:
                        f.write(f"  {line_nums[i]}: {display_lines[i]}\n")
                        # Mark line as noted
                        self.mark_noted_line(self.context_menu_side, line_nums[i])
                
                f.write('\n')
            
            self.note_count += 1
            self.update_status()
        except:
            pass
    
    def set_initial_size(self):
        """Set initial window size"""
        # Create a font object to measure actual dimensions
        import tkinter.font as tkfont
        font = tkfont.Font(family='Courier', size=12, weight='bold')
        
        # Measure the actual width of a character
        char_width = font.measure('0')
        
        # Get font metrics for height
        font_metrics = font.metrics()
        line_height = font_metrics['linespace']
        
        # Calculate width for 160 characters of the chosen font
        line_num_width = font.measure('000000')
        total_content_chars = 160
        content_width = total_content_chars * char_width
        scrollbar_width = 20
        diff_map_width = 30
        
        # Calculate height for 50 lines
        num_lines = 50
        content_height = num_lines * line_height
        status_bar_height = 30
        h_scrollbar_height = 20
        
        # Total width: line numbers (both sides) + content + diff map + scrollbar + padding
        total_width = (line_num_width * 2) + content_width + diff_map_width + scrollbar_width + 20
        total_height = content_height + status_bar_height + h_scrollbar_height + 20
        
        self.root.geometry(f"{total_width}x{total_height}")
    
    def bind_keys(self):
        """Bind keyboard shortcuts"""
        # Bind to root window
        self.root.bind('<n>', lambda e: self.next_change())
        self.root.bind('<N>', lambda e: self.next_change())
        self.root.bind('<p>', lambda e: self.prev_change())
        self.root.bind('<P>', lambda e: self.prev_change())
        self.root.bind('<t>', lambda e: self.go_to_top())
        self.root.bind('<T>', lambda e: self.go_to_top())
        self.root.bind('<b>', lambda e: self.go_to_bottom())
        self.root.bind('<B>', lambda e: self.go_to_bottom())
        self.root.bind('<Escape>', lambda e: self.root.quit())
        
        # Also bind to text widgets so keys work when they have focus
        # Return "break" to prevent default text insertion behavior
        for widget in [self.base_content_text, self.modified_content_text]:
            widget.bind('<n>', lambda e: self.next_change() or "break")
            widget.bind('<N>', lambda e: self.next_change() or "break")
            widget.bind('<p>', lambda e: self.prev_change() or "break")
            widget.bind('<P>', lambda e: self.prev_change() or "break")
            widget.bind('<t>', lambda e: self.go_to_top() or "break")
            widget.bind('<T>', lambda e: self.go_to_top() or "break")
            widget.bind('<b>', lambda e: self.go_to_bottom() or "break")
            widget.bind('<B>', lambda e: self.go_to_bottom() or "break")
            widget.bind('<Escape>', lambda e: self.root.quit() or "break")
    
    def on_v_scroll(self, *args):
        """Handle vertical scrolling"""
        self.base_content_text.yview(*args)
        self.modified_content_text.yview(*args)
        self.base_line_text.yview(*args)
        self.modified_line_text.yview(*args)
        self.update_diff_map()
    
    def on_h_scroll(self, *args):
        """Handle horizontal scrolling"""
        self.base_content_text.xview(*args)
        self.modified_content_text.xview(*args)
    
    def update_scrollbar(self, *args):
        """Update scrollbar position and sync vertical scrolling"""
        self.v_scrollbar.set(*args)
        self.modified_content_text.yview_moveto(args[0])
        self.base_line_text.yview_moveto(args[0])
        self.modified_line_text.yview_moveto(args[0])
        self.update_diff_map()
    
    def update_h_scrollbar(self, *args):
        """Update horizontal scrollbar and sync horizontal scrolling"""
        self.h_scrollbar.set(*args)
        self.modified_content_text.xview_moveto(args[0])
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel scrolling"""
        if event.num == 5 or event.delta < 0:
            delta = 1
        else:
            delta = -1
        
        self.base_content_text.yview_scroll(delta, 'units')
        self.modified_content_text.yview_scroll(delta, 'units')
        self.base_line_text.yview_scroll(delta, 'units')
        self.modified_line_text.yview_scroll(delta, 'units')
        self.update_diff_map()
    
    def on_line_click(self, event, side):
        """Handle line click"""
        text_widget = self.base_content_text if side == 'base' else self.modified_content_text
        index = text_widget.index(f'@{event.x},{event.y}')
        line_num = int(index.split('.')[0]) - 1
        
        # Highlight line numbers
        self.selected_line = line_num
        self.highlight_line_numbers(line_num)
        
        # Find which change region this is in
        for i, (tag, display_start, display_end, i1, i2, j1, j2) in enumerate(self.change_regions):
            if display_start <= line_num < display_end:
                self.current_region = i
                self.update_status()
                break
    
    def highlight_line_numbers(self, line_num):
        """Highlight line numbers for selected line"""
        # Clear previous highlights
        for text in [self.base_line_text, self.modified_line_text]:
            text.config(state=tk.NORMAL)
            text.tag_remove('highlight', '1.0', tk.END)
            text.config(state=tk.DISABLED)
        
        # Add new highlights
        for text in [self.base_line_text, self.modified_line_text]:
            text.config(state=tk.NORMAL)
            text.tag_add('highlight', f'{line_num+1}.0', f'{line_num+2}.0')
            text.tag_config('highlight', background='white', foreground='black')
            text.config(state=tk.DISABLED)
    
    def on_double_click(self, event, side):
        """Handle double-click for note taking"""
        if not self.note_file:
            messagebox.showinfo('Note Taking Disabled',
                              'No note taking file supplied. Note taking disabled.',
                              parent=self.root)
            return
        
        text_widget = self.base_content_text if side == 'base' else self.modified_content_text
        line_nums = self.base_line_nums if side == 'base' else self.modified_line_nums
        display_lines = self.base_display if side == 'base' else self.modified_display
        filename = self.base_file if side == 'base' else self.modified_file
        
        index = text_widget.index(f'@{event.x},{event.y}')
        line_num = int(index.split('.')[0]) - 1
        
        if line_nums[line_num] is None:
            return
        
        with open(self.note_file, 'a') as f:
            prefix = '(base): ' if side == 'base' else '(modi): '
            f.write(f"{prefix}{filename}\n")
            f.write(f"  {line_nums[line_num]}: {display_lines[line_num]}\n\n")
        
        # Mark line as noted
        self.mark_noted_line(side, line_nums[line_num])
        
        self.note_count += 1
        self.update_status()
    
    def on_diff_map_click(self, event):
        """Handle click on diff map"""
        total_lines = len(self.base_display)
        canvas_height = self.diff_map.winfo_height()
        
        clicked_ratio = event.y / canvas_height
        target_line = int(clicked_ratio * total_lines)
        
        # Find which change region contains this line
        for i, (tag, display_start, display_end, i1, i2, j1, j2) in enumerate(self.change_regions):
            if display_start <= target_line < display_end:
                self.current_region = i
                break
        else:
            # If not in a change region, find the nearest one
            min_distance = float('inf')
            nearest_region = self.current_region
            for i, (tag, display_start, display_end, i1, i2, j1, j2) in enumerate(self.change_regions):
                distance = min(abs(target_line - display_start), abs(target_line - display_end))
                if distance < min_distance:
                    min_distance = distance
                    nearest_region = i
            self.current_region = nearest_region
        
        self.center_on_line(target_line)
        self.update_status()
    
    def center_on_line(self, line_num):
        """Center view on specific line"""
        # Use see() to make the line visible, which centers it better
        line_index = f"{line_num+1}.0"
        self.base_content_text.see(line_index)
        self.modified_content_text.see(line_index)
        self.base_line_text.see(line_index)
        self.modified_line_text.see(line_index)
        self.update_diff_map()
    
    def next_change(self):
        """Go to next change region"""
        if not self.change_regions:
            return
        
        if self.current_region < len(self.change_regions) - 1:
            self.current_region += 1
            tag, display_start, display_end, i1, i2, j1, j2 = self.change_regions[self.current_region]
            self.center_on_line(display_start)
            self.highlight_current_region()
            self.update_status()
    
    def prev_change(self):
        """Go to previous change region"""
        if not self.change_regions:
            return
        
        if self.current_region > 0:
            self.current_region -= 1
            tag, display_start, display_end, i1, i2, j1, j2 = self.change_regions[self.current_region]
            self.center_on_line(display_start)
            self.highlight_current_region()
            self.update_status()
    
    def highlight_current_region(self):
        """Highlight the current change region with a box."""
        if not self.change_regions:
            return
        
        # Remove previous region highlights
        self.base_content_text.tag_remove('current_region', '1.0', tk.END)
        self.modified_content_text.tag_remove('current_region', '1.0', tk.END)
        
        # Add box around current region
        tag, display_start, display_end, i1, i2, j1, j2 = self.change_regions[self.current_region]
        start_idx = f"{display_start+1}.0"
        end_idx = f"{display_end+1}.0"
        
        self.base_content_text.tag_add('current_region', start_idx, end_idx)
        self.modified_content_text.tag_add('current_region', start_idx, end_idx)
    
    def go_to_top(self):
        """Go to top with first change region"""
        if self.change_regions:
            self.current_region = 0
        
        self.base_content_text.yview_moveto(0)
        self.modified_content_text.yview_moveto(0)
        self.base_line_text.yview_moveto(0)
        self.modified_line_text.yview_moveto(0)
        self.highlight_current_region()
        self.update_diff_map()
        self.update_status()
    
    def go_to_bottom(self):
        """Go to bottom with last change region"""
        if self.change_regions:
            self.current_region = len(self.change_regions) - 1
        
        self.base_content_text.yview_moveto(1.0)
        self.modified_content_text.yview_moveto(1.0)
        self.base_line_text.yview_moveto(1.0)
        self.modified_line_text.yview_moveto(1.0)
        self.highlight_current_region()
        self.update_diff_map()
        self.update_status()
    
    def update_status(self):
        """Update status bar"""
        total_regions = len(self.change_regions)
        current = self.current_region + 1 if total_regions > 0 else 0
        self.region_label.config(text=f"Region: {current} of {total_regions}")
        self.notes_label.config(text=f"Notes: {self.note_count}")
    
    def run(self):
        """Run the application"""
        self.root.mainloop()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python diff_viewer.py <base_file> <modified_file> [note_file]")
        sys.exit(1)
    
    base_file = sys.argv[1]
    modified_file = sys.argv[2]
    note_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        viewer = DiffViewer(base_file, modified_file, note_file)
        viewer.run()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)