from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_FILE = Path(__file__).resolve().parents[4] / "data" / "elster_field_catalog.json"


@lru_cache(maxsize=1)
def load_field_catalog() -> list[dict[str, Any]]:
    with DATA_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_field_mapping(field_id: str) -> dict[str, Any] | None:
    for record in load_field_catalog():
        if record.get("internal_id") == field_id:
            return record
    return None
