"""
Command-line interface for the viewport configuration tool.

This module handles CLI argument parsing and batch processing.
"""

import argparse
import os
from .core import ViewportConfigurationManager


def main_cli():
    """Main entry point for CLI mode."""
    parser = argparse.ArgumentParser(
        description='ROM Viewport Configuration Settings - Process multiple emulation systems',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Launch GUI (default)
  %(prog)s

  # Process FinalBurn Neo with global override
  %(prog)s --fbneo /path/to/fbneo.dat /path/to/fbneo_roms --fbneo-override 1920 1080

  # Process with position override
  %(prog)s --fbneo /path/to/fbneo.dat /path/to/fbneo_roms --fbneo-override 1920 1080 10 20

  # Process MAME 2003 Plus
  %(prog)s --mame /path/to/mame2003-plus.xml /path/to/mame_roms

  # Process both systems with different overrides
  %(prog)s \\
    --fbneo /path/to/fbneo.dat /path/to/fbneo_roms --fbneo-override 1920 1080 0 0 \\
    --mame /path/to/mame2003-plus.xml /path/to/mame_roms --mame-override 640 480

  # Process multiple MAME versions
  %(prog)s \\
    --system "MAME 2003 Plus" /path/to/mame2003-plus.xml /path/to/mame2003_roms \\
    --system "MAME 2010" /path/to/mame2010.xml /path/to/mame2010_roms
        '''
    )

    # FinalBurn Neo system
    parser.add_argument(
        '--fbneo',
        nargs=2,
        metavar=('DAT_FILE', 'ROM_FOLDER'),
        help='FinalBurn Neo DAT file and ROM folder'
    )
    parser.add_argument(
        '--fbneo-override',
        nargs='+',
        type=int,
        metavar=('WIDTH', 'HEIGHT', '[X]', '[Y]'),
        help='Resolution override for FinalBurn Neo games (WIDTH HEIGHT [X Y])'
    )
    parser.add_argument(
        '--fbneo-export',
        metavar='EXPORT_FOLDER',
        help='Export folder for FinalBurn Neo configs (optional)'
    )

    # MAME system
    parser.add_argument(
        '--mame',
        nargs=2,
        metavar=('DAT_FILE', 'ROM_FOLDER'),
        help='MAME DAT file and ROM folder'
    )
    parser.add_argument(
        '--mame-override',
        nargs='+',
        type=int,
        metavar=('WIDTH', 'HEIGHT', '[X]', '[Y]'),
        help='Resolution override for MAME games (WIDTH HEIGHT [X Y])'
    )
    parser.add_argument(
        '--mame-export',
        metavar='EXPORT_FOLDER',
        help='Export folder for MAME configs (optional)'
    )

    # Generic system (can be used multiple times)
    parser.add_argument(
        '--system',
        action='append',
        nargs=3,
        metavar=('NAME', 'DAT_FILE', 'ROM_FOLDER'),
        help='Add a custom system (can be used multiple times)'
    )
    parser.add_argument(
        '--system-override',
        action='append',
        nargs='+',
        metavar=('NAME', 'WIDTH', 'HEIGHT', '[X]', '[Y]'),
        help='Resolution override for a custom system (NAME WIDTH HEIGHT [X Y])'
    )
    parser.add_argument(
        '--system-export',
        action='append',
        nargs=2,
        metavar=('NAME', 'EXPORT_FOLDER'),
        help='Export folder for a custom system'
    )

    args = parser.parse_args()

    # Check if at least one system was configured
    has_systems = args.fbneo or args.mame or args.system

    if not has_systems:
        parser.print_help()
        print("\nNo systems configured. Use --fbneo, --mame, or --system to add systems.")
        print("Or run without arguments to launch GUI mode.")
        return 1

    # Process systems
    results = {}
    total_processed = 0
    total_skipped = 0

    # Process FinalBurn Neo system
    if args.fbneo:
        dat_file, rom_folder = args.fbneo
        override_w = None
        override_h = None
        override_x = None
        override_y = None

        if args.fbneo_override:
            if len(args.fbneo_override) >= 2:
                override_w = args.fbneo_override[0]
                override_h = args.fbneo_override[1]
            if len(args.fbneo_override) >= 4:
                override_x = args.fbneo_override[2]
                override_y = args.fbneo_override[3]
            elif len(args.fbneo_override) not in [2, 4]:
                print(f"Error: --fbneo-override requires 2 or 4 values (WIDTH HEIGHT [X Y])")
                return 1

        export_folder = args.fbneo_export if args.fbneo_export else None

        if not os.path.exists(dat_file):
            print(f"Error: FinalBurn Neo DAT file not found: {dat_file}")
            return 1
        if not os.path.exists(rom_folder):
            print(f"Error: FinalBurn Neo ROM folder not found: {rom_folder}")
            return 1

        print("\n" + "=" * 70)
        print("Processing: FinalBurn Neo")
        print("=" * 70)

        try:
            manager = ViewportConfigurationManager(
                dat_file, rom_folder, override_w, override_h, override_x, override_y, export_folder
            )
            manager.parse_dat_file()
            processed, skipped = manager.process_roms()
            results["FinalBurn Neo"] = (processed, skipped)
            total_processed += processed
            total_skipped += skipped
        except Exception as e:
            print(f"Error processing FinalBurn Neo: {e}")
            results["FinalBurn Neo"] = (0, 0)

    # Process MAME system
    if args.mame:
        dat_file, rom_folder = args.mame
        override_w = None
        override_h = None
        override_x = None
        override_y = None

        if args.mame_override:
            if len(args.mame_override) >= 2:
                override_w = args.mame_override[0]
                override_h = args.mame_override[1]
            if len(args.mame_override) >= 4:
                override_x = args.mame_override[2]
                override_y = args.mame_override[3]
            elif len(args.mame_override) not in [2, 4]:
                print(f"Error: --mame-override requires 2 or 4 values (WIDTH HEIGHT [X Y])")
                return 1

        export_folder = args.mame_export if args.mame_export else None

        if not os.path.exists(dat_file):
            print(f"Error: MAME DAT file not found: {dat_file}")
            return 1
        if not os.path.exists(rom_folder):
            print(f"Error: MAME ROM folder not found: {rom_folder}")
            return 1

        print("\n" + "=" * 70)
        print("Processing: MAME")
        print("=" * 70)

        try:
            manager = ViewportConfigurationManager(
                dat_file, rom_folder, override_w, override_h, override_x, override_y, export_folder
            )
            manager.parse_dat_file()
            processed, skipped = manager.process_roms()
            results["MAME"] = (processed, skipped)
            total_processed += processed
            total_skipped += skipped
        except Exception as e:
            print(f"Error processing MAME: {e}")
            results["MAME"] = (0, 0)

    # Process custom systems
    if args.system:
        # Build override and export dictionaries
        overrides = {}
        exports = {}

        if args.system_override:
            for override_args in args.system_override:
                if len(override_args) == 3:
                    # NAME WIDTH HEIGHT
                    name, width, height = override_args
                    overrides[name] = (int(width), int(height), None, None)
                elif len(override_args) == 5:
                    # NAME WIDTH HEIGHT X Y
                    name, width, height, x, y = override_args
                    overrides[name] = (int(width), int(height), int(x), int(y))
                else:
                    print(f"Error: --system-override requires 3 or 5 values (NAME WIDTH HEIGHT [X Y])")
                    return 1

        if args.system_export:
            for name, export_folder in args.system_export:
                exports[name] = export_folder

        for name, dat_file, rom_folder in args.system:
            if not os.path.exists(dat_file):
                print(f"Error: DAT file not found for {name}: {dat_file}")
                return 1
            if not os.path.exists(rom_folder):
                print(f"Error: ROM folder not found for {name}: {rom_folder}")
                return 1

            print("\n" + "=" * 70)
            print(f"Processing: {name}")
            print("=" * 70)

            override_w, override_h, override_x, override_y = overrides.get(name, (None, None, None, None))
            export_folder = exports.get(name, None)

            try:
                manager = ViewportConfigurationManager(
                    dat_file, rom_folder, override_w, override_h, override_x, override_y, export_folder
                )
                manager.parse_dat_file()
                processed, skipped = manager.process_roms()
                results[name] = (processed, skipped)
                total_processed += processed
                total_skipped += skipped
            except Exception as e:
                print(f"Error processing {name}: {e}")
                results[name] = (0, 0)

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for system_name, (processed, skipped) in results.items():
        print(f"\n{system_name}:")
        print(f"  Processed: {processed}")
        print(f"  Skipped: {skipped}")

    print(f"\nTOTAL:")
    print(f"  Processed: {total_processed}")
    print(f"  Skipped: {total_skipped}")

    return 0
