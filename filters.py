# --- filters.py ---

import os
import time
from typing import List, Set, Optional, Callable, Dict
from models import FileNode

# --- Configuration for Filters ---
# (These can later be moved to a settings object)

# Default patterns for temporary/cache/log files
# Using lower-case for case-insensitive matching
TEMP_EXTENSIONS = {
    ".tmp", ".temp", ".log", ".cache", ".bak", ".old", ".thumbcache",
    ".swp", ".swo", ".swn"
}

TEMP_FILENAMES = {
    "thumbs.db", "desktop.ini", ".ds_store"
}

TEMP_DIRNAMES = {
    "__pycache__", "node_modules", ".pytest_cache", ".cache",
    "pip_cache"
}

# --- Filter Functions ---

def get_large_files(files: Set[FileNode], min_size_mb: int = 100) -> List[FileNode]:
    """
    Filters for files larger than a specific size.
    Sorts the result from largest to smallest.
    """
    min_size_bytes = min_size_mb * 1000 * 1000  # Use decimal MB
    large_files = [
        node for node in files 
        if not node.is_dir and node.size_bytes > min_size_bytes
    ]
    
    # Sort by size, descending
    large_files.sort(key=lambda x: x.size_bytes, reverse=True)
    return large_files


def get_old_files(files: Set[FileNode], min_days_old: int = 365) -> List[FileNode]:
    """
    Filters for files last modified more than N days ago.
    Uses 'mtime' (modification time) as it's the most reliable.
    Sorts the result from oldest to newest.
    """
    now = time.time()
    seconds_ago = min_days_old * 24 * 60 * 60
    cutoff_time = now - seconds_ago
    
    old_files = [
        node for node in files
        if not node.is_dir and node.mtime < cutoff_time
    ]
    
    # Sort by mtime, ascending (oldest first)
    old_files.sort(key=lambda x: x.mtime, reverse=False)
    return old_files


def get_never_accessed_files(files: Set[FileNode], 
                             fallback_to_mtime: bool = True,
                             min_days_old: int = 365) -> List[FileNode]:
    """
    Filters for files last accessed more than N days ago.
    
    NOTE: 'atime' (access time) is often disabled or unreliable on modern OS
    (e.g., Windows, Linux with 'relatime').
    
    If 'atime' seems unreliable (e.g., older than mtime), 
    it can fallback to using 'mtime'.
    """
    now = time.time()
    seconds_ago = min_days_old * 24 * 60 * 60
    cutoff_time = now - seconds_ago
    
    unaccessed_files = []
    for node in files:
        if node.is_dir:
            continue
            
        time_to_check = node.atime
        
        # Fallback logic: If atime is older than mtime, OS probably
        # isn't updating it. Use mtime instead.
        if fallback_to_mtime and node.atime < node.mtime:
            time_to_check = node.mtime
            
        if time_to_check < cutoff_time:
            unaccessed_files.append(node)
            
    # Sort by atime, ascending (oldest first)
    unaccessed_files.sort(key=lambda x: x.atime, reverse=False)
    return unaccessed_files


def get_temp_files(all_nodes: Dict[str, FileNode]) -> List[FileNode]: # <--- PERBAIKAN TIPE HINT
    """
    Filters for temporary files, cache files, logs, and common "junk" folders.
    Matches against extensions, filenames, and directory names.
    If a directory matches (e.g., 'node_modules'), all its children are included.
    """
    temp_items = []
    
    # We need to iterate over the values (FileNode objects), not the keys (paths)
    for node in all_nodes.values(): # <--- PERBAIKAN LOOP
        # Check by directory name
        if node.is_dir and node.name.lower() in TEMP_DIRNAMES:
            temp_items.append(node)
            # Optimization: We could add all children here, but letting
            # the delete op handle recursion might be safer.
            continue 
            
        # Check by file extension or specific filename
        if not node.is_dir:
            name_lower = node.name.lower()
            if node.ext in TEMP_EXTENSIONS or name_lower in TEMP_FILENAMES:
                temp_items.append(node)
                
    # Sort by size, descending, to show worst offenders first
    temp_items.sort(key=lambda x: x.size_bytes, reverse=True)
    return temp_items


def get_zero_byte_files(files: Set[FileNode]) -> List[FileNode]:
    """
    Filters for files that have a size of exactly 0 bytes.
    """
    zero_files = [
        node for node in files
        if not node.is_dir and node.size_bytes == 0
    ]
    # Sort by name
    zero_files.sort(key=lambda x: x.path, reverse=False)
    return zero_files


def get_empty_folders(dirs: Set[FileNode]) -> List[FileNode]:
    """
    Filters for directories that contain no files and no sub-directories.
    """
    empty_dirs = [
        node for node in dirs
        if node.is_dir and not node.children
    ]
    # Sort by name
    empty_dirs.sort(key=lambda x: x.path, reverse=False)
    return empty_dirs

# --- On-Demand Hashing (for Duplicates) ---
# This is more complex and involves I/O, so it's kept separate.

def compute_hash(file_path: str, buffer_size=65536) -> Optional[str]:
    """
    Calculates the SHA-256 hash for a single file.
    Returns None on error (e.g., PermissionError).
    """
    import hashlib
    sha256 = hashlib.sha256()
    
    try:
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(buffer_size)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()
    except (IOError, PermissionError, OSError) as e:
        print(f"[Hash Error] Could not hash {file_path}: {e}")
        return None


def find_duplicates(
    files: Set[FileNode], 
    progress_callback: Callable[[int, int], None]
) -> Dict[str, List[FileNode]]:
    """
    Finds duplicate files based on SHA-256 hash.
    This is an I/O intensive operation.
    
    Step 1: Group files by size.
    Step 2: Only hash files that share the same size (groups > 1).
    Step 3: Group by hash.
    Step 4: Return groups where hash count > 1.
    """
    from collections import defaultdict
    
    # Step 1: Group by size
    size_groups = defaultdict(list)
    for node in files:
        if not node.is_dir and node.size_bytes > 0: # Ignore 0-byte
            size_groups[node.size_bytes].append(node)
            
    # Step 2: Filter for potential duplicates (groups with same size)
    potential_duplicates = []
    for size, nodes in size_groups.items():
        if len(nodes) > 1:
            potential_duplicates.extend(nodes)
            
    # Step 3: Hash files and group by hash
    hash_groups = defaultdict(list)
    total_files = len(potential_duplicates)
    
    for i, node in enumerate(potential_duplicates):
        progress_callback(i + 1, total_files) # Report progress
        
        # Use cached hash if available
        file_hash = node.hash_sha256
        if not file_hash:
            file_hash = compute_hash(node.path)
            node.hash_sha256 = file_hash # Cache the hash
            
        if file_hash:
            hash_groups[file_hash].append(node)
            
    # Step 4: Filter for actual duplicates (groups with same hash)
    duplicate_sets = {
        file_hash: nodes
        for file_hash, nodes in hash_groups.items()
        if len(nodes) > 1
    }
    
    return duplicate_sets