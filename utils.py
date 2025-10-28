# --- utils.py ---

import os
import shutil
from typing import Tuple

def format_bytes(size_bytes: int) -> str:
    """
Signature: `format_bytes(size_bytes: int) -> str`

Converts a size in bytes to a human-readable string (KB, MB, GB, TB).
Uses decimal (1000) instead of binary (1024) for storage representation.
"""
    if size_bytes < 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    power = 1000.0  # Use decimal (base 1000)
    
    i = 0
    while size_bytes >= power and i < len(units) - 1:
        size_bytes /= power
        i += 1
        
    return f"{size_bytes:.2f} {units[i]}"


def get_drive_usage(path: str) -> Tuple[int, int, int]:
    """
Signature: `get_drive_usage(path: str) -> Tuple[int, int, int]`

Gets the total disk space, used space, and free space for the drive
that contains the given path.
Returns (total, used, free) in bytes.
Returns (0, 0, 0) on failure (e.g., path not found).
"""
    try:
        # For Windows, get the drive letter (e.g., 'C:\\')
        # For POSIX, shutil.disk_usage typically uses the path itself.
        drive_root = os.path.abspath(path)
        if os.name == 'nt':
            drive_root = os.path.splitdrive(drive_root)[0] + os.sep
        
        usage = shutil.disk_usage(drive_root)
        return usage.total, usage.used, usage.free
    except FileNotFoundError:
        return (0, 0, 0) # Path doesn't exist
    except Exception as e:
        print(f"[Error] Could not get disk usage for '{path}': {e}")
        return (0, 0, 0)


def calculate_percentage(part: int, whole: int) -> float:
    """
Signature: `calculate_percentage(part: int, whole: int) -> float`

Calculates what percentage 'part' is of 'whole'.
Returns 0.0 if 'whole' is 0 to avoid division by zero.
"""
    if whole == 0:
        return 0.0
    return (part / whole) * 100.0


def is_symlink(path: str) -> bool:
    """
Signature: `is_symlink(path: str) -> bool`

Safely checks if a path is a symbolic link.
"""
    try:
        return os.path.islink(path)
    except OSError:
        # e.g., PermissionError or path too long
        return False


def has_read_permission(path: str) -> bool:
    """
Signature: `has_read_permission(path: str) -> bool`

Checks if the current user has read access to a file or directory.
"""
    return os.access(path, os.R_OK)


def safe_join_path(*args) -> str:
    """
Signature: `safe_join_path(*args) -> str`

Wrapper around os.path.join for robustness.
(Currently a simple wrapper, can be expanded for more complex path logic).
"""
    try:
        return os.path.join(*args)
    except TypeError:
        return "" # Handle potential errors if non-string paths are passed


def get_time_ago_days(timestamp: float) -> int:
    """
Signature: `get_time_ago_days(timestamp: float) -> int`

Calculates how many days ago a given timestamp occurred.
Returns the number of days as an integer.
"""
    import time
    now = time.time()
    seconds_ago = now - timestamp
    days_ago = seconds_ago / (60 * 60 * 24)
    return int(days_ago)