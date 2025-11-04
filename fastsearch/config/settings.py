from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict

from fastsearch.index.db import DATA_DIR


SETTINGS_PATH = DATA_DIR / "settings.json"


@dataclass
class Settings:
    enable_ocr: bool = False

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

