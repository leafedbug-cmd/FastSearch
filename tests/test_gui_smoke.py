from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PySide6 import QtWidgets

from fastsearch.config.settings import Settings
from fastsearch.gui.views.main_window import MainWindow
from fastsearch.index.docs_repo import SearchFilters


class DummyRepo:
    def location_ids_for_paths(self, paths):
        return []

    def search(self, query, filters: SearchFilters, limit: int = 500, mode: str = "all"):
        return [], {"filetype": {}, "size_bucket": {}, "date_bucket": {}, "location": {}}


class DummyWatcher:
    def on_status(self, fn):
        self._cb = fn

    def start_in_thread(self):
        pass

    def stop(self):
        pass


class MainWindowSmokeTestCase(unittest.TestCase):
    def test_main_window_constructs_and_closes(self) -> None:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with tempfile.TemporaryDirectory() as tmpdir:
            watch_dir = Path(tmpdir)
            settings = Settings()
            settings.watch_dirs = [str(watch_dir)]
            win = MainWindow(repo=DummyRepo(), watch_dirs=[watch_dir], watcher=DummyWatcher(), settings=settings)
            win.show()
            QtWidgets.QApplication.processEvents()
            win.close()
            QtWidgets.QApplication.processEvents()


if __name__ == "__main__":
    unittest.main()
