#!/usr/bin/env python3
"""Small boundary tests; real native conversions are validated in the workspace."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import zipfile

import convert_android as port


class AndroidConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def archive(self, *, payload=b"mesh fixture", first="manifest.json", extra=None, pending=False):
        original = b"mesh fixture"
        manifest = {"format": port.FORMAT, "gameVersion": port.GAME, "character": "Keqing",
                    "packageVersion": 1, "title": "fixture", "fxPending": pending,
                    "resources": [{"file": "assets/body.blk", "bytes": len(original), "type": 43,
                                   "sha256": hashlib.sha256(original).hexdigest()}]}
        entries = {"manifest.json": json.dumps(manifest).encode(), "README.md": b"source credit",
                   "assets/body.blk": payload}
        if extra:
            entries[extra] = b"extra"
        path = self.root / "fixture.lunamod"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(first, entries.pop(first))
            for name, data in entries.items():
                archive.writestr(name, data)
        return path

    def test_archive_integrity_and_tampering(self):
        result = port.verify_archive(self.archive())
        self.assertTrue(result["zip_crc_and_resource_hashes_verified"])
        self.assertFalse(result["runtime_verified"])
        with self.assertRaises(ValueError):
            port.verify_archive(self.archive(payload=b"Mesh fixture"))

    def test_importer_envelope(self):
        for kwargs in ({"first": "README.md"}, {"extra": "../outside.txt"},
                       {"extra": "assets/"}, {"pending": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                port.verify_archive(self.archive(**kwargs))

    def test_control_changes_require_adaptation(self):
        source = self.root / "pc"
        source.mkdir()
        content = b"[Constants]\nglobal $choice = 0\n"
        (source / "Control.ini").write_bytes(content)
        (source / "option.buf").write_bytes(b"option")
        profile = {"inis": {"Control.ini": hashlib.sha256(content).hexdigest()}, "extras": ["option.buf"]}
        self.assertEqual(len(port.calibrated_input(source, profile)["files"]), 2)
        (source / "Control.ini").write_bytes(content.replace(b"= 0", b"= 1"))
        with self.assertRaises(ValueError):
            port.calibrated_input(source, profile)
        (source / "Control.ini").write_bytes(content)
        (source / "Extra.ini").write_text("[ShaderRegex]\npattern = changed\n")
        with self.assertRaises(ValueError):
            port.calibrated_input(source, profile)

    def test_output_cannot_modify_input_tree(self):
        source = self.root / "pc"
        source.mkdir()
        output = source / "converted"
        args = SimpleNamespace(profile="keqing-silverwolf", output=output)
        with self.assertRaises(ValueError):
            port.convert(args, {"root": str(source)}, self.root, self.root, self.root)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
