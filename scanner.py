# --- scanner.py ---

import os
import threading
import time
from typing import Callable, Optional, Dict, List, Any

# Import models dan utilities
from models import FileNode, ScanResult
from utils import is_symlink
import filters # Import semua filter

class Scanner(threading.Thread):
    """
    Runs the directory scan and filtering in a separate thread.
    """
    
    def __init__(self, 
                 root_path: str,
                 on_progress: Callable[[str], None],
                 # --- DIPERBAIKI: Callback sekarang mengembalikan (result, filtered_lists) ---
                 on_complete: Callable[[ScanResult, Dict[str, List[FileNode]]], None],
                 on_error: Callable[[str], None],
                 skip_symlinks: bool = True):
        
        super().__init__()
        self.daemon = True
        
        self.root_path = root_path
        self.skip_symlinks = skip_symlinks
        
        # Callbacks
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error
        
        # Thread control
        self._running_event = threading.Event()
        self._running_event.set()

    def run(self):
        """The main entry point for the thread."""
        try:
            if not os.path.isdir(self.root_path):
                self.on_error(f"Path is not a valid directory: {self.root_path}")
                return

            try:
                stat = os.stat(self.root_path)
                root_node = FileNode(
                    path=self.root_path,
                    name=os.path.basename(self.root_path) or self.root_path,
                    is_dir=True,
                    size_bytes=0,
                    mtime=stat.st_mtime,
                    atime=stat.st_atime,
                    ctime=stat.st_ctime
                )
            except Exception as e:
                self.on_error(f"Cannot access root path: {e}")
                return
                
            scan_result = ScanResult(root_node=root_node)
            scan_result.all_nodes[root_node.path] = root_node
            scan_result.all_dirs.add(root_node)
            scan_result.total_dirs_count = 1

            # --- Langkah 1: Pindai disk secara rekursif ---
            self._scan_recursive(self.root_path, root_node, scan_result)

            if not self._running_event.is_set():
                return # Dibatalkan

            # --- Langkah 2: Hitung ukuran folder (masih di thread) ---
            self.on_progress("Calculating folder sizes...")
            root_node.size_bytes = self._calculate_folder_size(root_node)
            scan_result.total_size_bytes = root_node.size_bytes

            if not self._running_event.is_set():
                return # Dibatalkan

            # --- Langkah 3: Terapkan semua filter (masih di thread) ---
            self.on_progress("Filtering results...")
            
            # Buat list datar untuk RecycleView "All Files (List)"
            all_files_list = sorted(
                scan_result.all_files, 
                key=lambda x: x.path
            )
            
            # Buat list filter lainnya
            large_files = filters.get_large_files(scan_result.all_files)
            old_files = filters.get_old_files(scan_result.all_files)
            temp_files = filters.get_temp_files(scan_result.all_nodes) # all_nodes adalah Dict
            zero_files = filters.get_zero_byte_files(scan_result.all_files)
            empty_dirs = filters.get_empty_folders(scan_result.all_dirs)
            
            # Kumpulkan semua hasil filter ke dalam satu dict
            filtered_lists = {
                "all_files": all_files_list,
                "large": large_files,
                "old": old_files,
                "temp": temp_files,
                "zero_empty": zero_files + empty_dirs
            }

            if self._running_event.is_set():
                # --- Langkah 4: Kirim SEMUA hasil kembali ke main thread ---
                self.on_complete(scan_result, filtered_lists)

        except Exception as e:
            self.on_error(f"An unexpected error occurred: {e}")

    def _scan_recursive(self, current_path: str, parent_node: FileNode, scan_result: ScanResult):
        """Helper function to perform the recursive directory traversal."""
        
        self.on_progress(current_path)

        try:
            with os.scandir(current_path) as it:
                for entry in it:
                    if not self._running_event.is_set():
                        return

                    entry_path = entry.path

                    if self.skip_symlinks and is_symlink(entry_path):
                        continue

                    try:
                        stat = entry.stat(follow_symlinks=False)
                    except (PermissionError, FileNotFoundError, OSError) as e:
                        error_node = FileNode(
                            path=entry_path, name=entry.name, is_dir=entry.is_dir(),
                            size_bytes=0, mtime=0, atime=0, ctime=0,
                            parent=parent_node, scan_error=str(e)
                        )
                        parent_node.children.append(error_node)
                        scan_result.all_nodes[error_node.path] = error_node
                        scan_result.scan_errors.append(f"Cannot access: {entry_path} ({type(e).__name__})")
                        continue

                    is_dir = entry.is_dir(follow_symlinks=False)
                    node = FileNode(
                        path=entry_path, name=entry.name, is_dir=is_dir,
                        size_bytes=stat.st_size if not is_dir else 0,
                        mtime=stat.st_mtime, atime=stat.st_atime, ctime=stat.st_ctime,
                        parent=parent_node
                    )

                    parent_node.children.append(node)
                    scan_result.all_nodes[node.path] = node
                    
                    if is_dir:
                        scan_result.all_dirs.add(node)
                        scan_result.total_dirs_count += 1
                        self._scan_recursive(entry_path, node, scan_result)
                    else:
                        scan_result.all_files.add(node)
                        scan_result.total_files_count += 1
                        # (Total size akan dihitung nanti)

        except PermissionError as e:
            parent_node.scan_error = str(e)
            scan_result.scan_errors.append(f"Cannot scan directory: {current_path} (Permission Denied)")
        except OSError as e:
            parent_node.scan_error = str(e)
            scan_result.scan_errors.append(f"Error scanning directory: {current_path} ({e})")

    def _calculate_folder_size(self, node: FileNode) -> int:
        """Recursively calculates folder size *after* scan is complete."""
        if not node.is_dir:
            return node.size_bytes
        
        size = sum(self._calculate_folder_size(child) for child in node.children)
        node.size_bytes = size
        return size

    def cancel(self):
        """Signals the scanning thread to stop."""
        self.on_progress("Cancelling...")
        self._running_event.clear()