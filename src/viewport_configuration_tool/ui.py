"""
Terminal user interface (TUI) for the viewport configuration tool.

This module provides a curses-based interactive GUI for managing
ROM viewport configurations across multiple emulation systems.
"""

import curses
import json
import os
from pathlib import Path
from typing import List, Optional, Tuple

from .core import GameInfo, ViewportConfigurationManager
from .network import get_dat_sources, download_dat_file

class SystemConfig:
    """Configuration for a single emulation system."""

    def __init__(self, name: str, dat_file: str = "", rom_folder: str = "",
                 override_width: Optional[int] = None,
                 override_height: Optional[int] = None,
                 override_x: Optional[int] = None,
                 override_y: Optional[int] = None,
                 export_folder: str = ""):
        self.name = name
        self.dat_file = dat_file
        self.rom_folder = rom_folder
        self.override_width = override_width
        self.override_height = override_height
        self.override_x = override_x
        self.override_y = override_y
        self.export_folder = export_folder
        self.manager: Optional[ViewportConfigurationManager] = None

    def to_dict(self) -> dict:
        """Convert system config to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "dat_file": self.dat_file,
            "rom_folder": self.rom_folder,
            "override_width": self.override_width,
            "override_height": self.override_height,
            "override_x": self.override_x,
            "override_y": self.override_y,
            "export_folder": self.export_folder
        }

    @staticmethod
    def from_dict(data: dict) -> 'SystemConfig':
        """Create system config from dictionary."""
        return SystemConfig(
            name=data.get("name", ""),
            dat_file=data.get("dat_file", ""),
            rom_folder=data.get("rom_folder", ""),
            override_width=data.get("override_width"),
            override_height=data.get("override_height"),
            override_x=data.get("override_x"),
            override_y=data.get("override_y"),
            export_folder=data.get("export_folder", "")
        )


class CursesGUI:
    CONFIG_FILE = Path.home() / ".resolution_override_config.json"

    def __init__(self, stdscr):
        """Initialize the curses GUI."""
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()

        # Initialize colors
        curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLUE)  # Selected - yellow on blue (matches footer)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Success
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)    # Error
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Warning
        curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Info
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Box backgrounds - light on dark (A_DIM for muted effect)
        curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_BLUE)    # Header background - cyan on blue
        curses.init_pair(8, curses.COLOR_YELLOW, curses.COLOR_BLUE)  # Footer background - yellow on blue
        curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_BLUE)   # Alert window background - white on blue
        curses.init_pair(10, curses.COLOR_GREEN, curses.COLOR_BLUE)   # Success on blue
        curses.init_pair(11, curses.COLOR_WHITE, curses.COLOR_BLUE)   # Error on blue (white for better readability)
        curses.init_pair(12, curses.COLOR_YELLOW, curses.COLOR_BLUE)  # Warning on blue
        curses.init_pair(13, curses.COLOR_CYAN, curses.COLOR_BLUE)    # Info on blue
        curses.init_pair(14, curses.COLOR_WHITE, curses.COLOR_BLUE)   # White on blue

        # Multi-system support
        self.systems: List[SystemConfig] = []
        self.current_system_idx = 0
        self.auto_save_enabled = True  # Auto-save on exit by default

        # UI state
        self.log_messages: List[str] = []
        self.current_screen = "main_menu"

        # Auto-load config if it exists
        self.auto_load_config()

    def log(self, message: str) -> None:
        """Add a message to the log."""
        self.log_messages.append(message)
        if len(self.log_messages) > 1000:
            self.log_messages = self.log_messages[-1000:]

    def save_config(self) -> bool:
        """Save current system configurations to JSON file."""
        try:
            config_data = {
                "systems": [system.to_dict() for system in self.systems],
                "current_system_idx": self.current_system_idx,
                "auto_save_enabled": self.auto_save_enabled
            }

            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=2)

            self.log(f"Configuration saved to {self.CONFIG_FILE}")
            return True
        except Exception as e:
            self.log(f"Error saving configuration: {e}")
            return False

    def load_config(self) -> bool:
        """Load system configurations from JSON file."""
        try:
            if not self.CONFIG_FILE.exists():
                return False

            with open(self.CONFIG_FILE, 'r') as f:
                config_data = json.load(f)

            self.systems = [SystemConfig.from_dict(s) for s in config_data.get("systems", [])]
            self.current_system_idx = config_data.get("current_system_idx", 0)
            self.auto_save_enabled = config_data.get("auto_save_enabled", True)

            # Clamp current_system_idx to valid range
            if self.systems:
                self.current_system_idx = max(0, min(self.current_system_idx, len(self.systems) - 1))
            else:
                self.current_system_idx = 0

            self.log(f"Configuration loaded from {self.CONFIG_FILE}")
            self.log(f"Loaded {len(self.systems)} system(s)")
            return True
        except Exception as e:
            self.log(f"Error loading configuration: {e}")
            return False

    def auto_load_config(self) -> None:
        """Automatically load config on startup if it exists."""
        if self.CONFIG_FILE.exists():
            self.load_config()

    def draw_header(self, title: str) -> None:
        """Draw the header bar."""
        try:
            self.stdscr.attron(curses.color_pair(7) | curses.A_BOLD)
            header_text = f" {title} "
            self.stdscr.addstr(0, 0, header_text.ljust(self.width)[:self.width])
            self.stdscr.attroff(curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass

    def draw_footer(self, text: str) -> None:
        """Draw the footer bar with help text."""
        try:
            footer_y = self.height - 1
            self.stdscr.attron(curses.color_pair(8) | curses.A_BOLD)
            self.stdscr.addstr(footer_y, 0, text.ljust(self.width)[:self.width])
            self.stdscr.attroff(curses.color_pair(8) | curses.A_BOLD)
        except curses.error:
            pass

    def draw_menu(self, title: str, items: List, selected: int, start_y: int = 2) -> None:
        """Draw a menu with selectable items.

        Items can be either strings or tuples of (item_text, description).
        """
        for idx, item in enumerate(items):
            y = start_y + idx
            if y >= self.height - 2:
                break

            # Handle both string items and tuple items (text, description)
            item_text = item[0] if isinstance(item, tuple) else item

            if idx == selected:
                self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                self.stdscr.addstr(y, 2, f"> {item_text}".ljust(self.width - 4)[:self.width - 4])
                self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
            else:
                self.stdscr.addstr(y, 2, f"  {item_text}"[:self.width - 4])

    def get_menu_selection_from_key(self, key: int, menu_items: List) -> Optional[int]:
        """
        Get menu selection index from a key press.

        Extracts the prefix (number or letter) from menu items like:
        - "[1] Option" -> matches key '1'
        - "[2] Option" -> matches key '2'
        - "[a] Option" -> matches key 'a'

        Args:
            key: The key code pressed
            menu_items: List of menu item strings or tuples (item_text, description)

        Returns:
            Index of the matching menu item, or None if no match
        """
        key_char = chr(key) if 32 <= key <= 126 else None
        if not key_char:
            return None

        for idx, item in enumerate(menu_items):
            # Handle both string items and tuple items (text, description)
            item_text = item[0] if isinstance(item, tuple) else item

            # Extract prefix from [X] format
            if item_text.strip().startswith('[') and ']' in item_text:
                start = item_text.index('[') + 1
                end = item_text.index(']')
                prefix = item_text[start:end].strip()
                if prefix == key_char:
                    return idx

        return None

    def get_input(self, prompt: str, default: str = "") -> Optional[str]:
        """Get text input from user in a centered window."""
        curses.echo()
        curses.curs_set(1)

        # Build message lines
        lines = [prompt]
        if default:
            lines.append("")
            lines.append(f"Current: {default}")
            lines.append("(Press Enter to keep current)")

        # Calculate window size with padding
        max_line_len = max(len(line) for line in lines) if lines else len(prompt)
        max_line_len = max(max_line_len, 40)  # Minimum width for input
        window_width = min(max_line_len + 10, self.width - 4)
        window_height = len(lines) + 5  # Title + content + input line + borders + padding

        # Calculate centered position
        start_y = max(1, (self.height - window_height) // 2)
        start_x = max(1, (self.width - window_width) // 2)

        # Draw background with blue color for entire window area
        self.stdscr.clear()
        self.stdscr.attron(curses.color_pair(9))
        for y in range(start_y, min(start_y + window_height + 2, self.height - 1)):
            self.stdscr.addstr(y, start_x, " " * window_width)

        # Top border with blue background
        self.stdscr.addstr(start_y, start_x, "┌" + "─" * (window_width - 2) + "┐")

        # Title line with blue background
        title_text = " Input "
        title_line = " " * (window_width - 2)
        self.stdscr.addstr(start_y + 1, start_x, "│" + title_line + "│")
        self.stdscr.attron(curses.color_pair(13) | curses.A_BOLD)  # Cyan on blue
        self.stdscr.addstr(start_y + 1, start_x + (window_width - len(title_text)) // 2, title_text)
        self.stdscr.attroff(curses.color_pair(13) | curses.A_BOLD)
        self.stdscr.attron(curses.color_pair(9))

        # Separator after title
        self.stdscr.addstr(start_y + 2, start_x, "├" + "─" * (window_width - 2) + "┤")

        # Empty line for padding
        self.stdscr.addstr(start_y + 3, start_x, "│" + " " * (window_width - 2) + "│")

        # Content lines with blue background
        content_y = start_y + 4
        for idx, line in enumerate(lines):
            y = content_y + idx
            content_line = " " * (window_width - 2)
            self.stdscr.addstr(y, start_x, "│" + content_line + "│")
            self.stdscr.attron(curses.color_pair(13))  # Cyan on blue for input content
            # Center-align content
            content_x = start_x + (window_width - len(line)) // 2
            self.stdscr.addstr(y, content_x, line[:window_width - 4])
            self.stdscr.attroff(curses.color_pair(13))
            self.stdscr.attron(curses.color_pair(9))

        # Input line with blue background
        input_y = content_y + len(lines)
        self.stdscr.addstr(input_y, start_x, "│" + " " * (window_width - 2) + "│")

        # Empty line for padding
        padding_y = input_y + 1
        self.stdscr.addstr(padding_y, start_x, "│" + " " * (window_width - 2) + "│")

        # Bottom border
        bottom_y = padding_y + 1
        self.stdscr.addstr(bottom_y, start_x, "└" + "─" * (window_width - 2) + "┘")
        self.stdscr.attroff(curses.color_pair(9))

        self.stdscr.refresh()

        # Get input at the input line position
        input_x = start_x + 3
        input_width = window_width - 6
        try:
            # Set color for input text (cyan on blue background)
            self.stdscr.attron(curses.color_pair(13))
            result = self.stdscr.getstr(input_y, input_x, input_width).decode('utf-8').strip()
            self.stdscr.attroff(curses.color_pair(13))
        except KeyboardInterrupt:
            result = None

        curses.noecho()
        curses.curs_set(0)

        if result == "" and default:
            return default
        return result if result else None

    def file_browser(self, title: str, start_path: str = None,
                     select_dirs: bool = False, file_pattern: str = None) -> Optional[str]:
        """
        Browse and select files or directories.

        Args:
            title: Browser window title
            start_path: Starting directory (defaults to home or current path)
            select_dirs: If True, allow selecting directories; if False, only files
            file_pattern: Optional pattern to filter files (e.g., "*.xml", "*.dat")

        Returns:
            Selected path or None if cancelled
        """
        if start_path and os.path.exists(start_path):
            if os.path.isfile(start_path):
                current_dir = Path(start_path).parent
            else:
                current_dir = Path(start_path)
        else:
            current_dir = Path.home()

        selected = 0
        scroll_offset = 0

        while True:
            # Get directory contents
            try:
                items = []

                # Add parent directory option
                if current_dir.parent != current_dir:
                    items.append(("../", True, current_dir.parent))

                # List directories
                dirs = sorted([d for d in current_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])
                for d in dirs:
                    items.append((d.name + "/", True, d))

                # List files (if not selecting directories only)
                if not select_dirs:
                    files = sorted([f for f in current_dir.iterdir() if f.is_file() and not f.name.startswith('.')])

                    # Apply file pattern filter if specified
                    if file_pattern:
                        import fnmatch
                        # Support multiple patterns separated by semicolon
                        patterns = [p.strip() for p in file_pattern.split(';')]
                        filtered_files = []
                        for f in files:
                            for pattern in patterns:
                                if fnmatch.fnmatch(f.name.lower(), pattern.lower()):
                                    filtered_files.append(f)
                                    break
                        files = filtered_files

                    for f in files:
                        items.append((f.name, False, f))

            except PermissionError:
                items = [("../", True, current_dir.parent)]

            # Adjust scroll
            max_visible = self.height - 8
            if selected < scroll_offset:
                scroll_offset = selected
            elif selected >= scroll_offset + max_visible:
                scroll_offset = selected - max_visible + 1

            # Draw browser
            self.stdscr.clear()
            self.draw_header(title)

            # Show current path
            path_str = str(current_dir)
            if len(path_str) > self.width - 10:
                path_str = "..." + path_str[-(self.width - 13):]

            self.stdscr.attron(curses.color_pair(5))
            self.stdscr.addstr(2, 2, f"Path: {path_str}")
            self.stdscr.attroff(curses.color_pair(5))

            # Display items
            y = 4
            for idx in range(scroll_offset, min(scroll_offset + max_visible, len(items))):
                if y >= self.height - 3:
                    break

                name, is_dir, path = items[idx]

                if idx == selected:
                    self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                    self.stdscr.addstr(y, 2, f"> {name}".ljust(self.width - 4)[:self.width - 4])
                    self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
                else:
                    if is_dir:
                        self.stdscr.attron(curses.color_pair(5))
                    self.stdscr.addstr(y, 2, f"  {name}"[:self.width - 4])
                    if is_dir:
                        self.stdscr.attroff(curses.color_pair(5))

                y += 1

            # Footer
            if select_dirs:
                footer = "Up/Down: Navigate | Enter: Select Dir/Open | Space: Select Current Dir | Esc/q: Cancel"
            else:
                footer = "Up/Down: Navigate | Enter: Select/Open | Esc/q: Cancel"
            self.draw_footer(footer)

            self.stdscr.refresh()

            # Handle input
            key = self.stdscr.getch()

            if key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(items) - 1:
                selected += 1
            elif key == ord(' ') and select_dirs:
                # Select current directory
                return str(current_dir)
            elif key == ord('\n'):
                if items:
                    name, is_dir, path = items[selected]
                    if is_dir:
                        # Navigate into directory
                        current_dir = path
                        selected = 0
                        scroll_offset = 0
                    else:
                        # Select file
                        return str(path)
            elif key == 27 or key == ord('q'):  # ESC or q
                return None

    def _draw_alert_window(self, title: str, message: str, footer_text: str,
                           color_pair: int = 5, footer_color: int = 5) -> tuple:
        """Shared method to draw a centered alert window. Returns (start_y, start_x, window_width, bottom_y)."""
        lines = message.split('\n')

        # Map color pairs to their blue-background equivalents
        # 2->10 (success), 3->11 (error), 4->12 (warning), 5->13 (info)
        color_map = {2: 10, 3: 11, 4: 12, 5: 13}
        content_color = color_map.get(color_pair, 14)  # Default to white on blue
        title_color = color_map.get(color_pair, 14)
        footer_color_blue = color_map.get(footer_color, 14)

        # Calculate window size with padding
        max_line_len = max(len(line) for line in lines) if lines else 0
        max_line_len = max(max_line_len, len(title) + 4, len(footer_text) + 4)
        window_width = min(max_line_len + 10, self.width - 4)  # Increased padding
        window_height = len(lines) + 6  # Title + content + borders + padding

        # Calculate centered position
        start_y = max(1, (self.height - window_height) // 2)
        start_x = max(1, (self.width - window_width) // 2)

        # Draw shadow effect (bottom and right edges)
        shadow_offset = 1
        # Right shadow
        for y in range(start_y + 1, min(start_y + window_height + 2, self.height - 1)):
            if start_x + window_width + shadow_offset < self.width:
                self.stdscr.attron(curses.A_DIM)
                self.stdscr.addstr(y, start_x + window_width, "░")
                self.stdscr.attroff(curses.A_DIM)
        # Bottom shadow
        if start_y + window_height + 2 < self.height - 1:
            for x in range(start_x + shadow_offset, min(start_x + window_width + shadow_offset, self.width)):
                self.stdscr.attron(curses.A_DIM)
                self.stdscr.addstr(start_y + window_height + 2, x, "░")
                self.stdscr.attroff(curses.A_DIM)

        # Draw background with blue color for entire window area
        self.stdscr.attron(curses.color_pair(9))
        for y in range(start_y, min(start_y + window_height + 2, self.height - 1)):
            self.stdscr.addstr(y, start_x, " " * window_width)

        # Top border with blue background
        self.stdscr.addstr(start_y, start_x, "┌" + "─" * (window_width - 2) + "┐")

        # Title line with blue background
        title_text = f" {title} "
        title_line = " " * (window_width - 2)
        self.stdscr.addstr(start_y + 1, start_x, "│" + title_line + "│")
        self.stdscr.attron(curses.color_pair(title_color) | curses.A_BOLD)
        self.stdscr.addstr(start_y + 1, start_x + (window_width - len(title_text)) // 2, title_text)
        self.stdscr.attroff(curses.color_pair(title_color) | curses.A_BOLD)
        self.stdscr.attron(curses.color_pair(9))

        # Separator after title
        self.stdscr.addstr(start_y + 2, start_x, "├" + "─" * (window_width - 2) + "┤")

        # Empty line for padding
        self.stdscr.addstr(start_y + 3, start_x, "│" + " " * (window_width - 2) + "│")

        # Content lines with blue background
        for idx, line in enumerate(lines):
            y = start_y + 4 + idx
            content_line = " " * (window_width - 2)
            self.stdscr.addstr(y, start_x, "│" + content_line + "│")
            self.stdscr.attron(curses.color_pair(content_color))
            # Center-align content within the window
            content_x = start_x + (window_width - len(line)) // 2
            self.stdscr.addstr(y, content_x, line[:window_width - 4])
            self.stdscr.attroff(curses.color_pair(content_color))
            self.stdscr.attron(curses.color_pair(9))

        # Empty line for padding
        bottom_padding_y = start_y + 4 + len(lines)
        self.stdscr.addstr(bottom_padding_y, start_x, "│" + " " * (window_width - 2) + "│")

        # Bottom border
        bottom_y = bottom_padding_y + 1
        self.stdscr.addstr(bottom_y, start_x, "└" + "─" * (window_width - 2) + "┘")

        # Footer message below window with blue background
        footer_y = bottom_y + 1
        if footer_y < self.height - 1:
            self.stdscr.addstr(footer_y, start_x, " " * window_width)
            self.stdscr.attron(curses.color_pair(footer_color_blue))
            self.stdscr.addstr(footer_y, start_x + (window_width - len(footer_text)) // 2, footer_text)
            self.stdscr.attroff(curses.color_pair(footer_color_blue))

        self.stdscr.attroff(curses.color_pair(9))

        return start_y, start_x, window_width, bottom_y

    def show_message(self, title: str, message: str, color_pair: int = 5) -> None:
        """Show a message in a centered window and wait for user to press a key."""
        self._draw_alert_window(title, message, "Press any key to continue...", color_pair, 5)
        self.stdscr.refresh()
        self.stdscr.getch()

    def show_confirm(self, title: str, message: str, color_pair: int = 5) -> bool:
        """Show a confirmation dialog in a centered window. Returns True if 'y' pressed."""
        self._draw_alert_window(title, message, "Press 'y' to confirm, any other key to cancel", color_pair, 4)
        self.stdscr.refresh()
        key = self.stdscr.getch()
        return key == ord('y') or key == ord('Y')

    def get_current_system(self) -> Optional[SystemConfig]:
        """Get the currently selected system."""
        if 0 <= self.current_system_idx < len(self.systems):
            return self.systems[self.current_system_idx]
        return None

    def main_menu(self) -> None:
        """Display and handle the main menu."""
        selected = 0
        menu_items = [
            ("1", "Manage Systems", "Add, edit, or remove system configurations"),
            ("2", "Select Active System", "Choose which system to work with"),
            ("3", "Configure Current System", "Set DAT file, ROM folder, and viewport configuration"),
            ("4", "Browse DAT File", "Explore games in the DAT file with detailed metadata"),
            ("5", "Process Current System", "Apply viewport configurations to current system ROMs"),
            ("6", "Process All Systems", "Apply viewport configurations to all configured systems"),
            ("7", "Remove Current System Overrides", "Remove viewport overrides from current system config files"),
            ("8", "Remove All Systems Overrides", "Remove viewport overrides from all systems config files"),
            ("s", "Save Configuration", "Save all system configurations to disk"),
            ("c", "Load Configuration", "Load system configurations from disk"),
            ("0", "Settings", "Configure application preferences"),
            ("l", "View Log", "View application log messages"),
            ("q", "Exit", "Quit the application")
        ]

        while True:
            self.stdscr.clear()
            self.draw_header("Viewport Configuration Tool - Main Menu")

            # Display system overview
            y = 2
            self.stdscr.attron(curses.color_pair(5))
            self.stdscr.addstr(y, 2, f"Systems: {len(self.systems)}")
            auto_save_status = "On" if self.auto_save_enabled else "Off"
            self.stdscr.addstr(y, self.width - 20, f"Auto-Save: {auto_save_status}")
            self.stdscr.attroff(curses.color_pair(5))

            # Display current system in a rectangle
            current_system = self.get_current_system()
            y += 2
            box_width = self.width - 6
            box_x = 3

            # Draw top border
            self.stdscr.attron(curses.color_pair(6) | curses.A_DIM)
            self.stdscr.addstr(y, box_x, "┌" + "─" * (box_width - 2) + "┐")
            y += 1

            if current_system:
                # Current system name
                system_line = f"Current System: {current_system.name}"
                self.stdscr.attron(curses.color_pair(6) | curses.A_DIM | curses.A_BOLD)
                self.stdscr.addstr(y, box_x, "│ " + system_line[:box_width-4].ljust(box_width-3) + "│")
                self.stdscr.attroff(curses.color_pair(6) | curses.A_DIM | curses.A_BOLD)
                y += 1

                # DAT file
                self.stdscr.attron(curses.color_pair(6) | curses.A_DIM)
                dat_status = current_system.dat_file if current_system.dat_file else "[Not Set]"
                dat_line = f"  DAT: {dat_status}"
                self.stdscr.addstr(y, box_x, "│ " + dat_line[:box_width-4].ljust(box_width-3) + "│")
                y += 1

                # ROM folder
                rom_status = current_system.rom_folder if current_system.rom_folder else "[Not Set]"
                rom_line = f"  ROMs: {rom_status}"
                self.stdscr.addstr(y, box_x, "│ " + rom_line[:box_width-4].ljust(box_width-3) + "│")
                y += 1

                # Export folder
                export_status = current_system.export_folder if current_system.export_folder else "[None - use ROM folder]"
                export_line = f"  Export: {export_status}"
                self.stdscr.addstr(y, box_x, "│ " + export_line[:box_width-4].ljust(box_width-3) + "│")
                y += 1

                # Override
                override_status = f"{current_system.override_width}x{current_system.override_height}" \
                    if current_system.override_width else "[None]"
                override_line = f"  Override: {override_status}"
                self.stdscr.addstr(y, box_x, "│ " + override_line[:box_width-4].ljust(box_width-3) + "│")
            else:
                # No system configured
                msg = "No systems configured - use 'Manage Systems' to add one"
                self.stdscr.attron(curses.color_pair(6) | curses.A_DIM)
                self.stdscr.addstr(y, box_x, "│ " + msg[:box_width-4].ljust(box_width-3) + "│")

            y += 1
            # Draw bottom border
            self.stdscr.addstr(y, box_x, "└" + "─" * (box_width - 2) + "┘")
            self.stdscr.attroff(curses.color_pair(6) | curses.A_DIM)

            # Menu items
            y += 2
            for idx, (key, label, _) in enumerate(menu_items):
                if idx == selected:
                    self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                    self.stdscr.addstr(y, 4, f"> [{key}] {label}")
                    self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
                else:
                    self.stdscr.addstr(y, 4, f"  [{key}] {label}")
                y += 1

            # Show description of selected option at bottom
            _, _, description = menu_items[selected]
            desc_y = self.height - 3
            self.stdscr.attron(curses.color_pair(5))
            self.stdscr.addstr(desc_y, 2, description[:self.width-4])
            self.stdscr.attroff(curses.color_pair(5))

            self.draw_footer("Up/Down: Navigate | 1-8/s/c/0/l: Select | Enter: Confirm | q: Quit")
            self.stdscr.refresh()

            key = self.stdscr.getch()

            # Handle navigation
            if key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(menu_items) - 1:
                selected += 1
            # Direct key execution
            elif key == ord('1'):
                self.manage_systems()
            elif key == ord('2'):
                self.select_system()
            elif key == ord('3'):
                self.configure_current_system()
            elif key == ord('4'):
                self.browse_dat_file()
            elif key == ord('5'):
                self.process_current_system()
            elif key == ord('6'):
                self.process_all_systems()
            elif key == ord('7'):
                self.remove_current_system_overrides()
            elif key == ord('8'):
                self.remove_all_systems_overrides()
            elif key == ord('s') or key == ord('S'):
                self.save_config_menu()
            elif key == ord('c') or key == ord('C'):
                self.load_config_menu()
            elif key == ord('0'):
                self.settings_menu()
            elif key == ord('l') or key == ord('L'):
                self.view_log()
            elif key == ord('q') or key == ord('Q'):
                break
            # Enter key executes selected item
            elif key == ord('\n'):
                if selected == 0:
                    self.manage_systems()
                elif selected == 1:
                    self.select_system()
                elif selected == 2:
                    self.configure_current_system()
                elif selected == 3:
                    self.browse_dat_file()
                elif selected == 4:
                    self.process_current_system()
                elif selected == 5:
                    self.process_all_systems()
                elif selected == 6:
                    self.remove_current_system_overrides()
                elif selected == 7:
                    self.remove_all_systems_overrides()
                elif selected == 8:
                    self.save_config_menu()
                elif selected == 9:
                    self.load_config_menu()
                elif selected == 10:
                    self.settings_menu()
                elif selected == 11:
                    self.view_log()
                elif selected == 12:
                    break

    def settings_menu(self) -> None:
        """Settings menu for configuring application preferences."""
        selected = 0

        while True:
            self.stdscr.clear()
            self.draw_header("Settings")

            y = 2
            self.stdscr.attron(curses.color_pair(5))
            self.stdscr.addstr(y, 2, "Current Settings:")
            self.stdscr.attroff(curses.color_pair(5))

            y += 2
            auto_save_status = "Enabled" if self.auto_save_enabled else "Disabled"
            auto_save_color = 2 if self.auto_save_enabled else 3
            self.stdscr.addstr(y, 4, "Auto-Save on Exit: ")
            self.stdscr.attron(curses.color_pair(auto_save_color) | curses.A_BOLD)
            self.stdscr.addstr(auto_save_status)
            self.stdscr.attroff(curses.color_pair(auto_save_color) | curses.A_BOLD)

            y += 1
            self.stdscr.attron(curses.color_pair(4))
            self.stdscr.addstr(y, 4, f"Config File: {self.CONFIG_FILE}")
            self.stdscr.attroff(curses.color_pair(4))

            y += 2
            menu_items = [
                (f"Toggle Auto-Save (Currently: {auto_save_status})", "Automatically save configuration when exiting the application"),
            ]

            self.draw_menu("", menu_items, selected, y)

            # Show description of selected option at bottom
            _, description = menu_items[selected]
            desc_y = self.height - 3
            self.stdscr.attron(curses.color_pair(5))
            self.stdscr.addstr(desc_y, 2, description[:self.width-4])
            self.stdscr.attroff(curses.color_pair(5))

            self.draw_footer("Up/Down: Navigate | Enter: Select | Esc/q: Back")
            self.stdscr.refresh()

            key = self.stdscr.getch()

            if key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(menu_items) - 1:
                selected += 1
            elif key == ord('\n'):
                if selected == 0:
                    # Toggle auto-save
                    self.auto_save_enabled = not self.auto_save_enabled
                    status = "enabled" if self.auto_save_enabled else "disabled"
                    self.log(f"Auto-save {status}")
                    self.show_message("Success",
                                    f"Auto-save on exit is now {status}.\n\n"
                                    f"{'Configuration will be automatically saved when you exit.' if self.auto_save_enabled else 'You will need to manually save configuration before exiting.'}", 2)
            elif key == 27 or key == ord('q'):
                break

    def save_config_menu(self) -> None:
        """Menu for saving configuration."""
        if not self.systems:
            self.show_message("Warning", "No systems configured.\nNothing to save.", 4)
            return

        # Show confirmation with details
        system_list = "\n".join([f"  - {s.name}" for s in self.systems])
        message = f"Save {len(self.systems)} system(s) to:\n{self.CONFIG_FILE}\n\nSystems:\n{system_list}"

        if self.show_confirm("Save Configuration", message, 5):
            if self.save_config():
                self.show_message("Success", f"Configuration saved!\n\nLocation: {self.CONFIG_FILE}", 2)
            else:
                self.show_message("Error", "Failed to save configuration.\nCheck the log for details.", 3)

    def load_config_menu(self) -> None:
        """Menu for loading configuration."""
        if not self.CONFIG_FILE.exists():
            self.show_message("Error", f"No saved configuration found.\n\nExpected location:\n{self.CONFIG_FILE}", 3)
            return

        # Show confirmation
        current_count = len(self.systems)
        message = f"Load configuration from:\n{self.CONFIG_FILE}\n"

        if current_count > 0:
            message += f"\nWarning: This will replace your current {current_count} system(s)!"

        if self.show_confirm("Load Configuration", message, 4 if current_count > 0 else 5):
            if self.load_config():
                system_list = "\n".join([f"  - {s.name}" for s in self.systems])
                self.show_message("Success",
                                f"Configuration loaded!\n\nLoaded {len(self.systems)} system(s):\n{system_list}", 2)
            else:
                self.show_message("Error", "Failed to load configuration.\nCheck the log for details.", 3)

    def browse_dat_file(self) -> None:
        """Browse DAT file with detailed information, split view, and filtering."""
        system = self.get_current_system()
        if not system:
            self.show_message("Error", "No system selected.", 3)
            return

        if not system.dat_file:
            self.show_message("Error", "No DAT file set for current system.\nPlease configure the system first.", 3)
            return

        try:
            # Create temporary manager to parse DAT
            temp_manager = ViewportConfigurationManager(
                system.dat_file,
                None,
                system.override_width,
                system.override_height,
                system.override_x,
                system.override_y,
                None,  # No export folder needed for browsing
                log_callback=self.log
            )
            temp_manager.parse_dat_file()

            all_games = sorted(temp_manager.game_info.values(), key=lambda g: g.name)

            if not all_games:
                self.show_message("Warning", "No games with resolution data found in DAT file.", 4)
                return

            selected = 0
            scroll_offset = 0
            filter_text = ""
            games = all_games  # Initially show all games

            while True:
                self.stdscr.clear()

                # Calculate split point (60% top, 40% bottom)
                split_y = int(self.height * 0.6)

                # === TOP SECTION: Game List ===
                if filter_text:
                    self.draw_header(f"DAT Browser: {system.name} ({len(games)}/{len(all_games)} games) Filter: {filter_text}")
                else:
                    self.draw_header(f"DAT Browser: {system.name} ({len(games)} games)")

                # Column headers for top section - dynamic width calculation
                y = 2
                available_width = self.width - 4  # Leave some margin

                # Calculate dynamic column widths based on available width
                # Minimum widths for fixed columns
                name_width = 15
                year_width = 6
                res_width = 11
                orient_width = 6   # Orientation (rotate)
                screen_width = 8   # Screen type (raster/vector/etc)
                clone_width = 10
                rom_width = 4      # ROM status (Y/N/-)
                ovr_width = 4      # Override status (Y/N)

                # Remaining width split between description and manufacturer
                fixed_width = name_width + year_width + res_width + orient_width + screen_width + clone_width + rom_width + ovr_width + 8  # spaces between
                remaining = available_width - fixed_width

                if remaining > 30:
                    desc_width = int(remaining * 0.6)
                    mfr_width = remaining - desc_width
                else:
                    desc_width = max(20, remaining // 2)
                    mfr_width = max(10, remaining - desc_width)

                self.stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
                header = f"{'Name':<{name_width}} {'Desc':<{desc_width}} {'Year':<{year_width}} {'Mfr':<{mfr_width}} {'Res':<{res_width}} {'Orient':<{orient_width}} {'Screen':<{screen_width}} {'Clone':<{clone_width}} {'ROM':<{rom_width}} {'OVR':<{ovr_width}}"
                self.stdscr.addstr(y, 0, header[:self.width])
                self.stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)

                # Calculate visible games in top section
                max_visible_top = split_y - 4  # Header + column header + padding

                # Adjust scroll
                if selected < scroll_offset:
                    scroll_offset = selected
                elif selected >= scroll_offset + max_visible_top:
                    scroll_offset = selected - max_visible_top + 1

                # Display games in top section
                y = 3
                for idx in range(scroll_offset, min(scroll_offset + max_visible_top, len(games))):
                    if y >= split_y - 1:
                        break

                    game = games[idx]

                    # Check if ROM exists
                    rom_status = "-"
                    if system.rom_folder:
                        rom_path = Path(system.rom_folder) / f"{game.name}.zip"
                        rom_status = "Y" if rom_path.exists() else "N"

                    # Check if viewport override exists in config
                    override_status = "N"
                    config_path = None

                    # Determine config file location
                    if system.export_folder:
                        config_path = Path(system.export_folder) / f"{game.name}.zip.cfg"
                    elif system.rom_folder:
                        config_path = Path(system.rom_folder) / f"{game.name}.zip.cfg"

                    # Check if config exists and contains viewport overrides
                    if config_path is not None and config_path.exists():
                        try:
                            with open(config_path, 'r') as f:
                                content = f.read()
                                if 'custom_viewport_width' in content or 'custom_viewport_height' in content:
                                    override_status = "Y"
                        except Exception:
                            # If we can't read the file, assume no override
                            pass

                    # Truncate fields to fit calculated widths
                    name = game.name[:name_width-1]
                    desc = game.description[:desc_width-1]
                    year = game.year[:year_width-1]
                    mfr = game.manufacturer[:mfr_width-1]
                    res = f"{game.width}x{game.height}"[:res_width-1]
                    orient = (game.rotate[:orient_width-1] if game.rotate else "-")
                    screen = (game.screen_type[:screen_width-1] if game.screen_type else "-")
                    clone = (game.cloneof[:clone_width-1] if game.cloneof else "-")

                    line = f"{name:<{name_width}} {desc:<{desc_width}} {year:<{year_width}} {mfr:<{mfr_width}} {res:<{res_width}} {orient:<{orient_width}} {screen:<{screen_width}} {clone:<{clone_width}} {rom_status:<{rom_width}} {override_status:<{ovr_width}}"

                    if idx == selected:
                        self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                        self.stdscr.addstr(y, 0, f">{line}"[:self.width])
                        self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
                    else:
                        self.stdscr.addstr(y, 0, f" {line}"[:self.width])

                    y += 1

                # Draw separator line
                self.stdscr.attron(curses.color_pair(5))
                self.stdscr.addstr(split_y, 0, "=" * self.width)
                self.stdscr.attroff(curses.color_pair(5))

                # === BOTTOM SECTION: Config Preview ===
                y = split_y + 1
                self.stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
                self.stdscr.addstr(y, 1, "Overrides Preview:")
                self.stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)

                y += 1
                if selected < len(games):
                    game = games[selected]

                    # Determine what resolution will be written
                    final_width = system.override_width if system.override_width else game.width
                    final_height = system.override_height if system.override_height else game.height

                    # Show game details
                    self.stdscr.attron(curses.color_pair(5))
                    game_line = f"Game: {game.name}"
                    self.stdscr.addstr(y, 1, game_line[:self.width-2])
                    y += 1
                    if game.description:
                        desc_display = game.description if len(game.description) <= self.width - 15 else game.description[:self.width-18] + "..."
                        desc_line = f"Description: {desc_display}"
                        self.stdscr.addstr(y, 1, desc_line[:self.width-2])
                        y += 1

                    # Show year and manufacturer on same line if they fit
                    if game.year or game.manufacturer:
                        info_line = ""
                        if game.year:
                            info_line += f"Year: {game.year}"
                        if game.manufacturer:
                            if info_line:
                                info_line += "  |  "
                            info_line += f"Manufacturer: {game.manufacturer}"
                        self.stdscr.addstr(y, 1, info_line[:self.width-2])
                        y += 1

                    # Show orientation and screen type if available
                    if game.rotate or game.screen_type:
                        display_line = ""
                        if game.rotate:
                            display_line += f"Orientation: {game.rotate}"
                        if game.screen_type:
                            if display_line:
                                display_line += "  |  "
                            display_line += f"Screen: {game.screen_type}"
                        self.stdscr.addstr(y, 1, display_line[:self.width-2])
                        y += 1

                    if game.cloneof:
                        clone_line = f"Clone of: {game.cloneof}"
                        self.stdscr.addstr(y, 1, clone_line[:self.width-2])
                        y += 1

                    self.stdscr.attroff(curses.color_pair(5))

                    y += 1

                    # Show original vs final resolution
                    res_line = f"Original Resolution: {game.width}x{game.height}"
                    self.stdscr.addstr(y, 1, res_line[:self.width-2])
                    y += 1

                    if system.override_width or system.override_height:
                        self.stdscr.attron(curses.color_pair(4))
                        override_line = f"Override Applied: {final_width}x{final_height}"
                        self.stdscr.addstr(y, 1, override_line[:self.width-2])
                        self.stdscr.attroff(curses.color_pair(4))
                        y += 1

                    y += 1

                    # Show config file name outside the box
                    cfg_line = f"Overrides will be written to {game.name}.zip.cfg as:"
                    self.stdscr.addstr(y, 1, cfg_line[:self.width-2])
                    y += 1

                    # Draw rectangle for config file preview
                    box_width = self.width - 4
                    box_x = 2

                    # Draw top border with dark gray background
                    self.stdscr.attron(curses.color_pair(6) | curses.A_DIM)
                    self.stdscr.addstr(y, box_x, "┌" + "─" * (box_width - 2) + "┐")
                    y += 1

                    # Config file entries inside box with dark gray background
                    # Show aspect_ratio_index first
                    aspect_line = f"aspect_ratio_index = \"23\""
                    self.stdscr.addstr(y, box_x, "│ " + aspect_line[:box_width-4].ljust(box_width-3) + "│")
                    y += 1

                    # Show X and Y position (always show them, use override if set or 0 if not)
                    final_x = system.override_x if system.override_x is not None else 0
                    final_y = system.override_y if system.override_y is not None else 0

                    x_line = f"custom_viewport_x = \"{final_x}\""
                    self.stdscr.addstr(y, box_x, "│ " + x_line[:box_width-4].ljust(box_width-3) + "│")
                    y += 1

                    y_line = f"custom_viewport_y = \"{final_y}\""
                    self.stdscr.addstr(y, box_x, "│ " + y_line[:box_width-4].ljust(box_width-3) + "│")
                    y += 1

                    width_line = f"custom_viewport_width = \"{final_width}\""
                    self.stdscr.addstr(y, box_x, "│ " + width_line[:box_width-4].ljust(box_width-3) + "│")
                    y += 1

                    height_line = f"custom_viewport_height = \"{final_height}\""
                    self.stdscr.addstr(y, box_x, "│ " + height_line[:box_width-4].ljust(box_width-3) + "│")
                    y += 1

                    # Draw bottom border
                    self.stdscr.addstr(y, box_x, "└" + "─" * (box_width - 2) + "┘")
                    self.stdscr.attroff(curses.color_pair(6) | curses.A_DIM)

                self.draw_footer("Up/Down: Navigate | Enter: Write Config | d: Delete Override | /: Filter | c: Clear | q: Back")
                self.stdscr.refresh()

                key = self.stdscr.getch()

                if key == curses.KEY_UP and selected > 0:
                    selected -= 1
                elif key == curses.KEY_DOWN and selected < len(games) - 1:
                    selected += 1
                elif key == ord('d') or key == ord('D'):
                    # Delete override for selected game
                    if selected < len(games):
                        game = games[selected]

                        # Determine output location
                        if system.export_folder:
                            output_location = system.export_folder
                        elif system.rom_folder:
                            output_location = system.rom_folder
                        else:
                            self.show_message("Error", "No ROM folder or export folder set.\nPlease configure the system first.", 3)
                            continue

                        # Confirm with user
                        confirm_msg = f"Remove viewport override for {game.name}?\n\n"
                        confirm_msg += f"This will remove:\n"
                        confirm_msg += f"  - custom_viewport_width\n"
                        confirm_msg += f"  - custom_viewport_height\n"
                        confirm_msg += f"  - aspect_ratio_index\n\n"
                        confirm_msg += f"Location: {output_location}"

                        if self.show_confirm("Confirm Remove Override", confirm_msg, 4):
                            try:
                                # Create a temporary manager to remove the config
                                remove_manager = ViewportConfigurationManager(
                                    system.dat_file,
                                    system.rom_folder if system.rom_folder else None,
                                    system.override_width,
                                    system.override_height,
                                    system.override_x,
                                    system.override_y,
                                    system.export_folder if system.export_folder else None,
                                    log_callback=self.log
                                )
                                removed, is_empty = remove_manager.remove_rom_config(game.name, delete_if_empty=False)
                                if removed:
                                    if is_empty:
                                        # Ask if user wants to delete empty file
                                        delete_msg = f"Config file for {game.name} is now empty.\n\nDelete the empty config file?"
                                        if self.show_confirm("Delete Empty Config?", delete_msg, 3):
                                            remove_manager.delete_empty_config(game.name)
                                            self.show_message("Success", f"Removed override and deleted empty config for {game.name}", 2)
                                        else:
                                            self.show_message("Success", f"Removed viewport override for {game.name}\n(Empty config file kept)", 2)
                                    else:
                                        self.show_message("Success", f"Removed viewport override for {game.name}", 2)
                                    # Force screen refresh to update OVR column
                                    continue
                                else:
                                    self.show_message("Info", f"No viewport override found for {game.name}", 5)
                            except Exception as e:
                                self.show_message("Error", f"Failed to remove override:\n{str(e)}", 3)
                elif key == ord('\n'):
                    # Write config for selected game
                    if selected < len(games):
                        game = games[selected]
                        final_width = system.override_width if system.override_width else game.width
                        final_height = system.override_height if system.override_height else game.height

                        # Determine output location
                        if system.export_folder:
                            output_location = system.export_folder
                        elif system.rom_folder:
                            output_location = system.rom_folder
                        else:
                            self.show_message("Error", "No ROM folder or export folder set.\nPlease configure the system first.", 3)
                            continue

                        # Confirm with user
                        confirm_msg = f"Write config for {game.name}?\n\n"
                        confirm_msg += f"Resolution: {final_width}x{final_height}\n"
                        confirm_msg += f"Output: {output_location}"

                        if self.show_confirm("Confirm Write Config", confirm_msg, 5):
                            try:
                                # Create a temporary manager to write the config
                                write_manager = ViewportConfigurationManager(
                                    system.dat_file,
                                    system.rom_folder if system.rom_folder else None,
                                    system.override_width,
                                    system.override_height,
                                    system.override_x,
                                    system.override_y,
                                    system.export_folder if system.export_folder else None,
                                    log_callback=self.log
                                )
                                write_manager.parse_dat_file()
                                write_manager.update_rom_config(game.name, final_width, final_height,
                                                               system.override_x, system.override_y)
                                self.show_message("Success", f"Config written for {game.name}\n{final_width}x{final_height}", 2)
                            except Exception as e:
                                self.show_message("Error", f"Failed to write config:\n{str(e)}", 3)
                elif key == ord('/'):
                    # Enter filter mode
                    new_filter = self.get_input("Filter games (name/description/year/mfr):", filter_text)
                    if new_filter is not None:
                        filter_text = new_filter.lower()
                        # Apply filter
                        if filter_text:
                            games = [g for g in all_games if
                                    filter_text in g.name.lower() or
                                    filter_text in g.description.lower() or
                                    filter_text in g.year.lower() or
                                    filter_text in g.manufacturer.lower()]
                        else:
                            games = all_games
                        # Reset selection
                        selected = 0
                        scroll_offset = 0
                elif key == ord('c') or key == ord('C'):
                    # Clear filter
                    filter_text = ""
                    games = all_games
                    selected = 0
                    scroll_offset = 0
                elif key == 27 or key == ord('q'):  # ESC or q
                    break

        except Exception as e:
            self.show_message("Error", f"Failed to browse DAT file:\n{str(e)}", 3)

    def manage_systems(self) -> None:
        """Manage system configurations."""
        selected = 0

        while True:
            menu_items = []
            for system in self.systems:
                status = "OK" if system.dat_file and system.rom_folder else "!"
                menu_items.append((f"[{status}] {system.name}", f"Configure {system.name} settings"))

            menu_items.extend([
                ("", ""),
                ("Add New System", "Add a new emulation system configuration"),
                ("Remove Selected System", "Remove the currently selected system"),
                ("Back", "Return to main menu")
            ])

            self.stdscr.clear()
            self.draw_header("Manage Systems")

            self.draw_menu("", menu_items, selected, 2)

            # Show description of selected option at bottom
            _, description = menu_items[selected]
            if description:  # Only show if there's a description
                desc_y = self.height - 3
                self.stdscr.attron(curses.color_pair(5))
                self.stdscr.addstr(desc_y, 2, description[:self.width-4])
                self.stdscr.attroff(curses.color_pair(5))

            self.draw_footer("Up/Down: Navigate | Enter: Select | Esc/q: Back")
            self.stdscr.refresh()

            key = self.stdscr.getch()

            if key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(menu_items) - 1:
                selected += 1
            elif key == ord('\n'):
                item_text = menu_items[selected][0] if isinstance(menu_items[selected], tuple) else menu_items[selected]

                if selected < len(self.systems):
                    # Edit existing system
                    self.current_system_idx = selected
                    self.configure_current_system()
                elif item_text == "Add New System":
                    self.add_new_system()
                elif item_text == "Remove Selected System":
                    if self.systems and self.current_system_idx < len(self.systems):
                        removed = self.systems.pop(self.current_system_idx)
                        self.show_message("Success", f"Removed system: {removed.name}", 2)
                        if self.current_system_idx >= len(self.systems) and self.systems:
                            self.current_system_idx = len(self.systems) - 1
                elif item_text == "Back":
                    break
            elif key == 27 or key == ord('q'):
                break

    def add_new_system(self) -> None:
        """Add a new system configuration."""
        name = self.get_input("Enter system name (e.g., 'FinalBurn Neo', 'MAME 2003 Plus'):", "")
        if name:
            self.systems.append(SystemConfig(name))
            self.current_system_idx = len(self.systems) - 1
            self.show_message("Success", f"Added system: {name}\nConfigure it in the next screen.", 2)
            self.configure_current_system()

    def select_system(self) -> None:
        """Select the active system."""
        if not self.systems:
            self.show_message("Error", "No systems configured.\nAdd a system first.", 3)
            return

        selected = self.current_system_idx

        while True:
            self.stdscr.clear()
            self.draw_header("Select Active System")

            menu_items = [system.name for system in self.systems]
            self.draw_menu("", menu_items, selected, 2)

            self.draw_footer("Up/Down: Navigate | Enter: Select | Esc/q: Back")
            self.stdscr.refresh()

            key = self.stdscr.getch()

            if key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(menu_items) - 1:
                selected += 1
            elif key == ord('\n'):
                self.current_system_idx = selected
                self.show_message("Success", f"Active system: {self.systems[selected].name}", 2)
                break
            elif key == 27 or key == ord('q'):
                break

    def configure_current_system(self) -> None:
        """Configure the current system."""
        system = self.get_current_system()
        if not system:
            self.show_message("Error", "No system selected.", 3)
            return

        selected = 0
        menu_items = [
            ("[1] Set DAT File Path", "Browse or manually enter DAT file path"),
            ("[2] Download and set DAT File from Web", "Download DAT file from libretro repositories"),
            ("[3] Set ROM Folder Path", "Browse or manually enter ROM folder path"),
            ("[4] Set Export Folder Path", "Set optional export folder for config files"),
            ("[5] Set Viewport Configuration", "Configure viewport width, height, and position overrides"),
            ("[6] Backup Config Files", "Create a zip backup of all config files"),
            ("[7] Restore Config Files", "Restore config files from a zip backup"),
            ("[8] Back", "Return to main menu")
        ]

        while True:
            self.stdscr.clear()
            self.draw_header(f"Configure: {system.name}")

            y = 2
            self.stdscr.attron(curses.color_pair(5))
            self.stdscr.addstr(y, 2, "Current Settings:")
            self.stdscr.attroff(curses.color_pair(5))

            y += 1
            dat_status = system.dat_file if system.dat_file else "[Not Set]"
            self.stdscr.addstr(y, 4, f"DAT: {dat_status[:self.width-10]}")

            y += 1
            rom_status = system.rom_folder if system.rom_folder else "[Not Set]"
            self.stdscr.addstr(y, 4, f"ROMs: {rom_status[:self.width-10]}")

            y += 1
            export_status = system.export_folder if system.export_folder else "[None - use ROM folder]"
            self.stdscr.addstr(y, 4, f"Export: {export_status[:self.width-10]}")

            y += 1
            override_status = f"{system.override_width}x{system.override_height}" \
                if system.override_width else "[None]"
            self.stdscr.addstr(y, 4, f"Override: {override_status}")

            y += 2
            self.draw_menu("", menu_items, selected, y)

            # Show description of selected option at bottom
            _, description = menu_items[selected]
            desc_y = self.height - 3
            self.stdscr.attron(curses.color_pair(5))
            self.stdscr.addstr(desc_y, 2, description[:self.width-4])
            self.stdscr.attroff(curses.color_pair(5))

            self.draw_footer("Up/Down: Navigate | Enter: Select | Esc/q: Back")
            self.stdscr.refresh()

            key = self.stdscr.getch()

            # Check for numeric key press
            key_selection = self.get_menu_selection_from_key(key, menu_items)
            if key_selection is not None:
                selected = key_selection
                # Simulate Enter key press
                key = ord('\n')

            if key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(menu_items) - 1:
                selected += 1
            elif key == ord('\n'):
                if selected == 0:
                    self.set_system_dat_file(system)
                elif selected == 1:
                    self.download_dat_file_from_web(system)
                elif selected == 2:
                    self.set_system_rom_folder(system)
                elif selected == 3:
                    self.set_system_export_folder(system)
                elif selected == 4:
                    self.set_system_resolution_override(system)
                elif selected == 5:
                    self.backup_system_configs(system)
                elif selected == 6:
                    self.restore_system_configs(system)
                elif selected == 7:
                    break
            elif key == 27 or key == ord('q'):
                break


    def set_system_dat_file(self, system: SystemConfig) -> None:
        """Set the DAT file path for a system."""
        # Show selection menu: Browse or Manual Entry
        selected = 0
        menu_items = [
            ("[1] Browse for File", "Use file browser to select DAT file"),
            ("[2] Manual Entry", "Manually enter the DAT file path"),
            ("[3] Cancel", "Cancel and return to previous menu")
        ]

        while True:
            self.stdscr.clear()
            self.draw_header(f"Set DAT File: {system.name}")

            y = 2
            if system.dat_file:
                self.stdscr.attron(curses.color_pair(5))
                self.stdscr.addstr(y, 2, f"Current: {system.dat_file[:self.width-12]}")
                self.stdscr.attroff(curses.color_pair(5))
                y += 2

            self.draw_menu("", menu_items, selected, y)

            # Show description of selected option at bottom
            _, description = menu_items[selected]
            desc_y = self.height - 3
            self.stdscr.attron(curses.color_pair(5))
            self.stdscr.addstr(desc_y, 2, description[:self.width-4])
            self.stdscr.attroff(curses.color_pair(5))

            self.draw_footer("Up/Down: Navigate | Enter: Select | Esc/q: Cancel")
            self.stdscr.refresh()

            key = self.stdscr.getch()

            # Check for numeric key press
            key_selection = self.get_menu_selection_from_key(key, menu_items)
            if key_selection is not None:
                selected = key_selection
                key = ord('\n')

            if key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(menu_items) - 1:
                selected += 1
            elif key == ord('\n'):
                if selected == 0:  # Browse
                    start_path = system.dat_file if system.dat_file else None
                    result = self.file_browser(
                        f"Select DAT File for {system.name}",
                        start_path=start_path,
                        select_dirs=False,
                        file_pattern="*.xml;*.dat"
                    )
                    if result:
                        system.dat_file = result
                        system.manager = None
                        self.show_message("Success", f"DAT file set to:\n{result}", 2)
                        break
                elif selected == 1:  # Manual Entry
                    result = self.get_input(f"Enter DAT file path for {system.name}:", system.dat_file)
                    if result:
                        if os.path.exists(result):
                            system.dat_file = result
                            system.manager = None
                            self.show_message("Success", f"DAT file set to:\n{result}", 2)
                            break
                        else:
                            self.show_message("Error", f"File not found:\n{result}", 3)
                else:  # Cancel
                    break
            elif key == 27 or key == ord('q'):
                break

    def download_dat_file_from_web(self, system: SystemConfig) -> None:
        """Download a DAT file from predefined web sources."""
        dat_sources = get_dat_sources()

        selected = 0
        while True:
            self.stdscr.clear()
            self.draw_header("Download and set DAT File from Web")

            y = 2
            self.stdscr.attron(curses.color_pair(5))
            self.stdscr.addstr(y, 2, "Select a DAT file to download:")
            self.stdscr.attroff(curses.color_pair(5))
            y += 2

            # Display menu items
            for idx, source in enumerate(dat_sources):
                if idx == selected:
                    self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                    self.stdscr.addstr(y, 4, f"> [{idx + 1}] {source.name}")
                    self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
                else:
                    self.stdscr.addstr(y, 4, f"  [{idx + 1}] {source.name}")
                y += 1

            # Display Back option
            if selected == len(dat_sources):
                self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                self.stdscr.addstr(y, 4, f"> [{len(dat_sources) + 1}] Back")
                self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
            else:
                self.stdscr.addstr(y, 4, f"  [{len(dat_sources) + 1}] Back")

            self.draw_footer("Up/Down: Navigate | Enter: Download | Esc/q: Back")
            self.stdscr.refresh()

            key = self.stdscr.getch()

            # Handle numeric key presses (1-9)
            if ord('1') <= key <= ord('9'):
                key_num = key - ord('1')  # Convert to 0-based index
                if key_num < len(dat_sources):
                    selected = key_num
                    # Simulate Enter key press
                    key = ord('\n')
                elif key_num == len(dat_sources):
                    # "Back" option
                    break

            if key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(dat_sources):
                selected += 1
            elif key == ord('\n'):
                if selected == len(dat_sources):
                    break

                source = dat_sources[selected]

                # Create downloaded_dats folder in script directory
                script_dir = Path(__file__).parent.parent.parent / "downloaded_dats"
                script_dir.mkdir(exist_ok=True)  # Create directory if it doesn't exist

                # Show downloading message
                self.stdscr.clear()
                self.draw_header("Downloading DAT File")
                self.stdscr.addstr(self.height // 2 - 1, 4, f"Downloading: {source.name}")
                self.stdscr.addstr(self.height // 2, 4, f"URL: {source.url[:self.width-10]}")
                self.stdscr.addstr(self.height // 2 + 1, 4, "Please wait...")
                self.stdscr.refresh()

                # Download using network module
                success, file_path, error_msg = download_dat_file(source, script_dir)

                if success:
                    # Set the downloaded file as the DAT file
                    system.dat_file = str(file_path)
                    self.show_message("Success",
                                    f"Downloaded: {source.name}\n\n"
                                    f"File: {file_path}\n\n"
                                    f"Set as DAT file for {system.name}", 2)
                    break
                else:
                    # Show error message
                    self.show_message("Error",
                                    f"Failed to download {source.name}:\n\n"
                                    f"{error_msg}", 3)

            elif key == 27 or key == ord('q'):
                break

    def set_system_rom_folder(self, system: SystemConfig) -> None:
        """Set the ROM folder path for a system."""
        # Show selection menu: Browse or Manual Entry
        selected = 0
        menu_items = [
            ("[1] Browse for Folder", "Use file browser to select ROM folder"),
            ("[2] Manual Entry", "Manually enter the ROM folder path"),
            ("[3] Cancel", "Cancel and return to previous menu")
        ]

        while True:
            self.stdscr.clear()
            self.draw_header(f"Set ROM Folder: {system.name}")

            y = 2
            if system.rom_folder:
                self.stdscr.attron(curses.color_pair(5))
                self.stdscr.addstr(y, 2, f"Current: {system.rom_folder[:self.width-12]}")
                self.stdscr.attroff(curses.color_pair(5))
                y += 2

            self.draw_menu("", menu_items, selected, y)

            # Show description of selected option at bottom
            _, description = menu_items[selected]
            desc_y = self.height - 3
            self.stdscr.attron(curses.color_pair(5))
            self.stdscr.addstr(desc_y, 2, description[:self.width-4])
            self.stdscr.attroff(curses.color_pair(5))

            self.draw_footer("Up/Down: Navigate | Enter: Select | Esc/q: Cancel")
            self.stdscr.refresh()

            key = self.stdscr.getch()

            # Check for numeric key press
            key_selection = self.get_menu_selection_from_key(key, menu_items)
            if key_selection is not None:
                selected = key_selection
                key = ord('\n')

            if key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(menu_items) - 1:
                selected += 1
            elif key == ord('\n'):
                if selected == 0:  # Browse
                    start_path = system.rom_folder if system.rom_folder else None
                    result = self.file_browser(
                        f"Select ROM Folder for {system.name}",
                        start_path=start_path,
                        select_dirs=True
                    )
                    if result:
                        system.rom_folder = result
                        system.manager = None
                        self.show_message("Success", f"ROM folder set to:\n{result}", 2)
                        break
                elif selected == 1:  # Manual Entry
                    result = self.get_input(f"Enter ROM folder path for {system.name}:", system.rom_folder)
                    if result:
                        if os.path.exists(result) and os.path.isdir(result):
                            system.rom_folder = result
                            system.manager = None
                            self.show_message("Success", f"ROM folder set to:\n{result}", 2)
                            break
                        else:
                            self.show_message("Error", f"Directory not found:\n{result}", 3)
                else:  # Cancel
                    break
            elif key == 27 or key == ord('q'):
                break

    def set_system_export_folder(self, system: SystemConfig) -> None:
        """Set the export folder path for a system."""
        # Show selection menu: Browse, Manual Entry, or Clear
        selected = 0
        menu_items = [
            ("[1] Browse for Folder", "Use file browser to select export folder"),
            ("[2] Manual Entry", "Manually enter the export folder path"),
            ("[3] Clear Export Folder", "Clear export folder setting (will use ROM folder)"),
            ("[4] Cancel", "Cancel and return to previous menu")
        ]

        while True:
            self.stdscr.clear()
            self.draw_header(f"Set Export Folder: {system.name}")

            y = 2
            if system.export_folder:
                self.stdscr.attron(curses.color_pair(5))
                self.stdscr.addstr(y, 2, f"Current: {system.export_folder[:self.width-12]}")
                self.stdscr.attroff(curses.color_pair(5))
            else:
                self.stdscr.attron(curses.color_pair(4))
                self.stdscr.addstr(y, 2, "Not set - will use ROM folder")
                self.stdscr.attroff(curses.color_pair(4))
            y += 2

            self.draw_menu("", menu_items, selected, y)

            # Show description of selected option at bottom
            _, description = menu_items[selected]
            desc_y = self.height - 3
            self.stdscr.attron(curses.color_pair(5))
            self.stdscr.addstr(desc_y, 2, description[:self.width-4])
            self.stdscr.attroff(curses.color_pair(5))

            self.draw_footer("Up/Down: Navigate | Enter: Select | Esc/q: Cancel")
            self.stdscr.refresh()

            key = self.stdscr.getch()

            # Check for numeric key press
            key_selection = self.get_menu_selection_from_key(key, menu_items)
            if key_selection is not None:
                selected = key_selection
                key = ord('\n')

            if key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(menu_items) - 1:
                selected += 1
            elif key == ord('\n'):
                if selected == 0:  # Browse
                    start_path = system.export_folder if system.export_folder else None
                    result = self.file_browser(
                        f"Select Export Folder for {system.name}",
                        start_path=start_path,
                        select_dirs=True
                    )
                    if result:
                        system.export_folder = result
                        self.show_message("Success", f"Export folder set to:\n{result}", 2)
                        break
                elif selected == 1:  # Manual Entry
                    result = self.get_input(f"Enter export folder path for {system.name}:", system.export_folder)
                    if result:
                        if os.path.exists(result) and os.path.isdir(result):
                            system.export_folder = result
                            self.show_message("Success", f"Export folder set to:\n{result}", 2)
                            break
                        else:
                            self.show_message("Error", f"Directory not found:\n{result}", 3)
                elif selected == 2:  # Clear
                    system.export_folder = ""
                    self.show_message("Success", "Export folder cleared.\nWill use ROM folder.", 2)
                    break
                else:  # Cancel
                    break
            elif key == 27 or key == ord('q'):
                break

    def set_system_resolution_override(self, system: SystemConfig) -> None:
        """Set viewport configuration for a system."""
        width = self.get_input("Enter override width (or leave empty for none):",
                              str(system.override_width) if system.override_width else "")
        if width:
            try:
                system.override_width = int(width)
            except ValueError:
                self.show_message("Error", "Invalid width value", 3)
                return
        else:
            system.override_width = None

        height = self.get_input("Enter override height (or leave empty for none):",
                               str(system.override_height) if system.override_height else "")
        if height:
            try:
                system.override_height = int(height)
            except ValueError:
                self.show_message("Error", "Invalid height value", 3)
                return
        else:
            system.override_height = None

        x = self.get_input("Enter viewport X position (or leave empty for none):",
                          str(system.override_x) if system.override_x else "")
        if x:
            try:
                system.override_x = int(x)
            except ValueError:
                self.show_message("Error", "Invalid X position value", 3)
                return
        else:
            system.override_x = None

        y = self.get_input("Enter viewport Y position (or leave empty for none):",
                          str(system.override_y) if system.override_y else "")
        if y:
            try:
                system.override_y = int(y)
            except ValueError:
                self.show_message("Error", "Invalid Y position value", 3)
                return
        else:
            system.override_y = None

        if system.manager:
            system.manager.override_width = system.override_width
            system.manager.override_height = system.override_height
            system.manager.override_x = system.override_x
            system.manager.override_y = system.override_y

        # Build success message with position and size
        if system.override_width and system.override_height:
            msg_lines = ["Viewport configuration set to:"]

            x_val = system.override_x if system.override_x is not None else 0
            y_val = system.override_y if system.override_y is not None else 0
            msg_lines.append(f"Position: ({x_val}, {y_val})")
            msg_lines.append(f"Size: {system.override_width}x{system.override_height}")

            self.show_message("Success", "\n".join(msg_lines), 2)
        elif system.override_x is not None or system.override_y is not None:
            x_val = system.override_x if system.override_x is not None else 0
            y_val = system.override_y if system.override_y is not None else 0
            self.show_message("Success",
                            f"Viewport position set to:\n({x_val}, {y_val})\n\nNote: Width and height not set", 2)
        else:
            self.show_message("Success", "Viewport configuration cleared", 2)

    def backup_system_configs(self, system: SystemConfig) -> None:
        """Backup all config files for a system to a zip file."""
        if not self.initialize_system_manager(system, require_rom_folder=True):
            return

        # Get config folder (export folder or rom folder)
        config_folder = system.manager.export_folder if system.manager.export_folder else system.manager.rom_folder

        if not config_folder or not config_folder.exists():
            self.show_message("Error", f"Config folder not found:\n{config_folder}", 3)
            return

        # Check if there are any config files
        config_files = list(config_folder.glob('*.cfg'))
        if not config_files:
            self.show_message("Error", "No config files found to backup", 3)
            return

        # Ask user for backup location
        result = self.file_browser(
            "Select location to save backup",
            start_path=str(config_folder),
            select_dirs=True,
            file_pattern=None
        )

        if not result:
            return

        # Generate backup filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"config_backup_{timestamp}.zip"
        backup_path = Path(result) / backup_name

        # Show progress message
        self.show_message("Backup", f"Creating backup...\n{len(config_files)} config files", 1)

        # Create backup
        success, final_path, error = system.manager.backup_configs(backup_path)

        if success:
            self.show_message("Success",
                            f"Backup created successfully!\n\n"
                            f"Location: {final_path}\n"
                            f"Files backed up: {len(config_files)}",
                            3)
        else:
            self.show_message("Error", f"Backup failed:\n{error}", 3)

    def restore_system_configs(self, system: SystemConfig) -> None:
        """Restore config files from a zip backup."""
        if not self.initialize_system_manager(system, require_rom_folder=True):
            return

        # Get config folder (export folder or rom folder)
        config_folder = system.manager.export_folder if system.manager.export_folder else system.manager.rom_folder

        if not config_folder or not config_folder.exists():
            self.show_message("Error", f"Config folder not found:\n{config_folder}", 3)
            return

        # Ask user to select backup file
        result = self.file_browser(
            "Select backup file to restore",
            start_path=str(config_folder),
            select_dirs=False,
            file_pattern="*.zip"
        )

        if not result:
            return

        backup_path = Path(result)

        # Ask user about overwrite behavior
        overwrite = self.show_confirm(
            "Restore Config Files",
            f"Restore configs from:\n{backup_path.name}\n\n"
            f"Overwrite existing config files?",
            3
        )

        if overwrite is None:  # User cancelled
            return

        # Show progress message
        self.show_message("Restore", "Restoring config files...", 1)

        # Restore backup
        restored, skipped, error = system.manager.restore_configs(backup_path, overwrite=overwrite)

        if error:
            self.show_message("Error", f"Restore failed:\n{error}", 3)
        else:
            msg_lines = ["Restore complete!"]
            msg_lines.append(f"Restored: {restored}")
            if skipped > 0:
                msg_lines.append(f"Skipped: {skipped}")
            self.show_message("Success", "\n".join(msg_lines), 3)

    def initialize_system_manager(self, system: SystemConfig, require_rom_folder: bool = True) -> bool:
        """Initialize or reinitialize the manager for a system.

        Args:
            system: System configuration
            require_rom_folder: If True, ROM folder must be set (default: True)
        """
        if not system.dat_file:
            self.show_message("Error", f"Please set DAT file for {system.name}", 3)
            return False

        if require_rom_folder and not system.rom_folder:
            self.show_message("Error",
                            f"Please set both DAT file and ROM folder for {system.name}", 3)
            return False

        try:
            if not system.manager:
                system.manager = ViewportConfigurationManager(
                    system.dat_file,
                    system.rom_folder if system.rom_folder else None,
                    system.override_width,
                    system.override_height,
                    system.override_x,
                    system.override_y,
                    system.export_folder if system.export_folder else None,
                    log_callback=self.log
                )
                system.manager.parse_dat_file()
            return True
        except Exception as e:
            self.show_message("Error", f"Failed to initialize {system.name}:\n{str(e)}", 3)
            return False

    def view_game_list(self) -> None:
        """View the list of games with resolutions and ROM status."""
        system = self.get_current_system()
        if not system:
            self.show_message("Error", "No system selected.", 3)
            return

        # Require ROM folder for game list
        if not self.initialize_system_manager(system, require_rom_folder=True):
            return

        # Get all games with full metadata
        all_games = sorted(system.manager.game_info.values(), key=lambda g: g.name)
        rom_files = {f.stem for f in system.manager.get_rom_files()}

        if not all_games:
            self.show_message("Warning", "No games with resolution data found in DAT file.", 4)
            return

        selected = 0
        scroll_offset = 0
        filter_text = ""
        games = all_games

        while True:
            self.stdscr.clear()

            # Calculate split point (60% top, 40% bottom)
            split_y = int(self.height * 0.6)

            # === TOP SECTION: Game List ===
            if filter_text:
                self.draw_header(f"ROM Collection: {system.name} ({len(games)}/{len(all_games)} games) Filter: {filter_text}")
            else:
                self.draw_header(f"ROM Collection: {system.name} ({len(games)} games)")

            # Column headers
            y = 2
            available_width = self.width - 4

            # Calculate dynamic column widths
            name_width = 15
            year_width = 6
            res_width = 11
            orient_width = 6
            screen_width = 8
            status_width = 8

            fixed_width = name_width + year_width + res_width + orient_width + screen_width + status_width + 6
            remaining = available_width - fixed_width

            if remaining > 30:
                desc_width = int(remaining * 0.6)
                mfr_width = remaining - desc_width
            else:
                desc_width = max(20, remaining // 2)
                mfr_width = max(10, remaining - desc_width)

            self.stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
            header = f"{'Name':<{name_width}} {'Desc':<{desc_width}} {'Year':<{year_width}} {'Mfr':<{mfr_width}} {'Res':<{res_width}} {'Orient':<{orient_width}} {'Screen':<{screen_width}} {'Status':<{status_width}}"
            self.stdscr.addstr(y, 0, header[:self.width])
            self.stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)

            # Calculate visible games
            max_visible_top = split_y - 4

            # Adjust scroll
            if selected < scroll_offset:
                scroll_offset = selected
            elif selected >= scroll_offset + max_visible_top:
                scroll_offset = selected - max_visible_top + 1

            # Display games
            y = 3
            for idx in range(scroll_offset, min(scroll_offset + max_visible_top, len(games))):
                if y >= split_y - 1:
                    break

                game = games[idx]
                has_rom = game.name in rom_files

                # Truncate fields
                name = game.name[:name_width-1]
                desc = game.description[:desc_width-1]
                year = game.year[:year_width-1]
                mfr = game.manufacturer[:mfr_width-1]
                res = f"{game.width}x{game.height}"[:res_width-1]
                orient = (game.rotate[:orient_width-1] if game.rotate else "-")
                screen = (game.screen_type[:screen_width-1] if game.screen_type else "-")
                status = "Found" if has_rom else "Missing"

                line = f"{name:<{name_width}} {desc:<{desc_width}} {year:<{year_width}} {mfr:<{mfr_width}} {res:<{res_width}} {orient:<{orient_width}} {screen:<{screen_width}} "

                if idx == selected:
                    self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                    self.stdscr.addstr(y, 0, f">{line}"[:self.width-status_width-2])
                    self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
                    status_color = 2 if has_rom else 3
                    self.stdscr.attron(curses.color_pair(status_color) | curses.A_BOLD)
                    self.stdscr.addstr(y, self.width - status_width, status)
                    self.stdscr.attroff(curses.color_pair(status_color) | curses.A_BOLD)
                else:
                    self.stdscr.addstr(y, 0, f" {line}"[:self.width-status_width-2])
                    status_color = 2 if has_rom else 3
                    self.stdscr.attron(curses.color_pair(status_color))
                    self.stdscr.addstr(y, self.width - status_width, status)
                    self.stdscr.attroff(curses.color_pair(status_color))

                y += 1

            # Draw separator
            self.stdscr.attron(curses.color_pair(5))
            self.stdscr.addstr(split_y, 0, "=" * self.width)
            self.stdscr.attroff(curses.color_pair(5))

            # === BOTTOM SECTION: Game Details ===
            y = split_y + 1
            self.stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
            self.stdscr.addstr(y, 1, "Game Details:")
            self.stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)

            y += 1
            if selected < len(games):
                game = games[selected]
                has_rom = game.name in rom_files

                # Show game details
                self.stdscr.attron(curses.color_pair(5))
                game_line = f"Game: {game.name}"
                self.stdscr.addstr(y, 1, game_line[:self.width-2])
                y += 1

                if game.description:
                    desc_display = game.description if len(game.description) <= self.width - 15 else game.description[:self.width-18] + "..."
                    desc_line = f"Description: {desc_display}"
                    self.stdscr.addstr(y, 1, desc_line[:self.width-2])
                    y += 1

                if game.year or game.manufacturer:
                    info_line = ""
                    if game.year:
                        info_line += f"Year: {game.year}"
                    if game.manufacturer:
                        if info_line:
                            info_line += "  |  "
                        info_line += f"Manufacturer: {game.manufacturer}"
                    self.stdscr.addstr(y, 1, info_line[:self.width-2])
                    y += 1

                if game.rotate or game.screen_type:
                    display_line = ""
                    if game.rotate:
                        display_line += f"Orientation: {game.rotate}"
                    if game.screen_type:
                        if display_line:
                            display_line += "  |  "
                        display_line += f"Screen: {game.screen_type}"
                    self.stdscr.addstr(y, 1, display_line[:self.width-2])
                    y += 1

                res_line = f"Resolution: {game.width}x{game.height}"
                self.stdscr.addstr(y, 1, res_line[:self.width-2])
                y += 1

                self.stdscr.attroff(curses.color_pair(5))

                # ROM status
                status_color = 2 if has_rom else 3
                self.stdscr.attron(curses.color_pair(status_color) | curses.A_BOLD)
                status_line = f"ROM Status: {'Found' if has_rom else 'Missing'}"
                self.stdscr.addstr(y, 1, status_line[:self.width-2])
                self.stdscr.attroff(curses.color_pair(status_color) | curses.A_BOLD)

            self.draw_footer("Up/Down: Navigate | Enter: Write Config | /: Filter | c: Clear | q: Back")
            self.stdscr.refresh()

            key = self.stdscr.getch()

            if key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(games) - 1:
                selected += 1
            elif key == ord('\n'):
                # Write config for selected game
                if selected < len(games):
                    game = games[selected]
                    has_rom = game.name in rom_files

                    # Determine final resolution
                    final_width = system.override_width if system.override_width else game.width
                    final_height = system.override_height if system.override_height else game.height

                    # Determine output location
                    if system.export_folder:
                        output_location = system.export_folder
                    elif system.rom_folder:
                        output_location = system.rom_folder
                    else:
                        self.show_message("Error", "No ROM folder or export folder set.\nPlease configure the system first.", 3)
                        continue

                    # Build confirmation message
                    confirm_msg = f"Write config for {game.name}?\n\n"
                    confirm_msg += f"Resolution: {final_width}x{final_height}\n"
                    confirm_msg += f"Output: {output_location}\n"

                    # Show ROM status
                    if has_rom:
                        confirm_msg += f"ROM Status: Found"
                    else:
                        confirm_msg += f"ROM Status: Missing (config will still be created)"

                    if self.show_confirm("Confirm Write Config", confirm_msg, 5):
                        try:
                            # Create a temporary manager to write the config
                            write_manager = ViewportConfigurationManager(
                                system.dat_file,
                                system.rom_folder if system.rom_folder else None,
                                system.override_width,
                                system.override_height,
                                system.export_folder if system.export_folder else None,
                                log_callback=self.log
                            )
                            write_manager.parse_dat_file()
                            write_manager.update_rom_config(game.name, final_width, final_height)
                            self.show_message("Success", f"Config written for {game.name}\n{final_width}x{final_height}", 2)
                        except Exception as e:
                            self.show_message("Error", f"Failed to write config:\n{str(e)}", 3)
            elif key == ord('/'):
                # Enter filter mode
                new_filter = self.get_input("Filter games (name/description/year/mfr):", filter_text)
                if new_filter is not None:
                    filter_text = new_filter.lower()
                    # Apply filter
                    if filter_text:
                        games = [g for g in all_games if
                                filter_text in g.name.lower() or
                                filter_text in g.description.lower() or
                                filter_text in g.year.lower() or
                                filter_text in g.manufacturer.lower()]
                    else:
                        games = all_games
                    # Reset selection
                    selected = 0
                    scroll_offset = 0
            elif key == ord('c') or key == ord('C'):
                # Clear filter
                filter_text = ""
                games = all_games
                selected = 0
                scroll_offset = 0
            elif key == 27 or key == ord('q'):  # ESC or q
                break

    def process_current_system(self) -> None:
        """Process ROMs for the current system."""
        system = self.get_current_system()
        if not system:
            self.show_message("Error", "No system selected.", 3)
            return

        if not self.initialize_system_manager(system):
            return

        # Confirm with user
        output_location = system.export_folder if system.export_folder else system.rom_folder
        confirm_msg = f"Process all ROMs for {system.name}?\n\n"
        confirm_msg += f"This will create/update config files for all games.\n"
        confirm_msg += f"Output: {output_location}"

        if not self.show_confirm("Confirm Process System", confirm_msg, 5):
            return

        # Progress screen
        def progress_callback(current: int, total: int, rom_name: str):
            self.stdscr.clear()
            self.draw_header(f"Processing: {system.name}")

            progress_y = self.height // 2 - 2

            # Progress bar
            bar_width = self.width - 10
            filled = int(bar_width * current / total)
            bar = "#" * filled + "-" * (bar_width - filled)

            self.stdscr.attron(curses.color_pair(2))
            self.stdscr.addstr(progress_y, 4, f"[{bar}]")
            self.stdscr.attroff(curses.color_pair(2))

            # Progress text
            percent = int(100 * current / total)
            self.stdscr.addstr(progress_y + 2, 4, f"Progress: {current}/{total} ({percent}%)")
            self.stdscr.addstr(progress_y + 3, 4, f"Current: {rom_name}")

            self.stdscr.refresh()

        try:
            processed, skipped = system.manager.process_roms(progress_callback)
            self.show_message("Success",
                            f"{system.name} - Processing complete!\n\n"
                            f"Processed: {processed}\n"
                            f"Skipped: {skipped}", 2)
        except Exception as e:
            self.show_message("Error", f"Processing failed:\n{str(e)}", 3)

    def process_all_systems(self) -> None:
        """Process ROMs for all configured systems."""
        if not self.systems:
            self.show_message("Error", "No systems configured.", 3)
            return

        # Build list of systems that will be processed
        processable_systems = [s for s in self.systems if s.dat_file and s.rom_folder]

        if not processable_systems:
            self.show_message("Error", "No systems are fully configured.\nEach system needs a DAT file and ROM folder.", 3)
            return

        # Confirm with user
        system_list = "\n".join([f"  - {s.name}" for s in processable_systems])
        confirm_msg = f"Process {len(processable_systems)} system(s)?\n\n"
        confirm_msg += f"This will create/update config files for all games.\n\n"
        confirm_msg += f"Systems:\n{system_list}"

        if not self.show_confirm("Confirm Process All Systems", confirm_msg, 5):
            return

        results = []
        total_processed = 0
        total_skipped = 0

        for idx, system in enumerate(self.systems):
            if not system.dat_file or not system.rom_folder:
                self.log(f"Skipping {system.name}: Not fully configured")
                continue

            try:
                if not self.initialize_system_manager(system):
                    continue

                # Progress screen
                def progress_callback(current: int, total: int, rom_name: str):
                    self.stdscr.clear()
                    self.draw_header(f"Processing All Systems ({idx+1}/{len(self.systems)})")

                    y = self.height // 2 - 4

                    self.stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
                    self.stdscr.addstr(y, 4, f"Current System: {system.name}")
                    self.stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)

                    y += 2

                    # Progress bar
                    bar_width = self.width - 10
                    filled = int(bar_width * current / total)
                    bar = "#" * filled + "-" * (bar_width - filled)

                    self.stdscr.attron(curses.color_pair(2))
                    self.stdscr.addstr(y, 4, f"[{bar}]")
                    self.stdscr.attroff(curses.color_pair(2))

                    y += 2
                    percent = int(100 * current / total)
                    self.stdscr.addstr(y, 4, f"Progress: {current}/{total} ({percent}%)")
                    self.stdscr.addstr(y + 1, 4, f"Current: {rom_name}")

                    self.stdscr.refresh()

                processed, skipped = system.manager.process_roms(progress_callback)
                results.append((system.name, processed, skipped))
                total_processed += processed
                total_skipped += skipped

            except Exception as e:
                self.log(f"Error processing {system.name}: {e}")

        # Show summary
        summary = "All Systems Processing Complete!\n\n"
        for name, processed, skipped in results:
            summary += f"{name}:\n"
            summary += f"  Processed: {processed}\n"
            summary += f"  Skipped: {skipped}\n\n"

        summary += f"TOTAL:\n"
        summary += f"  Processed: {total_processed}\n"
        summary += f"  Skipped: {total_skipped}"

        self.show_message("Success", summary, 2)

    def remove_current_system_overrides(self) -> None:
        """Remove all viewport overrides from current system config files."""
        system = self.get_current_system()
        if not system:
            self.show_message("Error", "No system selected.", 3)
            return

        # Determine output location
        if system.export_folder:
            output_location = system.export_folder
        elif system.rom_folder:
            output_location = system.rom_folder
        else:
            self.show_message("Error", "No ROM folder or export folder set.\nPlease configure the system first.", 3)
            return

        # Count config files before showing confirmation
        output_folder = Path(output_location)
        if not output_folder.exists():
            self.show_message("Error", f"Output folder does not exist:\n{output_location}", 3)
            return

        config_files = list(output_folder.glob('*.zip.cfg'))

        if not config_files:
            self.show_message("Info", f"No config files found in:\n{output_location}", 5)
            return

        # Count files with overrides
        files_with_overrides = 0
        for config_file in config_files:
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
                    if 'custom_viewport_width' in content or 'custom_viewport_height' in content or 'aspect_ratio_index' in content:
                        files_with_overrides += 1
            except Exception:
                pass

        if files_with_overrides == 0:
            self.show_message("Info", f"No viewport overrides found in {len(config_files)} config files.", 5)
            return

        # Confirm with user
        confirm_msg = f"Remove ALL viewport overrides for {system.name}?\n\n"
        confirm_msg += f"This will remove from {files_with_overrides} config file(s):\n"
        confirm_msg += f"  - custom_viewport_width\n"
        confirm_msg += f"  - custom_viewport_height\n"
        confirm_msg += f"  - aspect_ratio_index\n\n"
        confirm_msg += f"Location: {output_location}\n\n"
        confirm_msg += f"Empty config files will be deleted."

        if not self.show_confirm("Confirm Remove All Overrides", confirm_msg, 4):
            return

        # Initialize manager
        if not self.initialize_system_manager(system):
            return

        # Progress screen
        def progress_callback(current: int, total: int, rom_name: str):
            self.stdscr.clear()
            self.draw_header(f"Removing Overrides: {system.name}")

            progress_y = self.height // 2 - 2

            # Progress bar
            bar_width = self.width - 10
            filled = int(bar_width * current / total)
            bar = "#" * filled + "-" * (bar_width - filled)

            self.stdscr.attron(curses.color_pair(4))
            self.stdscr.addstr(progress_y, 4, f"[{bar}]")
            self.stdscr.attroff(curses.color_pair(4))

            # Progress text
            percent = int(100 * current / total)
            self.stdscr.addstr(progress_y + 2, 4, f"Progress: {current}/{total} ({percent}%)")
            self.stdscr.addstr(progress_y + 3, 4, f"Current: {rom_name}")

            self.stdscr.refresh()

        try:
            removed, skipped = system.manager.remove_all_overrides(progress_callback)
            self.show_message("Success",
                            f"{system.name} - Removal complete!\n\n"
                            f"Removed: {removed}\n"
                            f"Skipped: {skipped}", 2)
        except Exception as e:
            self.show_message("Error", f"Removal failed:\n{str(e)}", 3)

    def remove_all_systems_overrides(self) -> None:
        """Remove viewport overrides from all configured systems."""
        if not self.systems:
            self.show_message("Error", "No systems configured.", 3)
            return

        # Build list of systems that can have overrides removed
        processable_systems = [s for s in self.systems if (s.rom_folder or s.export_folder)]

        if not processable_systems:
            self.show_message("Error", "No systems have ROM folder or export folder configured.", 3)
            return

        # Check if any systems have overrides before confirming
        total_with_overrides = 0
        for system in processable_systems:
            output_folder = Path(system.export_folder) if system.export_folder else Path(system.rom_folder) if system.rom_folder else None
            if output_folder and output_folder.exists():
                config_files = list(output_folder.glob('*.zip.cfg'))
                for config_file in config_files:
                    try:
                        with open(config_file, 'r') as f:
                            content = f.read()
                            if 'custom_viewport_width' in content or 'custom_viewport_height' in content or 'aspect_ratio_index' in content:
                                total_with_overrides += 1
                                break  # Found at least one in this system, move to next
                    except Exception:
                        pass

        if total_with_overrides == 0:
            self.show_message("Info", f"No viewport overrides found in any of the {len(processable_systems)} system(s).", 5)
            return

        # Confirm with user
        system_list = "\n".join([f"  - {s.name}" for s in processable_systems])
        confirm_msg = f"Remove viewport overrides from {len(processable_systems)} system(s)?\n\n"
        confirm_msg += f"This will remove viewport settings from all config files.\n\n"
        confirm_msg += f"Systems:\n{system_list}"

        if not self.show_confirm("Confirm Remove All Systems Overrides", confirm_msg, 4):
            return

        results = []
        total_removed = 0
        total_skipped = 0

        for idx, system in enumerate(processable_systems):
            # Determine output location
            if system.export_folder:
                output_location = system.export_folder
            elif system.rom_folder:
                output_location = system.rom_folder
            else:
                continue

            # Initialize manager
            if not self.initialize_system_manager(system):
                self.log(f"Skipping {system.name}: Failed to initialize manager")
                continue

            # Progress screen
            def progress_callback(current: int, total: int, rom_name: str):
                self.stdscr.clear()
                self.draw_header(f"Removing Overrides: {idx+1}/{len(processable_systems)}")

                # System progress
                y = self.height // 2 - 4
                self.stdscr.addstr(y, 4, f"Current System: {system.name}")
                y += 2

                # File progress bar
                bar_width = self.width - 10
                filled = int(bar_width * current / total)
                bar = "#" * filled + "-" * (bar_width - filled)

                self.stdscr.attron(curses.color_pair(4))
                self.stdscr.addstr(y, 4, f"[{bar}]")
                self.stdscr.attroff(curses.color_pair(4))

                y += 2
                percent = int(100 * current / total)
                self.stdscr.addstr(y, 4, f"Progress: {current}/{total} ({percent}%)")
                self.stdscr.addstr(y + 1, 4, f"Current: {rom_name}")

                self.stdscr.refresh()

            try:
                removed, skipped = system.manager.remove_all_overrides(progress_callback)
                results.append((system.name, removed, skipped))
                total_removed += removed
                total_skipped += skipped
            except Exception as e:
                self.log(f"Error removing overrides for {system.name}: {e}")

        # Show summary
        summary = "All Systems Removal Complete!\n\n"
        for name, removed, skipped in results:
            summary += f"{name}:\n"
            summary += f"  Removed: {removed}\n"
            summary += f"  Skipped: {skipped}\n\n"

        summary += f"TOTAL:\n"
        summary += f"  Removed: {total_removed}\n"
        summary += f"  Skipped: {total_skipped}"

        self.show_message("Success", summary, 2)

    def view_log(self) -> None:
        """View the log messages."""
        selected = max(0, len(self.log_messages) - (self.height - 6))

        while True:
            self.stdscr.clear()
            self.draw_header(f"Log ({len(self.log_messages)} messages)")

            max_visible = self.height - 4

            # Display log messages
            for idx in range(selected, min(selected + max_visible, len(self.log_messages))):
                y = 2 + (idx - selected)
                if y < self.height - 2:
                    msg = self.log_messages[idx]
                    self.stdscr.addstr(y, 2, msg[:self.width - 4])

            self.draw_footer("Up/Down: Scroll | Esc/q: Back")
            self.stdscr.refresh()

            key = self.stdscr.getch()

            if key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(self.log_messages) - max_visible:
                selected += 1
            elif key == 27 or key == ord('q'):  # ESC or q
                break

    def run(self) -> None:
        """Run the GUI main loop."""
        curses.curs_set(0)  # Hide cursor
        self.stdscr.keypad(True)  # Enable keypad mode

        self.main_menu()

        # Auto-save on exit if enabled and systems are configured
        if self.auto_save_enabled and self.systems:
            self.save_config()
            self.log("Configuration auto-saved on exit")


def main_gui(stdscr):
    """Main entry point for curses GUI."""
    gui = CursesGUI(stdscr)
    gui.run()


