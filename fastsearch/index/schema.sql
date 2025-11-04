PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA temp_store=MEMORY;
PRAGMA mmap_size=268435456; -- 256MB
PRAGMA page_size=4096;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS locations (
  id INTEGER PRIMARY KEY,
  path TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS docs (
  id INTEGER PRIMARY KEY,
  path TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  name_norm TEXT NOT NULL,
  parent TEXT NOT NULL,
  ext TEXT,
  size_bytes INTEGER NOT NULL,
  mtime_ns INTEGER NOT NULL,
  ctime_ns INTEGER NOT NULL,
  filetype TEXT NOT NULL,
  size_bucket TEXT NOT NULL,
  date_bucket TEXT NOT NULL,
  location_id INTEGER,
  deleted INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY(location_id) REFERENCES locations(id)
);

CREATE INDEX IF NOT EXISTS idx_docs_name_lower ON docs(LOWER(name));
CREATE INDEX IF NOT EXISTS idx_docs_path_lower ON docs(LOWER(path));
CREATE INDEX IF NOT EXISTS idx_docs_parent ON docs(parent);
CREATE INDEX IF NOT EXISTS idx_docs_mtime ON docs(mtime_ns);
CREATE INDEX IF NOT EXISTS idx_docs_buckets ON docs(size_bucket, date_bucket, filetype);
CREATE INDEX IF NOT EXISTS idx_docs_location ON docs(location_id);

-- Full-text search over extracted content (rowid aligned to docs.id)
CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
  content,
  tokenize = 'unicode61 remove_diacritics 2 tokenchars "-_'"'
);
