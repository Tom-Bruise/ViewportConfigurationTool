"""
Viewport Configuration Tool - Manage viewport settings for RetroArch ROM configs.

This package provides tools for parsing DAT files (FinalBurn Neo, MAME) and
creating/updating RetroArch configuration files with custom viewport configurations.

Modules:
    core: Core functionality for parsing and config management
    ui: Terminal user interface (TUI) using curses
    cli: Command-line interface for batch processing
"""

__version__ = "1.1.0"
__author__ = "Viewport Configuration Tool Contributors"

from .core import GameInfo, ViewportConfigurationManager
from .ui import SystemConfig, CursesGUI, main_gui
from .cli import main_cli

__all__ = [
    'GameInfo',
    'ViewportConfigurationManager',
    'SystemConfig',
    'CursesGUI',
    'main_gui',
    'main_cli',
]
