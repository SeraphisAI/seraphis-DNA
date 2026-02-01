from __future__ import annotations
import re
from typing import Optional, Tuple

DNA_IUPAC_RE = re.compile(r"^[ACGTRYSWKMBDHVN]+$")
def sanitize_sequence(seq: Optional[str]) -> Tuple[str, int]:
    if seq is None:
        return "", 0
    s = re.sub(r"\s+", "", seq).upper()
    ambig = 1 if re.search(r"[^ACGTRYSWKMBDHVN]", s) else 0
    return s, ambig

def is_iupac(seq: str) -> bool:
    return DNA_IUPAC_RE.fullmatch(seq or "") is not None
