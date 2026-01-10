# Copyright (c) 2025, 2026  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Keyboard bindings configuration for diff_review

This module handles loading and parsing keyboard bindings from JSON config files.
"""
import json
import sys
from PyQt6.QtCore import Qt


class KeySequence:
    """Represents a sequence of key presses (up to 15 keys)"""

    def __init__(self, keys):
        """
        Args:
            keys: List of (qt_key, modifiers) tuples
        """
        self.keys = keys

    def __repr__(self):
        return f"KeySequence({self.keys})"

    def __eq__(self, other):
        return isinstance(other, KeySequence) and self.keys == other.keys

    def __hash__(self):
        return hash(tuple(self.keys))


class KeyBindings:
    """Manages keyboard bindings from config file with fallback to defaults"""

    MAX_SEQUENCE_LENGTH = 15

    # Default key bindings - used as fallback
    DEFAULT_BINDINGS = {
        'global': {
            'shortcuts_help': ['F1', 'Ctrl+Shift+?'],
            'quit_application': ['Ctrl+q'],
            'close_tab': ['Ctrl+w'],
            'next_tab': ['Ctrl+Tab'],
            'prev_tab': ['Ctrl+Shift+Tab'],
            'increase_font': ['Ctrl++', 'Ctrl+='],
            'decrease_font': ['Ctrl+-'],
            'reset_font': ['Ctrl+0'],
            'toggle_sidebar': ['Ctrl+b'],
            'toggle_focus_mode': ['Ctrl+\\'],
            'search': ['Ctrl+f', 'Ctrl+s'],
            'find_next': ['F3'],
            'find_prev': ['Shift+F3'],
        },
        'terminal': {
            'terminal_escape': ['Ctrl+;'],
            'next_bookmark': [']'],
            'prev_bookmark': ['['],
        },
        'diff': {
            'next_change': ['n'],
            'prev_change': ['p'],
            'top_of_file': ['T'],
            'bottom_of_file': ['B'],
            'toggle_bookmark': ['m'],
            'next_bookmark': [']'],
            'prev_bookmark': ['['],
            'center_region': ['c'],
            'toggle_collapse_region': ['x'],
            'toggle_collapse_all': ['Shift+x'],
            'take_note': ['Ctrl+n'],
            'jump_to_note': ['Ctrl+j'],
            'toggle_base_modi_focus': ['Tab'],
            'reload': ['F5'],
            'toggle_diff_map': ['Ctrl+h'],
            'toggle_line_numbers': ['Ctrl+l'],
            'toggle_tab_highlight': ['Ctrl+t'],
            'toggle_eol_highlight': ['Ctrl+e'],
            'toggle_intraline': ['Ctrl+i'],
        },
        'note': {
            'reload': ['F5'],
        },
        'commit_msg': {
            'take_note': ['Ctrl+n'],
            'jump_to_note': ['Ctrl+j'],
            'toggle_bookmark': ['m'],
            'next_bookmark': [']'],
            'prev_bookmark': ['['],
            'reload': ['F5'],
        },
    }

    # Reserved keys that should not be rebound (hardcoded behavior)
    RESERVED_KEYS = {
    }

    def __init__(self, config_file=None, context='global'):
        """
        Initialize key bindings from config file or use defaults.

        Args:
            config_file: Path to JSON config file, or None for defaults only
            context: Context for bindings - 'global', 'diff', 'note', or 'commit_msg'
        """
        self.context = context
        self.action_to_sequences = {}
        self.sequence_to_action = {}

        # Start with defaults
        self._load_defaults()

        # Override with config file if provided
        if config_file:
            self._load_config(config_file)

        # Build reverse lookup
        self._build_reverse_lookup()

    def _load_defaults(self):
        """Load default key bindings for global and current context"""
        # Load global bindings
        if 'global' in self.DEFAULT_BINDINGS:
            for action, key_strings in self.DEFAULT_BINDINGS['global'].items():
                sequences = []
                for key_string in key_strings:
                    seq = self._parse_key_string(key_string)
                    if seq:
                        sequences.append(seq)
                if sequences:
                    self.action_to_sequences[action] = sequences
        
        # Load context-specific bindings
        if self.context != 'global' and self.context in self.DEFAULT_BINDINGS:
            for action, key_strings in self.DEFAULT_BINDINGS[self.context].items():
                sequences = []
                for key_string in key_strings:
                    seq = self._parse_key_string(key_string)
                    if seq:
                        sequences.append(seq)
                if sequences:
                    self.action_to_sequences[action] = sequences

    def _is_reserved_key(self, key_string):
        """Check if a key string matches a reserved key"""
        key_normalized = key_string.strip()
        for reserved in self.RESERVED_KEYS:
            if key_normalized.lower() == reserved.lower():
                return True
        return False

    def _get_reserved_reason(self, key_string):
        """Get the reason a key is reserved"""
        key_normalized = key_string.strip()
        for reserved, reason in self.RESERVED_KEYS.items():
            if key_normalized.lower() == reserved.lower():
                return reason
        return "Unknown reason"

    def _load_config(self, config_file):
        """Load and parse JSON config file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            # Load global section
            if 'global' in config:
                self._load_section(config['global'], 'global')
            
            # Load context-specific section
            if self.context != 'global' and self.context in config:
                self._load_section(config[self.context], self.context)

        except FileNotFoundError:
            print(f"Warning: Keybindings file not found: {config_file}", file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in {config_file}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Error loading keybindings from {config_file}: {e}", file=sys.stderr)
    
    def _load_section(self, section_bindings, section_name):
        """Load bindings from a specific section of the config"""
        if not isinstance(section_bindings, dict):
            print(f"Warning: '{section_name}' must be a dictionary", file=sys.stderr)
            return

        for action, key_list in section_bindings.items():
            if not isinstance(key_list, list):
                print(f"Warning: Keybinding for '{action}' must be a list, got {type(key_list).__name__}", file=sys.stderr)
                continue

            sequences = []
            for key_string in key_list:
                if not isinstance(key_string, str):
                    print(f"Warning: Key binding '{key_string}' for action '{action}' must be a string", file=sys.stderr)
                    continue

                # Check if this is a reserved key
                if self._is_reserved_key(key_string):
                    reserved_reason = self._get_reserved_reason(key_string)
                    print(f"Warning: Key binding '{key_string}' for action '{action}' uses a reserved key: {reserved_reason}", file=sys.stderr)
                    continue

                seq = self._parse_key_string(key_string)
                if seq:
                    sequences.append(seq)
                else:
                    print(f"Warning: Invalid key binding '{key_string}' for action '{action}'", file=sys.stderr)

            if sequences:
                self.action_to_sequences[action] = sequences

    def _parse_key_string(self, key_string):
        """
        Parse a key string into a KeySequence.

        Format: Space-separated keys, each with optional modifiers.
        Examples: "n", "g g", "Ctrl+F", "Ctrl+g g", "Ctrl+g Shift+n"

        Args:
            key_string: String representation of key sequence

        Returns:
            KeySequence or None if invalid
        """
        parts = key_string.split(' ')
        if len(parts) > self.MAX_SEQUENCE_LENGTH:
            return None

        keys = []
        for part in parts:
            result = self._parse_single_key(part)
            if result is None:
                return None
            keys.append(result)

        return KeySequence(keys)

    def _parse_single_key(self, key_part):
        """
        Parse a single key with modifiers.

        Format: "Modifier+Modifier+Key"
        Examples: "n", "Ctrl+F", "Shift+Ctrl+g", "Ctrl++"

        Args:
            key_part: String representation of single key press

        Returns:
            (qt_key, modifiers) tuple or None if invalid
        """
        # Special case: handle "Ctrl++" or similar where + is the key itself
        # Count the + characters - if there are more than expected modifiers, last + is the key
        plus_count = key_part.count('+')
        if plus_count >= 2 and key_part.endswith('++'):
            # Parse as modifier(s) + the '+' key
            # e.g., "Ctrl++" -> components = ["Ctrl", "+"]
            modifier_part = key_part[:-2]  # Everything except the last ++
            components = modifier_part.split('+') if modifier_part else []
            components.append('+')  # Add + as the base key
        else:
            components = key_part.split('+')
        
        if len(components) == 0:
            return None

        modifiers = Qt.KeyboardModifier.NoModifier
        base_key = components[-1]

        # Parse modifiers
        for i in range(len(components) - 1):
            mod = components[i].lower()
            if mod == 'ctrl':
                modifiers |= Qt.KeyboardModifier.ControlModifier
            elif mod == 'shift':
                modifiers |= Qt.KeyboardModifier.ShiftModifier
            elif mod == 'alt':
                modifiers |= Qt.KeyboardModifier.AltModifier
            elif mod == 'cmd' or mod == 'meta':
                modifiers |= Qt.KeyboardModifier.MetaModifier
            else:
                return None

        # Parse base key
        qt_key = self._key_name_to_qt(base_key)
        if qt_key is None:
            return None

        return (qt_key, modifiers)

    def _key_name_to_qt(self, key_name):
        """
        Convert key name string to Qt.Key enum value.

        Args:
            key_name: String key name (case-insensitive for single chars)

        Returns:
            Qt.Key value or None if invalid
        """
        # Handle special keys
        if key_name == '<space>':
            return Qt.Key.Key_Space

        # Function keys
        if key_name.upper().startswith('F') and len(key_name) > 1:
            try:
                num = int(key_name[1:])
                if 1 <= num <= 35:
                    return getattr(Qt.Key, f'Key_F{num}')
            except ValueError:
                pass

        # Special named keys
        special_keys = {
            'space': Qt.Key.Key_Space,
            'tab': Qt.Key.Key_Tab,
            'return': Qt.Key.Key_Return,
            'enter': Qt.Key.Key_Enter,
            'backspace': Qt.Key.Key_Backspace,
            'delete': Qt.Key.Key_Delete,
            'escape': Qt.Key.Key_Escape,
            'esc': Qt.Key.Key_Escape,
            'home': Qt.Key.Key_Home,
            'end': Qt.Key.Key_End,
            'pageup': Qt.Key.Key_PageUp,
            'pagedown': Qt.Key.Key_PageDown,
            'up': Qt.Key.Key_Up,
            'down': Qt.Key.Key_Down,
            'left': Qt.Key.Key_Left,
            'right': Qt.Key.Key_Right,
            'insert': Qt.Key.Key_Insert,
        }

        key_lower = key_name.lower()
        if key_lower in special_keys:
            return special_keys[key_lower]

        # Single character keys
        if len(key_name) == 1:
            char = key_name.upper()
            # Letters
            if 'A' <= char <= 'Z':
                return getattr(Qt.Key, f'Key_{char}')
            # Digits
            if '0' <= char <= '9':
                return getattr(Qt.Key, f'Key_{char}')
            # Symbols
            symbol_map = {
                '[': Qt.Key.Key_BracketLeft,
                ']': Qt.Key.Key_BracketRight,
                '?': Qt.Key.Key_Question,
                '/': Qt.Key.Key_Slash,
                '\\': Qt.Key.Key_Backslash,
                '=': Qt.Key.Key_Equal,
                '-': Qt.Key.Key_Minus,
                '+': Qt.Key.Key_Plus,
                '*': Qt.Key.Key_Asterisk,
                '.': Qt.Key.Key_Period,
                ',': Qt.Key.Key_Comma,
                ';': Qt.Key.Key_Semicolon,
                ':': Qt.Key.Key_Colon,
                '\'': Qt.Key.Key_Apostrophe,
                '"': Qt.Key.Key_QuoteDbl,
                '<': Qt.Key.Key_Less,
                '>': Qt.Key.Key_Greater,
                '!': Qt.Key.Key_Exclam,
                '@': Qt.Key.Key_At,
                '#': Qt.Key.Key_NumberSign,
                '$': Qt.Key.Key_Dollar,
                '%': Qt.Key.Key_Percent,
                '^': Qt.Key.Key_AsciiCircum,
                '&': Qt.Key.Key_Ampersand,
                '(': Qt.Key.Key_ParenLeft,
                ')': Qt.Key.Key_ParenRight,
                '{': Qt.Key.Key_BraceLeft,
                '}': Qt.Key.Key_BraceRight,
                '|': Qt.Key.Key_Bar,
                '~': Qt.Key.Key_AsciiTilde,
                '`': Qt.Key.Key_QuoteLeft,
            }
            if char in symbol_map:
                return symbol_map[char]

        return None

    def _build_reverse_lookup(self):
        """Build sequence -> action lookup table and detect conflicts"""
        self.sequence_to_action = {}
        for action, sequences in self.action_to_sequences.items():
            for seq in sequences:
                # Check if this sequence is already assigned to a different action
                if seq in self.sequence_to_action:
                    existing_action = self.sequence_to_action[seq]
                    if existing_action != action:
                        seq_str = self._sequence_to_string(seq)
                        print(f"Warning: Duplicate keybinding - '{seq_str}' assigned to both "
                              f"'{existing_action}' and '{action}'. Using '{action}'.",
                              file=sys.stderr)
                self.sequence_to_action[seq] = action
        
        # Detect conflicts where a complete binding shadows a multi-key prefix
        self._detect_conflicts()
    
    def _detect_conflicts(self):
        """Detect and warn about conflicting keybindings"""
        sequences = list(self.sequence_to_action.keys())
        
        for i, seq1 in enumerate(sequences):
            for seq2 in sequences[i+1:]:
                # Check if seq1 is a prefix of seq2
                if len(seq1.keys) < len(seq2.keys):
                    if seq2.keys[:len(seq1.keys)] == seq1.keys:
                        action1 = self.sequence_to_action[seq1]
                        action2 = self.sequence_to_action[seq2]
                        seq1_str = self._sequence_to_string(seq1)
                        seq2_str = self._sequence_to_string(seq2)
                        print(f"Warning: Keybinding conflict - '{seq1_str}' for '{action1}' "
                              f"shadows '{seq2_str}' for '{action2}'. "
                              f"The longer sequence will never be triggered.",
                              file=sys.stderr)
                # Check if seq2 is a prefix of seq1
                elif len(seq2.keys) < len(seq1.keys):
                    if seq1.keys[:len(seq2.keys)] == seq2.keys:
                        action1 = self.sequence_to_action[seq1]
                        action2 = self.sequence_to_action[seq2]
                        seq1_str = self._sequence_to_string(seq1)
                        seq2_str = self._sequence_to_string(seq2)
                        print(f"Warning: Keybinding conflict - '{seq2_str}' for '{action2}' "
                              f"shadows '{seq1_str}' for '{action1}'. "
                              f"The longer sequence will never be triggered.",
                              file=sys.stderr)
    
    def _sequence_to_string(self, sequence):
        """Convert a KeySequence back to a readable string for error messages"""
        parts = []
        for qt_key, modifiers in sequence.keys:
            key_parts = []
            
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                key_parts.append("Ctrl")
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                key_parts.append("Shift")
            if modifiers & Qt.KeyboardModifier.AltModifier:
                key_parts.append("Alt")
            if modifiers & Qt.KeyboardModifier.MetaModifier:
                key_parts.append("Cmd")
            
            # Get key name
            key_name = self._qt_key_to_name(qt_key)
            key_parts.append(key_name)
            
            parts.append("+".join(key_parts))
        
        return " ".join(parts)
    
    def _qt_key_to_name(self, qt_key):
        """Convert Qt.Key enum back to string name (best effort)"""
        # Try to find the key name from Qt.Key enum
        for attr_name in dir(Qt.Key):
            if attr_name.startswith('Key_'):
                if getattr(Qt.Key, attr_name) == qt_key:
                    key_name = attr_name[4:]  # Strip 'Key_' prefix
                    # Special case for common keys
                    if key_name == 'Space':
                        return '<space>'
                    return key_name
        return f"Key_{qt_key}"

    def get_action(self, sequence):
        """
        Get action for a key sequence.

        Args:
            sequence: KeySequence object

        Returns:
            Action name string or None if no match
        """
        return self.sequence_to_action.get(sequence)

    def get_sequences(self, action):
        """
        Get all key sequences for an action.

        Args:
            action: Action name string

        Returns:
            List of KeySequence objects, or empty list if action not found
        """
        return self.action_to_sequences.get(action, [])
