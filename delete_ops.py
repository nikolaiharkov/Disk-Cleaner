# --- delete_ops.py ---

import os
import shutil
from send2trash import send2trash
from typing import List, Callable, Tuple
from models import FileNode

# Define a type for the progress callback
# Callback(current_path: str, is_error: bool, message: str)
DeleteProgressCallback = Callable[[str, bool, str], None]

class DeleteResult:
    """Holds the summary of the delete operation."""
    def __init__(self):
        self.files_deleted: int = 0
        self.dirs_deleted: int = 0
        self.total_size_freed: int = 0
        self.errors: List[str] = []

    def add_success(self, node: FileNode):
        """Record a successful deletion."""
        if node.is_dir:
            self.dirs_deleted += 1
        else:
            self.files_deleted += 1
        # Add the size regardless of type.
        # For dirs, this is the recursively calculated size.
        self.total_size_freed += node.size_bytes

    def add_error(self, path: str, error: Exception):
        """Record a failed deletion."""
        self.errors.append(f"Failed to delete {path}: {error}")


def delete_selected_items(
    nodes_to_delete: List[FileNode],
    use_permanent_delete: bool = False,
    progress_callback: DeleteProgressCallback = None
) -> DeleteResult:
    """
    Deletes a list of FileNode objects.
    
    It safely handles nested deletions (e.g., if both a parent folder
    and its child file are selected, it only deletes the parent).
    
    Args:
        nodes_to_delete: A flat list of FileNode objects marked for deletion.
        use_permanent_delete: If True, bypasses Recycle Bin. DANGEROUS.
        progress_callback: A function to call with progress updates.
    
    Returns:
        A DeleteResult object summarizing the operation.
    """
    
    result = DeleteResult()
    
    # --- 1. Filter out redundant nodes ---
    # Create a set of all paths for efficient lookup
    paths_to_delete = {node.path for node in nodes_to_delete}
    
    # We only want to delete the *top-level* selected items.
    # If a node's parent is also in the delete list, skip the node.
    top_level_nodes = []
    for node in nodes_to_delete:
        is_child_of_selected = False
        parent = node.parent
        while parent:
            if parent.path in paths_to_delete:
                is_child_of_selected = True
                break
            parent = parent.parent
            
        if not is_child_of_selected:
            top_level_nodes.append(node)

    # --- 2. Sort nodes for deletion (files first, then dirs) ---
    # This isn't strictly necessary for send2trash, but it's good practice
    # for permanent delete (though rmtree handles it).
    top_level_nodes.sort(key=lambda n: n.is_dir)

    # --- 3. Execute deletion ---
    for node in top_level_nodes:
        if not os.path.exists(node.path):
            # Item was already deleted (e.g., child of a deleted folder)
            continue
            
        if progress_callback:
            op_type = "Permanently deleting" if use_permanent_delete else "Sending to Trash"
            progress_callback(node.path, False, f"{op_type} {node.name}...")
        
        try:
            if use_permanent_delete:
                _delete_permanently(node)
            else:
                _delete_to_trash(node)
                
            # If successful, record it
            result.add_success(node)
            
            if progress_callback:
                progress_callback(node.path, False, f"Deleted {node.name}")

        except Exception as e:
            # If deletion fails
            result.add_error(node.path, e)
            if progress_callback:
                progress_callback(node.path, True, f"Error deleting {node.name}: {e}")

    return result


def _delete_to_trash(node: FileNode):
    """
    Private helper to send a single node (file or dir) to trash.
    send2trash handles both files and directories seamlessly.
    """
    send2trash(node.path)


def _delete_permanently(node: FileNode):
    """
    Private helper to *permanently* delete a file or directory.
    USE WITH EXTREME CAUTION.
    """
    if node.is_dir:
        # Use shutil.rmtree for recursive directory deletion
        shutil.rmtree(node.path, ignore_errors=False)
    else:
        # Use os.remove for a single file
        os.remove(node.path)