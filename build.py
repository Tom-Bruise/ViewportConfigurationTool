#!/usr/bin/env python3
"""
Build script for creating standalone executable using PyInstaller.

This script packages the Resolution Override Tool into a single executable
that can be distributed and run without Python installed.

Works with both pip3 and pipx installations of PyInstaller.
"""

import subprocess
import sys
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent
src_dir = project_root / "src"
output_dir = project_root / "dist"
build_dir = project_root / "build"

# Determine executable name based on platform
exe_name = "resolutionOverrideTool"
if sys.platform == "win32":
    exe_name += ".exe"

print("=" * 70)
print("Building Resolution Override Tool")
print("=" * 70)
print(f"Source: {src_dir}")
print(f"Output: {output_dir}")
print(f"Executable: {exe_name}")
print("=" * 70)

# PyInstaller arguments
pyinstaller_args = [
    "pyinstaller",
    str(src_dir / "resolution_override_tool" / "__main__.py"),
    "--name=resolutionOverrideTool",
    f"--distpath={output_dir}",
    f"--workpath={build_dir}",
    f"--specpath={project_root}",
    "--onefile",  # Create a single executable
    "--console",  # Console application (needed for curses)
    "--clean",    # Clean build cache
    # Add source directory to Python path
    f"--paths={src_dir}",
    # Collect all package data
    "--collect-all=resolution_override_tool",
]

# Run PyInstaller as a subprocess (works with both pip3 and pipx)
print("\nRunning PyInstaller...")
try:
    result = subprocess.run(pyinstaller_args, check=True)
    print("\n" + "=" * 70)
    print("Build complete!")
    print(f"Executable location: {output_dir / exe_name}")
    print("=" * 70)
    sys.exit(0)
except subprocess.CalledProcessError as e:
    print(f"\n❌ Build failed with error code {e.returncode}")
    sys.exit(e.returncode)
except FileNotFoundError:
    print("\n❌ Error: PyInstaller not found!")
    print("Please install PyInstaller first:")
    print("  pip3 install pyinstaller")
    print("  OR")
    print("  pipx install pyinstaller")
    sys.exit(1)
