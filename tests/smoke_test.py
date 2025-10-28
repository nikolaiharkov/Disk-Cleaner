# --- tests/smoke_test.py ---

import os
import sys
import time
import unittest

# Add the parent directory to the Python path
# so we can import our application modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from models import FileNode
    import utils
    import filters
except ImportError as e:
    print(f"Error: Could not import application modules. {e}")
    print("Please ensure this test is in a 'tests/' directory at the project root.")
    sys.exit(1)

class TestUtils(unittest.TestCase):
    """Tests for helper functions in utils.py"""

    def test_format_bytes(self):
        print("\nTesting: utils.format_bytes...")
        self.assertEqual(utils.format_bytes(0), "0.00 B")
        self.assertEqual(utils.format_bytes(1000), "1.00 KB")
        # --- PERBAIKAN #1: Mengganti '1.S KB' menjadi '1.50 KB' ---
        self.assertEqual(utils.format_bytes(1500), "1.50 KB") # <--- DIPERBAIKI
        self.assertEqual(utils.format_bytes(1000**2), "1.00 MB")
        self.assertEqual(utils.format_bytes(123456789), "123.46 MB")
        self.assertEqual(utils.format_bytes(1000**3), "1.00 GB")
        self.assertEqual(utils.format_bytes(1000**4), "1.00 TB")
        print("PASS: utils.format_bytes")


class TestFilters(unittest.TestCase):
    """Tests for logic functions in filters.py"""

    def setUp(self):
        """Create a mock set of FileNodes for testing"""
        print("\nSetting up mock FileNodes...")
        
        now = time.time()
        two_years_ago = now - (2 * 365 * 24 * 60 * 60)
        
        # --- Create Nodes ---
        self.root = FileNode(path="/fake", name="fake", is_dir=True, size_bytes=0, mtime=now, atime=now, ctime=now)
        
        # 1. Large file
        self.large_file = FileNode(
            path="/fake/large.dat", name="large.dat", is_dir=False,
            size_bytes=150 * 1000 * 1000, # 150 MB
            mtime=now, atime=now, ctime=now, parent=self.root
        )
        
        # 2. Old file
        self.old_file = FileNode(
            path="/fake/old.txt", name="old.txt", is_dir=False,
            size_bytes=100,
            mtime=two_years_ago, atime=two_years_ago, ctime=two_years_ago, parent=self.root
        )
        
        # 3. Temp file (by ext)
        self.temp_file_ext = FileNode(
            path="/fake/report.tmp", name="report.tmp", is_dir=False,
            size_bytes=1024,
            mtime=now, atime=now, ctime=now, parent=self.root
        )
        
        # 4. Temp file (by name)
        self.temp_file_name = FileNode(
            path="/fake/Thumbs.db", name="Thumbs.db", is_dir=False,
            size_bytes=2048,
            mtime=now, atime=now, ctime=now, parent=self.root
        )
        
        # 5. Temp dir (by name)
        self.temp_dir = FileNode(
            path="/fake/node_modules", name="node_modules", is_dir=True,
            size_bytes=5000000, # 5 MB
            mtime=now, atime=now, ctime=now, parent=self.root
        )
        
        # --- PERBAIKAN #2: Menjadikan self.temp_dir TIDAK kosong ---
        # Kita tambahkan file anak, sehingga tidak lagi dihitung sebagai 'empty'
        self.temp_dir.children = [FileNode(path="/fake/node_modules/fake.js", name="fake.js", 
                                          is_dir=False, size_bytes=100, mtime=now, 
                                          atime=now, ctime=now, parent=self.temp_dir)] # <--- DIPERBAIKI
        
        # 6. Zero-byte file
        self.zero_file = FileNode(
            path="/fake/empty.file", name="empty.file", is_dir=False,
            size_bytes=0,
            mtime=now, atime=now, ctime=now, parent=self.root
        )
        
        # 7. Empty folder
        self.empty_dir = FileNode(
            path="/fake/EmptyFolder", name="EmptyFolder", is_dir=True,
            size_bytes=0,
            mtime=now, atime=now, ctime=now, parent=self.root
        )
        
        # 8. Normal file (should not be caught)
        self.normal_file = FileNode(
            path="/fake/document.pdf", name="document.pdf", is_dir=False,
            size_bytes=1000000, # 1 MB
            mtime=now, atime=now, ctime=now, parent=self.root
        )

        # --- Create Sets for Filters ---
        self.all_files = {
            self.large_file, self.old_file, self.temp_file_ext,
            self.temp_file_name, self.zero_file, self.normal_file
        }
        
        self.all_dirs = { self.root, self.temp_dir, self.empty_dir }
        
        self.all_nodes = self.all_files.union(self.all_dirs)

    def test_get_large_files(self):
        print("Testing: filters.get_large_files (min 100MB)...")
        result = filters.get_large_files(self.all_files, min_size_mb=100)
        self.assertEqual(len(result), 1)
        self.assertIn(self.large_file, result)
        print("PASS: filters.get_large_files")

    def test_get_old_files(self):
        print("Testing: filters.get_old_files (min 365 days)...")
        result = filters.get_old_files(self.all_files, min_days_old=365)
        self.assertEqual(len(result), 1)
        self.assertIn(self.old_file, result)
        print("PASS: filters.get_old_files")

    def test_get_temp_files(self):
        print("Testing: filters.get_temp_files...")
        result = filters.get_temp_files(self.all_nodes)
        self.assertEqual(len(result), 3)
        self.assertIn(self.temp_file_ext, result)
        self.assertIn(self.temp_file_name, result)
        self.assertIn(self.temp_dir, result)
        print("PASS: filters.get_temp_files")

    def test_get_zero_byte_files(self):
        print("Testing: filters.get_zero_byte_files...")
        result = filters.get_zero_byte_files(self.all_files)
        self.assertEqual(len(result), 1)
        self.assertIn(self.zero_file, result)
        print("PASS: filters.get_zero_byte_files")

    def test_get_empty_folders(self):
        print("Testing: filters.get_empty_folders...")
        # Note: self.root is not empty, it's the parent
        self.root.children = [self.large_file] 
        result = filters.get_empty_folders(self.all_dirs)
        
        # Sekarang 'self.temp_dir' memiliki anak, jadi 'result'
        # akan dengan benar HANYA berisi 'self.empty_dir'.
        # 'self.assertEqual(len(result), 1)' sekarang akan lolos.
        
        self.assertEqual(len(result), 1)
        self.assertIn(self.empty_dir, result)
        self.assertNotIn(self.root, result)
        print("PASS: filters.get_empty_folders")


if __name__ == "__main__":
    print("--- Running Disk Cleaner Smoke Tests ---")
    unittest.main()
    print("----------------------------------------")