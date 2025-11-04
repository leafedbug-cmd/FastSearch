from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence


@dataclass
class FacetCounts:
    filetype: Dict[str, int] = field(default_factory=dict)
    size_bucket: Dict[str, int] = field(default_factory=dict)
    date_bucket: Dict[str, int] = field(default_factory=dict)
    location: Dict[str, int] = field(default_factory=dict)  # location path → count


@dataclass
class FacetSelection:
    filetype: List[str] = field(default_factory=list)
    size_bucket: List[str] = field(default_factory=list)
    date_bucket: List[str] = field(default_factory=list)
    location: List[str] = field(default_factory=list)  # selected location paths

    def is_empty(self) -> bool:
        return not (self.filetype or self.size_bucket or self.date_bucket or self.location)

