from __future__ import annotations

import gc
import tempfile
import unittest
from pathlib import Path

from fastsearch.index.db import initialize
from fastsearch.index.docs_repo import DocsRepo, SearchFilters


class DocsRepoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.db_path = self.root / "test.db"
        initialize(self.db_path)
        self.repo = DocsRepo(db_path=self.db_path)

    def tearDown(self) -> None:
        self.repo = None
        gc.collect()
        self._tmpdir.cleanup()

    def _create_file(self, relative: str, content: str = "sample") -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.repo.upsert_file(path, [self.root])
        return path

    def test_search_with_filters_and_facets(self) -> None:
        target = self._create_file("docs/report.txt", "quarterly report")
        self._create_file("media/photo.jpg", "binary")

        filters = SearchFilters(filetypes=["Document"])
        rows, facets = self.repo.search("report", filters, mode="filename")

        self.assertEqual(len(rows), 1)
        self.assertEqual(Path(rows[0]["path"]), target)
        self.assertIn("filetype", facets)
        self.assertIn("Document", facets["filetype"])

    def test_iter_paths_missing_content_batches(self) -> None:
        files = [
            self._create_file(f"docs/file_{i}.txt", f"payload {i}")
            for i in range(3)
        ]

        batches = list(self.repo.iter_paths_missing_content([self.root], batch=1))
        flattened = [p for batch in batches for p in batch]

        self.assertGreater(len(batches), 1)  # ensured batching
        self.assertEqual({path.resolve() for path in flattened}, {f.resolve() for f in files})


if __name__ == "__main__":
    unittest.main()
