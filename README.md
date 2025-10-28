# Disk Cleaner (Python/Kivy)

**WARNING: THIS IS A UTILITY THAT CAN PERMANENTLY DELETE DATA. USE AT YOUR OWN RISK. ALWAYS DOUBLE-CHECK YOUR SELECTIONS BEFORE DELETING.**

Disk Cleaner is a cross-platform desktop utility built with Python and the Kivy framework. It is designed to scan directories, categorize files by various criteria (size, age, type), and help users reclaim storage space by deleting unwanted items.

The application is engineered for safety and performance, defaulting to the system's Recycle Bin / Trash and using a multi-threaded architecture to keep the UI responsive, even when scanning millions of files.

## Core Features

* **Asynchronous Scanning:** The entire scanning and file-filtering process runs in a separate background thread (`scanner.py`). This ensures the Kivy UI remains fluid and responsive, with a progress bar and status label providing real-time feedback [from `main.py`, `scanner.py`].
* **High-Performance UI:** Uses Kivy's `RecycleView` widget for *all* file lists, including the "All Files" tab. This approach is highly optimized and can render lists of tens of thousands of items without the performance bottlenecks (like `[CRITICAL] Clock` warnings) that would occur with a traditional `TreeView` or `ScrollView`.
* **Smart Filter Categories:** Files are automatically categorized in the background thread (`scanner.py`, `filters.py`) and presented in separate tabs:
    * **Large Files:** Identifies files exceeding a configurable size (default: 100MB).
    * **Old Files:** Finds files not modified in over a year (default: 365 days).
    * **Temporary:** Catches common junk files (`.tmp`, `.log`, `.bak`) and cache folders (`__pycache__`, `node_modules`, `.cache`) [from `filters.py`].
    * **Zero-byte & Empty:** Isolates 0-byte files and completely empty folders.
    * **Duplicates (On-Demand):** An optional, I/O-intensive scan that finds duplicate files by comparing file sizes and then SHA-256 hashes (`filters.py`).
* **Safe & Permanent Deletion:**
    * **Safe by Default:** Defaults to using `send2trash` to move items to the system Recycle Bin / Trash.
    * **Permanent Option:** A separate, clearly-marked option allows for permanent deletion (`shutil.rmtree` and `os.remove`), bypassing the bin [from `delete_ops.py`].
* **Intelligent Deletion Logic:** The delete operation is smart. If you select both a parent folder and its children, it will only issue one delete command for the top-level parent, preventing redundant operations [from `delete_ops.py`].
* **Cross-Platform Native Dialogs:** Uses `plyer` to invoke the native OS "Select Folder" dialog for a seamless user experience [from `main.py`].
* **Cleanup Summary:** After deletion, a popup shows exactly how much space was freed and provides a list of any errors encountered (`main.py`, `delete_ops.py`).

## How It Works (Application Architecture)

The application is designed to separate concerns and prevent the UI from freezing during heavy operations.

1.  **Main Thread (UI) - `main.py`:**
    * Runs the Kivy application and manages all UI widgets defined in `ui.kv`.
    * Handles user input (button clicks, folder selection).
    * Manages UI state (e.g., "scanning", "ready", "deleting").
    * Spawns background threads for scanning and deletion.

2.  **Scanner Thread - `scanner.py`:**
    * Launched when the user clicks "Scan".
    * Recursively walks the target directory (`_scan_recursive`), building a tree of `FileNode` objects [from `models.py`].
    * Calculates the size of each folder (`_calculate_folder_size`).
    * **Crucially, it runs all filtering logic** (`filters.py`) *within this thread*.
    * When complete, it passes the pre-filtered lists (e.g., `large_files`, `old_files`) back to the main thread.

3.  **UI Population - `main.py`:**
    * The main thread receives the `filtered_lists` from the scanner via a `Clock.schedule_once` callback.
    * It then populates the `RecycleView`s by simply assigning these lists to their `data` properties. This step is extremely fast as all the processing is already done.

4.  **Deletion Thread - `delete_ops.py`:**
    * To prevent the UI from freezing during I/O-heavy deletion, `main.py` spawns *another* thread to call `delete_selected_items`.
    * This thread handles the "top-level node" filtering and executes either `send2trash` or `shutil.rmtree`/`os.remove` for each item.
    * A `DeleteResult` object is passed back to the main thread to show the summary popup.

## Installation & Running

This application is built for Python 3.10 and newer.

### 1. Prerequisites

* **Python 3.10+**
* (Optional but Recommended) Git for cloning.

### 2. Setup

It is highly recommended to run this application in a virtual environment.

```bash
# 1. Clone or download the repository
# git clone https://your-repo-url/disk-cleaner.git
# cd disk-cleaner

# 2. Create a virtual environment
python -m venv venv

# 3. Activate the environment
# On Windows (cmd):
.\venv\Scripts\activate
# On macOS/Linux (bash/zsh):
source venv/bin/activate

# 4. Install the required dependencies
pip install -r requirements.txt

# 5. Run the application
python main.py