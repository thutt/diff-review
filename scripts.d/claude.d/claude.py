#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import sys
import difflib
import os

class DiffViewer:
    def __init__(self, root, base_file, modified_file, notes_file=None):
        self.root = root
        self.root.title(f"Diff Viewer: {base_file} vs {modified_file}")

        # Store file names
        self.base_file = base_file
        self.modified_file = modified_file
        self.notes_file = notes_file

        # Calculate window width to accommodate 160 characters
        char_width = 7.2
        content_width = int(160 * char_width)
        line_num_width = 60
        diff_map_width = 30
        scrollbar_width = 20
        total_width = (2 * (line_num_width + content_width)) + diff_map_width + scrollbar_width + 20

        self.root.geometry(f"{int(total_width)}x800")

        # Read files
        with open(base_file, 'r') as f:
            self.base_lines = f.readlines()
        with open(modified_file, 'r') as f:
            self.modified_lines = f.readlines()

        # Calculate differences and create aligned display
        self.create_aligned_diff()

        # Create main frame
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Configure grid weights for resizing
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=0)
        self.main_frame.grid_columnconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(3, weight=0)

        # Create widgets
        self.create_widgets()

        # Populate canvases
        self.populate_canvases()

        # Bind events
        self.bind_events()

        # Create context menu
        self.create_context_menu()

    def get_intraline_diff(self, line1, line2):
        """Calculate character-level differences between two lines"""
        matcher = difflib.SequenceMatcher(None, line1, line2)
        changes_line1 = []
        changes_line2 = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'delete':
                changes_line1.append((i1, i2, 'deletion'))
            elif tag == 'insert':
                changes_line2.append((j1, j2, 'addition'))
            elif tag == 'replace':
                changes_line1.append((i1, i2, 'change'))
                changes_line2.append((j1, j2, 'change'))

        return changes_line1, changes_line2

    def create_aligned_diff(self):
        """Create aligned display with blank lines for additions/deletions"""
        matcher = difflib.SequenceMatcher(None, self.base_lines, self.modified_lines)

        self.aligned_base = []
        self.aligned_modified = []
        self.base_line_numbers = []
        self.modified_line_numbers = []
        self.diff_types = []
        self.intraline_changes = []
        self.change_blocks = []
        self.current_change_index = -1

        base_line_num = 1
        modified_line_num = 1
        current_block_start = None
        current_block_type = None

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                if current_block_start is not None:
                    self.change_blocks.append((current_block_start, len(self.aligned_base) - 1, current_block_type))
                    current_block_start = None
                    current_block_type = None

                for i, j in zip(range(i1, i2), range(j1, j2)):
                    self.aligned_base.append(self.base_lines[i])
                    self.aligned_modified.append(self.modified_lines[j])
                    self.base_line_numbers.append(base_line_num)
                    self.modified_line_numbers.append(modified_line_num)
                    self.diff_types.append('normal')
                    self.intraline_changes.append(([], []))
                    base_line_num += 1
                    modified_line_num += 1

            elif tag == 'delete':
                if current_block_start is None:
                    current_block_start = len(self.aligned_base)
                    current_block_type = 'deletion'

                for i in range(i1, i2):
                    self.aligned_base.append(self.base_lines[i])
                    self.aligned_modified.append('')
                    self.base_line_numbers.append(base_line_num)
                    self.modified_line_numbers.append(None)
                    self.diff_types.append('deletion')
                    line_len = len(self.base_lines[i].rstrip('\n'))
                    self.intraline_changes.append(([(0, line_len, 'deletion')], []))
                    base_line_num += 1

            elif tag == 'insert':
                if current_block_start is None:
                    current_block_start = len(self.aligned_base)
                    current_block_type = 'addition'

                for j in range(j1, j2):
                    self.aligned_base.append('')
                    self.aligned_modified.append(self.modified_lines[j])
                    self.base_line_numbers.append(None)
                    self.modified_line_numbers.append(modified_line_num)
                    self.diff_types.append('addition')
                    line_len = len(self.modified_lines[j].rstrip('\n'))
                    self.intraline_changes.append(([], [(0, line_len, 'addition')]))
                    modified_line_num += 1

            elif tag == 'replace':
                if current_block_start is None:
                    current_block_start = len(self.aligned_base)
                    current_block_type = 'change'

                base_count = i2 - i1
                mod_count = j2 - j1
                max_count = max(base_count, mod_count)

                for k in range(max_count):
                    base_changes = []
                    mod_changes = []

                    if k < base_count and k < mod_count:
                        base_line = self.base_lines[i1 + k].rstrip('\n')
                        mod_line = self.modified_lines[j1 + k].rstrip('\n')
                        base_changes, mod_changes = self.get_intraline_diff(base_line, mod_line)
                    elif k < base_count:
                        line_len = len(self.base_lines[i1 + k].rstrip('\n'))
                        base_changes = [(0, line_len, 'deletion')]
                    else:
                        line_len = len(self.modified_lines[j1 + k].rstrip('\n'))
                        mod_changes = [(0, line_len, 'addition')]

                    if k < base_count:
                        self.aligned_base.append(self.base_lines[i1 + k])
                        self.base_line_numbers.append(base_line_num)
                        base_line_num += 1
                    else:
                        self.aligned_base.append('')
                        self.base_line_numbers.append(None)

                    if k < mod_count:
                        self.aligned_modified.append(self.modified_lines[j1 + k])
                        self.modified_line_numbers.append(modified_line_num)
                        modified_line_num += 1
                    else:
                        self.aligned_modified.append('')
                        self.modified_line_numbers.append(None)

                    self.diff_types.append('change')
                    self.intraline_changes.append((base_changes, mod_changes))

        if current_block_start is not None:
            self.change_blocks.append((current_block_start, len(self.aligned_base) - 1, current_block_type))

    def create_widgets(self):
        """Create all GUI widgets"""
        # Left canvas (base file)
        self.left_canvas = tk.Canvas(self.main_frame, bg='white')
        self.left_canvas.grid(row=0, column=0, sticky='nsew')

        # Diff map in center
        self.diff_map = tk.Canvas(self.main_frame, width=30, bg='light gray', cursor='hand2')
        self.diff_map.grid(row=0, column=1, sticky='ns')

        # Right canvas (modified file)
        self.right_canvas = tk.Canvas(self.main_frame, bg='white')
        self.right_canvas.grid(row=0, column=2, sticky='nsew')

        # Vertical scrollbar on right
        self.v_scrollbar = tk.Scrollbar(self.main_frame, orient=tk.VERTICAL)
        self.v_scrollbar.grid(row=0, column=3, sticky='ns')
        self.v_scrollbar.config(command=self.sync_vertical_scroll)

        # Horizontal scrollbar at bottom
        self.h_scrollbar = tk.Scrollbar(self.main_frame, orient=tk.HORIZONTAL)
        self.h_scrollbar.grid(row=1, column=0, columnspan=3, sticky='ew')
        self.h_scrollbar.config(command=self.sync_horizontal_scroll)

        # Create text widgets
        self.create_text_widgets()

    def create_text_widgets(self):
        """Create text widgets for line numbers and content"""
        # Left side (base file)
        self.left_line_text = tk.Text(self.left_canvas, width=6, state='disabled',
                                      bg='light grey', fg='grey', font=('Courier', 12, 'bold'),
                                      takefocus=0, cursor='arrow')
        self.left_content_text = tk.Text(self.left_canvas, state='disabled',
                                         wrap='none', font=('Courier', 12, 'bold'),
                                         bg='light grey')

        # Right side (modified file)
        self.right_line_text = tk.Text(self.right_canvas, width=6, state='disabled',
                                       bg='light grey', fg='grey', font=('Courier', 12, 'bold'),
                                       takefocus=0, cursor='arrow')
        self.right_content_text = tk.Text(self.right_canvas, state='disabled',
                                          wrap='none', font=('Courier', 12, 'bold'),
                                          bg='light grey')

        # Pack text widgets
        self.left_line_text.pack(side=tk.LEFT, fill=tk.Y)
        self.left_content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.right_line_text.pack(side=tk.LEFT, fill=tk.Y)
        self.right_content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Disable selection in line number widgets
        for line_widget in [self.left_line_text, self.right_line_text]:
            line_widget.bind('<Button-1>', lambda e: 'break')
            line_widget.bind('<B1-Motion>', lambda e: 'break')
            line_widget.bind('<Double-Button-1>', lambda e: 'break')
            line_widget.bind('<Triple-Button-1>', lambda e: 'break')

        # Configure tags for highlighting
        for text_widget in [self.left_content_text, self.right_content_text]:
            text_widget.tag_config('blank', background='dark grey')

        # Line number widgets also need blank tag
        for line_widget in [self.left_line_text, self.right_line_text]:
            line_widget.tag_config('blank', background='dark grey')

        # Intraline highlighting tags
        self.left_content_text.tag_config('intra_deletion', background='red')
        self.left_content_text.tag_config('intra_change', background='salmon')

        self.right_content_text.tag_config('intra_addition', background='green')
        self.right_content_text.tag_config('intra_change', background='salmon')

        # Raise intraline tags
        self.left_content_text.tag_raise('intra_deletion')
        self.left_content_text.tag_raise('intra_change')
        self.right_content_text.tag_raise('intra_addition')
        self.right_content_text.tag_raise('intra_change')

    def populate_canvases(self):
        """Populate text widgets with aligned file content"""
        # Calculate maximum line length for blank line padding
        max_line_len = 0
        for line in self.aligned_base + self.aligned_modified:
            if line:
                max_line_len = max(max_line_len, len(line.rstrip('\n')))

        self.left_line_text.config(state='normal')
        self.left_content_text.config(state='normal')
        self.right_line_text.config(state='normal')
        self.right_content_text.config(state='normal')

        for i in range(len(self.aligned_base)):
            # Left side (base file)
            base_line_num = self.base_line_numbers[i]
            if base_line_num is not None:
                self.left_line_text.insert(tk.END, f"{base_line_num:>6}\n")
            else:
                self.left_line_text.insert(tk.END, f"{'':>6}\n")
                # Add dark grey background to line number for blank lines
                self.left_line_text.tag_add('blank', f"{i+1}.0", f"{i+1}.end")

            base_content = self.aligned_base[i]
            if not base_content:
                self.left_content_text.insert(tk.END, " " * max_line_len + "\n")
                self.left_content_text.tag_add('blank', f"{i+1}.0", f"{i+1}.end")
            else:
                self.left_content_text.insert(tk.END, base_content)
                base_changes, _ = self.intraline_changes[i]
                for start, end, change_type in base_changes:
                    tag_name = 'intra_deletion' if change_type == 'deletion' else 'intra_change'
                    self.left_content_text.tag_add(tag_name, f"{i+1}.{start}", f"{i+1}.{end}")

            # Right side (modified file)
            mod_line_num = self.modified_line_numbers[i]
            if mod_line_num is not None:
                self.right_line_text.insert(tk.END, f"{mod_line_num:>6}\n")
            else:
                self.right_line_text.insert(tk.END, f"{'':>6}\n")
                # Add dark grey background to line number for blank lines
                self.right_line_text.tag_add('blank', f"{i+1}.0", f"{i+1}.end")

            mod_content = self.aligned_modified[i]
            if not mod_content:
                self.right_content_text.insert(tk.END, " " * max_line_len + "\n")
                self.right_content_text.tag_add('blank', f"{i+1}.0", f"{i+1}.end")
            else:
                self.right_content_text.insert(tk.END, mod_content)
                _, mod_changes = self.intraline_changes[i]
                for start, end, change_type in mod_changes:
                    tag_name = 'intra_addition' if change_type == 'addition' else 'intra_change'
                    self.right_content_text.tag_add(tag_name, f"{i+1}.{start}", f"{i+1}.{end}")

        self.left_line_text.config(state='disabled')
        self.left_content_text.config(state='disabled')
        self.right_line_text.config(state='disabled')
        self.right_content_text.config(state='disabled')

        self.draw_diff_map()

    def draw_diff_map(self):
        """Draw the diff map"""
        self.diff_map.delete('all')
        height = self.diff_map.winfo_height()
        if height <= 1:
            self.root.after(100, self.draw_diff_map)
            return

        total_lines = len(self.aligned_base)
        if total_lines == 0:
            return

        self.map_items = []

        # Draw change blocks
        for start_line, end_line, change_type in self.change_blocks:
            y1 = (start_line / total_lines) * height
            y2 = ((end_line + 1) / total_lines) * height

            if y2 - y1 < 3:
                y2 = y1 + 3

            if change_type == 'deletion':
                color = 'red'
            elif change_type == 'addition':
                color = 'green'
            else:
                color = 'blue'

            item = self.diff_map.create_rectangle(0, y1, 30, y2, fill=color, outline=color)
            self.map_items.append((item, start_line, end_line, change_type))

        # Draw viewport indicator
        try:
            top, bottom = self.left_content_text.yview()
            indicator_top = int(top * height)
            indicator_bottom = int(bottom * height)

            self.diff_map.create_rectangle(0, indicator_top, 30, indicator_bottom,
                                          fill='grey', stipple='gray50', outline='')
        except:
            pass

    def jump_to_line(self, line_num):
        """Jump to a specific line and center it"""
        total_lines = len(self.aligned_base)
        if total_lines == 0:
            return

        try:
            visible_lines = int(self.left_content_text.index('@0,0').split('.')[0])
            bottom_visible = int(self.left_content_text.index(f'@0,{self.left_content_text.winfo_height()}').split('.')[0])
            visible_height = bottom_visible - visible_lines

            center_offset = visible_height // 2
            target_line = max(0, line_num - center_offset)

            fraction = target_line / total_lines

            self.left_content_text.yview_moveto(fraction)
            self.right_content_text.yview_moveto(fraction)
            self.left_line_text.yview_moveto(fraction)
            self.right_line_text.yview_moveto(fraction)
            self.update_scrollbar()
            self.update_viewport_indicator()
        except:
            pass

    def next_change(self, event=None):
        """Jump to the next change block"""
        if not self.change_blocks:
            return

        self.current_change_index = (self.current_change_index + 1) % len(self.change_blocks)
        start_line, end_line, change_type = self.change_blocks[self.current_change_index]
        self.jump_to_line(start_line)

    def prev_change(self, event=None):
        """Jump to the previous change block"""
        if not self.change_blocks:
            return

        self.current_change_index = (self.current_change_index - 1) % len(self.change_blocks)
        start_line, end_line, change_type = self.change_blocks[self.current_change_index]
        self.jump_to_line(start_line)

    def on_map_click(self, event):
        """Handle clicks on the diff map - center corresponding area"""
        height = self.diff_map.winfo_height()
        total_lines = len(self.aligned_base)
        if total_lines == 0:
            return

        y = event.y
        fraction = y / height
        target_line = int(fraction * total_lines)

        self.jump_to_line(target_line)

    def on_single_click(self, event, text_widget):
        """Handle single click to select entire line"""
        # Store click position and time for detecting drag vs click
        self.click_start_pos = text_widget.index(f"@{event.x},{event.y}")
        self.click_start_time = event.time
        # Don't return 'break' - allow default behavior initially

    def on_button_release(self, event, text_widget):
        """Handle button release - select line only if no drag occurred"""
        try:
            release_pos = text_widget.index(f"@{event.x},{event.y}")

            # Check if this was a drag (different position) or a click (same position)
            if hasattr(self, 'click_start_pos') and self.click_start_pos == release_pos:
                # It was a click, not a drag - select the entire line
                line_num = int(release_pos.split('.')[0])
                text_widget.tag_remove(tk.SEL, "1.0", tk.END)
                text_widget.tag_add(tk.SEL, f"{line_num}.0", f"{line_num}.end")
                text_widget.mark_set(tk.INSERT, f"{line_num}.0")
        except:
            pass

    def on_double_click(self, event, text_widget, file_name, line_numbers, file_label):
        """Handle double-click to take note of single line"""
        if not self.notes_file:
            # Show dialog if no notes file supplied
            from tkinter import messagebox
            messagebox.showinfo("Note Taking Disabled",
                              "No note taking file supplied. Note taking disabled.",
                              parent=self.root)
            return

        try:
            # Get the line that was clicked
            index = text_widget.index(f"@{event.x},{event.y}")
            line_num = int(index.split('.')[0])

            # Get actual file line number
            actual_line_num = line_numbers[line_num - 1]
            if actual_line_num is None:
                return  # Don't note blank lines

            # Get the line text
            line_text = text_widget.get(f"{line_num}.0", f"{line_num}.end")

            # Append to notes file
            with open(self.notes_file, 'a') as f:
                f.write(f"{file_label}: {file_name}\n")
                f.write(f"  {actual_line_num}:{line_text}\n\n")
        except:
            pass

    def create_context_menu(self):
        """Create right-click context menu"""
        self.context_menu = tk.Menu(self.root, tearoff=0)

        if self.notes_file:
            self.context_menu.add_command(label="Take Note", command=self.take_note_from_menu)
        else:
            self.context_menu.add_command(label="Take Note (no file supplied)", command=None, state=tk.DISABLED)

        # Store which widget was right-clicked
        self.context_widget = None
        self.context_file_name = None
        self.context_line_numbers = None
        self.context_file_label = None

    def show_context_menu(self, event, text_widget, file_name, line_numbers, file_label):
        """Show context menu on right-click"""
        self.context_widget = text_widget
        self.context_file_name = file_name
        self.context_line_numbers = line_numbers
        self.context_file_label = file_label

        # Check if there's a selection and notes file exists
        try:
            sel_start = text_widget.index(tk.SEL_FIRST)
            sel_end = text_widget.index(tk.SEL_LAST)
            has_selection = True
        except:
            has_selection = False

        # Enable or disable menu item based on selection and notes file
        if self.notes_file:
            if has_selection:
                self.context_menu.entryconfig(0, state=tk.NORMAL)
            else:
                self.context_menu.entryconfig(0, state=tk.DISABLED)

        self.context_menu.post(event.x_root, event.y_root)

    def take_note_from_menu(self):
        """Take note of selected lines"""
        if not self.context_widget:
            return

        try:
            # Get selection range
            sel_start = self.context_widget.index(tk.SEL_FIRST)
            sel_end = self.context_widget.index(tk.SEL_LAST)

            start_line = int(sel_start.split('.')[0])
            end_line = int(sel_end.split('.')[0])

            # Append to notes file
            with open(self.notes_file, 'a') as f:
                f.write(f"{self.context_file_label}: {self.context_file_name}\n")

                for line_num in range(start_line, end_line + 1):
                    actual_line_num = self.context_line_numbers[line_num - 1]
                    if actual_line_num is None:
                        continue  # Skip blank lines

                    line_text = self.context_widget.get(f"{line_num}.0", f"{line_num}.end")
                    f.write(f"  {actual_line_num}:{line_text}\n")

                f.write("\n")
        except:
            pass

    def sync_vertical_scroll(self, *args):
        """Synchronize vertical scrolling"""
        self.left_line_text.yview(*args)
        self.left_content_text.yview(*args)
        self.right_line_text.yview(*args)
        self.right_content_text.yview(*args)
        self.update_scrollbar()
        self.update_viewport_indicator()

    def sync_horizontal_scroll(self, *args):
        """Synchronize horizontal scrolling of content only"""
        self.left_content_text.xview(*args)
        self.right_content_text.xview(*args)
        self.update_h_scrollbar()

    def update_scrollbar(self):
        """Update vertical scrollbar position"""
        top, bottom = self.left_content_text.yview()
        self.v_scrollbar.set(top, bottom)

    def update_viewport_indicator(self):
        """Update the viewport indicator on the diff map"""
        self.draw_diff_map()

    def update_h_scrollbar(self):
        """Update horizontal scrollbar position"""
        left, right = self.left_content_text.xview()
        self.h_scrollbar.set(left, right)

    def bind_events(self):
        """Bind keyboard and mouse events"""
        self.root.bind('<Escape>', lambda e: self.root.quit())
        self.root.bind('n', self.next_change)
        self.root.bind('N', self.next_change)
        self.root.bind('p', self.prev_change)
        self.root.bind('P', self.prev_change)

        # Single-click to select entire line (on button release)
        self.left_content_text.bind('<Button-1>',
            lambda e: self.on_single_click(e, self.left_content_text))
        self.right_content_text.bind('<Button-1>',
            lambda e: self.on_single_click(e, self.right_content_text))

        self.left_content_text.bind('<ButtonRelease-1>',
            lambda e: self.on_button_release(e, self.left_content_text))
        self.right_content_text.bind('<ButtonRelease-1>',
            lambda e: self.on_button_release(e, self.right_content_text))

        # Double-click for note taking
        self.left_content_text.bind('<Double-Button-1>',
            lambda e: self.on_double_click(e, self.left_content_text, self.base_file, self.base_line_numbers, '(base)'))
        self.right_content_text.bind('<Double-Button-1>',
            lambda e: self.on_double_click(e, self.right_content_text, self.modified_file, self.modified_line_numbers, '(modi)'))

        # Right-click context menu
        self.left_content_text.bind('<Button-3>',
            lambda e: self.show_context_menu(e, self.left_content_text, self.base_file, self.base_line_numbers, '(base)'))
        self.right_content_text.bind('<Button-3>',
            lambda e: self.show_context_menu(e, self.right_content_text, self.modified_file, self.modified_line_numbers, '(modi)'))

        # Mouse wheel scrolling
        for widget in [self.left_canvas, self.right_canvas, self.left_line_text,
                      self.left_content_text, self.right_line_text, self.right_content_text,
                      self.diff_map]:
            widget.bind('<MouseWheel>', self.on_mousewheel)
            widget.bind('<Button-4>', self.on_mousewheel)
            widget.bind('<Button-5>', self.on_mousewheel)

        # Text widget scrolling
        for widget in [self.left_content_text, self.right_content_text]:
            widget.config(yscrollcommand=self.on_text_scroll)
            widget.config(xscrollcommand=self.on_h_text_scroll)

        self.diff_map.bind('<Configure>', lambda e: self.draw_diff_map())
        self.diff_map.bind('<Button-1>', self.on_map_click)

    def on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        if event.num == 5 or event.delta < 0:
            delta = 1
        else:
            delta = -1
        self.left_content_text.yview_scroll(delta, 'units')
        self.right_content_text.yview_scroll(delta, 'units')
        self.left_line_text.yview_scroll(delta, 'units')
        self.right_line_text.yview_scroll(delta, 'units')
        self.update_scrollbar()
        self.update_viewport_indicator()
        return 'break'

    def on_text_scroll(self, *args):
        """Handle text widget vertical scroll events"""
        self.v_scrollbar.set(*args)
        self.sync_vertical_scroll('moveto', args[0])

    def on_h_text_scroll(self, *args):
        """Handle text widget horizontal scroll events"""
        self.h_scrollbar.set(*args)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python diff_viewer.py <base_file> <modified_file> [notes_file]")
        sys.exit(1)

    base_file = sys.argv[1]
    modified_file = sys.argv[2]
    notes_file = sys.argv[3] if len(sys.argv) >= 4 else None

    # Check that the directory for notes file exists if provided
    if notes_file:
        notes_dir = os.path.dirname(notes_file)
        if notes_dir and not os.path.exists(notes_dir):
            print(f"Error: Directory '{notes_dir}' does not exist")
            sys.exit(1)

    try:
        root = tk.Tk()
        app = DiffViewer(root, base_file, modified_file, notes_file)
        root.mainloop()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
