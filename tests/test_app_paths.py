"""Ресурсы всегда читаются из внешней папки res рядом с программой."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import app_paths

ROOT = Path(__file__).resolve().parents[1]


class AppPathsTest(unittest.TestCase):
    def test_running_from_sources_does_not_depend_on_current_directory(self):
        with patch.object(sys, "frozen", False, create=True):
            self.assertEqual(app_paths.app_dir(), ROOT)
            self.assertEqual(app_paths.res_path("finans.ui"), ROOT / "res/finans.ui")
            self.assertEqual(app_paths.res_path("data.db"), ROOT / "res/data.db")

    def test_pyinstaller_uses_exe_directory_instead_of_internal(self):
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / "dist/main/main.exe"
            internal = exe.parent / "_internal"
            with patch.object(sys, "frozen", True, create=True), \
                 patch.object(sys, "executable", str(exe)), \
                 patch.object(sys, "_MEIPASS", str(internal), create=True):
                self.assertEqual(app_paths.app_dir(), exe.parent)
                self.assertEqual(app_paths.res_path("finans.ui"),
                                 exe.parent / "res/finans.ui")
                self.assertEqual(app_paths.res_path("data.db"),
                                 exe.parent / "res/data.db")


if __name__ == "__main__":
    unittest.main()
