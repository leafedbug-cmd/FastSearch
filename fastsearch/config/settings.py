from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set

try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[import]

from fastsearch.index.db import DATA_DIR


SETTINGS_PATH = DATA_DIR / "settings.json"
DEFAULTS_PATH = Path(__file__).with_name("defaults.toml")
_DEFAULTS_CACHE: Dict[str, Any] | None = None


def _load_defaults() -> Dict[str, Any]:
    global _DEFAULTS_CACHE
    if _DEFAULTS_CACHE is not None:
        return _DEFAULTS_CACHE
    if not DEFAULTS_PATH.exists():
        _DEFAULTS_CACHE = {}
        return _DEFAULTS_CACHE
    try:
        with DEFAULTS_PATH.open("rb") as fh:
            _DEFAULTS_CACHE = tomllib.load(fh)
    except Exception:
        _DEFAULTS_CACHE = {}
    return _DEFAULTS_CACHE


def _coerce_paths(raw_paths: Sequence[str]) -> List[Path]:
    paths: List[Path] = []
    for raw in raw_paths:
        p = Path(raw).expanduser()
        if p.exists() and p.is_dir():
            paths.append(p)
    return paths


def default_watch_dirs() -> List[Path]:
    cfg = _load_defaults()
    raw = cfg.get("watch_dirs", []) or []
    return _coerce_paths([str(p) for p in raw])


def default_exclude_names(fallback: Sequence[str] | None = None) -> Set[str]:
    cfg = _load_defaults()
    names = cfg.get("exclude_dir_names")
    if not names:
        fb = fallback or []
        return {name.lower() for name in fb}
    return {str(name).lower() for name in names}


def default_preview_max_bytes(fallback: int = 2_000_000) -> int:
    cfg = _load_defaults()
    value = cfg.get("preview_max_bytes")
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


@dataclass
class Settings:
    enable_ocr: bool = False
    watch_dirs: List[str] = field(default_factory=list)

    @classmethod
    def load(cls) -> "Settings":
        try:
            if SETTINGS_PATH.exists():
                data = json.loads(SETTINGS_PATH.read_text("utf-8"))
                return cls(**data)
        except Exception:
            pass
        return cls()

    def save(self) -> None:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def resolved_watch_dirs_from_settings(settings: Settings) -> List[Path]:
    return _coerce_paths(settings.watch_dirs)

