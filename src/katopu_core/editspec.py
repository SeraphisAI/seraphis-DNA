"""EditSpec parsing and normalization.

KATOPU Ω is *spec-first*:

- /nl/spec produces a versioned EditSpec
- /edit/apply accepts EditSpec only

This module turns Turkish NL intents into a canonical EditSpec.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from katopu_shared.contract_utils import (
    ERR_INTENT_UNPARSED,
    ERR_INVALID_BASE,
    ERR_INVALID_POSITION,
    ERR_MISSING_PARAM,
    ERR_OUT_OF_RANGE,
    ERR_UNSUPPORTED_SYNONYM,
    make_editspec,
    sha256_hex,
)


DNA_BASES = {"A", "C", "G", "T"}


def normalize_intent_tr(text: str) -> str:
    """Normalize Turkish intent text into a canonical, lowercased form.

    Goals:
    - make apostrophes consistent
    - collapse whitespace
    - keep digits and letters
    """
    if text is None:
        return ""
    s = text.strip()
    # Normalize common unicode apostrophes/quotes into ASCII apostrophe
    s = s.replace("’", "'").replace("‘", "'").replace("`", "'")
    # Normalize Turkish dotted/dotless i safely with casefold
    s = s.casefold()
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    return s


def _canonical_prefix(n: int) -> str:
    return f"ilk {n} baz sil"


def _canonical_suffix(n: int) -> str:
    return f"son {n} baz sil"


def _canonical_pmut(pos: int, base: str) -> str:
    return f"pozisyon {pos}'deki bazı {base} yap"


def parse_intent_to_editspec(
    *,
    sequence: str,
    intent: str,
    mode: str = "strict",
    spec_version: str = "1.0.0",
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return an EditSpec dict.

    In strict mode we only accept the canonical grammars:
      - "ilk N baz sil"
      - "son N baz sil"
      - "pozisyon P'deki bazı X yap"

    Any failure becomes a validation error attached to the EditSpec.
    """
    strict = (mode or "strict").lower() == "strict"
    intent_norm = normalize_intent_tr(intent)
    intent_sha = sha256_hex(intent_norm)

    errors: List[Dict[str, Any]] = []

    if not intent_norm:
        errors.append({"code": ERR_MISSING_PARAM, "detail": {"field": "intent"}})
        return make_editspec(
            sequence=sequence,
            intent_norm=intent_norm,
            intent_norm_sha256=intent_sha,
            strict_mode=strict,
            spec_version=spec_version,
            op="UNPARSED",
            params={},
            validation_errors=errors,
            request_id=request_id,
        )

    # Accept digits written with punctuation (e.g. "10.") by stripping trailing dot.
    def _to_int(tok: str) -> Optional[int]:
        tok = tok.strip()
        tok = tok[:-1] if tok.endswith(".") else tok
        if tok.isdigit():
            return int(tok)
        return None

    # 1) Strict canonical prefix/suffix deletion
    m = re.fullmatch(r"ilk (\d+) baz sil", intent_norm)
    if m:
        n = _to_int(m.group(1))
        if n is None:
            errors.append({"code": ERR_MISSING_PARAM, "detail": {"field": "n"}})
        return make_editspec(
            sequence=sequence,
            intent_norm=_canonical_prefix(n or 0) if n is not None else intent_norm,
            intent_norm_sha256=intent_sha,
            strict_mode=strict,
            spec_version=spec_version,
            op="PREFIX_DELETE",
            params={"n": n},
            validation_errors=errors,
            request_id=request_id,
        )

    m = re.fullmatch(r"son (\d+) baz sil", intent_norm)
    if m:
        n = _to_int(m.group(1))
        if n is None:
            errors.append({"code": ERR_MISSING_PARAM, "detail": {"field": "n"}})
        return make_editspec(
            sequence=sequence,
            intent_norm=_canonical_suffix(n or 0) if n is not None else intent_norm,
            intent_norm_sha256=intent_sha,
            strict_mode=strict,
            spec_version=spec_version,
            op="SUFFIX_DELETE",
            params={"n": n},
            validation_errors=errors,
            request_id=request_id,
        )

    # 2) Strict canonical point mutation
    # Accept variants like:
    #   "pozisyon 10'daki bazı a yap"
    #   "pozisyon 10'deki bazi a yap" (casefold)
    #   "10'daki bazı a yap" (lenient)
    pmut_pat = re.compile(
        r"pozisyon (\d+)(?:[' ]*(?:deki|daki))? (?:bazı|bazi) ([acgt]) yap"
    )
    m = pmut_pat.fullmatch(intent_norm)
    if m:
        pos = _to_int(m.group(1))
        base = m.group(2).upper()
        if pos is None:
            errors.append({"code": ERR_INVALID_POSITION, "detail": {"position": m.group(1)}})
        if base not in DNA_BASES:
            errors.append({"code": ERR_INVALID_BASE, "detail": {"base": base}})
        return make_editspec(
            sequence=sequence,
            intent_norm=_canonical_pmut(pos or 0, base),
            intent_norm_sha256=intent_sha,
            strict_mode=strict,
            spec_version=spec_version,
            op="POINT_MUTATION",
            params={"position": pos, "base": base},
            validation_errors=errors,
        )

    # 3) Lenient synonyms (explicitly classify in strict)
    # Prefix deletion synonyms
    syn_prefix = re.fullmatch(r"başlangıçtan (\d+) baz (?:sil|çıkar)", intent_norm)
    if syn_prefix:
        if strict:
            errors.append({"code": ERR_UNSUPPORTED_SYNONYM, "detail": {"intent": intent_norm}})
            return make_editspec(
                sequence=sequence,
                intent_norm=intent_norm,
                intent_norm_sha256=intent_sha,
                strict_mode=strict,
                spec_version=spec_version,
                op="UNPARSED",
                params={},
                validation_errors=errors,
                request_id=request_id,
            )
        n = _to_int(syn_prefix.group(1))
        return make_editspec(
            sequence=sequence,
            intent_norm=_canonical_prefix(n or 0),
            intent_norm_sha256=intent_sha,
            strict_mode=strict,
            spec_version=spec_version,
            op="PREFIX_DELETE",
            params={"n": n},
            validation_errors=errors,
            request_id=request_id,
        )

    syn_suffix = re.fullmatch(r"sondan (\d+) baz (?:sil|çıkar)", intent_norm)
    if syn_suffix:
        if strict:
            errors.append({"code": ERR_UNSUPPORTED_SYNONYM, "detail": {"intent": intent_norm}})
            return make_editspec(
                sequence=sequence,
                intent_norm=intent_norm,
                intent_norm_sha256=intent_sha,
                strict_mode=strict,
                spec_version=spec_version,
                op="UNPARSED",
                params={},
                validation_errors=errors,
            )
        n = _to_int(syn_suffix.group(1))
        return make_editspec(
            sequence=sequence,
            intent_norm=_canonical_suffix(n or 0),
            intent_norm_sha256=intent_sha,
            strict_mode=strict,
            spec_version=spec_version,
            op="SUFFIX_DELETE",
            params={"n": n},
            validation_errors=errors,
        )

    # Lenient point mutation without explicit "pozisyon" keyword
    if not strict:
        pmut2 = re.fullmatch(r"(\d+)(?:[' ]*(?:deki|daki))? (?:bazı|bazi) ([acgt]) yap", intent_norm)
        if pmut2:
            pos = _to_int(pmut2.group(1))
            base = pmut2.group(2).upper()
            return make_editspec(
                sequence=sequence,
                intent_norm=_canonical_pmut(pos or 0, base),
                intent_norm_sha256=intent_sha,
                strict_mode=strict,
                spec_version=spec_version,
                op="POINT_MUTATION",
                params={"position": pos, "base": base},
                validation_errors=errors,
            )

    # Otherwise: parse error
    errors.append({"code": ERR_INTENT_UNPARSED, "detail": {"intent": intent_norm}})
    return make_editspec(
        sequence=sequence,
        intent_norm=intent_norm,
        intent_norm_sha256=intent_sha,
        strict_mode=strict,
        spec_version=spec_version,
        op="UNPARSED",
        params={},
        validation_errors=errors,
    )
