# Resolution Override Tool

A comprehensive tool for managing RetroArch viewport resolution overrides for ROM configuration files. Supports multiple emulation systems including FinalBurn Neo and MAME.

## Features

- **Interactive TUI (Text User Interface)**: Curses-based terminal GUI with numeric key navigation
- **CLI Mode**: Batch processing support for automation
- **Multi-System Support**: FinalBurn Neo, MAME, and custom systems
- **DAT File Parsing**: Extracts resolution data from XML DAT files
- **DAT Download**: Download DAT files directly from libretro GitHub repositories
- **Full Viewport Control**: Configure width, height, and position (X/Y coordinates)
- **Bulk Operations**: Process all ROMs or individual games
- **Override Management**: Add or remove viewport settings
- **Export Folders**: Optional separate config output location
- **Interactive DAT Browser**: Browse games with full metadata and config preview

## Installation

### From Source

```bash
# Clone the repository
git clone <repository-url>
cd resolutionOverrideTool

# Run directly (no installation needed)
python3 -m src.resolution_override_tool
```

### Building Standalone Executable

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

# Find executable in dist/resolutionOverrideTool
```

**Troubleshooting:** If you get "pyinstaller: command not found" after `pipx install`:
- Run `pipx ensurepath` and restart your terminal
- Or add to your shell profile: `export PATH="$HOME/.local/bin:$PATH"`
- Verify with: `which pyinstaller`

## Usage

### GUI Mode (Default)

Simply run without arguments to launch the interactive interface:

```bash
python3 -m src.resolution_override_tool
```

Or with the built executable:

```bash
./dist/resolutionOverrideTool
```

### CLI Mode

Process systems via command-line arguments:

```bash
# Process FinalBurn Neo with size override
python3 -m src.resolution_override_tool \
  --fbneo /path/to/fbneo.dat /path/to/roms \
  --fbneo-override 1920 1080

# Process FinalBurn Neo with size and position override
python3 -m src.resolution_override_tool \
  --fbneo /path/to/fbneo.dat /path/to/roms \
  --fbneo-override 1920 1080 10 20

# Process MAME
python3 -m src.resolution_override_tool \
  --mame /path/to/mame.xml /path/to/mame_roms

# Process multiple systems with different overrides
python3 -m src.resolution_override_tool \
  --fbneo /path/to/fbneo.dat /path/to/fbneo_roms --fbneo-override 1920 1080 0 0 \
  --mame /path/to/mame.xml /path/to/mame_roms --mame-override 640 480

# Custom system with position override
python3 -m src.resolution_override_tool \
  --system "MAME 2003 Plus" /path/to/dat /path/to/roms \
  --system-override "MAME 2003 Plus" 1920 1080 10 20
```

**Override Format:**
- `WIDTH HEIGHT` - Set viewport size only
- `WIDTH HEIGHT X Y` - Set viewport size and position

## Project Structure

```
resolutionOverrideTool/
├── src/
│   └── resolution_override_tool/
│       ├── __init__.py       # Package initialization
│       ├── __main__.py       # Entry point
│       ├── core.py           # Core library (parsing, config management)
│       ├── ui.py             # Terminal user interface
│       ├── cli.py            # Command-line interface
│       └── network.py        # Network utilities (DAT file downloads)
├── downloaded_dats/          # Downloaded DAT files (auto-created)
├── build.py                  # PyInstaller build script
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── .gitignore               # Git ignore patterns
```

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

### Navigation
- **Numeric Keys**: Press [1], [2], etc. to quickly select menu options
- **Arrow Keys**: Traditional navigation support
- **ESC/Q**: Quick exit from submenus
- **Consistent UI**: Uniform [number] formatting across all menus

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
