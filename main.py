# --- main.py ---

import os
import sys
import threading
from functools import partial
from typing import Set, Dict, List, Optional

# --- Kivy Imports ---
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.treeview import TreeViewLabel
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.clock import Clock
from kivy.properties import ObjectProperty, StringProperty
from kivy.lang import Builder
from plyer import filechooser

# --- Project Imports ---
from models import FileNode, ScanResult
import utils
from scanner import Scanner
import filters
from delete_ops import delete_selected_items, DeleteResult

# --- Kivy Widget Definitions ---

class FileTreeNode(TreeViewLabel):
    # Kelas ini masih dirujuk oleh ui.kv (meskipun tidak terlihat)
    # dan oleh logic _refresh_all_ui_selections.
    node = ObjectProperty(None)

class FileListItem(BoxLayout):
    node = ObjectProperty(None)

class MainLayout(BoxLayout):
    pass

# --- Main Application Class ---

class DiskCleanerApp(App):
    
    # --- Internal State Properties ---
    scanner_thread: Optional[Scanner] = None
    scan_result: Optional[ScanResult] = None # Kita masih simpan ini untuk fitur Duplicates
    selected_nodes: Set[FileNode] = set()
    current_scan_path: str = ""
    total_drive_bytes: int = 0
    _is_refreshing: bool = False

    def build(self):
        return Builder.load_file('ui.kv')

    def on_stop(self):
        self.cancel_scan()

    # --- UI State Management ---

    def set_ui_state(self, state: str):
        ids = self.root.ids
        if state == 'scanning':
            ids.select_dir_button.disabled = True
            ids.scan_button.disabled = True
            ids.delete_button.disabled = True
            ids.scan_duplicates_button.disabled = True
            ids.cancel_scan_button.disabled = False
            ids.cancel_scan_button.opacity = 1
            ids.scan_status_label.text = "Starting scan..."
        elif state == 'deleting':
            ids.select_dir_button.disabled = True
            ids.scan_button.disabled = True
            ids.delete_button.disabled = True
            ids.scan_duplicates_button.disabled = True
            ids.cancel_scan_button.disabled = True
            ids.cancel_scan_button.opacity = 0
            ids.scan_status_label.text = "Deleting items..."
        elif state == 'ready':
            ids.select_dir_button.disabled = False
            ids.scan_button.disabled = not bool(self.current_scan_path)
            ids.delete_button.disabled = not bool(self.selected_nodes)
            ids.scan_duplicates_button.disabled = not bool(self.scan_result)
            ids.cancel_scan_button.disabled = True
            ids.cancel_scan_button.opacity = 0
            if not self.scan_result:
                ids.scan_status_label.text = "Ready. Select a directory."
            else:
                total_size = self.scan_result.total_size_bytes
                ids.scan_status_label.text = f"Scan complete. Total size: {utils.format_bytes(total_size)}"

    # --- 1. Scan Logic ---

    def show_folder_chooser(self):
        try:
            path = filechooser.choose_dir(
                title="Select a directory to scan"
            )
            if path:
                self.current_scan_path = path[0]
                self.root.ids.selected_dir_label.text = self.current_scan_path
                self.set_ui_state('ready')
                self.total_drive_bytes, _, _ = utils.get_drive_usage(self.current_scan_path)
        except Exception as e:
            self.show_popup("Error", f"Could not open folder chooser: {e}")

    def start_scan(self):
        if not self.current_scan_path:
            return
            
        self.clear_all_data()
        self.set_ui_state('scanning')

        def on_progress(path):
            Clock.schedule_once(lambda dt: self._on_scan_progress(path))
            
        # --- DIPERBAIKI: Callback sekarang menerima 2 argumen ---
        def on_complete(result, filtered_lists):
            Clock.schedule_once(lambda dt: self._on_scan_complete(result, filtered_lists))

        def on_error(error_msg):
            Clock.schedule_once(lambda dt: self._on_scan_error(error_msg))

        self.scanner_thread = Scanner(
            root_path=self.current_scan_path,
            on_progress=on_progress,
            on_complete=on_complete,
            on_error=on_error
        )
        self.scanner_thread.start()

    def cancel_scan(self):
        if self.scanner_thread and self.scanner_thread.is_alive():
            self.scanner_thread.cancel()
        self.set_ui_state('ready')
        self.root.ids.scan_status_label.text = "Scan cancelled."

    def _on_scan_progress(self, path: str):
        short_path = path.replace(self.current_scan_path, "...", 1)
        self.root.ids.scan_status_label.text = f"Scanning: {short_path}"

    def _on_scan_error(self, error_msg: str):
        self.show_popup("Scan Error", error_msg)
        self.set_ui_state('ready')

    # --- DIPERBAIKI: Fungsi ini sekarang menerima 'filtered_lists' ---
    def _on_scan_complete(self, result: ScanResult, filtered_lists: Dict[str, List[FileNode]]):
        """UI Callback: Populates all UI elements once scan is done."""
        # Simpan hasil lengkap (masih berisi tree) untuk seleksi & duplikat
        self.scan_result = result
        
        # --- DIPERBAIKI: Langsung populate RecycleViews dari list yang sudah jadi ---
        # Ini sangat cepat dan tidak memblokir UI
        self.root.ids.all_files_rv.data = [
            {'node': n} for n in filtered_lists['all_files']
        ]
        self.root.ids.large_files_rv.data = [
            {'node': n} for n in filtered_lists['large']
        ]
        self.root.ids.old_files_rv.data = [
            {'node': n} for n in filtered_lists['old']
        ]
        self.root.ids.temp_files_rv.data = [
            {'node': n} for n in filtered_lists['temp']
        ]
        self.root.ids.zero_empty_rv.data = [
            {'node': n} for n in filtered_lists['zero_empty']
        ]
        
        self.set_ui_state('ready')
        self.scanner_thread = None

    # --- 2. UI Population ---

    def clear_all_data(self):
        """Resets the UI and internal data to a clean state."""
        self.scan_result = None
        self.selected_nodes.clear()
        
        # --- DIPERBAIKI: Hapus referensi ke tree_view ---
        # Clear RecycleViews
        self.root.ids.all_files_rv.data = []
        self.root.ids.large_files_rv.data = []
        self.root.ids.old_files_rv.data = []
        self.root.ids.temp_files_rv.data = []
        self.root.ids.zero_empty_rv.data = []
        self.root.ids.duplicates_rv.data = []
        
        self.root.ids.duplicates_status_label.text = "Scan for duplicates by hashing files."
        self.update_selection_summary()

    # --- DIPERBAIKI: Hapus fungsi populate_tree_view dan populate_filter_tabs ---
    # (Fungsi-fungsi tersebut tidak diperlukan lagi)

    # --- 3. Selection Logic ---

    def on_node_select(self, node: FileNode, active: bool):
        """
        Called by *any* checkbox in the app.
        """
        if self._is_refreshing:
            return
        
        if not node:
            return
            
        # Logika rekursif masih berfungsi karena self.scan_result.root_node
        # masih menyimpan struktur pohon di memori.
        self._set_node_selected_recursive(node, active)
        
        if not active:
            self._update_parents_on_uncheck(node.parent)
            
        self.update_selection_summary()
        self._refresh_all_ui_selections()

    def _set_node_selected_recursive(self, node: FileNode, active: bool):
        node.selected = active
        if active:
            self.selected_nodes.add(node)
        else:
            self.selected_nodes.discard(node)
            
        for child in node.children:
            self._set_node_selected_recursive(child, active)

    def _update_parents_on_uncheck(self, parent: Optional[FileNode]):
        while parent:
            if parent.selected:
                parent.selected = False
                self.selected_nodes.discard(parent)
                parent = parent.parent
            else:
                break

    def update_selection_summary(self):
        total_size = 0
        paths_to_delete = {n.path for n in self.selected_nodes}
        top_level_selected = []
        for node in self.selected_nodes:
            is_child_of_selected = False
            parent = node.parent
            while parent:
                if parent.path in paths_to_delete:
                    is_child_of_selected = True
                    break
                parent = parent.parent
            if not is_child_of_selected:
                top_level_selected.append(node)
                
        total_size = sum(n.size_bytes for n in top_level_selected)
        count = len(self.selected_nodes)
        
        self.root.ids.selection_summary_label.text = \
            f"Selected: {count} items ({utils.format_bytes(total_size)})"
        self.root.ids.delete_button.disabled = (count == 0)

    # --- DIPERBAIKI: Logika refresh sekarang hanya me-refresh RecycleViews ---
    def _refresh_all_ui_selections(self):
        """
        Manually forces all visible RecycleViews to update their 'active'
        state from the underlying 'node.selected' model property.
        """
        self._is_refreshing = True
        
        # Refresh semua RecycleViews
        self.root.ids.all_files_rv.refresh_from_data()
        self.root.ids.large_files_rv.refresh_from_data()
        self.root.ids.old_files_rv.refresh_from_data()
        self.root.ids.temp_files_rv.refresh_from_data()
        self.root.ids.zero_empty_rv.refresh_from_data()
        self.root.ids.duplicates_rv.refresh_from_data()
        
        Clock.schedule_once(self._release_refresh_lock)

    def _release_refresh_lock(self, dt):
        """Helper function to release the refresh lock."""
        self._is_refreshing = False

    # --- 4. Deletion Logic (Tidak berubah) ---

    def show_delete_confirmation(self):
        content = BoxLayout(orientation='vertical', spacing='10dp', padding='10dp')
        summary = self.root.ids.selection_summary_label.text
        
        content.add_widget(Label(
            text=f"You are about to delete:\n{summary}\n\n"
                 "This action may be permanent depending on your choice."
        ))
        
        perm_box = BoxLayout(size_hint_y=None, height='30dp')
        perm_check = CheckBox(size_hint_x=None, width='40dp')
        perm_box.add_widget(perm_check)
        perm_box.add_widget(Label(
            text="Permanently delete (skip Recycle Bin)"
        ))
        content.add_widget(perm_box)

        btn_box = BoxLayout(size_hint_y=None, height='40dp', spacing='10dp')
        popup = Popup(
            title="Confirm Deletion",
            content=content,
            size_hint=(0.8, 0.5),
            auto_dismiss=False
        )
        btn_cancel = Button(text="Cancel")
        btn_cancel.bind(on_press=popup.dismiss)
        btn_delete = Button(
            text="Delete",
            background_color=(1, 0.2, 0.2, 1)
        )
        btn_delete.bind(
            on_press=lambda x: self.execute_delete(popup, perm_check.active)
        )
        
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_delete)
        content.add_widget(btn_box)
        popup.open()

    def execute_delete(self, popup: Popup, use_permanent_delete: bool):
        popup.dismiss()
        self.set_ui_state('deleting')
        nodes_to_delete = list(self.selected_nodes)
        threading.Thread(
            target=self._delete_thread_worker,
            args=(nodes_to_delete, use_permanent_delete),
            daemon=True
        ).start()

    def _delete_thread_worker(self, nodes: List[FileNode], is_permanent: bool):
        def on_progress(path, is_error, msg):
            status = "Error" if is_error else "Deleting"
            def update_label(dt):
                self.root.ids.scan_status_label.text = f"{status}: {path}"
            Clock.schedule_once(update_label)
            
        result = delete_selected_items(
            nodes_to_delete=nodes,
            use_permanent_delete=is_permanent,
            progress_callback=on_progress
        )
        Clock.schedule_once(lambda dt: self._on_delete_complete(result))
        
    def _on_delete_complete(self, result: DeleteResult):
        freed_percent = utils.calculate_percentage(
            result.total_size_freed,
            self.total_drive_bytes
        )
        drive_name = os.path.splitdrive(self.current_scan_path)[0] or "/"
        
        summary = (
            f"Cleanup Complete\n\n"
            f"Files Deleted: {result.files_deleted}\n"
            f"Folders Deleted: {result.dirs_deleted}\n"
            f"Total Space Freed: {utils.format_bytes(result.total_size_freed)}\n"
            f"({freed_percent:.2f}% of drive {drive_name})\n\n"
        )
        
        if result.errors:
            summary += "Errors encountered:\n"
            summary += "\n".join(result.errors[:5])
            if len(result.errors) > 5:
                summary += f"\n...and {len(result.errors) - 5} more."
                
        self.show_popup("Deletion Complete", summary)
        self.start_scan() # Rescan

    # --- 5. Duplicates Scan Logic (Tidak berubah) ---
    # Logika ini masih bergantung pada self.scan_result.all_files

    def start_duplicate_scan(self):
        if not self.scan_result:
            return
            
        self.root.ids.duplicates_status_label.text = "Scanning for duplicates... (Hashing files)"
        self.root.ids.scan_duplicates_button.disabled = True
        files = self.scan_result.all_files
        
        threading.Thread(
            target=self._duplicate_thread_worker,
            args=(files,),
            daemon=True
        ).start()

    def _duplicate_thread_worker(self, files: Set[FileNode]):
        def on_progress(current, total):
            def update_label(dt):
                self.root.ids.duplicates_status_label.text = f"Hashing... {current}/{total}"
            Clock.schedule_once(update_label)
            
        duplicate_sets = filters.find_duplicates(files, on_progress)
        Clock.schedule_once(
            lambda dt: self._on_duplicate_complete(duplicate_sets)
        )

    def _on_duplicate_complete(self, duplicate_sets: Dict[str, List[FileNode]]):
        flat_list = []
        for file_hash, nodes in duplicate_sets.items():
            flat_list.extend(nodes)
            
        flat_list.sort(key=lambda n: n.size_bytes, reverse=True)
        self.root.ids.duplicates_rv.data = [{'node': n} for n in flat_list]
        self.root.ids.duplicates_status_label.text = \
            f"Found {len(duplicate_sets)} sets of duplicates ({len(flat_list)} total files)."
        self.root.ids.scan_duplicates_button.disabled = False

    # --- Helper Methods (Tidak berubah) ---

    def format_bytes_proxy(self, size_bytes: int) -> str:
        return utils.format_bytes(size_bytes)
        
    def show_popup(self, title: str, text: str):
        content = BoxLayout(orientation='vertical', padding='10dp')
        content.add_widget(Label(text=text))
        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.75, 0.5)
        )
        btn_close = Button(text="Close", size_hint_y=None, height='40dp')
        btn_close.bind(on_press=popup.dismiss)
        content.add_widget(btn_close)
        popup.open()

# --- Entry Point ---
if __name__ == "__main__":
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception as e:
            print(f"Could not set DPI awareness: {e}")
            
    DiskCleanerApp().run()