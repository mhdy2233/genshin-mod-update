#!/usr/bin/env python3
"""Portable reference-reader regression tests using tiny synthetic files."""
import json
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
from reference_pack import FORMAT, NATIVE_FORMAT, ReferencePack, sha256


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mod-reference-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "pack"
        self.root.mkdir()
        self.target = {"platform": "PC", "game_version": "7.0.0", "graphics_api": "D3D11"}
        (self.root / "program.asm").write_text("ps_5_0\ndcl_temps 1\nret\n")
        (self.root / "example.ini").write_text("[TextureOverrideBody]\nhash=01234567\n")
        self.shader_id = "ps:0123456789abcdef"
        self.write("game.json", {"target": self.target, "catalogs": {}})
        self.write("libraries.json", {"files": {}})
        self.write("shaders.json", {"items": {self.shader_id: {
            "stage": "ps", "hash": "0123456789abcdef", "path": "program.asm",
            "sha256": sha256(self.root / "program.asm")}}})
        self.frame = {"id": "frame", "complete": True, "draws": [
            {"draw": 1, "ps": self.shader_id, "pixel_textures": {"0": "abcdef01"}},
            {"draw": 2, "ps": self.shader_id, "pixel_textures": {"0": "abcdef02"}},
            {"draw": 3, "ps": "ps:ffffffffffffffff", "pixel_textures": {"0": "abcdef01"}},
        ]}
        self.write("frame.json", self.frame)
        self.write("captures.json", {"items": {"frame": {"path": "frame.json", "draw_count": 3}}})
        self.write("character.json", {"id": "venti", "bone_mapping": "mapping.json", "example_mod": {
            "ini": "example.ini", "ini_sha256": sha256(self.root / "example.ini")}})
        self.write("mapping.json", {"direction": "old-to-new", "source_sha256": "a" * 64,
                                    "target_bone_count": 3, "old_to_new": {"1": 2}})
        self.write("effect.json", {"id": "example", "character": "venti", "example_ini": "example.ini",
                                   "shared_filter_dependencies": {}, "rules": [{
                                       "id": self.shader_id, "source_shader_sha256": sha256(self.root / "program.asm"),
                                       "texture_clauses": [{"0": "abcdef01"}], "matching_capture_draws": {"frame": [1]}}]})
        self.index = {"format": FORMAT, "id": "test", "target": self.target, "coverage": {},
                      "documents": {key: key + ".json" for key in ("game", "libraries", "shaders", "captures")},
                      "characters": {"venti": "character.json"}, "effects": {"example": "effect.json"},
                      "mappings": {"example": "mapping.json"}}
        self.reindex()

    def write(self, name, data):
        (self.root / name).write_text(json.dumps(data) + "\n")

    def reindex(self):
        self.index["files"] = {p.name: {"bytes": p.stat().st_size, "sha256": sha256(p)}
                               for p in self.root.iterdir() if p.is_file() and p.name != "index.json"}
        self.write("index.json", self.index)

    def test_portable_query_and_binding_selection(self):
        pack = ReferencePack(self.root)
        result = pack.verify("7.0.0")
        self.assertTrue(result["passed"])
        self.assertEqual(1, result["effect_rules_replayed"])
        self.assertEqual("venti", pack.show("character", "venti")["id"])
        self.assertEqual("program.asm", pack.show("shader", self.shader_id)["path"])

    def test_wrong_version_and_format_rejected(self):
        with self.assertRaisesRegex(ValueError, "Version mismatch"):
            ReferencePack(self.root).verify("7.1.0")
        self.index["format"] = "unknown-v2"
        self.write("index.json", self.index)
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            ReferencePack(self.root)

    def test_changed_program_rejected(self):
        (self.root / "program.asm").write_text("ps_5_0\ndiscard_nz r0.x\nret\n")
        with self.assertRaisesRegex(ValueError, "integrity mismatch"):
            ReferencePack(self.root).verify()

    def test_rehashed_but_inconsistent_binding_rejected(self):
        self.frame["draws"][0]["pixel_textures"]["0"] = "00000000"
        self.write("frame.json", self.frame)
        self.reindex()
        with self.assertRaisesRegex(ValueError, "draw selection mismatch"):
            ReferencePack(self.root).verify()

    def test_paths_cannot_escape_pack(self):
        outside = self.base / "outside.asm"
        outside.write_text("not part of this pack")
        (self.root / "external.asm").symlink_to(outside)
        self.reindex()
        with self.assertRaisesRegex(ValueError, "external"):
            ReferencePack(self.root).verify()
        with self.assertRaisesRegex(ValueError, "Invalid pack path"):
            ReferencePack(self.root).path("../outside.asm")

    def test_unknown_character_is_not_substituted(self):
        process = subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).with_name("reference_pack.py")),
                                  "show", str(self.root), "character", "ayaka"], capture_output=True, text=True)
        self.assertEqual(2, process.returncode)
        self.assertIn("ayaka", json.loads(process.stderr)["error"])
        self.assertEqual("", process.stdout)

    def test_invalid_mapping_range_rejected(self):
        mapping = json.loads((self.root / "mapping.json").read_text())
        mapping["old_to_new"]["1"] = 3
        self.write("mapping.json", mapping)
        self.reindex()
        with self.assertRaisesRegex(ValueError, "out of range"):
            ReferencePack(self.root).verify()

    def add_native_fixture(self):
        self.index["format"] = NATIVE_FORMAT
        identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        binary = struct.pack("<16f", *identity) * 2 + struct.pack("<4f4I", 1, 0, 0, 0, 1, 0, 0, 0) + struct.pack("<2I", 1, 2)
        (self.root / "mesh.bin").write_bytes(binary)
        self.native_mesh = {"id": "cab-test:10", "kind": "native_mesh", "source_cab": "cab-test", "parsed": True,
                            "raw_binary": "mesh.bin", "raw_sha256": sha256(self.root / "mesh.bin"), "raw_bytes": len(binary),
                            "layout": {"bindposes": {"offset": 0, "bytes": 128, "count": 2, "stride": 64},
                                       "bindpose_matrices_row_major": [identity, identity],
                                       "bone_hashes": {"offset": 160, "bytes": 8, "count": 2, "stride": 4},
                                       "bone_name_hashes": [1, 2], "weighted_bone_indices": [1],
                                       "skin": {"count": 1, "offset": 128, "bytes": 32, "stride": 32},
                                       "indices": {"count": 0, "offset": 168, "bytes": 0, "stride": 1},
                                       "vertex_data": {"count": 0, "offset": 168, "bytes": 0, "stride": 1}}}
        self.write("native-mesh.json", self.native_mesh)
        pointer = lambda ident: {"file_id": 0, "path_id": str(ident)}
        self.native_prefab = {"profile": "ayaka", "source_cab": "cab-test", "transforms": {
            "1": {"name": "root", "parent": pointer(0), "children": [pointer(2)], "path_components": ["root"]},
            "2": {"name": "hand", "parent": pointer(1), "children": [], "path_components": ["root", "hand"]}},
            "renderers": [{"mesh": pointer(10), "mesh_ref": "cab-test:10", "materials": [], "material_refs": [],
                           "bones": [pointer(1), pointer(2)], "bone_names": ["root", "hand"],
                           "bone_paths": [["root"], ["root", "hand"]]}],
            "static_mesh_filters": [], "lod_mesh_groups": []}
        self.write("native-prefab.json", self.native_prefab)
        self.write("native-profile.json", {"id": "ayaka", "character_id": "ayaka", "prefabs": [{"path": "native-prefab.json"}]})
        self.write("native-sources.json", {"items": {"cab-test": {"platform": 19, "externals": []}}})
        self.write("roster.json", {"avatars": []})
        self.write("prior-record.json", [{"position_vb": "12345678"}])
        self.write("prior-draws.json", {"repository": "https://example.invalid/pinned-source", "commit": "a" * 40,
                                         "claimed_game_release": "up to 6.7", "7_0_live_verified": False,
                                         "files": [{"name": "Ayaka", "sha256": sha256(self.root / "prior-record.json")}],
                                         "items": {"Ayaka": "prior-record.json"}})
        self.write("native.json", {"target": self.target, "platform_code": 19, "sources": "native-sources.json",
                                    "roster": "roster.json", "profiles": {"ayaka": {"path": "native-profile.json"}},
                                    "objects": {"cab-test:10": {"kind": "mesh", "path": "native-mesh.json", "parsed": True}}})
        self.write("ayaka.json", {"id": "ayaka", "example_mod": None, "bone_mapping": None,
                                   "native_profiles": {"ayaka": "native-profile.json"}})
        self.index["characters"]["ayaka"] = "ayaka.json"
        self.index["native_profiles"] = {"ayaka": "native-profile.json"}
        self.index["documents"].update({"native": "native.json", "prior_draws": "prior-draws.json"})
        self.reindex()

    def test_native_query_preserves_provenance(self):
        self.add_native_fixture()
        pack = ReferencePack(self.root)
        self.assertEqual(1, pack.verify()["native_renderers_verified"])
        self.assertIsNone(pack.show("character", "ayaka")["example_mod"])
        self.assertEqual("mesh.bin", pack.show("native", "cab-test:10")["raw_binary"])
        self.assertFalse(pack.show("prior-draw", "Ayaka")["target_runtime_verified"])
        self.assertEqual("up to 6.7", pack.show("prior-draw", "Ayaka")["claimed_game_release"])

    def test_rehashed_native_bone_order_rejected(self):
        self.add_native_fixture()
        self.native_prefab["renderers"][0]["bone_names"].reverse()
        self.write("native-prefab.json", self.native_prefab)
        self.reindex()
        with self.assertRaisesRegex(ValueError, "bone order mismatch"):
            ReferencePack(self.root).verify()

    def test_rehashed_native_bindpose_domain_rejected(self):
        self.add_native_fixture()
        mesh = self.native_mesh["layout"]
        mesh["bindposes"].update(count=1, bytes=64)
        mesh["bindpose_matrices_row_major"].pop()
        mesh["weighted_bone_indices"] = [0]
        self.write("native-mesh.json", self.native_mesh)
        self.reindex()
        with self.assertRaisesRegex(ValueError, "bindpose domains differ"):
            ReferencePack(self.root).verify()

    def test_native_null_bone_slot_is_preserved(self):
        self.add_native_fixture()
        renderer = self.native_prefab["renderers"][0]
        renderer["bones"][1]["path_id"] = "0"
        renderer["bone_names"][1] = renderer["bone_paths"][1] = None
        self.write("native-prefab.json", self.native_prefab)
        self.reindex()
        self.assertTrue(ReferencePack(self.root).verify()["passed"])

    def test_nested_prior_draw_variant_cannot_be_lost(self):
        self.add_native_fixture()
        prior = json.loads((self.root / "prior-draws.json").read_text())
        prior["files"].append({"name": "Ayaka/Coat", "sha256": prior["files"][0]["sha256"]})
        self.write("prior-draws.json", prior)
        self.reindex()
        with self.assertRaisesRegex(ValueError, "omitted or merged source variants"):
            ReferencePack(self.root).verify()


if __name__ == "__main__":
    unittest.main(verbosity=2)
