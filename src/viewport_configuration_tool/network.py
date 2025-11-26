"""
Network utilities for downloading DAT files from the web.

This module handles downloading DAT files from predefined sources,
including zip file extraction and error handling.
"""

import urllib.request
import urllib.error
import zipfile
from pathlib import Path
from typing import Tuple, Optional, List, NamedTuple


class DATSource(NamedTuple):
    """Information about a DAT file source."""
    name: str
    url: str
    filename: str


# Predefined DAT file sources from libretro repositories
DAT_SOURCES: List[DATSource] = [
    DATSource("FBNeo (Arcade only)",
              "https://raw.githubusercontent.com/libretro/FBNeo/master/dats/FinalBurn%20Neo%20(ClrMame%20Pro%20XML%2C%20Arcade%20only).dat",
              "fbneo_arcade.dat"),
    DATSource("MAME 2003 Plus",
              "https://raw.githubusercontent.com/libretro/mame2003-plus-libretro/master/metadata/mame2003-plus.xml",
              "mame2003-plus.xml"),
    DATSource("MAME 2000 (0.37b5)",
              "https://raw.githubusercontent.com/libretro/mame2000-libretro/master/metadata/MAME%200.37b5%20XML.dat",
              "mame2000.dat"),
    DATSource("MAME 2003",
              "https://raw.githubusercontent.com/libretro/mame2003-libretro/master/metadata/mame2003.xml",
              "mame2003.xml"),
    DATSource("MAME 2010",
              "https://raw.githubusercontent.com/libretro/mame2010-libretro/master/metadata/mame2010.xml",
              "mame2010.xml"),
    DATSource("MAME 2015",
              "https://raw.githubusercontent.com/libretro/mame2015-libretro/master/metadata/mame2015-xml.zip",
              "mame2015.zip"),
    DATSource("MAME 2016 (0.174)",
              "https://raw.githubusercontent.com/libretro/mame2016-libretro/master/metadata/MAME%200.174%20Arcade%20XML%20DAT.zip",
              "mame2016.zip"),
]


class DownloadError(Exception):
    """Base exception for download errors."""
    pass


class NetworkError(DownloadError):
    """Network connectivity error."""
    pass


class HTTPError(DownloadError):
    """HTTP error response."""
    def __init__(self, message: str, status_code: int, reason: str):
        super().__init__(message)
        self.status_code = status_code
        self.reason = reason


class ZipExtractionError(DownloadError):
    """Error extracting zip archive."""
    pass


def download_dat_file(source: DATSource, output_dir: Path) -> Tuple[bool, Optional[Path], Optional[str]]:
    """
    Download a DAT file from a source URL.

    Args:
        source: DATSource containing name, URL, and filename
        output_dir: Directory to save the downloaded file

    Returns:
        Tuple of (success: bool, file_path: Optional[Path], error_message: Optional[str])
    """
    output_path = output_dir / source.filename

    try:
        # Download file
        urllib.request.urlretrieve(source.url, output_path)

        # If it's a zip file, extract it
        if source.filename.endswith('.zip'):
            try:
                extracted_path = _extract_dat_from_zip(output_path, output_dir)
                # Remove the zip file after successful extraction
                output_path.unlink()
                return True, extracted_path, None
            except ZipExtractionError as e:
                # Clean up zip file on extraction error
                if output_path.exists():
                    output_path.unlink()
                return False, None, str(e)
        else:
            # Regular DAT/XML file
            return True, output_path, None

    except urllib.error.URLError as e:
        # Network error
        if output_path.exists():
            output_path.unlink()
        error_msg = f"Network error: {str(e)}\n\nPlease check your internet connection."
        return False, None, error_msg

    except urllib.error.HTTPError as e:
        # HTTP error
        if output_path.exists():
            output_path.unlink()
        error_msg = f"HTTP error:\nStatus code: {e.code}\nReason: {e.reason}"
        return False, None, error_msg

    except Exception as e:
        # General error
        if output_path.exists():
            output_path.unlink()
        error_msg = f"Download failed: {str(e)}"
        return False, None, error_msg


def _extract_dat_from_zip(zip_path: Path, extract_dir: Path) -> Path:
    """
    Extract DAT/XML file from a zip archive.

    Args:
        zip_path: Path to the zip file
        extract_dir: Directory to extract to

    Returns:
        Path to the extracted DAT/XML file

    Raises:
        ZipExtractionError: If extraction fails or no DAT/XML found
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # List files in zip
            zip_files = zip_ref.namelist()

            # Find the .dat or .xml file
            dat_file = None
            for zf in zip_files:
                if zf.endswith('.dat') or zf.endswith('.xml'):
                    dat_file = zf
                    break

            if not dat_file:
                raise ZipExtractionError("No DAT or XML file found in zip archive.")

            # Extract just the DAT file
            zip_ref.extract(dat_file, extract_dir)
            extracted_path = extract_dir / dat_file

            return extracted_path

    except zipfile.BadZipFile:
        raise ZipExtractionError("Downloaded file is not a valid zip archive.")
    except Exception as e:
        raise ZipExtractionError(f"Failed to extract zip: {str(e)}")


def get_dat_sources() -> List[DATSource]:
    """
    Get the list of available DAT file sources.

    Returns:
        List of DATSource objects
    """
    return DAT_SOURCES.copy()
