from __future__ import annotations
import re
import unicodedata
from typing import Any, Dict, Optional, Tuple

from katopu_shared.ids import EDITOP_SCHEMA_ID

_TR_MAP = str.maketrans(
    {
        "ğ": "g", "Ğ": "g",
        "ü": "u", "Ü": "u",
        "ş": "s", "Ş": "s",
        "ı": "i", "İ": "i",
        "ö": "o", "Ö": "o",
        "ç": "c", "Ç": "c",
        "’": "'", "‘": "'", "´": "'", "“": '"', "”": '"',
        "–": "-", "—": "-", "−": "-",
    }
)

_NUM_WORDS = {
    # TR (normalize_intent + _TR_MAP sonrası ascii)
    "sifir": 0, "bir": 1, "iki": 2, "uc": 3, "dort": 4, "bes": 5, "alti": 6, "yedi": 7, "sekiz": 8, "dokuz": 9,
    "on": 10, "onbir": 11, "oniki": 12, "onuc": 13, "ondort": 14, "onbes": 15, "onalti": 16, "onyedi": 17,
    "onsekiz": 18, "ondokuz": 19, "yirmi": 20,
    # EN
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}

def normalize_intent(intent: str) -> str:
    s = (intent or "").strip()
    s = unicodedata.normalize("NFKC", s).translate(_TR_MAP).lower()
    s = s.replace("→", "->").replace("=>", "->")
    s = re.sub(r"(\d+)\s*\.\.+\s*(\d+)", r"\1-\2", s)  # 13..24 -> 13-24
    s = re.sub(r"\s+", " ", s).strip()
    return s

def parse_int_loose(token: str) -> Optional[int]:
    if not token:
        return None
    t = token.strip().lower()
    if re.fullmatch(r"\d+", t):
        try:
            return int(t)
        except Exception:
            return None
    t2 = re.sub(r"\s+", "", t)  # "on bir" -> "onbir"
    return _NUM_WORDS.get(t2)

def _parse_range(text: str) -> Optional[Tuple[int, int]]:
    m = re.search(r"(\d+)\s*[-/]\s*(\d+)", text)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return min(a, b), max(a, b)

    m = re.search(r"(\d+)\s*(?:ile|ve)\s*(\d+)", text)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return min(a, b), max(a, b)

    m = re.search(r"(\d+)\s*(?:den|dan|ten|tan)\s*(\d+)\s*(?:e|a|ye|ya)(?:\s*kadar)?", text)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return min(a, b), max(a, b)

    m = re.search(r"(\d+)\D+(\d+)", text)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return min(a, b), max(a, b)

    return None

def local_nl_to_edit(intent: str) -> Optional[Dict[str, Any]]:
    t = normalize_intent(intent)

    del_verbs = ("sil", "kaldir", "cikar", "remove", "delete")
    ins_verbs = ("ekle", "insert", "add", "append", "yerlestir")
    sub_verbs = ("degistir", "cevir", "yap", "replace", "mutate", "donustur")

    has_del = any(v in t for v in del_verbs)
    has_ins = any(v in t for v in ins_verbs)
    has_sub = any(v in t for v in sub_verbs)

    # deletion
    if has_del:
        m_pre = re.search(
            r"\b(?:ilk|bastan|basindan|en bastaki)\s+([0-9]+|[a-z]+(?:\s+[a-z]+)?)\s*(?:baz|nt|nukleotid|harf)\b",
            t,
        )
        if m_pre:
            n = parse_int_loose(m_pre.group(1))
            if n is not None:
                return {"schema": EDITOP_SCHEMA_ID, "op": {"type": "prefix_deletion", "n": n}}

        m_suf = re.search(
            r"\b(?:son|sondan|en sondaki)\s+([0-9]+|[a-z]+(?:\s+[a-z]+)?)\s*(?:baz|nt|nukleotid|harf)\b",
            t,
        )
        if m_suf:
            n = parse_int_loose(m_suf.group(1))
            if n is not None:
                return {"schema": EDITOP_SCHEMA_ID, "op": {"type": "suffix_deletion", "n": n}}

        rng = _parse_range(t)
        if rng:
            i, j = rng
            return {"schema": EDITOP_SCHEMA_ID, "op": {"type": "deletion", "i": i, "j": j}}

        return None

    # insertion
    if has_ins:
        mseq = re.search(r"([acgt]{2,})", t)
        if not mseq:
            return None
        ins_seq = mseq.group(1).upper()

        mpos = re.search(
            r"(\d+)\s*(?:\.?\s*(?:pozisyon|pos|konum|baz))?\s*(?:den|dan|ten|tan)?\s*(?:sonra|sonrasi|sonrasina|sonrasindan)?",
            t,
        )
        if not mpos:
            mpos = re.search(r"(\d+)", t)
        if not mpos:
            return None

        i = int(mpos.group(1))
        return {"schema": EDITOP_SCHEMA_ID, "op": {"type": "insertion", "i": i, "seq": ins_seq}}

    # substitution
    mpos = re.search(r"(\d+)", t)
    marrow = re.search(r"(?<![a-z])([acgt])\s*->\s*([acgt])(?![a-z])", t)

    if mpos and marrow and (" ise " in f" {t} " or " olursa " in f" {t} "):
        i = int(mpos.group(1))
        return {
            "schema": EDITOP_SCHEMA_ID,
            "op": {"type": "conditional_substitution", "i": i, "if_base": marrow.group(1).upper(), "to": marrow.group(2).upper(), "else": "noop"},
        }

    if mpos and marrow:
        i = int(mpos.group(1))
        return {"schema": EDITOP_SCHEMA_ID, "op": {"type": "substitution", "i": i, "from": marrow.group(1).upper(), "to": marrow.group(2).upper()}}

    if has_sub and mpos:
        i = int(mpos.group(1))
        bases = re.findall(r"(?<![a-z])[acgt](?![a-z])", t)
        if len(bases) >= 2:
            frm, to = bases[-2].upper(), bases[-1].upper()
            return {"schema": EDITOP_SCHEMA_ID, "op": {"type": "substitution", "i": i, "from": frm, "to": to}}

    return None

def edit_map_preview(edit_obj: Dict[str, Any]) -> str:
    op = (edit_obj or {}).get("op") if isinstance(edit_obj, dict) else None
    if not isinstance(op, dict):
        return "NA"
    t = op.get("type")
    if t == "deletion":
        return f"del:[{op.get('i')}-{op.get('j')}]"
    if t == "prefix_deletion":
        return f"pdel:first {op.get('n')}"
    if t == "suffix_deletion":
        return f"sdel:last {op.get('n')}"
    if t == "insertion":
        s = op.get("seq", "") or ""
        return f"ins@{op.get('i')}:+{len(s)}"
    if t == "substitution":
        return f"sub:{op.get('i')}:{op.get('from')}->{op.get('to')}"
    if t == "conditional_substitution":
        return f"csub:{op.get('i')}:{op.get('if_base')}?->{op.get('to')}"
    return "NA"
