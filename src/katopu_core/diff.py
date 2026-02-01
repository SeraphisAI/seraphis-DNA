from __future__ import annotations
import difflib
from typing import List

def bounded_window_diff(before: str, after: str, window: int = 40, max_ops: int = 200) -> str:
    if before is None or after is None:
        return ""
    if not isinstance(before, str):
        before = str(before)
    if not isinstance(after, str):
        after = str(after)
    if before == after:
        return "(no changes)"

    sm = difflib.SequenceMatcher(a=before, b=after)
    opcodes = sm.get_opcodes()

    best = None
    best_score = -1
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            continue
        score = (i2 - i1) + (j2 - j1)
        if score > best_score or (score == best_score and best is not None and i1 < best[1]):
            best_score = score
            best = (tag, i1, i2, j1, j2)

    if best is None:
        return "(no changes)"

    _, i1, i2, j1, j2 = best
    a0 = max(0, i1 - window)
    a1 = min(len(before), i2 + window)
    b0 = max(0, j1 - window)
    b1 = min(len(after), j2 + window)

    a_slice = before[a0:a1]
    b_slice = after[b0:b1]

    lines: List[str] = []
    for d in difflib.ndiff(list(a_slice), list(b_slice)):
        if len(lines) >= max_ops:
            lines.append("…")
            break
        if d.startswith("? "):
            continue
        lines.append(d.rstrip("\n"))

    header = f"[A:{a0}-{a1} of {len(before)}] [B:{b0}-{b1} of {len(after)}]"
    return header + "\n" + "\n".join(lines)
