#!/usr/bin/env python3
# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Help dialog for diff_review

This module contains the help dialog that displays user documentation.
"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton


class HelpDialog(QDialog):
    """Dialog that displays help documentation for the diff viewer"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Diff Viewer - How to Use")
        self.setMinimumSize(700, 600)
        
        layout = QVBoxLayout(self)
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml(self.get_help_html())
        
        layout.addWidget(help_text)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
    
    @staticmethod
    def get_help_html():
        """Returns the HTML content for the help dialog"""
        return """
        <h2>Diff Viewer - User Guide</h2>
        
        <h3>Overview</h3>
        <p>This diff viewer displays side-by-side comparison of files with synchronized scrolling and highlighting of changes. Multiple diffs can be opened in tabs with a sidebar for file navigation.</p>
        
        <h3>Sidebar</h3>
        <ul>
            <li><b>File List:</b> Click any file to open it in a new tab (or switch to existing tab)</li>
            <li><b>Open All Files:</b> Button at top opens all files at once</li>
            <li><b>Blue Mark:</b> Indicates which files have open tabs</li>
            <li><b>Ctrl+B / Cmd+B:</b> Toggle sidebar visibility</li>
            <li><b>Resizable:</b> Drag the divider to resize the sidebar</li>
        </ul>
        
        <h3>Tab Management</h3>
        <ul>
            <li><b>Ctrl+Tab:</b> Switch to next tab (left-to-right, wraps around)</li>
            <li><b>Ctrl+Shift+Tab:</b> Switch to previous tab (right-to-left, wraps around)</li>
            <li><b>Ctrl+W:</b> Close current tab</li>
            <li><b>Ctrl+Q:</b> Quit application</li>
            <li><b>X button:</b> Close individual tabs</li>
            <li>Clicking a file in the sidebar switches to its tab if already open</li>
        </ul>
        
        <h3>Navigation</h3>
        <ul>
            <li><b>Arrow Keys:</b> Navigate up/down/left/right</li>
            <li><b>Tab:</b> When focus is in a text pane, switch focus between base and modified panes (stays on same line). When focus is elsewhere, navigate between UI elements.</li>
            <li><b>N:</b> Jump to next change region</li>
            <li><b>P:</b> Jump to previous change region</li>
            <li><b>C:</b> Center on the currently selected region</li>
            <li><b>T:</b> Jump to top of file</li>
            <li><b>B:</b> Jump to bottom of file</li>
            <li><b>Escape:</b> Close the application</li>
        </ul>
        
        <h3>Visual Indicators</h3>
        <ul>
            <li><b>Blue Border:</b> Thin blue box around current line in the focused pane</li>
            <li><b>Gray Border:</b> Thin gray box around current line in the non-focused pane</li>
            <li><b>Yellow Background:</b> Lines where notes have been taken</li>
            <li><b>Magenta Vertical Line:</b> Indicates the maximum allowed line length; content beyond this line exceeds the character limit</li>
        </ul>
        
        <h3>Progressive Highlighting</h3>
        <p>Files are highlighted in the background when tabs are first opened. A status message appears at the bottom of each viewer showing highlighting progress (e.g., "Highlighting: 45% (2250/5000 lines)"). The viewer remains fully interactive during highlighting. Large files may take a few seconds to complete.</p>
        
        <h3>Color Coding</h3>
        <p>The diff viewer uses a colorblind-friendly palette by default (blue/orange). You can switch to the traditional red/green palette via the Palette menu.</p>
        <ul>
            <li><b>Colorblind Friendly (Default):</b>
                <ul>
                    <li><span style="background-color: rgb(200, 220, 255); padding: 2px 6px;">Added lines background</span> / <span style="background-color: rgb(135, 206, 250); padding: 2px 6px;">added text</span></li>
                    <li><span style="background-color: rgb(255, 220, 180); padding: 2px 6px;">Deleted lines background</span> / <span style="background-color: rgb(255, 140, 0); padding: 2px 6px;">deleted text</span></li>
                    <li><span style="background-color: rgb(255, 255, 100); padding: 2px 6px;">Modified content (intraline)</span></li>
                    <li>Line number backgrounds: <span style="background-color: rgb(200, 220, 255); padding: 2px 6px;">modified lines</span>, <span style="background-color: rgb(255, 220, 180); padding: 2px 6px;">base changes</span></li>
                </ul>
            </li>
            <li><b>Standard:</b>
                <ul>
                    <li><span style="background-color: rgb(220, 255, 220); padding: 2px 6px;">Added lines background</span> / <span style="background-color: lightgreen; padding: 2px 6px;">added text</span></li>
                    <li><span style="background-color: rgb(255, 220, 220); padding: 2px 6px;">Deleted lines background</span> / <span style="background-color: red; color: white; padding: 2px 6px;">deleted text</span></li>
                    <li><span style="background-color: yellow; padding: 2px 6px;">Modified content (intraline)</span></li>
                    <li>Line number backgrounds: <span style="background-color: rgb(220, 255, 220); padding: 2px 6px;">modified lines</span>, <span style="background-color: rgb(255, 220, 220); padding: 2px 6px;">base changes</span></li>
                </ul>
            </li>
            <li><b>Both palettes:</b>
                <ul>
                    <li><span style="background-color: darkgray; padding: 2px 6px;">Placeholder lines (don't exist in one version)</span></li>
                    <li><span style="background-color: rgb(255, 0, 255); padding: 2px 6px;">Maximum line length indicator</span></li>
                    <li><span style="background-color: orange; padding: 2px 6px;">Unknown markers</span></li>
                </ul>
            </li>
        </ul>
        
        <h3>Search Functionality</h3>
        <ul>
            <li><b>Ctrl+S:</b> Open search dialog to search across base, modified, and commit message files</li>
            <li><b>Right-click â†’ Search:</b> Search for currently selected text</li>
            <li>Use checkboxes in search dialog to choose which sources to search (Base/Modi/Desc)</li>
            <li>Toggle case sensitivity in search dialog</li>
            <li>Double-click search results to jump to that location</li>
        </ul>
        
        <h3>Note Taking</h3>
        <ul>
            <li><b>Double-click:</b> Quick note - adds the clicked line to your notes file</li>
            <li><b>Right-click â†’ Take Note:</b> Add selected text to notes file</li>
            <li><b>Ctrl+N / Cmd+N:</b> Take note of selected text (works in commit message view too)</li>
            <li><b>Yellow background:</b> Lines where notes have been taken are highlighted</li>
            <li>All notes are appended to the notes file specified at startup</li>
        </ul>
        
        <h3>Diff Map</h3>
        <ul>
            <li>Vertical bar shows overview of all changes in the file</li>
            <li><b>Color scheme depends on selected palette:</b>
                <ul>
                    <li><b>Colorblind Friendly:</b> <span style="background-color: rgb(70, 130, 180); padding: 2px 6px;">Insertions</span>, <span style="background-color: rgb(255, 140, 0); padding: 2px 6px;">Deletions</span>, <span style="background-color: rgb(255, 200, 120); padding: 2px 6px;">Modifications</span></li>
                    <li><b>Standard:</b> <span style="background-color: green; padding: 2px 6px;">Insertions</span>, <span style="background-color: red; padding: 2px 6px;">Deletions</span>, <span style="background-color: salmon; padding: 2px 6px;">Modifications</span></li>
                </ul>
            </li>
            <li><span style="background-color: rgba(128, 128, 128, 0.4); padding: 2px 6px;">Gray rectangle: Current viewport position</span></li>
            <li><b>Click on diff map:</b> Jump to that location in the file</li>
            <li><b>Alt+H / Cmd+H:</b> Toggle diff map visibility</li>
            <li><b>Mouse wheel:</b> Scroll through the file</li>
        </ul>
        
        <h3>Line Numbers</h3>
        <ul>
            <li>Shows original line numbers from each file</li>
            <li>Background colors indicate changed lines (colors depend on selected palette)</li>
            <li><b>Alt+L / Cmd+L:</b> Toggle line number visibility</li>
        </ul>
        
        <h3>Whitespace Display</h3>
        <ul>
            <li><b>Show Whitespace:</b> View → Show Whitespace to toggle highlighting of all whitespace characters</li>
            <li><b>Show Tabs:</b> View → Show Tabs to toggle highlighting of tab characters</li>
            <li><b>Show Trailing Whitespace:</b> View → Show Trailing Whitespace to toggle highlighting of whitespace at end of lines</li>
            <li><b>Colors (Colorblind Friendly):</b> <span style="background-color: rgb(210, 210, 240); padding: 2px 6px;">Spaces (light purple-blue)</span>, <span style="background-color: rgb(255, 200, 100); padding: 2px 6px;">Tabs (light orange)</span>, <span style="background-color: rgb(255, 200, 150); padding: 2px 6px;">Trailing (light orange)</span></li>
            <li><b>Colors (Standard):</b> <span style="background-color: rgb(220, 220, 255); padding: 2px 6px;">Spaces (light blue)</span>, <span style="background-color: rgb(255, 180, 255); padding: 2px 6px;">Tabs (light magenta)</span>, <span style="background-color: rgb(255, 200, 200); padding: 2px 6px;">Trailing (light red)</span></li>
            <li>Toggle affects current tab immediately; other tabs update when viewed</li>
        </ul>
        
        <h3>Auto-reload Files</h3>
        <ul>
            <li><b>Automatic monitoring:</b> Watches source files for changes on disk</li>
            <li><b>Visual indicator:</b> Sidebar button changes to change-indicator color when files are modified</li>
            <li><b>Auto-reload (default ON):</b> Automatically reloads files 500ms after they stop changing</li>
            <li><b>Manual reload:</b> Press F5 to reload current file at any time</li>
            <li><b>Preserves position:</b> Scroll position is maintained after reload</li>
            <li><b>Toggle preference:</b> View â†’ Auto-reload Files to turn automatic reloading on/off</li>
            <li><b>Status notification:</b> Brief "File reloaded" message appears in status bar</li>
            <li><b>When OFF:</b> Files are still monitored, sidebar shows change indicator, but reload only happens with F5</li>
        </ul>
        
        <h3>Line Length Indicator</h3>
        <ul>
            <li>A vivid magenta vertical line marks the maximum allowed line length</li>
            <li>The line scrolls horizontally with the text content</li>
            <li>Any text to the right of this line exceeds the configured character limit</li>
            <li>The position is set via the --max-line-length parameter at startup</li>
        </ul>
        
        <h3>Color Palette</h3>
        <ul>
            <li><b>Access:</b> Use the Palette menu to switch between color schemes</li>
            <li><b>Colorblind Friendly (Default):</b> Uses blue/orange color scheme that is distinguishable for most types of colorblindness</li>
            <li><b>Standard:</b> Uses traditional red/green color scheme</li>
            <li><b>Instant Update:</b> All open tabs update immediately when palette is changed</li>
            <li><b>Persistent:</b> Selected palette applies to all subsequently opened files</li>
        </ul>
        
        <h3>Command Line Options</h3>
        <ul>
            <li><b>--display-n-lines:</b> Set number of lines visible in initial window (default: 60)</li>
            <li><b>--display-n-chars:</b> Set number of characters per pane in initial window (default: 90)</li>
            <li><b>--max-line-length:</b> Set maximum line length indicator position (default: 80)</li>
            <li><b>--note-file:</b> Specify file for saving notes</li>
        </ul>
        
        <h3>Status Bar</h3>
        <ul>
            <li><b>Region:</b> Shows current change region number and total regions</li>
            <li><b>Notes:</b> Count of notes taken during this session</li>
        </ul>
        
        <h3>Commit Message View</h3>
        <ul>
            <li>Click "Commit Message" in sidebar to view commit message/description</li>
            <li>Search and note-taking work the same way in commit message view</li>
            <li>Ctrl+S and Ctrl+N shortcuts work in commit message window</li>
        </ul>
        """
