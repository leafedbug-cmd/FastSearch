FastSearch (MVP)
================

Fast, local desktop file search focused on instant filename/path search with a modern, faceted UI. This is the first iteration with a solid UI, a real-time watcher, and a local SQLite index. Future phases will add full-text and semantic search.

Quick Start
-----------

1. Create and activate a Python 3.10+ environment.
2. Install: `pip install -e .`
3. Run: `python scripts/run_gui.py`

Features (MVP)
--------------

- Real-time indexing of configured folders via watchdog.
- Blazing-fast filename/path search using SQLite with tuned PRAGMAs.
- Faceted filters: File Type, Size, Date Modified, Location.
- Polished PySide6 UI with a results table and preview pane.
- Optional OCR for image previews (toggle in Settings). Requires Tesseract OCR installed and available on PATH.

Configuration
-------------

Edit `fastsearch/config/defaults.toml` to set `watch_dirs`. You can also add directories from the UI (Settings button in the toolbar).

Folders & Files
---------------

- Database lives at `fastsearch_data/fastsearch.db` by default (created on first run).
- Logs are written to stdout (integrated logging config coming soon).

Roadmap (next)
--------------

- Full-text indexing (FTS5) and content extraction.
- Semantic search with local embeddings.
- OCR for PDFs + content indexing.
- Background service packaging (Windows service / LaunchAgent / systemd).
