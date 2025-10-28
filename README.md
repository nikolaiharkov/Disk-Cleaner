# Disk Cleaner (Python/Kivy)

**WARNING: THIS IS A UTILITY THAT CAN PERMANENTLY DELETE DATA. USE AT YOUR OWN RISK. ALWAYS DOUBLE-CHECK YOUR SELECTIONS BEFORE DELETING.**

**Disk Cleaner** is a simple, cross-platform desktop application built with Python and Kivy. It helps users scan a directory, categorize files by various criteria (size, age, type), and reclaim storage space by deleting unwanted items.

It prioritizes safety by defaulting to the system's Recycle Bin / Trash.

## Features

* **Select & Scan:** Choose any directory on your system to scan.
* **Asynchronous Scanning:** The UI remains responsive while the app scans your files in the background. A progress bar and status label keep you updated.
* **Cancel Scan:** Stop the scanning process at any time.
* **Comprehensive Tree View:** The "All Files" tab shows a complete, expandable tree of your directory with checkboxes for selection.
* **Smart Categories:** Scan results are automatically sorted into tabs:
    * **Large Files:** Files over a (soon-to-be-configurable) size threshold.
    * **Old Files:** Files not modified in over a year.
    * **Temporary:** Common junk files/folders (`.tmp`, `.log`, `__pycache__`, etc.).
    * **Zero-byte & Empty:** 0-byte files and empty folders.
    * **Duplicates (On-Demand):** An optional, I/O-intensive scan to find duplicate files by hashing.
* **Safe Deletion:**
    * By default, all items are sent to the **System Recycle Bin / Trash** via `send2trash`.
    * A **Permanent Delete** option is available, but requires explicit confirmation.
* **Cleanup Summary:** After deletion, a popup shows you exactly how much space was freed and what percentage of your drive that represents.

## Installation & Running

This application is built on Python 3.10+ and Kivy.

### 1. Prerequisites

* **Python 3.10 or newer.**
* (Optional but Recommended) Git for cloning.

### 2. Setup a Virtual Environment

It is highly recommended to run this application in a virtual environment.

```bash
# Clone the repository (or just download the files)
# git clone https://your-repo-url/disk_cleaner.git
# cd disk_cleaner

# Create a virtual environment
python -m venv venv

# Activate the environment
# On Windows (cmd):
.\venv\Scripts\activate
# On macOS/Linux (bash/zsh):
source venv/bin/activate