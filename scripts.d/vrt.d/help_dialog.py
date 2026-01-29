# Copyright (c) 2025, 2026  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Help dialog for diff_review

This module contains the help dialog that displays user documentation.
Each help topic is available as a separate section that can be shown individually.
"""
import sys
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeySequence, QShortcut


# Help section identifiers
HELP_SECTION_OVERVIEW = "overview"
HELP_SECTION_TABS = "tabs"
HELP_SECTION_TERMINAL = "terminal"
HELP_SECTION_SIDEBAR = "sidebar"
HELP_SECTION_NAVIGATION = "navigation"
HELP_SECTION_COLORS = "colors"
HELP_SECTION_SEARCH = "search"
HELP_SECTION_NOTES = "notes"
HELP_SECTION_BOOKMARKS = "bookmarks"
HELP_SECTION_DIFFMAP = "diffmap"
HELP_SECTION_FILE_TREE = "file_tree"
HELP_SECTION_UNCOMMITTED = "uncommitted"
HELP_SECTION_COMMIT_LIST = "commit_list"
HELP_SECTION_ALL = "all"


def _get_mod_key():
    """Return the platform-appropriate modifier key name."""
    if sys.platform == 'darwin':
        return "Cmd"
    return "Ctrl"


def _get_mac_note():
    """Return Mac-specific note for non-Mac platforms."""
    if sys.platform == 'darwin':
        return ""
    return ("<p><strong>Mac Users:</strong> On macOS, use <b>Cmd</b> instead "
            "of <b>Ctrl</b> for all keyboard shortcuts (e.g., <b>Ctrl+H</b> "
            "becomes <b>Cmd+H</b>).</p>")


def get_help_overview():
    """Return HTML for Overview, Basic Usage, Focus Modes, Visual Indicators, Progressive Highlighting."""
    mod_key = _get_mod_key()
    mac_note = _get_mac_note()

    return f"""
    <h2>Diff Viewer - Overview</h2>

    <p><strong>Tip:</strong> Press <b>F1</b> or <b>{mod_key}+?</b> for a quick keyboard shortcuts reference card!</p>

    {mac_note}
    <h3>Overview</h3>
    <p>view-review-tabs is a graphical diff viewer for examining side-by-side file comparisons. It works with pre-generated diff directories containing base.d/ (original files) and modi.d/ (modified files) subdirectories.</p>

    <h3>Basic Usage</h3>
    <ul>
        <li><b>Start the viewer:</b> view-review-tabs --diff-dir /path/to/diff/directory</li>
        <li><b>Remote diffs:</b> view-review-tabs --diff-url https://example.com/diffs/review</li>
        <li><b>Multiple files:</b> Files are shown in a sidebar tree; click to open tabs</li>
        <li><b>Synchronized scrolling:</b> Both panes scroll together for easy comparison</li>
        <li><b>Change highlighting:</b> Insertions, deletions, and modifications are color-coded</li>
    </ul>

    <h3>Focus Modes</h3>
    <p>The viewer operates in two focus modes that control which area responds to keyboard input:</p>
    <ul>
        <li><b>Content Mode:</b> Keyboard input goes to the active tab (diff viewer, commit message, or review notes)</li>
        <li><b>Sidebar Mode:</b> Keyboard input goes to the file tree sidebar for navigation</li>
        <li><b>{mod_key}+\\:</b> Toggle between Content and Sidebar modes</li>
        <li><b>Visual feedback:</b> Unfocused area has a semi-transparent gray overlay</li>
        <li><b>Mouse clicks:</b> Clicking in an area automatically switches focus to that area</li>
        <li><b>Status bar:</b> Shows current focus mode (Content or Sidebar)</li>
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
    """


def get_help_tabs():
    """Return HTML for Tab Types and their shortcuts, Tab Management."""
    mod_key = _get_mod_key()

    return f"""
    <h2>Tab Types and Management</h2>

    <h3>Tab Types and Their Shortcuts</h3>
    <p>Different tab types support different keyboard shortcuts when in Content mode:</p>
    <ul>
        <li><b>Diff Viewer Tabs:</b> Full navigation (N/P/C/T/B), collapse regions (X), all common shortcuts</li>
        <li><b>Commit Message Tab:</b> Search ({mod_key}+S/{mod_key}+F), Take Note ({mod_key}+N), Jump to Note ({mod_key}+J), Bookmarks (M/[/])</li>
        <li><b>Review Notes Tab:</b> Search ({mod_key}+S/{mod_key}+F), standard text navigation</li>
        <li><b>Terminal Editor Tabs (Vim/Emacs):</b> All keys pass to editor; use escape prefix for global shortcuts (see below)</li>
        <li><b>All Tabs:</b> Tab switching (Ctrl+Tab/Ctrl+Shift+Tab), Close tab ({mod_key}+W), Search (F3/Shift+F3)</li>
    </ul>
    <p><i>Note: Diff-specific shortcuts (N, P, C, T, B, X) only work in diff viewer tabs, not in commit message or review notes tabs.</i></p>

    <h3>Tab Management</h3>
    <ul>
        <li><b>{mod_key}+Tab:</b> Switch to next tab (left-to-right, wraps around)</li>
        <li><b>{mod_key}+Shift+Tab:</b> Switch to previous tab (right-to-left, wraps around)</li>
        <li><b>{mod_key}+W:</b> Close current tab</li>
        <li><b>{mod_key}+Q:</b> Quit application</li>
        <li><b>X button:</b> Close individual tabs</li>
        <li>Clicking a file in the sidebar switches to its tab if already open</li>
    </ul>
    """


def get_help_terminal():
    """Return HTML for Terminal Editor tabs."""
    mod_key = _get_mod_key()

    return f"""
    <h2>Terminal Editor Tabs</h2>

    <h3>Terminal Editor Tabs</h3>
    <p>When using a terminal-based editor (Vim, Emacs) for review notes, all keyboard input is passed
    directly to the editor. This allows full use of editor-native commands without interference from the application.</p>
    <ul>
        <li><b>Escape Prefix:</b> Press {mod_key}+` (backtick) to activate the escape prefix; the terminal border turns blue</li>
        <li><b>Global Shortcuts:</b> After the escape prefix, press any global shortcut (e.g., {mod_key}+\\ to switch modes, {mod_key}+B to toggle sidebar)</li>
        <li><b>Bookmark Navigation:</b> After the escape prefix, press ] for next bookmark or [ for previous bookmark</li>
        <li><b>Timeout:</b> The escape prefix times out after 2 seconds if no key is pressed</li>
        <li><b>Cancel:</b> Press any non-recognized key after the prefix to cancel (key is consumed, border reverts)</li>
        <li><b>Tab Close:</b> Closing a terminal editor tab saves the buffer and exits the editor cleanly</li>
    </ul>
    """


def get_help_sidebar():
    """Return HTML for Sidebar."""
    mod_key = _get_mod_key()

    return f"""
    <h2>Sidebar</h2>

    <h3>Sidebar</h3>
    <ul>
        <li><b>Tree View:</b> Files organized by top-level directory with collapsible nodes</li>
        <li><b>Left-click file:</b> Opens file and focuses diff viewer for immediate keyboard navigation</li>
        <li><b>Right-click anywhere in tree:</b> Gives focus to tree view for keyboard navigation</li>
        <li><b>Spacebar (when tree focused):</b> Opens selected file and returns focus to diff viewer</li>
        <li><b>Directory Nodes:</b> Click to expand/collapse; shows open file count when collapsed (e.g., "src (3)" means 3 open files)</li>
        <li><b>File List:</b> Click any file to open it in a new tab (or switch to existing tab)</li>
        <li><b>Open All Files:</b> Button at top opens all files at once (shows total count)</li>
        <li><b>Blue Text:</b> Indicates open tabs - bold for active tab, normal weight for other open tabs</li>
        <li><b>Orange Background:</b> File has changed on disk (with auto-reload enabled, reloads automatically)</li>
        <li><b>{mod_key}+B:</b> Toggle sidebar visibility</li>
        <li><b>Resizable:</b> Drag the divider to resize the sidebar</li>
    </ul>
    """


def get_help_navigation():
    """Return HTML for Navigation."""
    return """
    <h2>Navigation</h2>

    <h3>Navigation</h3>
    <ul>
        <li><b>Arrow Keys:</b> Navigate up/down/left/right (both panels scroll together)</li>
        <li><b>PageUp/PageDown:</b> Scroll up/down by ~10 lines (both panels scroll together)</li>
        <li><b>Space:</b> Page down (both panels scroll together)</li>
        <li><b>Shift+Space:</b> Page up (both panels scroll together)</li>
        <li><b>Home/End:</b> Jump to start/end of file</li>
        <li><b>Tab:</b> In Diff Viewer tabs (when in Content mode), switch focus between base and modified panes (stays on same line). Tab key is blocked when in Sidebar mode.</li>
        <li><b>N:</b> Jump to next change region</li>
        <li><b>P:</b> Jump to previous change region</li>
        <li><b>C:</b> Center on the currently selected region</li>
        <li><b>T:</b> Jump to top of file</li>
        <li><b>B:</b> Jump to bottom of file</li>
    </ul>
    """


def get_help_colors():
    """Return HTML for Color Coding."""
    return """
    <h2>Color Coding</h2>

    <h3>Color Coding</h3>
    <p>The diff viewer uses a colorblind-friendly palette by default (blue/orange). You can switch between light and dark mode palettes via the Palette menu.</p>
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
        <li><b>Dark Mode Colorblind:</b>
            <ul>
                <li><span style="background-color: rgb(40, 60, 80); color: white; padding: 2px 6px;">Added lines background</span> / <span style="background-color: rgb(120, 180, 255); color: black; padding: 2px 6px;">added text</span></li>
                <li><span style="background-color: rgb(80, 60, 40); color: white; padding: 2px 6px;">Deleted lines background</span> / <span style="background-color: rgb(255, 160, 80); color: black; padding: 2px 6px;">deleted text</span></li>
                <li><span style="background-color: rgb(100, 100, 0); color: white; padding: 2px 6px;">Modified content (intraline)</span></li>
                <li>Line number backgrounds: <span style="background-color: rgb(40, 60, 80); color: white; padding: 2px 6px;">modified lines</span>, <span style="background-color: rgb(80, 60, 40); color: white; padding: 2px 6px;">base changes</span></li>
            </ul>
        </li>
        <li><b>Dark Mode Standard:</b>
            <ul>
                <li><span style="background-color: rgb(40, 80, 40); color: white; padding: 2px 6px;">Added lines background</span> / <span style="background-color: rgb(100, 200, 100); color: black; padding: 2px 6px;">added text</span></li>
                <li><span style="background-color: rgb(80, 40, 40); color: white; padding: 2px 6px;">Deleted lines background</span> / <span style="background-color: rgb(255, 100, 100); color: black; padding: 2px 6px;">deleted text</span></li>
                <li><span style="background-color: rgb(100, 100, 0); color: white; padding: 2px 6px;">Modified content (intraline)</span></li>
                <li>Line number backgrounds: <span style="background-color: rgb(40, 80, 40); color: white; padding: 2px 6px;">modified lines</span>, <span style="background-color: rgb(80, 40, 40); color: white; padding: 2px 6px;">base changes</span></li>
            </ul>
        </li>
        <li><b>All palettes:</b>
            <ul>
                <li><span style="background-color: darkgray; padding: 2px 6px;">Placeholder lines (don't exist in one version)</span></li>
                <li><span style="background-color: rgb(255, 0, 255); padding: 2px 6px;">Maximum line length indicator</span></li>
                <li><span style="background-color: orange; padding: 2px 6px;">Unknown markers</span></li>
            </ul>
        </li>
    </ul>
    """


def get_help_search():
    """Return HTML for Search Functionality."""
    mod_key = _get_mod_key()

    return f"""
    <h2>Search Functionality</h2>

    <h3>Search Functionality</h3>
    <ul>
        <li><b>{mod_key}+F or {mod_key}+S:</b> Open search dialog to search across base, modified, and commit message files</li>
        <li><b>F3:</b> Find next match (after performing a search)</li>
        <li><b>Shift+F3:</b> Find previous match (after performing a search)</li>
        <li><b>Right-click &rarr; Search:</b> Search for currently selected text</li>
        <li><b>Case Sensitive:</b> Toggle case sensitivity in search dialog</li>
        <li><b>Regular Expression:</b> Enable regex pattern matching in search (uses Python re module syntax)</li>
        <li><b>Search All Tabs:</b> When enabled, searches across all open tabs instead of just the current one</li>
        <li><b>Two-tier Highlighting:</b> All matches shown in subtle yellow, current match in bright yellow</li>
        <li><b>Navigation:</b> Use Previous/Next buttons, F3/Shift+F3, or double-click results to jump to matches</li>
        <li><b>Live Results:</b> Search results dialog stays open for easy navigation between matches</li>
        <li><b>Match Count:</b> Status bar shows current match position and total count (e.g., "Search: 3 of 47 matches")</li>
    </ul>
    """


def get_help_notes():
    """Return HTML for Note Taking."""
    mod_key = _get_mod_key()

    return f"""
    <h2>Note Taking</h2>

    <h3>Note Taking</h3>
    <ul>
        <li><b>Double-click:</b> Quick note - adds the clicked line to your notes file</li>
        <li><b>Right-click &rarr; Take Note:</b> Add selected text to notes file</li>
        <li><b>{mod_key}+N:</b> Take note of selected text (works in commit message view too)</li>
        <li><b>Yellow background:</b> Lines where notes have been taken are highlighted permanently</li>
        <li><b>{mod_key}+J:</b> Jump to note for the current line (if a note exists)</li>
        <li><b>Right-click on yellow line &rarr; Jump to Note:</b> Opens Review Notes tab and navigates to that note</li>
        <li><b>Review Notes tab:</b> Appears in sidebar after first note is taken; displays all notes in read-only view</li>
        <li><b>Auto-reload:</b> Review Notes tab automatically reloads when note file changes on disk</li>
        <li><b>Note file prompting:</b> If no note file is configured, you'll be prompted to choose one when taking a note</li>
        <li><b>File &rarr; Open Note:</b> Set or change the notes file for the current session</li>
        <li><b>Status bar:</b> Shows note file name (hover for full path)</li>
        <li>All notes are appended to the notes file in standardized format with file:line references</li>
    </ul>
    """


def get_help_bookmarks():
    """Return HTML for Bookmarks."""
    return """
    <h2>Bookmarks</h2>

    <h3>Bookmarks</h3>
    <ul>
        <li><b>M:</b> Toggle bookmark on current line</li>
        <li><b>[:</b> Navigate to previous bookmark (wraps around, switches tabs)</li>
        <li><b>]:</b> Navigate to next bookmark (wraps around, switches tabs)</li>
        <li><b>Visual indicator:</b> Cyan/teal vertical bar on left edge of bookmarked lines</li>
        <li><b>Global scope:</b> Bookmarks work across all open tabs</li>
        <li><b>Status bar:</b> Shows bookmark count next to notes count</li>
        <li>Bookmarks are not persisted - closing a tab removes its bookmarks</li>
    </ul>
    """


def get_help_diffmap():
    """Return HTML for Diff Map."""
    mod_key = _get_mod_key()

    return f"""
    <h2>Diff Map</h2>

    <h3>Diff Map</h3>
    <ul>
        <li>Vertical bar shows overview of all changes in the file</li>
        <li><b>Color scheme depends on selected palette:</b>
            <ul>
                <li><b>Colorblind Friendly:</b> <span style="background-color: rgb(70, 130, 180); padding: 2px 6px;">Insertions</span>, <span style="background-color: rgb(255, 140, 0); padding: 2px 6px;">Deletions</span>, <span style="background-color: rgb(255, 200, 120); padding: 2px 6px;">Modifications</span></li>
                <li><b>Standard:</b> <span style="background-color: green; padding: 2px 6px;">Insertions</span>, <span style="background-color: red; padding: 2px 6px;">Deletions</span>, <span style="background-color: salmon; padding: 2px 6px;">Modifications</span></li>
                <li><b>Dark Mode Colorblind:</b> <span style="background-color: rgb(70, 130, 200); color: white; padding: 2px 6px;">Insertions</span>, <span style="background-color: rgb(255, 140, 60); padding: 2px 6px;">Deletions</span>, <span style="background-color: rgb(220, 160, 100); padding: 2px 6px;">Modifications</span></li>
                <li><b>Dark Mode Standard:</b> <span style="background-color: rgb(50, 150, 50); color: white; padding: 2px 6px;">Insertions</span>, <span style="background-color: rgb(200, 50, 50); color: white; padding: 2px 6px;">Deletions</span>, <span style="background-color: rgb(200, 120, 60); padding: 2px 6px;">Modifications</span></li>
            </ul>
        </li>
        <li><span style="background-color: rgba(128, 128, 128, 0.4); padding: 2px 6px;">Gray rectangle: Current viewport position</span></li>
        <li><b>Click on diff map:</b> Jump to that location in the file</li>
        <li><b>{mod_key}+H:</b> Toggle diff map visibility</li>
        <li><b>Mouse wheel:</b> Scroll through the file</li>
    </ul>
    """


def get_help_advanced():
    """Return HTML for advanced topics (View Options, Font Size, etc.)."""
    mod_key = _get_mod_key()

    return f"""
    <h2>Advanced Options</h2>

    <h3>View Options</h3>
    <p>All View menu options are accessible via keyboard shortcuts and show their current state with checkmarks:</p>
    <ul>
        <li><b>{mod_key}+B:</b> Toggle Sidebar visibility</li>
        <li><b>{mod_key}+H:</b> Toggle Diff Map visibility</li>
        <li><b>{mod_key}+L:</b> Toggle Line Numbers visibility</li>
        <li><b>{mod_key}+T:</b> Toggle Tab character highlighting</li>
        <li><b>{mod_key}+E:</b> Toggle Trailing Whitespace highlighting</li>
        <li><b>{mod_key}+I:</b> Toggle Intraline Changes highlighting</li>
        <li><b>{mod_key}+R:</b> Toggle Auto-reload Files on/off</li>
        <li><b>{mod_key}+Y:</b> Cycle Stats Display - cycles through three modes: None -> Tabs Only -> Sidebar Only. Shows file statistics (line counts, additions, deletions, changes) in tab titles and/or sidebar file buttons.</li>
    </ul>

    <h3>Font Size</h3>
    <ul>
        <li><b>{mod_key}++:</b> Increase font size (up to 24pt)</li>
        <li><b>{mod_key}+-:</b> Decrease font size (down to 6pt)</li>
        <li><b>{mod_key}+0:</b> Reset font size to default (12pt)</li>
        <li>Font size changes apply to current tab only (including commit message tabs)</li>
        <li>Changes are not persisted between sessions</li>
    </ul>

    <h3>Line Numbers</h3>
    <ul>
        <li>Shows original line numbers from each file</li>
        <li>Background colors indicate changed lines (colors depend on selected palette)</li>
        <li><b>{mod_key}+L:</b> Toggle line number visibility</li>
    </ul>

    <h3>Whitespace Display</h3>
    <ul>
        <li><b>{mod_key}+T:</b> Toggle highlighting of tab characters</li>
        <li><b>{mod_key}+E:</b> Toggle highlighting of trailing whitespace at end of lines</li>
        <li><b>{mod_key}+I:</b> Toggle highlighting of intraline changes (character-level diffs)</li>
        <li><b>Colors (Colorblind Friendly):</b> <span style="background-color: rgb(210, 210, 240); padding: 2px 6px;">Spaces (light purple-blue)</span>, <span style="background-color: rgb(255, 200, 100); padding: 2px 6px;">Tabs (light orange)</span>, <span style="background-color: rgb(255, 200, 150); padding: 2px 6px;">Trailing (light orange)</span></li>
        <li><b>Colors (Standard):</b> <span style="background-color: rgb(220, 220, 255); padding: 2px 6px;">Spaces (light blue)</span>, <span style="background-color: rgb(255, 180, 255); padding: 2px 6px;">Tabs (light magenta)</span>, <span style="background-color: rgb(255, 200, 200); padding: 2px 6px;">Trailing (light red)</span></li>
        <li><b>Colors (Dark Mode palettes):</b> Similar colors adjusted for dark backgrounds</li>
        <li>Toggle affects current tab immediately; other tabs update when viewed</li>
    </ul>

    <h3>Auto-reload Files</h3>
    <ul>
        <li><b>{mod_key}+R:</b> Toggle auto-reload on/off</li>
        <li><b>F5:</b> Manually reload current file at any time</li>
        <li><b>Automatic monitoring:</b> Watches source files for changes on disk</li>
        <li><b>Visual indicator:</b> Sidebar button changes to change-indicator color when files are modified</li>
        <li><b>Auto-reload (default ON):</b> Automatically reloads files 500ms after they stop changing</li>
        <li><b>Preserves position:</b> Scroll position is maintained after reload</li>
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
        <li><b>Dark Mode Colorblind:</b> Blue/orange scheme optimized for dark backgrounds</li>
        <li><b>Dark Mode Standard:</b> Red/green scheme optimized for dark backgrounds</li>
        <li><b>Instant Update:</b> All open tabs update immediately when palette is changed</li>
        <li><b>Persistent:</b> Selected palette applies to all subsequently opened files</li>
        <li><b>Auto-detection:</b> On macOS, the viewer automatically selects a dark mode palette if the system is in dark mode</li>
    </ul>

    <h3>Command Line Options</h3>
    <ul>
        <li><b>--display-n-lines:</b> Set number of lines visible in initial window (default: 60)</li>
        <li><b>--display-n-chars:</b> Set number of characters per pane in initial window (default: 90)</li>
        <li><b>--max-line-length:</b> Set maximum line length indicator position (default: 80)</li>
        <li><b>--note-file:</b> Specify file for saving notes</li>
        <li><b>--tab-label-show-stats / --no-tab-label-show-stats:</b> Show/hide file statistics in tab labels (default: show)</li>
        <li><b>--file-label-show-stats / --no-file-label-show-stats:</b> Show/hide file statistics in sidebar file buttons (default: hide)</li>
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
        <li>{mod_key}+S and {mod_key}+N shortcuts work in commit message window</li>
    </ul>

    <h3>HTTP Authentication and Credential Storage</h3>
    <ul>
        <li><b>Authentication Dialog:</b> When accessing password-protected URLs, a dialog prompts for username and password</li>
        <li><b>Remember Credentials:</b> Check "Remember credentials" to store them securely in your operating system's keyring</li>
        <li><b>Keyring Storage:</b> Uses your OS's native credential storage (Keychain on macOS, Credential Manager on Windows, Secret Service on Linux)</li>
        <li><b>Session Cache:</b> Credentials are cached in memory during the session regardless of the "Remember" setting</li>
        <li><b>--keyring / --no-keyring:</b> Command line options to enable/disable keyring storage (default: enabled)</li>
        <li><b>Password Changes:</b> If you change your password on the remote server, the stored credentials will become invalid. On the next access attempt, authentication will fail and you'll be prompted to re-enter your credentials. The old credentials are automatically cleared from the keyring when authentication fails.</li>
        <li><b>Clearing Credentials:</b> Uncheck "Remember credentials" when prompted to clear stored credentials from the keyring</li>
        <li><b>SSL Certificate Warnings:</b> If a server has an invalid/self-signed certificate, you'll be warned and can choose to proceed (not recommended on untrusted networks)</li>
    </ul>
    """


def get_help_file_tree():
    """Return HTML for File Tree Selection."""
    mod_key = _get_mod_key()

    return f"""
    <h2>File Tree Selection</h2>

    <h3>Overview</h3>
    <p>The file tree in the sidebar organizes files by their directory structure.
    Files are grouped under collapsible directory nodes, making it easy to navigate
    large sets of changes.</p>

    <h3>Tree Structure</h3>
    <ul>
        <li><b>Directory Nodes:</b> Shown as expandable/collapsible items with folder-style presentation</li>
        <li><b>File Items:</b> Shown as leaf nodes under their parent directory</li>
        <li><b>Nesting:</b> Directories are nested according to the file path hierarchy</li>
        <li><b>Open Count:</b> Collapsed directories show a count of open files (e.g., "src (3)")</li>
    </ul>

    <h3>Mouse Interaction</h3>
    <ul>
        <li><b>Left-click file:</b> Opens the file in a new tab (or switches to existing tab) and focuses the diff viewer</li>
        <li><b>Left-click directory:</b> Expands or collapses the directory node</li>
        <li><b>Right-click anywhere:</b> Gives keyboard focus to the tree for navigation</li>
    </ul>

    <h3>Keyboard Navigation (when tree is focused)</h3>
    <ul>
        <li><b>Up/Down arrows:</b> Move selection through the tree</li>
        <li><b>Left arrow:</b> Collapse current directory, or move to parent</li>
        <li><b>Right arrow:</b> Expand current directory, or move to first child</li>
        <li><b>Space:</b> Open selected file and return focus to diff viewer</li>
        <li><b>Enter:</b> Open selected file (focus stays on tree)</li>
        <li><b>{mod_key}+Tab:</b> Switch focus to the commit list (when available)</li>
        <li><b>{mod_key}+Shift+Tab:</b> Switch focus to the commit list (when available)</li>
        <li><b>{mod_key}+\\:</b> Switch focus back to content area</li>
    </ul>

    <h3>Visual Indicators</h3>
    <ul>
        <li><b>Blue selection:</b> Currently selected item when tree has keyboard focus</li>
        <li><b>Grey selection:</b> Currently selected item when tree does not have focus</li>
        <li><b>Blue text:</b> File has an open tab</li>
        <li><b>Bold blue text:</b> File's tab is currently active</li>
        <li><b>Orange background:</b> File has changed on disk (with file watcher active)</li>
        <li><b>Normal text:</b> File is not currently open</li>
    </ul>

    <h3>Special Items</h3>
    <ul>
        <li><b>Commit Message:</b> Opens the commit message in a separate tab (shown in dark red)</li>
        <li><b>Review Notes:</b> Opens your review notes file (shown in blue, appears after first note)</li>
        <li><b>Open All button:</b> Opens all files at once; shows total file count</li>
    </ul>
    """


def get_help_uncommitted():
    """Return HTML for Uncommitted Comparison."""
    return """
    <h2>Uncommitted Comparison</h2>

    <h3>Overview</h3>
    <p>Uncommitted comparison mode lets you review changes that have not yet been
    committed to your repository. This is useful for reviewing your work before
    committing, or for understanding staged vs unstaged changes.</p>

    <h3>Comparison Modes</h3>
    <p>When viewing uncommitted changes, you can compare different versions of your files:</p>
    <ul>
        <li><b>HEAD vs Working (default):</b> Compare the last committed version against your current working directory. Shows all uncommitted changes, both staged and unstaged.</li>
        <li><b>HEAD vs Staged:</b> Compare the last committed version against the staging area (index). Shows only changes that have been staged with "git add".</li>
        <li><b>Staged vs Working:</b> Compare the staging area against the working directory. Shows changes that exist in your working directory but have not been staged.</li>
    </ul>

    <h3>File Visibility by Mode</h3>
    <ul>
        <li><b>HEAD vs Working:</b> All modified files are shown</li>
        <li><b>HEAD vs Staged:</b> Only files with staged content are shown</li>
        <li><b>Staged vs Working:</b> Only files with both staged and unstaged changes are shown</li>
    </ul>

    <h3>Staged vs Unstaged Files</h3>
    <ul>
        <li><b>Staged-only files:</b> Files where all changes have been staged (appear in HEAD vs Staged)</li>
        <li><b>Unstaged files:</b> Files with changes in working directory that may or may not have staged portions</li>
        <li><b>Mixed files:</b> Files with both staged and unstaged changes (visible in all three modes)</li>
    </ul>

    <h3>Usage</h3>
    <ul>
        <li>Use the View menu or toolbar to switch between comparison modes</li>
        <li>The sidebar updates automatically to show only relevant files for each mode</li>
        <li>Open tabs may close if their file is not applicable to the new mode</li>
    </ul>
    """


def get_help_commit_list():
    """Return HTML for Commit List (Committed Changes)."""
    mod_key = _get_mod_key()
    return f"""
    <h2>Commit List for Committed Changes</h2>

    <h3>Overview</h3>
    <p>When reviewing committed changes (a dossier with multiple revisions), the sidebar
    displays a list of commits that you can use to select revision ranges for comparison.</p>

    <h3>Commit List Structure</h3>
    <ul>
        <li><b>Header:</b> "Commits" label at the top of the list</li>
        <li><b>Committed (index 0):</b> Represents the repository state before the first commit in the range</li>
        <li><b>Commit entries:</b> Each commit shows its SHA prefix and commit message summary</li>
        <li><b>Order:</b> Commits are listed chronologically (oldest to newest, top to bottom)</li>
    </ul>

    <h3>Range Slider</h3>
    <p>A vertical range slider on the left side of the commit list allows you to select
    a revision range for comparison:</p>
    <ul>
        <li><b>Top handle:</b> Selects the base revision (what you're comparing FROM)</li>
        <li><b>Bottom handle:</b> Selects the modified revision (what you're comparing TO)</li>
        <li><b>Blue highlight:</b> Commits within the selected range are highlighted</li>
        <li><b>Drag handles:</b> Click and drag either handle to adjust the range</li>
        <li><b>Minimum range:</b> At least one commit must be between the handles</li>
    </ul>

    <h3>Keyboard Navigation</h3>
    <ul>
        <li><b>Up/Down arrows:</b> Move selection through commits</li>
        <li><b>Left/Right arrows:</b> Scroll the commit list horizontally (for long messages)</li>
        <li><b>Enter/Space:</b> Open the selected commit's message in a tab</li>
        <li><b>{mod_key}+Tab:</b> Switch focus to the file tree</li>
        <li><b>{mod_key}+Shift+Tab:</b> Switch focus to the file tree</li>
    </ul>

    <h3>Mouse Interaction</h3>
    <ul>
        <li><b>Click commit:</b> Opens that commit's message in a new tab</li>
        <li><b>Hover:</b> Commits highlight on hover to indicate clickability</li>
    </ul>

    <h3>Visual Indicators</h3>
    <ul>
        <li><b>Blue selection:</b> Currently keyboard-selected commit when list has focus</li>
        <li><b>Grey selection:</b> Currently keyboard-selected commit when list does not have focus</li>
        <li><b>Light blue background:</b> Commits within the selected revision range</li>
        <li><b>Italic "Committed":</b> The special entry representing pre-first-commit state</li>
        <li><b>Bold text:</b> Commit whose tab is currently active</li>
    </ul>

    <h3>File List Updates</h3>
    <p>When you change the revision range using the slider:</p>
    <ul>
        <li>The file tree updates to show files modified within that range</li>
        <li>Files are compared between the base and modified revision endpoints</li>
        <li>Selecting "Committed" as the base compares against the pre-first-commit state</li>
    </ul>
    """


def get_help_all():
    """Return HTML for all help sections combined."""
    return (get_help_overview() +
            get_help_tabs() +
            get_help_terminal() +
            get_help_sidebar() +
            get_help_navigation() +
            get_help_colors() +
            get_help_search() +
            get_help_notes() +
            get_help_bookmarks() +
            get_help_diffmap() +
            get_help_file_tree() +
            get_help_uncommitted() +
            get_help_commit_list() +
            get_help_advanced())


# Map section identifiers to their functions and titles
HELP_SECTIONS = {
    HELP_SECTION_OVERVIEW: (get_help_overview, "Overview"),
    HELP_SECTION_TABS: (get_help_tabs, "Tab Types"),
    HELP_SECTION_TERMINAL: (get_help_terminal, "Terminal Editors"),
    HELP_SECTION_SIDEBAR: (get_help_sidebar, "Sidebar"),
    HELP_SECTION_NAVIGATION: (get_help_navigation, "Navigation"),
    HELP_SECTION_COLORS: (get_help_colors, "Color Coding"),
    HELP_SECTION_SEARCH: (get_help_search, "Search"),
    HELP_SECTION_NOTES: (get_help_notes, "Note Taking"),
    HELP_SECTION_BOOKMARKS: (get_help_bookmarks, "Bookmarks"),
    HELP_SECTION_DIFFMAP: (get_help_diffmap, "Diff Map"),
    HELP_SECTION_FILE_TREE: (get_help_file_tree, "File Tree Selection"),
    HELP_SECTION_UNCOMMITTED: (get_help_uncommitted, "Uncommitted Comparison"),
    HELP_SECTION_COMMIT_LIST: (get_help_commit_list, "Commit List"),
    HELP_SECTION_ALL: (get_help_all, "Complete Guide"),
}


class HelpDialog(QDialog):
    """Dialog that displays help documentation for the diff viewer.

    Args:
        parent: Parent widget
        section: Which help section to display (use HELP_SECTION_* constants)
    """

    def __init__(self, parent=None, section=HELP_SECTION_ALL):
        super().__init__(parent, Qt.WindowType.Window)

        # Get section info
        if section not in HELP_SECTIONS:
            section = HELP_SECTION_ALL
        get_html_func, title = HELP_SECTIONS[section]

        self.setWindowTitle(f"Diff Viewer - {title}")
        self.setMinimumSize(700, 600)

        layout = QVBoxLayout(self)

        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml(get_html_func())

        self.current_font_size = 12
        font = QFont()
        font.setPointSize(self.current_font_size)
        help_text.setFont(font)

        layout.addWidget(help_text)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.help_text = help_text

        # Setup font size shortcuts
        self.setup_font_shortcuts()

    def setup_font_shortcuts(self):
        """Setup keyboard shortcuts for font size adjustment"""
        # Ctrl++ or Ctrl+=
        increase_shortcut = QShortcut(QKeySequence("Ctrl++"), self)
        increase_shortcut.activated.connect(self.increase_font_size)
        increase_shortcut2 = QShortcut(QKeySequence("Ctrl+="), self)
        increase_shortcut2.activated.connect(self.increase_font_size)

        # Ctrl+-
        decrease_shortcut = QShortcut(QKeySequence("Ctrl+-"), self)
        decrease_shortcut.activated.connect(self.decrease_font_size)

        # Ctrl+0
        reset_shortcut = QShortcut(QKeySequence("Ctrl+0"), self)
        reset_shortcut.activated.connect(self.reset_font_size)

        # Add Cmd shortcuts for macOS
        # Cmd++ or Cmd+=
        cmd_increase_shortcut = QShortcut(QKeySequence("Meta++"), self)
        cmd_increase_shortcut.activated.connect(self.increase_font_size)
        cmd_increase_shortcut2 = QShortcut(QKeySequence("Meta+="), self)
        cmd_increase_shortcut2.activated.connect(self.increase_font_size)

        # Cmd+-
        cmd_decrease_shortcut = QShortcut(QKeySequence("Meta+-"), self)
        cmd_decrease_shortcut.activated.connect(self.decrease_font_size)

        # Cmd+0
        cmd_reset_shortcut = QShortcut(QKeySequence("Meta+0"), self)
        cmd_reset_shortcut.activated.connect(self.reset_font_size)

    def increase_font_size(self):
        """Increase font size (max 24pt)"""
        if self.current_font_size < 24:
            self.current_font_size += 1
            self.update_font_size()

    def decrease_font_size(self):
        """Decrease font size (min 6pt)"""
        if self.current_font_size > 6:
            self.current_font_size -= 1
            self.update_font_size()

    def reset_font_size(self):
        """Reset font size to default (12pt)"""
        self.current_font_size = 12
        self.update_font_size()

    def update_font_size(self):
        """Apply current font size to the text widget"""
        font = self.help_text.font()
        font.setPointSize(self.current_font_size)
        self.help_text.setFont(font)
    

