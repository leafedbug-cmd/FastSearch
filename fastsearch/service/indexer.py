from __future__ import annotations

import threading
from queue import Queue, Empty
from pathlib import Path
from typing import Optional, Sequence

from fastsearch.extractors.router import extract_text_for_index
from fastsearch.index.fts import upsert_doc_content, delete_doc_content


class ContentIndexer:
    def __init__(self, workers: int = 2, *, roots: Sequence[Path] | None = None, settings=None) -> None:
        self.q: Queue[Path] = Queue(maxsize=10000)
        self._threads: list[threading.Thread] = []
        self._stop = threading.Event()
        self._workers = max(1, workers)
        self._settings = settings
        self._roots: tuple[Path, ...] | None = tuple(roots) if roots else None

    def set_roots(self, roots: Sequence[Path]) -> None:
        self._roots = tuple(roots)

    def start(self) -> None:
        if self._threads:
            return
        for i in range(self._workers):
            t = threading.Thread(target=self._run, name=f"ContentIndexer-{i}", daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        self._stop.set()
        for _ in self._threads:
            self.q.put_nowait(Path("/dev/null"))
        for t in self._threads:
            t.join(timeout=2.0)
        self._threads.clear()

    def enqueue(self, path: Path) -> None:
        try:
            self.q.put_nowait(path)
        except Exception:
            pass

    def queue_size(self) -> int:
        return self.q.qsize()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                p = self.q.get(timeout=0.5)
            except Empty:
                continue
            try:
                if not p.exists() or not p.is_file():
                    continue
                from fastsearch.index.docs_repo import DocsRepo
                repo = DocsRepo()
                roots = self._roots if self._roots else (p.parent,)
                doc_id = repo.upsert_file(p, roots)
                if not doc_id:
                    continue
                text = extract_text_for_index(p, self._settings)
                if text:
                    upsert_doc_content(doc_id, text)
                else:
                    # ensure remove if previously existed
                    delete_doc_content(doc_id)
            except Exception:
                pass
            finally:
                self.q.task_done()

