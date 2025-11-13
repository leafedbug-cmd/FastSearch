from __future__ import annotations

import gc
import tempfile
import unittest
from pathlib import Path

from fastsearch.index.db import initialize
from fastsearch.index.docs_repo import DocsRepo, SearchFilters

try:
    import watchdog  # type: ignore[unused-import]
except ModuleNotFoundError:  # pragma: no cover
    WATCHDOG_AVAILABLE = False
else:
    WATCHDOG_AVAILABLE = True

if WATCHDOG_AVAILABLE:
    from fastsearch.service.watcher import WatchService, WatcherConfig
else:  # pragma: no cover
    WatchService = WatcherConfig = None


class DummyIndexer:
    def __init__(self) -> None:
        self.enqueued: list[Path] = []

    def enqueue(self, path: Path) -> None:
        self.enqueued.append(Path(path))

    def queue_size(self) -> int:
        return len(self.enqueued)


@unittest.skipUnless(WATCHDOG_AVAILABLE, "watchdog not installed")
class WatchServiceScanTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.watch_root = self.root / "watched"
        self.db_path = self.root / "test.db"
        initialize(self.db_path)
        self.repo = DocsRepo(db_path=self.db_path)
        (self.watch_root / "alpha").mkdir(parents=True, exist_ok=True)
        (self.watch_root / "alpha" / "a.txt").write_text("a", encoding="utf-8")
        (self.watch_root / "alpha" / "b.txt").write_text("b", encoding="utf-8")
        self.indexer = DummyIndexer()
        cfg = WatcherConfig(roots=[self.watch_root], exclude_dir_names=set())
        self.watcher = WatchService(self.repo, cfg, indexer=self.indexer)
        self.statuses: list[str] = []
        self.watcher.on_status(self.statuses.append)

    def tearDown(self) -> None:
        self.repo = None
        gc.collect()
        self._tmpdir.cleanup()

    def test_scan_root_populates_index_and_queue(self) -> None:
        self.watcher._scan_root(self.watch_root)

        rows, _ = self.repo.search("", SearchFilters(), mode="filename")
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(self.indexer.enqueued), 2)
        self.assertTrue(any("queue depth" in msg for msg in self.statuses))


if __name__ == "__main__":
    unittest.main()
