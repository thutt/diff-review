#!/usr/bin/env python3
"""
Diff Review - Main entry point

A PyQt6-based diff viewer with unified search across base, modified, 
and description files.

Installation:
    pip install PyQt6

Usage:
    python diff_review.py <base_file> <modified_file> <note_file> <description_file>
    
    note_file: path to note file or 'None' for no notes
    description_file: path to description file or 'None' for no description
"""
import sys

from utils import install_message_handler
from diff_viewer import DiffViewer


def main():
    """Main entry point for the diff review application"""
    
    # Install Qt message handler to suppress warnings
    install_message_handler()
    
    # Check command line arguments
    if len(sys.argv) < 5:
        print("Usage: python diff_review.py <base_file> <modified_file> <note_file> <description_file>")
        print("  note_file: path to note file or 'None' for no notes")
        print("  description_file: path to description file or 'None' for no description")
        sys.exit(1)
    
    base_file = sys.argv[1]
    modified_file = sys.argv[2]
    note_file = sys.argv[3] if sys.argv[3] != 'None' else None
    description_file = sys.argv[4] if sys.argv[4] != 'None' else None
    
    # Verify files exist
    try:
        with open(base_file, 'r') as f:
            base_lines = f.readlines()
        with open(modified_file, 'r') as f:
            modified_lines = f.readlines()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Create and run viewer
    viewer = DiffViewer(base_file, modified_file, note_file, description_file)
    viewer.run()


if __name__ == '__main__':
    main()
