#!/usr/bin/env python3
"""Isolated regression checks for inventories and one-time Blend remapping."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
import inspect_mod
import remap_blend

SCRIPTS = Path(__file__).resolve().parent


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="mod-upgrade-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "old"
        self.root.mkdir()
        text = (
            "; 原文件保留注释\r\n[TextureOverrideBody]\r\nhash = 01234567\r\n"
            "if $state == 1\r\nrun = CommandListOne\r\nrun = CommandListTwo\r\n"
            "drawindexed = 3,0,0\r\nelse\r\ndrawindexed = 3,3,0\r\nendif\r\n"
            "[TextureOverrideBody]\r\nmatch_first_index = 7419\r\n"
            "[ResourcePosition]\r\nstride = 40\r\nfilename = .\\Position.buf\r\n"
            "[ResourceBlend]\r\nstride = 32\r\nfilename = Blend.buf\r\n"
            "[ResourceIndices]\r\nformat = DXGI_FORMAT_R16_UINT\r\nfilename = Body.ib\r\n"
            "[ResourceDiffuse]\r\nfilename = \"Body #1.dds\" ; reference with a comment\r\n"
        )
        (self.root / "Venti.ini").write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
        (self.root / "Position.buf").write_bytes(bytes(3 * 40))
        (self.root / "Blend.buf").write_bytes(bytes(3 * 32))
        (self.root / "Body.ib").write_bytes(struct.pack("<6H", 0, 1, 2, 2, 1, 0))
        header = bytearray(148)
        header[:4] = b"DDS "
        struct.pack_into("<I", header, 4, 124)
        struct.pack_into("<2I", header, 12, 32, 64)
        struct.pack_into("<I", header, 28, 7)
        header[84:88] = b"DX10"
        struct.pack_into("<I", header, 128, 98)
        (self.root / "Body #1.dds").write_bytes(header)

    def test_source_and_order_preserved_with_counts(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        result = inspect_mod.snapshot(self.root)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})
        self.assertEqual([], result["warnings"])
        ini = result["inis"]["Venti.ini"]
        self.assertIn("\r\n", ini["text"])
        sections = [s for s in ini["sections"] if s["name"] == "TextureOverrideBody"]
        self.assertEqual(2, len(sections))
        self.assertEqual(["CommandListOne", "CommandListTwo"],
                         [r["value"] for r in sections[0]["statements"] if r.get("key") == "run"])
        self.assertEqual(["if $state == 1", "else", "endif"],
                         [r["control"] for r in sections[0]["statements"] if "control" in r])
        resources = {r["section"]: r for r in result["resources"]}
        self.assertEqual(3, resources["ResourcePosition"]["buffer"]["element_count"])
        self.assertEqual(3, resources["ResourceBlend"]["buffer"]["element_count"])
        self.assertEqual({"format": "DXGI_FORMAT_R16_UINT", "count": 6, "trailing_bytes": 0,
                          "minimum": 0, "maximum": 2}, resources["ResourceIndices"]["indices"])
        image = result["files"]["Body #1.dds"]["image_header"]
        self.assertEqual((64, 32, 98), (image["width"], image["height"], image["dxgi_format"]))

    def test_observed_diff_is_narrow(self):
        new_root = self.base / "new"
        shutil.copytree(self.root, new_root)
        ini = new_root / "Venti.ini"
        ini.write_bytes(ini.read_bytes().replace(b"01234567", b"89abcdef"))
        (new_root / "Blend.buf").write_bytes(bytes([1]) + bytes(95))
        (new_root / "note.md").write_text("repair details", encoding="utf-8")
        difference = inspect_mod.compare(inspect_mod.snapshot(self.root), inspect_mod.snapshot(new_root))
        self.assertEqual(["Blend.buf", "Venti.ini"], [r["file"] for r in difference["changed"]])
        self.assertEqual(["note.md"], difference["added"])
        self.assertEqual(3, difference["unchanged_count"])
        self.assertIn("-hash = 01234567", difference["ini_diffs"]["Venti.ini"])
        self.assertIn("+hash = 89abcdef", difference["ini_diffs"]["Venti.ini"])

    def test_external_and_ambiguous_references_are_not_read(self):
        (self.base / "outside.buf").write_bytes(b"not mod data")
        (self.root / "linked.buf").symlink_to(self.base / "outside.buf")
        (self.root / "CASE.buf").write_bytes(b"a")
        (self.root / "case.buf").write_bytes(b"b")
        (self.root / "paths.ini").write_text(
            "[ResourceOutside]\nfilename = ../outside.buf\n"
            "[ResourceLink]\nfilename = linked.buf\n"
            "[ResourceCase]\nfilename = case.buf\n", encoding="utf-8")
        result = inspect_mod.snapshot(self.root)
        problems = {r["section"]: r["problem"] for r in result["resources"] if "problem" in r}
        self.assertIn("escapes", problems["ResourceOutside"])
        self.assertIn("symlink", problems["ResourceLink"])
        self.assertIn("Ambiguous", problems["ResourceCase"])
        self.assertNotIn("sha256", result["files"]["linked.buf"])
        self.assertNotIn("outside.buf", result["files"])

    def test_partial_index_and_stride_are_reported(self):
        (self.root / "Body.ib").write_bytes(b"\0\0\1")
        (self.root / "Blend.buf").write_bytes(bytes(97))
        result = inspect_mod.snapshot(self.root)
        resources = {r["section"]: r for r in result["resources"]}
        self.assertEqual(1, resources["ResourceIndices"]["indices"]["trailing_bytes"])
        self.assertEqual(1, resources["ResourceBlend"]["buffer"]["trailing_bytes"])
        self.assertEqual(2, len(result["warnings"]))

    def test_reports_cannot_overwrite_or_enter_source_root(self):
        result = inspect_mod.snapshot(self.root)
        with self.assertRaises(ValueError):
            inspect_mod.write_report(self.root / "report.json", result, (self.root,))
        self.assertFalse((self.root / "report.json").exists())
        target = self.base / "report.json"
        inspect_mod.write_report(target, result, (self.root,))
        original = target.read_bytes()
        with self.assertRaises(FileExistsError):
            inspect_mod.write_report(target, {"changed": True}, (self.root,))
        self.assertEqual(original, target.read_bytes())


class BlendTests(unittest.TestCase):
    def setUp(self):
        self.raw = (struct.pack("<4f4I", .5, .5, 0, 0, 4, 5, 0xffffffff, 99999)
                    + struct.pack("<4f4I", 0, .7, .2, 0, 0xffffffff, 6, 12, 0xdeadbeef)
                    + struct.pack("<4f4I", 1, 0, 0, 0, 0, 99999, 99999, 99999))
        self.spec = {"schema": 1, "direction": "old-to-new", "layout": remap_blend.LAYOUT,
                     "source_version": "fixture-old", "target_version": "fixture-new",
                     "source_sha256": hashlib.sha256(self.raw).hexdigest(), "target_bone_count": 117,
                     "old_to_new": {"0": 3, "4": 68, "5": 49, "6": 50, "12": 54},
                     "evidence": ["Synthetic regression fixture, not a production mapping"]}

    def test_only_weighted_index_words_change(self):
        output, receipt = remap_blend.remap(self.raw, self.spec)
        expected = (struct.pack("<4f4I", .5, .5, 0, 0, 68, 49, 0xffffffff, 99999)
                    + struct.pack("<4f4I", 0, .7, .2, 0, 0xffffffff, 50, 54, 0xdeadbeef)
                    + struct.pack("<4f4I", 1, 0, 0, 0, 3, 99999, 99999, 99999))
        self.assertEqual(expected, output)
        self.assertEqual(5, receipt["changed_slots"])
        self.assertEqual(5, receipt["weighted_slots"])
        self.assertFalse(receipt["weights_normalized"])
        self.assertLess(receipt["weight_sum_range"][0], 1)

    def test_wrong_or_already_remapped_input_rejected(self):
        output, _ = remap_blend.remap(self.raw, self.spec)
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            remap_blend.remap(output, self.spec)

    def test_incomplete_or_out_of_domain_mapping_rejected(self):
        bad = copy.deepcopy(self.spec)
        del bad["old_to_new"]["6"]
        with self.assertRaisesRegex(ValueError, "No verified mapping"):
            remap_blend.remap(self.raw, bad)
        for value in (117, -1, True):
            bad = copy.deepcopy(self.spec)
            bad["old_to_new"]["4"] = value
            with self.assertRaisesRegex(ValueError, "target bone domain"):
                remap_blend.remap(self.raw, bad)

    def test_invalid_layout_and_weights_rejected(self):
        bad = dict(self.spec, layout="not-confirmed")
        with self.assertRaisesRegex(ValueError, "32-byte"):
            remap_blend.remap(self.raw, bad)
        for raw in (self.raw[:-1], struct.pack("<f", float("nan")) + self.raw[4:]):
            bad = dict(self.spec, source_sha256=hashlib.sha256(raw).hexdigest())
            with self.assertRaises(ValueError):
                remap_blend.remap(raw, bad)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            json.loads('{"old_to_new":{"4":68,"4":49}}', object_pairs_hook=remap_blend.unique_pairs)

    def test_cli_preview_apply_and_overwrite_guards(self):
        with tempfile.TemporaryDirectory(prefix="blend-cli-test-") as directory:
            root = Path(directory)
            source, mapping = root / "source.buf", root / "mapping.json"
            source.write_bytes(self.raw)
            mapping.write_text(json.dumps(self.spec), encoding="utf-8")
            cmd = [sys.executable, "-B", str(SCRIPTS / "remap_blend.py"), str(source), "--mapping", str(mapping)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(json.loads(result.stdout)["preview_only"])
            self.assertEqual({"source.buf", "mapping.json"}, {p.name for p in root.iterdir()})
            output, receipt = root / "candidate" / "Blend.buf", root / "receipt.json"
            result = subprocess.run(cmd + ["--output", str(output), "--report", str(receipt)], capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(self.raw, source.read_bytes())
            self.assertEqual(remap_blend.remap(self.raw, self.spec)[0], output.read_bytes())
            self.assertFalse(json.loads(receipt.read_text())["preview_only"])
            result = subprocess.run(cmd + ["--output", str(output)], capture_output=True, text=True)
            self.assertNotEqual(0, result.returncode)
            another = root / "candidate2.buf"
            result = subprocess.run(cmd + ["--output", str(another), "--report", str(receipt)], capture_output=True, text=True)
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(another.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
