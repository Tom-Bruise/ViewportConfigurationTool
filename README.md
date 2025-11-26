# Viewport Configuration Tool

A tool for managing RetroArch viewport configurations for large ROM collections.   

* Fetches accurate per-game resolution information from DAT files, and applies user overrides easily for both single games and large collections.  
* Especially useful for arcade setups that use [CRTSwitchRes](https://docs.libretro.com/guides/crtswitchres/#option-2-crt-super-resolution), to fine tune super resolution configurations and precisely control how the game is rendered on the CRT screen.
* Easily set viewport x and y position, width and height.
* Supports multiple emulation systems including FinalBurn Neo and MAME.

## Features

- **Interactive TUI (Text User Interface)**: Curses-based terminal GUI with numeric key navigation and contextual help
- **CLI Mode**: Batch processing support for automation
- **Multi-System Support**: FinalBurn Neo, MAME, and custom systems
- **DAT File Parsing**: Extracts resolution data from XML DAT files
- **DAT Download**: Download DAT files directly from libretro GitHub repositories
- **Full Viewport Control**: Configure width, height, and position (X/Y coordinates)
- **Bulk Operations**: Process all ROMs or individual games
- **Override Management**: Add or remove viewport settings
- **Config Backup/Restore**: Create and restore zip backups of config files
- **Export Folders**: Optional separate config output location
- **Interactive DAT Browser**: Browse games with full metadata and config preview

## Usage

### GUI Mode (Default)

Simply run without arguments to launch the interactive interface:

```bash
# Using the launch script (recommended)
./launchTool.sh

# Or directly with Python
python3 -m src.viewport_configuration_tool

# Or with the built executable
./dist/viewportConfigurationTool
```

### CLI Mode

Process systems via command-line arguments (using launch script or direct Python):

```bash
# Process FinalBurn Neo with size override
./launchTool.sh \
  --fbneo /path/to/fbneo.dat /path/to/roms \
  --fbneo-override 1920 1080

# Process FinalBurn Neo with size and position override
python3 -m src.viewport_configuration_tool \
  --fbneo /path/to/fbneo.dat /path/to/roms \
  --fbneo-override 1920 1080 10 20

# Process MAME
python3 -m src.viewport_configuration_tool \
  --mame /path/to/mame.xml /path/to/mame_roms

# Process multiple systems with different overrides
python3 -m src.viewport_configuration_tool \
  --fbneo /path/to/fbneo.dat /path/to/fbneo_roms --fbneo-override 1920 1080 0 0 \
  --mame /path/to/mame.xml /path/to/mame_roms --mame-override 640 480

# Custom system with position override
python3 -m src.viewport_configuration_tool \
  --system "MAME 2003 Plus" /path/to/dat /path/to/roms \
  --system-override "MAME 2003 Plus" 1920 1080 10 20
```

**Override Format:**
- `WIDTH HEIGHT` - Set viewport size only
- `WIDTH HEIGHT X Y` - Set viewport size and position

## Configuration Files

The tool creates `.cfg` files alongside your ROM files with the following settings:

```
aspect_ratio_index = "23"
custom_viewport_x = "0"
custom_viewport_y = "0"
custom_viewport_width = "1920"
custom_viewport_height = "1080"
```

These settings configure RetroArch to use custom viewport dimensions and position for each game:
- **aspect_ratio_index**: Set to "23" for custom aspect ratio
- **custom_viewport_x/y**: Viewport position on screen (in pixels)
- **custom_viewport_width/height**: Viewport size (in pixels)

## GUI Features

### System Configuration
- **System Management**: Add, edit, remove multiple system configurations
- **DAT File Download**: Download DAT files from predefined libretro sources:
  - FinalBurn Neo (Arcade only)
  - MAME 2003 Plus
  - MAME 2000 (0.37b5)
  - MAME 2003
  - MAME 2010
  - MAME 2015
  - MAME 2016 (0.174)
- **Downloaded Files**: Automatically saved to `downloaded_dats` folder
- **Override Configuration**: Set viewport width, height, X position, and Y position
- **Backup/Restore**: Create timestamped zip backups of all config files and restore them when needed

### DAT Browser
- **Game Metadata**: View resolution, year, manufacturer, orientation, screen type, clone info
- **ROM Status**: Shows which ROMs exist and which have overrides applied
- **Config Preview**: See exactly what will be written to each game's config file
- **Filtering**: Search games by name, description, year, or manufacturer
- **Quick Actions**: Write/delete individual game configs with single key press

### Batch Operations
- **Process Current System**: Apply overrides to all ROMs in selected system
- **Process All Systems**: Apply overrides to all configured systems
- **Remove Overrides**: Remove overrides from current system or all systems
- **Configuration Persistence**: Save/load system configurations with auto-save option

## Building Standalone Executable

Install PyInstaller using **either** method:

```bash
# Option 1: Using pip3
pip3 install pyinstaller

# Option 2: Using pipx (isolated installation)
pipx install pyinstaller

# After pipx install, ensure PATH is configured:
pipx ensurepath
# You may need to restart your terminal or run:
source ~/.bashrc  # or ~/.zshrc depending on your shell
```

Then build the executable:

```bash
# Run build script
python3 build.py

# Find executable in dist/viewportConfigurationTool
```

**Troubleshooting:** If you get "pyinstaller: command not found" after `pipx install`:
- Run `pipx ensurepath` and restart your terminal
- Or add to your shell profile: `export PATH="$HOME/.local/bin:$PATH"`
- Verify with: `which pyinstaller`

## Project Structure

```
viewportConfigurationTool/
├── src/
│   └── viewport_configuration_tool/
│       ├── __init__.py       # Package initialization
│       ├── __main__.py       # Entry point
│       ├── core.py           # Core library (parsing, config management)
│       ├── ui.py             # Terminal user interface
│       ├── cli.py            # Command-line interface
│       └── network.py        # Network utilities (DAT file downloads)
├── downloaded_dats/          # Downloaded DAT files (auto-created)
├── launchTool.sh             # Convenience launch script
├── build.py                  # PyInstaller build script
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── .gitignore               # Git ignore patterns

## License

[MIT License](https://mit-license.org/)

