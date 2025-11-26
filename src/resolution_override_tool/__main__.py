"""
Main entry point for the Resolution Override Tool.

This module determines whether to launch in GUI or CLI mode
based on command-line arguments.
"""

import sys
import curses

# Use absolute imports for PyInstaller compatibility
try:
    from resolution_override_tool.ui import main_gui
    from resolution_override_tool.cli import main_cli
except ImportError:
    # Fallback to relative imports for development
    from .ui import main_gui
    from .cli import main_cli


if __name__ == '__main__':
    # If no arguments provided, launch GUI mode
    if len(sys.argv) == 1:
        curses.wrapper(main_gui)
    else:
        # CLI mode with arguments
        sys.exit(main_cli())
