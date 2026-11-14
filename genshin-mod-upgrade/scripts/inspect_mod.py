#!/usr/bin/env python3
"""Read-only MOD inventory and snapshot comparison; never evaluate INI commands."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import posixpath
import re
import struct
import sys

SCHEMA = "genshin-mod-inventory-v1"


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def literal(value):
    """Remove a trailing INI comment without splitting a quoted filename."""
    quote = None
    for i, character in enumerate(value):
        if character in "\"'":
            if quote == character:
                quote = None
            elif quote is None:
                quote = character
        if quote is None and character in ";#" and (i == 0 or value[i - 1].isspace()):
            value = value[:i]
            break
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def parse_ini(text):
    # Keep duplicate sections, run keys and control-flow statements in source order.
    sections = []
    current = {"name": "", "line": 1, "statements": []}
    sections.append(current)
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith((";", "#")):
            continue
        section = re.fullmatch(r"\[([^\]]+)\]\s*(?:[;#].*)?", line)
        if section:
            current = {"name": section[1], "line": number, "statements": []}
            sections.append(current)
            continue
        row = {"line": number, "text": raw}
        if re.match(r"(?:if|else|elif|endif)\b", line, re.I):
            row["control"] = line
        elif "=" in line:
            key, value = line.split("=", 1)
            row.update(key=key.strip().lower(), value=literal(value))
        current["statements"].append(row)
    return sections


def image_header(path):
    with path.open("rb") as stream:
        data = stream.read(148)
    if data.startswith(b"DDS "):
        if len(data) < 128 or struct.unpack_from("<I", data, 4)[0] != 124:
            return {"type": "DDS", "error": "Invalid or truncated DDS header"}
        height, width = struct.unpack_from("<2I", data, 12)
        result = {"type": "DDS", "width": width, "height": height,
                  "mip_count_declared": struct.unpack_from("<I", data, 28)[0],
                  "fourcc": data[84:88].decode("ascii", errors="backslashreplace"),
                  "rgb_bit_count": struct.unpack_from("<I", data, 88)[0]}
        if data[84:88] == b"DX10":
            if len(data) < 148:
                result["error"] = "Truncated DX10 header"
            else:
                result["dxgi_format"] = struct.unpack_from("<I", data, 128)[0]
        return result
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        if len(data) < 33 or data[12:16] != b"IHDR":
            return {"type": "PNG", "error": "Invalid or truncated IHDR"}
        width, height = struct.unpack_from(">2I", data, 16)
        return {"type": "PNG", "width": width, "height": height,
                "bit_depth": data[24], "colour_type": data[25]}
    return {"error": "Unrecognized image header"}


def resource_info(root, ini, section, filename, files, folded):
    value = filename["value"]
    item = {"ini": ini, "section": section["name"], "line": filename["line"], "filename": value}
    windows = PureWindowsPath(value)
    if not value or windows.drive or windows.is_absolute() or value.startswith(("/", "\\")) or "\0" in value:
        return dict(item, problem="External or invalid filename; not read")
    if "$" in value:
        return dict(item, problem="Dynamic filename; no INI expression evaluation")
    relative = posixpath.normpath(str(PurePosixPath(ini).parent / value.replace("\\", "/")))
    if relative == ".." or relative.startswith("../"):
        return dict(item, problem="Filename escapes inspected MOD root; not read")
    matches = folded.get(relative.casefold(), [])
    if len(matches) != 1:
        return dict(item, problem="Missing referenced file" if not matches else "Ambiguous filename case", candidates=matches)
    name = matches[0]
    item["resolved_file"] = name
    if files[name]["kind"] != "file":
        return dict(item, problem="Referenced symlink is not followed")
    settings = defaultdict(list)
    for row in section["statements"]:
        if "key" in row:
            settings[row["key"]].append(row["value"])
    item["conditional"] = any("control" in row for row in section["statements"])
    strides = set(settings.get("stride", []))
    if strides:
        if len(strides) == 1 and re.fullmatch(r"[0-9]+", next(iter(strides))) and int(next(iter(strides))) > 0:
            stride = int(next(iter(strides)))
            count, remainder = divmod(files[name]["bytes"], stride)
            item["buffer"] = {"stride": stride, "element_count": count, "trailing_bytes": remainder}
            if remainder:
                item["problem"] = "Buffer length is not divisible by its declared stride"
        else:
            item["problem"] = "Multiple or nonliteral stride declarations; not inferred"
    formats = set(v.upper() for v in settings.get("format", []))
    if len(formats) == 1 and next(iter(formats)) in ("DXGI_FORMAT_R16_UINT", "DXGI_FORMAT_R32_UINT"):
        format_name = next(iter(formats))
        stride = 2 if format_name.endswith("R16_UINT") else 4
        count, remainder = divmod(files[name]["bytes"], stride)
        item["indices"] = {"format": format_name, "count": count, "trailing_bytes": remainder}
        if remainder:
            item["problem"] = "Index buffer has a partial final index"
        else:
            minimum, maximum = None, None
            with (root / name).open("rb") as stream:
                while data := stream.read(1024 * 1024):
                    for (index,) in struct.iter_unpack("<H" if stride == 2 else "<I", data):
                        minimum = index if minimum is None else min(minimum, index)
                        maximum = index if maximum is None else max(maximum, index)
            item["indices"].update(minimum=minimum, maximum=maximum)
    return item


def snapshot(root, label=""):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("MOD root must be a directory")
    files, inis, warnings = {}, {}, []
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs.sort()
        links = [name for name in dirs if (Path(directory) / name).is_symlink()]
        dirs[:] = [name for name in dirs if name not in links]
        for name in sorted(names + links):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                files[relative] = {"kind": "symlink", "target": os.readlink(path)}
                warnings.append({"file": relative, "problem": "Symlink recorded but not read"})
                continue
            if not path.is_file():
                warnings.append({"file": relative, "problem": "Non-regular file not read"})
                continue
            info = {"kind": "file", "bytes": path.stat().st_size, "sha256": sha256(path)}
            files[relative] = info
            if path.suffix.lower() in (".dds", ".png"):
                info["image_header"] = image_header(path)
                if "error" in info["image_header"]:
                    warnings.append({"file": relative, "problem": info["image_header"]["error"]})
            if path.suffix.lower() != ".ini":
                continue
            if info["bytes"] > 2 * 1024 * 1024:
                warnings.append({"file": relative, "problem": "INI exceeds 2 MiB parsing limit; file hashed only"})
                continue
            raw = path.read_bytes()
            encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
            try:
                text = raw.decode(encoding)
            except UnicodeError:
                warnings.append({"file": relative, "problem": "INI is not UTF-8/UTF-16; determine encoding manually"})
                continue
            inis[relative] = {"encoding": encoding, "text": text, "sections": parse_ini(text)}
    folded = defaultdict(list)
    for name in files:
        folded[name.casefold()].append(name)
    resources = []
    for ini, data in inis.items():
        for section in data["sections"]:
            if not section["name"].lower().startswith("resource"):
                continue
            for row in section["statements"]:
                if row.get("key") == "filename":
                    item = resource_info(root, ini, section, row, files, folded)
                    resources.append(item)
                    if "problem" in item:
                        warnings.append({k: item[k] for k in ("ini", "section", "line", "filename", "problem")})
    return {"schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(), "label": label,
            "root": str(root), "files": files, "inis": inis, "resources": resources, "warnings": warnings,
            "limits": ["INI is retained, not executed; conditions/includes/external CommandLists need manual tracing",
                       "Image metadata is header-only, not decoded pixel validation",
                       "Resource counts do not determine new hashes or bone mapping"]}


def compare(before, after):
    if before.get("schema") != SCHEMA or after.get("schema") != SCHEMA:
        raise ValueError("Both inputs must be inspect_mod snapshots")
    old, new = before["files"], after["files"]
    changed = sorted(name for name in old.keys() & new.keys() if old[name] != new[name])
    diffs = {}
    for name in changed:
        a, b = before["inis"].get(name), after["inis"].get(name)
        if a is not None and b is not None:
            diffs[name] = "\n".join(difflib.unified_diff(a["text"].splitlines(), b["text"].splitlines(),
                fromfile="before/" + name, tofile="after/" + name, lineterm=""))
    return {"schema": "genshin-mod-diff-v1", "before_root": before["root"], "after_root": after["root"],
            "added": sorted(new.keys() - old.keys()), "removed": sorted(old.keys() - new.keys()),
            "changed": [{"file": name, "before": old[name], "after": new[name]} for name in changed],
            "unchanged_count": len(old.keys() & new.keys()) - len(changed), "ini_diffs": diffs,
            "before_warnings": before["warnings"], "after_warnings": after["warnings"],
            "meaning": "Observed file differences only; comparison does not infer which edits are correct"}


def write_report(path, value, protected_roots=()):
    path = Path(path).resolve()
    for root in protected_roots:
        if path.is_relative_to(Path(root).resolve()):
            raise ValueError("Write the report outside inspected MOD roots")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("snapshot", help="Inventory one MOD directory without changing it")
    scan.add_argument("root", type=Path)
    scan.add_argument("--label", default="")
    scan.add_argument("--output", type=Path, required=True)
    diff = commands.add_parser("compare", help="Compare two saved inventories")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    diff.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "snapshot":
            result = snapshot(args.root, args.label)
            roots = (args.root,)
            summary = {"files": len(result["files"]), "inis": len(result["inis"]),
                       "resources": len(result["resources"]), "warnings": len(result["warnings"])}
        else:
            before = json.loads(args.before.read_text(encoding="utf-8"))
            after = json.loads(args.after.read_text(encoding="utf-8"))
            result = compare(before, after)
            roots = (before["root"], after["root"])
            summary = {"added": len(result["added"]), "removed": len(result["removed"]),
                       "changed": [row["file"] for row in result["changed"]], "unchanged": result["unchanged_count"]}
        write_report(args.output, result, roots)
        print(json.dumps(dict(summary, output=str(args.output.resolve())), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
