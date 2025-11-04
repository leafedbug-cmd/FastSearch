Coding Conventions for FastSearch
=================================

- Python 3.10+, type hints encouraged but not required for UI code.
- Keep modules small and focused. Favor composition over inheritance in UI.
- Avoid blocking the UI thread; use QThread or executors for I/O and DB.
- Keep SQLite writes batched and wrapped in transactions.
- UI assets and styles live under `fastsearch/gui/assets`.
- Prefer dependency injection for DB paths and repositories in services/UI.

Directory Scope
---------------

This file applies to the entire repository.

