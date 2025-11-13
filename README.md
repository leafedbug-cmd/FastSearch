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

Watch roots are resolved in this order:

1. `FASTSEARCH_WATCH_DIRS` environment variable (path list separated by your OS path separator).
2. The persistent `settings.json` that the Settings dialog writes (stored in the FastSearch user-data directory, see below).
3. `fastsearch/config/defaults.toml` (`watch_dirs`, `exclude_dir_names`, `preview_max_bytes`).
4. A heuristic fallback (Documents / Downloads / Desktop / Home).

Use the Settings button in the toolbar to add/remove folders or toggle OCR; those choices are saved automatically.

Folders & Files
---------------

- Data and settings live under the user data directory reported by `platformdirs` (e.g. `%LOCALAPPDATA%\FastSearch\FastSearch` on Windows, `~/Library/Application Support/FastSearch` on macOS, `~/.local/share/FastSearch` on Linux). Legacy `fastsearch_data/` folders are migrated automatically on launch.
- Database: `<data_dir>/fastsearch.db`.
- Settings: `<data_dir>/settings.json` (watch directories + OCR preference).
- Logs are written to stdout (integrated logging config coming soon).

Roadmap (next)
--------------

- Full-text indexing (FTS5) and content extraction.
- Semantic search with local embeddings.
- OCR for PDFs + content indexing.
- Background service packaging (Windows service / LaunchAgent / systemd).
