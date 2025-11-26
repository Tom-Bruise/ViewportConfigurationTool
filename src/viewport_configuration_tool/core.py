"""
Core library for viewport configuration management.

This module contains the core functionality for parsing DAT files,
managing ROM configurations, and applying viewport configurations.
"""

import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, Callable, NamedTuple


class GameInfo(NamedTuple):
    """Information about a game from DAT file."""
    name: str
    width: int
    height: int
    description: str = ""
    year: str = ""
    manufacturer: str = ""
    cloneof: str = ""
    rotate: str = ""  # Screen orientation/rotation
    screen_type: str = ""  # Video type (raster, vector, lcd, etc)


class ViewportConfigurationManager:
    def __init__(self, dat_file: str = None, rom_folder: str = None,
                 override_width: Optional[int] = None,
                 override_height: Optional[int] = None,
                 override_x: Optional[int] = None,
                 override_y: Optional[int] = None,
                 export_folder: str = None,
                 log_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the Viewport Configuration Manager.

        Args:
            dat_file: Path to the FinalBurn Neo DAT file
            rom_folder: Path to the ROM folder
            override_width: Optional width override for all games
            override_height: Optional height override for all games
            override_x: Optional X position override for all games
            override_y: Optional Y position override for all games
            export_folder: Optional export folder for config files (if None, uses rom_folder)
            log_callback: Optional callback function for logging messages
        """
        self.dat_file = Path(dat_file) if dat_file else None
        self.rom_folder = Path(rom_folder) if rom_folder else None
        self.export_folder = Path(export_folder) if export_folder else None
        self.override_width = override_width
        self.override_height = override_height
        self.override_x = override_x
        self.override_y = override_y
        self.game_resolutions: Dict[str, Tuple[int, int]] = {}
        self.game_info: Dict[str, GameInfo] = {}  # Extended game information
        self.log_callback = log_callback or print

    def log(self, message: str) -> None:
        """Log a message using the callback or print."""
        self.log_callback(message)

    def parse_dat_file(self) -> None:
        """Parse the DAT file and extract game resolutions.

        Supports both FinalBurn Neo (display tag) and MAME (video tag) formats.
        """
        if not self.dat_file:
            raise ValueError("DAT file not set")

        self.log(f"Parsing DAT file: {self.dat_file}")

        try:
            tree = ET.parse(self.dat_file)
            root = tree.getroot()

            for game in root.findall('.//game'):
                game_name = game.get('name')
                if not game_name:
                    continue

                width = None
                height = None
                rotate = ""
                screen_type = ""

                # Extract metadata
                description_elem = game.find('description')
                year_elem = game.find('year')
                manufacturer_elem = game.find('manufacturer')

                description = description_elem.text if description_elem is not None and description_elem.text else ""
                year = year_elem.text if year_elem is not None and year_elem.text else ""
                manufacturer = manufacturer_elem.text if manufacturer_elem is not None and manufacturer_elem.text else ""
                cloneof = game.get('cloneof', "")

                # Try FinalBurn Neo format first (display tag)
                display = game.find('.//display')
                if display is not None:
                    width = display.get('width')
                    height = display.get('height')
                    rotate = display.get('rotate', "") or display.get('orientation', "")
                    screen_type = display.get('type', "")

                # If not found, try MAME/ClrMamePro format (video tag)
                if not width or not height:
                    video = game.find('.//video')
                    if video is not None:
                        width = video.get('width')
                        height = video.get('height')
                        rotate = video.get('rotate', "") or video.get('orientation', "")
                        screen_type = video.get('screen', "") or video.get('type', "")

                if width and height:
                    try:
                        w = int(width)
                        h = int(height)
                        self.game_resolutions[game_name] = (w, h)

                        # Store extended info
                        self.game_info[game_name] = GameInfo(
                            name=game_name,
                            width=w,
                            height=h,
                            description=description,
                            year=year,
                            manufacturer=manufacturer,
                            cloneof=cloneof,
                            rotate=rotate,
                            screen_type=screen_type
                        )
                    except ValueError:
                        self.log(f"Warning: Invalid resolution for {game_name}: {width}x{height}")

            self.log(f"Found {len(self.game_resolutions)} games with resolution data")

            if len(self.game_resolutions) == 0:
                # Count total games to provide helpful feedback
                total_games = len(root.findall('.//game')) + len(root.findall('.//machine'))
                if total_games > 0:
                    self.log(f"Warning: Found {total_games} game entries but none have resolution data.")
                    self.log("This DAT file may not contain display/video information.")
                    self.log("Please use a DAT file that includes resolution data (e.g., MAME XML, FinalBurn Neo DAT with display tags).")

        except ET.ParseError as e:
            self.log(f"Error parsing DAT file: {e}")
            raise
        except FileNotFoundError:
            self.log(f"DAT file not found: {self.dat_file}")
            raise

    def get_rom_files(self) -> list:
        """Get list of ROM files in the ROM folder."""
        if not self.rom_folder or not self.rom_folder.exists():
            self.log(f"ROM folder not found: {self.rom_folder}")
            return []

        rom_files = list(self.rom_folder.glob('*.zip'))
        self.log(f"Found {len(rom_files)} ROM files in {self.rom_folder}")
        return rom_files

    def read_config_file(self, config_path: Path) -> Dict[str, str]:
        """
        Read existing config file and return as dictionary.

        Args:
            config_path: Path to the config file

        Returns:
            Dictionary of config key-value pairs
        """
        config = {}
        if config_path.exists():
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        return config

    def write_config_file(self, config_path: Path, config: Dict[str, str]) -> None:
        """
        Write config dictionary to file.

        Args:
            config_path: Path to the config file
            config: Dictionary of config key-value pairs
        """
        # Define preferred order for viewport settings
        viewport_order = [
            'aspect_ratio_index',
            'custom_viewport_x',
            'custom_viewport_y',
            'custom_viewport_width',
            'custom_viewport_height'
        ]

        with open(config_path, 'w') as f:
            # Write viewport settings in preferred order first
            for key in viewport_order:
                if key in config:
                    f.write(f'{key} = {config[key]}\n')

            # Write any other settings in sorted order
            for key, value in sorted(config.items()):
                if key not in viewport_order:
                    f.write(f'{key} = {value}\n')

    def update_rom_config(self, rom_name: str, width: int, height: int,
                          x: Optional[int] = None, y: Optional[int] = None) -> None:
        """
        Update or create config file for a ROM.

        Args:
            rom_name: Name of the ROM (without .zip extension)
            width: Viewport width
            height: Viewport height
            x: Optional viewport X position
            y: Optional viewport Y position
        """
        # Use export folder if set, otherwise use ROM folder
        output_folder = self.export_folder if self.export_folder else self.rom_folder
        config_path = output_folder / f"{rom_name}.zip.cfg"

        # Read existing config or create new one
        config = self.read_config_file(config_path)

        # Update viewport settings
        config['custom_viewport_width'] = f'"{width}"'
        config['custom_viewport_height'] = f'"{height}"'
        # Always write x and y (default to 0 if not set)
        config['custom_viewport_x'] = f'"{x if x is not None else 0}"'
        config['custom_viewport_y'] = f'"{y if y is not None else 0}"'
        config['aspect_ratio_index'] = '"23"'

        # Write updated config
        self.write_config_file(config_path, config)

        action = "Updated" if config_path.exists() else "Created"
        log_msg = f"{action} config for {rom_name}.zip: {width}x{height}"
        if x is not None or y is not None:
            log_msg += f" at ({x if x is not None else 0}, {y if y is not None else 0})"
        self.log(log_msg)

    def remove_rom_config(self, rom_name: str, delete_if_empty: bool = True) -> Tuple[bool, bool]:
        """
        Remove viewport override settings from a ROM's config file.

        Removes custom_viewport_width, custom_viewport_height, custom_viewport_x,
        custom_viewport_y, and aspect_ratio_index from the config file.

        Args:
            rom_name: Name of the ROM (without .zip extension)
            delete_if_empty: If True, automatically delete empty config files.
                           If False, return info about empty files without deleting.

        Returns:
            Tuple of (removed: bool, is_empty: bool)
            - removed: True if settings were removed
            - is_empty: True if config file is now empty after removal
        """
        # Use export folder if set, otherwise use ROM folder
        output_folder = self.export_folder if self.export_folder else self.rom_folder
        config_path = output_folder / f"{rom_name}.zip.cfg"

        if not config_path.exists():
            self.log(f"No config file found for {rom_name}.zip")
            return False, False

        # Read existing config
        config = self.read_config_file(config_path)

        # Remove viewport settings
        removed_any = False
        for key in ['custom_viewport_width', 'custom_viewport_height',
                    'custom_viewport_x', 'custom_viewport_y', 'aspect_ratio_index']:
            if key in config:
                del config[key]
                removed_any = True

        if not removed_any:
            self.log(f"No viewport overrides found in config for {rom_name}.zip")
            return False, False

        # Check if config is now empty
        is_empty = not config

        if is_empty and delete_if_empty:
            config_path.unlink()
            self.log(f"Removed config file for {rom_name}.zip (was empty after removing overrides)")
        elif is_empty:
            # Config is empty but we're not deleting - write empty config
            self.write_config_file(config_path, config)
            self.log(f"Config for {rom_name}.zip is now empty after removing overrides")
        else:
            # Write updated config
            self.write_config_file(config_path, config)
            self.log(f"Removed viewport overrides from {rom_name}.zip config")

        return True, is_empty

    def delete_empty_config(self, rom_name: str) -> bool:
        """
        Delete an empty config file.

        Args:
            rom_name: Name of the ROM (without .zip extension)

        Returns:
            True if file was deleted, False if it didn't exist or wasn't empty
        """
        output_folder = self.export_folder if self.export_folder else self.rom_folder
        config_path = output_folder / f"{rom_name}.zip.cfg"

        if not config_path.exists():
            return False

        # Read config to verify it's empty
        config = self.read_config_file(config_path)
        if config:
            # Not empty, don't delete
            return False

        config_path.unlink()
        self.log(f"Deleted empty config file: {rom_name}.zip.cfg")
        return True

    def remove_all_overrides(self, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Tuple[int, int]:
        """
        Remove viewport override settings from all config files in the output folder.

        Args:
            progress_callback: Optional callback(current, total, rom_name) for progress updates

        Returns:
            Tuple of (removed_count, skipped_count)
        """
        # Use export folder if set, otherwise use ROM folder
        output_folder = self.export_folder if self.export_folder else self.rom_folder

        if not output_folder or not output_folder.exists():
            self.log(f"Output folder not found: {output_folder}")
            return 0, 0

        # Get all .cfg files
        config_files = list(output_folder.glob('*.zip.cfg'))
        self.log(f"Found {len(config_files)} config files in {output_folder}")

        removed_count = 0
        skipped_count = 0
        total = len(config_files)

        for idx, config_file in enumerate(config_files, 1):
            # Extract ROM name from config filename (remove .zip.cfg)
            rom_name = config_file.stem.replace('.zip', '')

            if progress_callback:
                progress_callback(idx, total, rom_name)

            # Read existing config
            config = self.read_config_file(config_file)

            # Check if it has viewport overrides
            has_overrides = any(key in config for key in
                              ['custom_viewport_width', 'custom_viewport_height', 'aspect_ratio_index'])

            if has_overrides:
                # Remove viewport settings
                config.pop('custom_viewport_width', None)
                config.pop('custom_viewport_height', None)
                config.pop('aspect_ratio_index', None)

                # If config is now empty, delete the file
                if not config:
                    config_file.unlink()
                    self.log(f"Removed {config_file.name} (was empty after removing overrides)")
                else:
                    # Write updated config
                    self.write_config_file(config_file, config)
                    self.log(f"Removed viewport overrides from {config_file.name}")

                removed_count += 1
            else:
                skipped_count += 1

        self.log(f"\nRemoval complete:")
        self.log(f"  Removed: {removed_count}")
        self.log(f"  Skipped: {skipped_count}")

        return removed_count, skipped_count

    def process_roms(self, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Tuple[int, int]:
        """
        Process all ROMs and update their config files.

        Args:
            progress_callback: Optional callback(current, total, rom_name) for progress updates

        Returns:
            Tuple of (processed_count, skipped_count)
        """
        rom_files = self.get_rom_files()

        processed_count = 0
        skipped_count = 0
        total = len(rom_files)

        for idx, rom_file in enumerate(rom_files, 1):
            rom_name = rom_file.stem

            if progress_callback:
                progress_callback(idx, total, rom_name)

            # Check if we have resolution data for this game
            if rom_name in self.game_resolutions:
                dat_width, dat_height = self.game_resolutions[rom_name]

                # Use override values if specified, otherwise use DAT values
                width = self.override_width if self.override_width is not None else dat_width
                height = self.override_height if self.override_height is not None else dat_height

                self.update_rom_config(rom_name, width, height, self.override_x, self.override_y)
                processed_count += 1
            else:
                self.log(f"Skipped {rom_name}.zip: No resolution data in DAT file")
                skipped_count += 1

        self.log(f"\nProcessing complete:")
        self.log(f"  Processed: {processed_count}")
        self.log(f"  Skipped: {skipped_count}")

        return processed_count, skipped_count

    def backup_configs(self, backup_path: Optional[Path] = None) -> Tuple[bool, Optional[Path], Optional[str]]:
        """
        Create a zip backup of all config files in the ROM folder.

        Args:
            backup_path: Optional path for the backup file. If None, generates a timestamped filename.

        Returns:
            Tuple of (success: bool, backup_path: Optional[Path], error_message: Optional[str])
        """
        # Use export folder if set, otherwise use ROM folder
        config_folder = self.export_folder if self.export_folder else self.rom_folder

        if not config_folder or not config_folder.exists():
            error_msg = f"Config folder not found: {config_folder}"
            self.log(error_msg)
            return False, None, error_msg

        # Get all .cfg files
        config_files = list(config_folder.glob('*.cfg'))

        if not config_files:
            error_msg = "No config files found to backup"
            self.log(error_msg)
            return False, None, error_msg

        # Generate backup filename if not provided
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = config_folder / f"config_backup_{timestamp}.zip"

        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for config_file in config_files:
                    # Add file to zip with just the filename (no path)
                    zipf.write(config_file, config_file.name)

            self.log(f"Backup created: {backup_path}")
            self.log(f"Backed up {len(config_files)} config files")
            return True, backup_path, None

        except Exception as e:
            error_msg = f"Backup failed: {str(e)}"
            self.log(error_msg)
            return False, None, error_msg

    def restore_configs(self, backup_path: Path, overwrite: bool = True) -> Tuple[int, int, Optional[str]]:
        """
        Restore config files from a zip backup.

        Args:
            backup_path: Path to the backup zip file
            overwrite: If True, overwrite existing config files. If False, skip existing files.

        Returns:
            Tuple of (restored_count: int, skipped_count: int, error_message: Optional[str])
        """
        # Use export folder if set, otherwise use ROM folder
        config_folder = self.export_folder if self.export_folder else self.rom_folder

        if not config_folder or not config_folder.exists():
            error_msg = f"Config folder not found: {config_folder}"
            self.log(error_msg)
            return 0, 0, error_msg

        if not backup_path.exists():
            error_msg = f"Backup file not found: {backup_path}"
            self.log(error_msg)
            return 0, 0, error_msg

        try:
            restored_count = 0
            skipped_count = 0

            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Get list of .cfg files in the zip
                cfg_files = [f for f in zipf.namelist() if f.endswith('.cfg')]

                if not cfg_files:
                    error_msg = "No config files found in backup"
                    self.log(error_msg)
                    return 0, 0, error_msg

                for filename in cfg_files:
                    target_path = config_folder / filename

                    if target_path.exists() and not overwrite:
                        self.log(f"Skipped {filename} (already exists)")
                        skipped_count += 1
                        continue

                    # Extract the file
                    zipf.extract(filename, config_folder)
                    self.log(f"Restored {filename}")
                    restored_count += 1

            self.log(f"\nRestore complete:")
            self.log(f"  Restored: {restored_count}")
            self.log(f"  Skipped: {skipped_count}")

            return restored_count, skipped_count, None

        except zipfile.BadZipFile:
            error_msg = "Invalid backup file (not a valid zip archive)"
            self.log(error_msg)
            return 0, 0, error_msg
        except Exception as e:
            error_msg = f"Restore failed: {str(e)}"
            self.log(error_msg)
            return 0, 0, error_msg
