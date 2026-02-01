from __future__ import annotations
import argparse
import json
from typing import Any, Dict, Callable, Tuple

def migrate_0_1_0_to_0_2_0(obj: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(obj)
    meta = out.get("_meta") if isinstance(out.get("_meta"), dict) else {}
    meta.setdefault("migrated_from", "0.1.0")
    meta["contract"] = "katopu.ucp.ultra.final.v2"
    out["_meta"] = meta
    errs = out.get("errors")
    if isinstance(errs, list):
        for e in errs:
            if isinstance(e, dict) and "detail" in e and "details" not in e:
                e["details"] = e.pop("detail")
    return out

MIGRATIONS: Dict[Tuple[str,str], Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    ("0.1.0", "0.2.0"): migrate_0_1_0_to_0_2_0,
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="input json")
    ap.add_argument("--out", dest="out", required=True, help="output json")
    ap.add_argument("--from", dest="frm", default="0.1.0", help="from version")
    ap.add_argument("--to", dest="to", required=True, help="to version")
    args = ap.parse_args()

    with open(args.inp, "r", encoding="utf-8") as f:
        obj = json.load(f)

    fn = MIGRATIONS.get((args.frm, args.to))
    if not fn:
        raise SystemExit(f"No migration registered: {args.frm} -> {args.to}")

    if not isinstance(obj, dict):
        raise SystemExit("Expected a JSON object")

    new = fn(obj)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=2)

    print(f"OK migrated {args.frm} -> {args.to} to {args.out}")

if __name__ == "__main__":
    main()
