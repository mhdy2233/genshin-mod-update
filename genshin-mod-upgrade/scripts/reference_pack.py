#!/usr/bin/env python3
"""Read and verify portable MOD reference data; requires no game or GUI."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

FORMAT = "genshin-mod-reference-v1"
NATIVE_FORMAT = "genshin-mod-reference-v2"


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class ReferencePack:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        self.index = json.loads((self.root / "index.json").read_text())
        if self.index.get("format") not in (FORMAT, NATIVE_FORMAT):
            raise ValueError("Unsupported reference format")

    def path(self, relative):
        name = PurePosixPath(relative)
        if name.is_absolute() or ".." in name.parts or "\\" in relative:
            raise ValueError(f"Invalid pack path: {relative}")
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root) or relative not in self.index["files"]:
            raise ValueError(f"Unlisted or external pack file: {relative}")
        return path

    def read(self, relative):
        return json.loads(self.path(relative).read_text())

    def document(self, name):
        return self.read(self.index["documents"][name])

    def show(self, kind, ident):
        if kind == "shader":
            return self.document("shaders")["items"][ident]
        if kind == "native":
            return self.read(self.document("native")["objects"][ident]["path"])
        if kind == "prior-draw":
            source = self.document("prior_draws")
            return {"id": ident, "repository": source["repository"], "commit": source["commit"],
                    "claimed_game_release": source["claimed_game_release"],
                    "target_runtime_verified": source["7_0_live_verified"],
                    "records": self.read(source["items"][ident])}
        return self.read(self.index[{"character": "characters", "effect": "effects", "mapping": "mappings",
                                     "profile": "native_profiles"}[kind]][ident])

    def verify_native(self):
        native = self.document("native")
        if native["target"] != self.index["target"] or native["platform_code"] != 19:
            raise ValueError("Native asset target differs from index")
        sources = self.read(native["sources"])["items"]
        for source in sources.values():
            platforms = (5, 19) if source.get("source_kind") == "installed_unity_builtin" else (19,)
            if source["platform"] not in platforms:
                raise ValueError("Native source platform mismatch")
        self.read(native["roster"])
        objects = {}
        for ident, entry in native["objects"].items():
            value = self.read(entry["path"])
            if value["id"] != ident or value["source_cab"] not in sources:
                raise ValueError("Native object identity or source mismatch")
            if value["kind"] != "native_" + entry["kind"] or value["parsed"] != entry["parsed"]:
                raise ValueError("Native object kind or parse status mismatch")
            if entry["kind"] == "mesh":
                binary = value["raw_binary"]
                self.path(binary)
                meta = self.index["files"][binary]
                if meta["sha256"] != value["raw_sha256"] or meta["bytes"] != value["raw_bytes"]:
                    raise ValueError("Native mesh payload mismatch")
                if value["parsed"]:
                    mesh = value["layout"]
                    if (mesh["bindposes"]["count"] != len(mesh["bindpose_matrices_row_major"])
                            or mesh["bone_hashes"]["count"] != len(mesh["bone_name_hashes"])):
                        raise ValueError("Native bone table length mismatch")
                    for field in ("vertex_data", "indices", "skin", "bindposes", "bone_hashes"):
                        span = mesh[field]
                        if span["offset"] < 0 or span["bytes"] < 0 or span["offset"] + span["bytes"] > value["raw_bytes"]:
                            raise ValueError("Native mesh byte range outside object")
                        if span["count"] * span["stride"] != span["bytes"]:
                            raise ValueError("Native mesh element count mismatch")
                    if any(i < 0 or i >= mesh["bindposes"]["count"] for i in mesh["weighted_bone_indices"]):
                        raise ValueError("Native weighted bone index out of range")
            objects[ident] = value

        def require(ident, kind):
            if ident is not None and (ident not in native["objects"] or native["objects"][ident]["kind"] != kind):
                raise ValueError(f"Native {kind} reference mismatch: {ident}")

        def pointer_ref(cab, pointer):
            if pointer["path_id"] == "0":
                return None
            if not 0 <= pointer["file_id"] <= len(sources[cab]["externals"]):
                raise ValueError("Native pointer file ID out of range")
            target = sources[cab]["externals"][pointer["file_id"] - 1] if pointer["file_id"] else cab
            return target + ":" + pointer["path_id"]

        for ident, value in objects.items():
            if value["kind"] == "native_material" and value["parsed"]:
                mat = value["material"]
                require(mat["shader_ref"], "shader_reference")
                if mat["shader_ref"] != pointer_ref(value["source_cab"], mat["shader"]):
                    raise ValueError("Native material shader pointer mismatch")
                for texture in mat["textures"]:
                    require(texture["texture_ref"], "texture")
                    if texture["texture_ref"] != pointer_ref(value["source_cab"], texture["pointer"]):
                        raise ValueError("Native material texture pointer mismatch")
        prefabs_seen, renderers = set(), 0
        for ident, relative in self.index["native_profiles"].items():
            profile = self.read(relative)
            if profile["id"] != ident or native["profiles"][ident]["path"] != relative:
                raise ValueError("Native profile identity mismatch")
            for item in profile["prefabs"]:
                prefab = self.read(item["path"])
                if prefab["profile"] != ident or prefab["source_cab"] not in sources:
                    raise ValueError("Native prefab owner or source mismatch")
                if item["path"] in prefabs_seen:
                    continue
                prefabs_seen.add(item["path"])
                nodes = prefab["transforms"]
                for node_id, node in nodes.items():
                    path, seen, cursor = [], set(), node_id
                    while cursor != "0":
                        if cursor in seen or cursor not in nodes:
                            raise ValueError("Native transform parent cycle or missing node")
                        seen.add(cursor)
                        path.append(nodes[cursor]["name"])
                        cursor = nodes[cursor]["parent"]["path_id"]
                    if list(reversed(path)) != node["path_components"]:
                        raise ValueError("Native transform path mismatch")
                    for child in node["children"]:
                        if child["file_id"] or nodes[child["path_id"]]["parent"] != {"file_id": 0, "path_id": node_id}:
                            raise ValueError("Native transform parent/child mismatch")
                for renderer in prefab["renderers"]:
                    renderers += 1
                    require(renderer["mesh_ref"], "mesh")
                    if renderer["mesh_ref"] != pointer_ref(prefab["source_cab"], renderer["mesh"]):
                        raise ValueError("Native renderer mesh pointer mismatch")
                    for pointer, ref in zip(renderer["materials"], renderer["material_refs"], strict=True):
                        require(ref, "material")
                        if ref != pointer_ref(prefab["source_cab"], pointer):
                            raise ValueError("Native renderer material pointer mismatch")
                    expected_names, expected_paths = [], []
                    for pointer in renderer["bones"]:
                        node = nodes[pointer["path_id"]] if pointer["path_id"] != "0" else None
                        expected_names.append(node["name"] if node else None)
                        expected_paths.append(node["path_components"] if node else None)
                    if expected_names != renderer["bone_names"] or expected_paths != renderer["bone_paths"]:
                        raise ValueError("Native renderer bone order mismatch")
                    mesh = objects.get(renderer["mesh_ref"])
                    if mesh and mesh["parsed"] and mesh["layout"]["skin"]["count"]:
                        if len(renderer["bones"]) != mesh["layout"]["bindposes"]["count"]:
                            raise ValueError("Native renderer and bindpose domains differ")
                for item in prefab["static_mesh_filters"]:
                    require(item["mesh_ref"], "mesh")
                for item in prefab["lod_mesh_groups"]:
                    for ref in item["mesh_refs"]:
                        require(ref, "mesh")
        for ident in self.index["characters"]:
            character = self.show("character", ident)
            for profile_id, relative in character.get("native_profiles", {}).items():
                if self.index["native_profiles"].get(profile_id) != relative or self.read(relative)["character_id"] != ident:
                    raise ValueError("Character native profile ownership mismatch")
        prior = self.document("prior_draws")
        names = [item["name"] for item in prior["files"]]
        if len(names) != len(set(names)) or set(names) != set(prior["items"]):
            raise ValueError("Prior draw index omitted or merged source variants")
        for item in prior["files"]:
            relative = prior["items"][item["name"]]
            self.read(relative)
            if self.index["files"][relative]["sha256"] != item["sha256"]:
                raise ValueError("Prior draw source digest mismatch")
        return {"native_objects_verified": len(objects), "native_prefabs_verified": len(prefabs_seen),
                "native_renderers_verified": renderers}

    def verify(self, expected_version=None):
        target = self.index["target"]
        if expected_version and target["game_version"] != expected_version:
            raise ValueError(f"Version mismatch: pack={target['game_version']}, requested={expected_version}")
        actual = {p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file()}
        if actual != set(self.index["files"]) | {"index.json"}:
            raise ValueError("Pack file set differs from index")
        for name, meta in self.index["files"].items():
            path = self.path(name)
            if not re.fullmatch(r"[0-9a-f]{64}", meta["sha256"]):
                raise ValueError(f"Invalid digest: {name}")
            if path.stat().st_size != meta["bytes"] or sha256(path) != meta["sha256"]:
                raise ValueError(f"File integrity mismatch: {name}")
        for name in self.index["documents"]:
            self.document(name)
        if self.document("game")["target"] != target:
            raise ValueError("Game target differs from index")
        for name in self.document("game")["catalogs"].values():
            self.read(name)
        for name in self.document("libraries")["files"].values():
            self.path(name)
        shaders = self.document("shaders")["items"]
        for ident, shader in shaders.items():
            if ident != shader["stage"] + ":" + shader["hash"]:
                raise ValueError(f"Shader identity mismatch: {ident}")
            if self.index["files"][shader["path"]]["sha256"] != shader["sha256"]:
                raise ValueError(f"Shader digest mismatch: {ident}")
            self.path(shader["path"])
        captures = {}
        for ident, entry in self.document("captures")["items"].items():
            frame = self.read(entry["path"])
            numbers = [draw["draw"] for draw in frame["draws"]]
            if frame["id"] != ident or not frame["complete"] or len(numbers) != entry["draw_count"] or len(set(numbers)) != len(numbers):
                raise ValueError(f"Invalid capture: {ident}")
            captures[ident] = frame
        for ident in self.index["characters"]:
            character = self.show("character", ident)
            if character["id"] != ident:
                raise ValueError("Character identity mismatch")
            example = character["example_mod"]
            if example:
                ini = example["ini"]
                if self.index["files"][ini]["sha256"] != example["ini_sha256"]:
                    raise ValueError(f"Character INI digest mismatch: {ident}")
                self.path(ini)
            elif not character.get("native_profiles"):
                raise ValueError("Character has no example or native assets")
            if character["bone_mapping"]:
                self.read(character["bone_mapping"])
        rules_checked = 0
        for ident in self.index["effects"]:
            effect = self.show("effect", ident)
            self.path(effect["example_ini"])
            if effect["id"] != ident or effect["character"] not in self.index["characters"]:
                raise ValueError("Effect identity or owner mismatch")
            for dependency in effect["shared_filter_dependencies"].values():
                if self.index["files"][dependency["path"]]["sha256"] != dependency["sha256"]:
                    raise ValueError("Shared library digest mismatch")
            for rule in effect["rules"]:
                if shaders[rule["id"]]["sha256"] != rule["source_shader_sha256"]:
                    raise ValueError("Effect source shader mismatch")
                selected = {}
                for frame_id, frame in captures.items():
                    numbers = [draw["draw"] for draw in frame["draws"] if draw["ps"] == rule["id"] and any(
                        all(draw["pixel_textures"].get(slot) == value for slot, value in clause.items())
                        for clause in rule["texture_clauses"])]
                    if numbers:
                        selected[frame_id] = numbers
                if selected != rule["matching_capture_draws"]:
                    raise ValueError(f"Effect draw selection mismatch: {rule['id']}")
                rules_checked += 1
        for ident in self.index["mappings"]:
            mapping = self.show("mapping", ident)
            if mapping["direction"] != "old-to-new" or not re.fullmatch(r"[0-9a-f]{64}", mapping["source_sha256"]):
                raise ValueError("Invalid mapping scope")
            if not all(0 <= int(value) < mapping["target_bone_count"] for value in mapping["old_to_new"].values()):
                raise ValueError("Mapping target out of range")
        native_result = self.verify_native() if self.index["format"] == NATIVE_FORMAT else {}
        return {"passed": True, "id": self.index["id"], "target": target,
                "files_verified": len(self.index["files"]), "effect_rules_replayed": rules_checked,
                "runtime_test_performed": False, "coverage": self.index["coverage"], **native_result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("pack", type=Path)
    verify.add_argument("--expect-version")
    summary = commands.add_parser("summary")
    summary.add_argument("pack", type=Path)
    show = commands.add_parser("show")
    show.add_argument("pack", type=Path)
    show.add_argument("kind", choices=["character", "shader", "effect", "mapping", "profile", "native", "prior-draw"])
    show.add_argument("id")
    args = parser.parse_args()
    try:
        pack = ReferencePack(args.pack)
        if args.command == "verify":
            result = pack.verify(args.expect_version)
        elif args.command == "summary":
            result = {key: pack.index[key] for key in ("id", "target", "coverage", "characters", "effects", "mappings")}
        else:
            result = pack.show(args.kind, args.id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
