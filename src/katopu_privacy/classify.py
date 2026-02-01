from __future__ import annotations
from typing import Literal

DataClass = Literal["public","internal","confidential","restricted"]

def classify_field(field: str) -> DataClass:
    if field in ("sequence","before","after"):
        return "restricted"
    return "internal"
