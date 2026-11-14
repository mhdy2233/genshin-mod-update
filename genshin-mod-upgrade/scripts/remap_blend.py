#!/usr/bin/env python3
"""Preview or copy-remap a verified little-endian float4/uint4 Blend buffer."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys

LAYOUT = "le-f32x4-u32x4-stride32"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate mapping/specification key: {key}")
        result[key] = value
    return result


def remap(raw, specification):
    if specification.get("schema") != 1 or specification.get("direction") != "old-to-new":
        raise ValueError("Mapping must declare schema=1 and direction=old-to-new")
    if specification.get("layout") != LAYOUT:
        raise ValueError("Only an independently confirmed 32-byte float4/uint4 layout is supported")
    for key in ("source_version", "target_version"):
        if not isinstance(specification.get(key), str) or not specification[key].strip():
            raise ValueError(f"Missing {key}")
    evidence = specification.get("evidence")
    if not isinstance(evidence, list) or not evidence or not all(isinstance(v, str) and v.strip() for v in evidence):
        raise ValueError("Record at least one concrete mapping evidence reference")
    expected = specification.get("source_sha256", "")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        raise ValueError("Mapping requires the exact original Blend SHA256")
    if digest(raw) != expected.lower():
        raise ValueError("Source SHA256 mismatch; wrong or already-remapped file. Do not force a second remap")
    if not raw or len(raw) % 32:
        raise ValueError("Blend byte length must be nonzero and divisible by 32")
    target_count = specification.get("target_bone_count")
    if type(target_count) is not int or not 0 < target_count <= 2**32:
        raise ValueError("Invalid target_bone_count")
    supplied = specification.get("old_to_new")
    if isinstance(supplied, list):
        table = dict(enumerate(supplied))
    elif isinstance(supplied, dict):
        if not all(isinstance(key, str) and re.fullmatch(r"0|[1-9][0-9]*", key) for key in supplied):
            raise ValueError("Mapping keys must be unambiguous nonnegative decimal strings")
        table = {int(key): value for key, value in supplied.items()}
    else:
        raise ValueError("old_to_new must be an index array or decimal-keyed object")
    if not table or any(key > 2**32 - 1 for key in table):
        raise ValueError("Empty mapping or old index outside uint32 range")
    if any(type(value) is not int or not 0 <= value < target_count for value in table.values()):
        raise ValueError("Every mapped index must fit the target bone domain")
    changed = bytearray(raw)
    changes, used = [], Counter()
    active_slots = 0
    weight_hasher = hashlib.sha256()
    sums = []
    for vertex, row in enumerate(struct.iter_unpack("<4f4I", raw)):
        weights, indices = row[:4], row[4:]
        if any(not math.isfinite(weight) or weight < 0 for weight in weights):
            raise ValueError(f"Nonfinite or negative weight at vertex {vertex}; verify the layout")
        weight_hasher.update(raw[vertex * 32:vertex * 32 + 16])
        sums.append(sum(weights))
        for slot, (weight, old_index) in enumerate(zip(weights, indices)):
            if weight == 0:
                continue  # Keep unused slot/sentinel bytes exactly as supplied by the artist.
            active_slots += 1
            if old_index not in table:
                raise ValueError(f"No verified mapping for weighted index {old_index} at vertex {vertex}, slot {slot}")
            new_index = table[old_index]
            used[(old_index, new_index)] += 1
            if new_index != old_index:
                offset = vertex * 32 + 16 + slot * 4
                changes.append((offset, raw[offset:offset + 4]))
                struct.pack_into("<I", changed, offset, new_index)
    # Restoring only the changed index words must reproduce every source byte.
    restored = bytearray(changed)
    for offset, original in changes:
        restored[offset:offset + 4] = original
    if restored != raw or len(changed) != len(raw):
        raise ValueError("Unexpected modification outside weighted index words")
    output = bytes(changed)
    return output, {"schema": "genshin-blend-remap-v1", "source_version": specification["source_version"],
                    "target_version": specification["target_version"], "layout": LAYOUT,
                    "source_sha256": digest(raw), "output_sha256": digest(output), "bytes": len(raw),
                    "vertices": len(raw) // 32, "weighted_slots": active_slots, "changed_slots": len(changes),
                    "weight_bytes_sha256": weight_hasher.hexdigest(), "weights_unchanged": True,
                    "zero_weight_indices_unchanged": True, "all_other_bytes_unchanged": True,
                    "weight_sum_range": [min(sums), max(sums)], "weights_normalized": False,
                    "used_mappings": [{"old": a, "new": b, "weighted_slots": count} for (a, b), count in sorted(used.items())],
                    "evidence": evidence, "mapping_semantics_verified_by_script": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="Write a new candidate file; omit for preview only")
    parser.add_argument("--report", type=Path, help="Optional new JSON receipt; existing paths are never overwritten")
    args = parser.parse_args()
    try:
        destinations = [p.resolve() for p in (args.output, args.report) if p is not None]
        if len(set(destinations)) != len(destinations):
            raise ValueError("Output buffer and report must be different files")
        for path in destinations:
            if path.exists() or path.is_symlink() or path in (args.input.resolve(), args.mapping.resolve()):
                raise ValueError(f"Refusing to overwrite an existing/input file: {path}")
        mapping_raw = args.mapping.read_bytes()
        output, report = remap(args.input.read_bytes(), json.loads(mapping_raw.decode("utf-8-sig"), object_pairs_hook=unique_pairs))
        report.update(input=str(args.input.resolve()), mapping_file=str(args.mapping.resolve()),
                      mapping_sha256=digest(mapping_raw), preview_only=args.output is None,
                      output=str(args.output.resolve()) if args.output else None)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("xb") as stream:
                stream.write(output)
            if digest(args.output.read_bytes()) != report["output_sha256"]:
                raise ValueError("Output readback differs from the validated candidate")
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, KeyError, struct.error) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
