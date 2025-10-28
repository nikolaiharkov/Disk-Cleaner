# --- models.py ---

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

@dataclass
class FileNode:
    """
    Represents a single file or directory node found during the scan.
    This is a pure data class.
    """
    path: str
    name: str
    is_dir: bool
    size_bytes: int
    
    # Timestamps (use float for compatibility with os.stat_result)
    mtime: float  # Last modification time
    atime: float  # Last access time
    ctime: float  # Creation time (Windows) or metadata change time (Unix)

    ext: str = ""  # File extension (e.g., ".txt")
    
    # Tree structure
    parent: Optional['FileNode'] = None
    children: List['FileNode'] = field(default_factory=list)
    
    # State for UI interaction
    # This will be manipulated by the UI and read by delete_ops
    selected: bool = False
    
    # On-demand properties
    hash_sha256: Optional[str] = None
    
    # Error handling
    scan_error: Optional[str] = None # e.g., "Permission Denied"

    def __post_init__(self):
        # Automatically populate extension if it's a file
        if not self.is_dir and '.' in self.name:
            self.ext = f".{self.name.split('.')[-1].lower()}"

    def __hash__(self):
        # Enable adding FileNode objects to sets or dict keys
        return hash(self.path)

    def __eq__(self, other):
        # Define equality based on the unique path
        if not isinstance(other, FileNode):
            return False
        return self.path == other.path


@dataclass
class ScanResult:
    """
    Holds the complete result of a directory scan.
    """
    root_node: FileNode  # The root node of the scanned tree
    
    # Flat list of all nodes for easier filtering in tabs
    # We store them in a dict for O(1) lookup by path
    all_nodes: Dict[str, FileNode] = field(default_factory=dict)
    
    # Quick-access sets for category tabs
    all_files: Set[FileNode] = field(default_factory=set)
    all_dirs: Set[FileNode] = field(default_factory=set)

    # Summary statistics
    total_size_bytes: int = 0
    total_files_count: int = 0
    total_dirs_count: int = 0
    
    # Errors encountered during the scan
    scan_errors: List[str] = field(default_factory=list) # List of paths that failed