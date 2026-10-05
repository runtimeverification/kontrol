#!/usr/bin/env python3
"""Dump symbolic terms from a KCFG split's target constraints.

Writing synthetic claims only tells you whether a candidate rule fires
*in general*. To check whether it fires on the *exact* term Kontrol got
stuck on, pull the term out of the proof's KCFG JSON.

Example:
    extract-stuck-term.py out/proofs/test%Foo.sol:Foo.test_bar\\(\\):0
    extract-stuck-term.py <proof-dir> --split 17

<proof-dir> is a directory under `out/proofs/`. Kontrol mangles the
test source path into the proof directory name:
    test/dir/File.sol:Contract.method(args)  →  test%dir%File%...:<idx>
The trailing `:<idx>` is the proof index.

Surface-syntax translation (K internal name → surface):
    lookup(M, K)                    → #lookup(M, K)
    buf(32, X)                      → #buf(32, X)
    asWord(X)                       → #asWord(X)
    _+Bytes__BYTES-...(A, B)        → A +Bytes B
    _|->_(K, V)                     → K |-> V
    _+Int_(X, Y)                    → X +Int Y
    _*Int_(X, Y)                    → X *Int Y
    _&Int_(A, B)                    → A &Int B
    _|Int_(A, B)                    → A |Int B
    _xorInt_(A, B)                  → A xorInt B
    _<<Int_(X, N)                   → X <<Int N
    _>>Int_(X, N)                   → X >>Int N
    _modInt_(X, Y)                  → X modInt Y
    _==Int_(X, Y)                   → X ==Int Y

Paste the reconstructed surface term into `runLemma(...)` using Kontrol's
KV-prefixed variable naming verbatim (e.g. `KV0_x:Int`) so any
`concrete(...)` / `symbolic(...)` attributes on lemmas line up with the
actual ground/symbolic split Kontrol saw.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TypeAlias

# Recursive JSON type — everything this script inspects is the direct
# output of json.load() on a KCFG file, so the types below are exact.
JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = (
    JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
)
JSONObject: TypeAlias = dict[str, JSONValue]


def _get_str(obj: JSONObject, key: str, default: str = "") -> str:
    v = obj.get(key, default)
    return v if isinstance(v, str) else default


def _get_object(obj: JSONObject, key: str) -> JSONObject | None:
    v = obj.get(key)
    return v if isinstance(v, dict) else None


def _get_list(obj: JSONObject, key: str) -> list[JSONValue]:
    v = obj.get(key)
    return v if isinstance(v, list) else []


def show(t: JSONValue) -> str:
    """Render a kore-term JSON node to approximate K surface syntax."""
    if not isinstance(t, dict):
        return repr(t)

    node = _get_str(t, "node")

    if node == "KVariable":
        name = _get_str(t, "name", "?")
        sort_obj = _get_object(t, "sort")
        sort = _get_str(sort_obj, "name", "") if sort_obj is not None else ""
        return f"{name}:{sort}" if sort else name

    if node == "KToken":
        return _get_str(t, "token", "?")

    if node == "KApply":
        label_obj = _get_object(t, "label")
        label = _get_str(label_obj, "name", "?") if label_obj is not None else "?"
        rendered = [show(a) for a in _get_list(t, "args")]
        # Heuristic: binary infix _OP_... → "(lhs OP rhs)"
        if label.startswith("_") and label.endswith("_") and len(rendered) == 2:
            op = label.strip("_").split("__", 1)[0]
            return f"({rendered[0]} {op} {rendered[1]})"
        return f"{label}({', '.join(rendered)})"

    return node or "<unknown>"


def dump_splits(proof_dir: Path, want_split: int | None) -> int:
    """Print constraints for each target of every split in the KCFG."""
    kcfg_path = proof_dir / "kcfg" / "kcfg.json"
    if not kcfg_path.is_file():
        print(f"error: {kcfg_path} not found", file=sys.stderr)
        return 1

    with kcfg_path.open() as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        print(f"error: {kcfg_path}: top-level JSON must be an object", file=sys.stderr)
        return 1
    kcfg: JSONObject = raw

    splits = _get_list(kcfg, "splits")
    if not splits:
        print("(no splits in KCFG)")
        return 0

    for s in splits:
        if not isinstance(s, dict):
            continue
        src_raw = s.get("source")
        src = src_raw if isinstance(src_raw, int) else None
        if want_split is not None and src != want_split:
            continue
        print(f"=== split source node {src} ===")
        for tgt in _get_list(s, "targets"):
            if not isinstance(tgt, dict):
                continue
            tgt_id = tgt.get("target")
            print(f"--- target {tgt_id}")
            csubst = _get_object(tgt, "csubst")
            if csubst is None:
                continue
            for c in _get_list(csubst, "constraints"):
                print(f"  {show(c)}")
        print()

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dump symbolic terms from a Kontrol KCFG split.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "proof_dir",
        type=Path,
        help="Path to the proof directory under out/proofs/ "
        "(e.g. out/proofs/test%%File.sol:C.m\\(\\):0)",
    )
    parser.add_argument(
        "--split",
        type=int,
        default=None,
        help="Filter to a single split by source node id (default: all).",
    )
    args = parser.parse_args()
    sys.exit(dump_splits(args.proof_dir, args.split))


if __name__ == "__main__":
    main()
