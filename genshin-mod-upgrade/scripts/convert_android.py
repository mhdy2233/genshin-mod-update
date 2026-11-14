#!/usr/bin/env python3
"""Convert calibrated PC MOD profiles with the workspace's verified Android backend."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

from inspect_mod import compare, snapshot

SKILL = Path(__file__).resolve().parents[1]
GAME = "7.0.0_47144228_47194594"
LOADER = "0.4.3"
FORMAT = "luna-android-mod-v1"
MAX_FILE, MAX_TOTAL, MAX_MANIFEST = 128 * 1024**2, 512 * 1024**2, 2 * 1024**2
PROFILES = {
    "keqing-silverwolf": {
        "character": "Keqing", "folder": "KeqingSilverWolf-7.0.0-android",
        "inis": {"Keqing.ini": "b21ad950ba417f3c9dc719b3c04ad0d64fc420e6c7bf228f4730afc2b0be0920"},
        "extras": ["KeqingHeadDiffuseKQ.dds", "KeqingBodyDiffuse no badge.dds"],
        "credit_files": ["README.txt", "Keqing.txt", "7.0.0-适配说明.md"],
        "credit": "模型与贴图来自指定的银狼刻晴 PC MOD，原始说明附后。",
    },
    "wanderer-blackred": {
        "character": "Wanderer", "folder": "WandererBlackRed-7.0.0-android",
        "inis": {
            "Wanderer.ini": "28a46a4b2b9df824bfafb85ea50b3acbce2933ab688f799df8baa1248d97cc01",
            "WandererFX.ini": "abcd04fbc6a17c9bf03cf3e0a889297665b2d6ef989972bef542259dd52410bf",
        },
        "extras": [], "credit_files": ["Wanderer.txt", "7.0.0-特效适配说明.md"],
        "credit": "原模型署名：M Anggiar Mustofa / Impact Teyvat。\n"
                  "https://www.youtube.com/channel/UC19KZfU5hO0siK6y_zfJJSA\n"
                  "原署名图片保留在 PC 输入目录。",
    },
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def put(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def calibrated_input(source, profile):
    record = snapshot(source, "pc-to-android input")
    if set(record["inis"]) != set(profile["inis"]):
        raise ValueError("INI 集合不属于此校准预设；先按 pc-to-android.md 适配，不能忽略额外 INI")
    for name, expected in profile["inis"].items():
        if record["files"][name]["sha256"] != expected:
            raise ValueError(f"{name} 与校准配置不同；需核对其语义并更新适配，不能直接套用预设")
    if record["warnings"]:
        raise ValueError("输入盘点存在问题：" + json.dumps(record["warnings"][:4], ensure_ascii=False))
    for name in profile["extras"]:
        if record["files"].get(name, {}).get("kind") != "file":
            raise ValueError("缺少已校准选项资源：" + name)
    return record


def environment(workspace, tools, character):
    work = workspace / "client-v3/mod-manager-v3"
    if tools is None:
        tools = Path(json.loads((work / "build/environment.json").read_text())["temporary_root"])
    tools = tools.resolve()
    research = work / "research/native-packages-20261109"
    pc = SKILL / "assets/reference-data/pc-osrelwin-7.0.0-r47194594-d3d11"
    required = [work / "tools" / name for name in
                ("convert_native_packages.py", "verify_native_packages.py", "port_wanderer_fx.py")]
    required += [research / "android-native/native.json", research / "android-native/native/sources.json",
                 research / "android-scan/cabs", work / "module/assets/templates/body-diffuse.cab",
                 pc / "native.json", tools / "venv/bin/python", tools / "AnimeStudio",
                 tools / "libooz.so", tools / "libtexture-host.so"]
    if character == "Wanderer":
        required += [tools / "texfx-tools/libsmolv.so", tools / "texfx-tools/libsmolv-legacy.so",
                     tools / "android-ndk-r27c/shader-tools/linux-x86_64/spirv-val"]
    missing = [str(path) for path in required if not path.exists()]
    missing += [name for name in ("java", "javac") if shutil.which(name) is None]
    if missing:
        raise ValueError("缺少转换数据或工具；见 pc-to-android.md 的环境恢复说明：" + ", ".join(missing))
    native = json.loads((research / "android-native/native.json").read_text())
    if native.get("platform") != 13 or native.get("version") != GAME:
        raise ValueError("安卓原生资料与此预设的目标版本不匹配")
    location = json.loads((work / "research/texfx/shader-location.json").read_text())
    if not (workspace / location["block"]).is_file():
        raise ValueError("缺少已校准的 Blb3 封装模板源块：" + location["block"])
    check = subprocess.run([str(tools / "venv/bin/python"), "-c", "import UnityPy; from PIL import Image"],
                           capture_output=True, text=True)
    if check.returncode:
        raise ValueError("转换 venv 缺少依赖：" + check.stderr[-1500:])
    return work, tools, pc


def verify_archive(path):
    """Check the actual Android importer's ZIP envelope; native object checks run separately."""
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if not names or names[0] != "manifest.json" or len(names) != len(set(names)):
            raise ValueError("ZIP 必须以 manifest.json 开头且不能有重复条目")
        if any(entry.is_dir() for entry in entries) or entries[0].file_size > MAX_MANIFEST:
            raise ValueError("ZIP 存在目录条目或清单过大")
        manifest = json.loads(archive.read("manifest.json"))
        if (manifest.get("format") != FORMAT or manifest.get("gameVersion") != GAME
                or manifest.get("character") not in {"Keqing", "Wanderer"}
                or manifest.get("packageVersion") != 1 or manifest.get("fxPending")):
            raise ValueError("清单目标不匹配，或特效转换尚未完成")
        resources = manifest["resources"]
        if not 1 <= len(resources) <= 256:
            raise ValueError("资源数量超出加载器范围")
        declared, total = set(), 0
        for row in resources:
            name = row["file"]
            if not re.fullmatch(r"assets/[a-z0-9-]+\.blk", name) or name in declared:
                raise ValueError("无效或重复资源路径：" + name)
            declared.add(name)
            size = row["bytes"]
            if (type(size) is not int or not 0 < size <= MAX_FILE or row["type"] not in (21, 28, 43)
                    or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])):
                raise ValueError("资源记录无效：" + name)
            total += size
            if total > MAX_TOTAL or archive.getinfo(name).file_size != size:
                raise ValueError("资源长度不符或总量超限：" + name)
            with archive.open(name) as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != row["sha256"]:
                    raise ValueError("资源摘要不符：" + name)
        extras = set(names) - declared - {"manifest.json"}
        if extras - {"README.md", "conversion.json"}:
            raise ValueError("ZIP 含加载器不支持的清单外文件")
        for name in extras:
            if archive.getinfo(name).file_size > MAX_MANIFEST:
                raise ValueError("附属记录过大：" + name)
            archive.read(name)
    return {"character": manifest["character"], "title": manifest["title"], "game_version": GAME,
            "resources": len(resources), "effects": len(manifest.get("effects", [])),
            "bytes": path.stat().st_size, "sha256": digest(path),
            "zip_crc_and_resource_hashes_verified": True, "runtime_verified": False}


def readme(source, profile, manifest):
    lines = [f"# {manifest['title']} · 安卓专用包", "", f"目标：{GAME}，默认服装；MOD 管理器 {LOADER} 或更高版本。",
             "本次生成包已做离线转换与资源检查，实际画面仍需在目标客户端验收。", "",
             "将 .lunamod 放到 MOD 目录，刷新后导入并启用；之后可直接启用已导入的包，恢复用对应角色的原装按钮。", "",
             "## 内容", ""]
    for row in manifest["renderers"]:
        if row.get("mesh", -1) >= 0:
            lines.append(f"- {row['name']}：{row['vertices']} 顶点，{row['boneCount']} 骨骼。")
    for row in manifest.get("options", []):
        lines.append(f"- {row['label']}：{' / '.join(row['values'])}。")
    lines += ["", *manifest["limitations"], *manifest.get("technicalNotes", []), "", "## 来源与署名", "", profile["credit"]]
    for name in profile["credit_files"]:
        path = source / name
        if path.is_file():
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            fence = "`" * max(3, 1 + max((len(m[0]) for m in re.finditer(r"`+", text)), default=0))
            lines += ["", "### 原始说明：" + name, "", fence + "text", text, fence]
    result = "\n".join(lines) + "\n"
    if len(result.encode()) > MAX_MANIFEST:
        raise ValueError("署名/说明超过加载器 README 大小限制；请先整理原始说明")
    return result


def convert(args, before, work, tools, pc):
    profile = PROFILES[args.profile]
    output = args.output.resolve()
    source = Path(before["root"])
    if output.is_relative_to(source):
        raise ValueError("输出必须位于 PC MOD 输入目录之外")
    output.mkdir(parents=True, exist_ok=False)
    evidence = output / "evidence"
    evidence.mkdir()
    put(evidence / "input-before.json", before)

    def run(name, script, arguments):
        print(name, flush=True)
        command = [str(tools / "venv/bin/python"), "-B", str(work / "tools" / script), *map(str, arguments)]
        with (evidence / (name + ".log")).open("w") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f"{name} 失败；原始输出见 {evidence / (name + '.log')}")

    run("geometry-textures", "convert_native_packages.py", ["--tools", tools, "--output", output,
        "--character", profile["character"], "--source", source, "--report", evidence / "segments.json"])
    folder = output / profile["folder"]
    if profile["character"] == "Wanderer":
        run("wanderer-fx", "port_wanderer_fx.py", ["--tools", tools, "--package", folder,
            "--report-dir", evidence / "fx"])
    run("native-verification", "verify_native_packages.py", ["--tools", tools, "--packages", output,
        "--pc-reference", pc, "--report", evidence / "native-verification.json"])
    after = snapshot(source, "after conversion")
    put(evidence / "input-after.json", after)
    changes = compare(before, after)
    put(evidence / "input-diff.json", changes)
    if any(changes[key] for key in ("added", "removed", "changed")):
        raise ValueError("转换期间 PC 输入发生变化；候选未封装，请检查输入和差异回执")
    manifest = json.loads((folder / "manifest.json").read_text())
    (folder / "README.md").write_text(readme(source, profile, manifest))
    temporary = output / (profile["folder"] + ".lunamod.partial")
    with zipfile.ZipFile(temporary, "x", zipfile.ZIP_DEFLATED) as archive:
        for name in ["manifest.json", "README.md", "conversion.json"] + [r["file"] for r in manifest["resources"]]:
            archive.write(folder / name, name)
    checked = verify_archive(temporary)
    artifact = temporary.with_suffix("")
    temporary.rename(artifact)
    receipt = {**checked, "profile": args.profile, "artifact": str(artifact), "source": str(source),
               "required_manager_version": LOADER, "source_inputs_unchanged": True,
               "native_verification": str(evidence / "native-verification.json"),
               "backend_sha256": {name: digest(work / "tools" / name) for name in
                   ("convert_native_packages.py", "port_wanderer_fx.py", "verify_native_packages.py")}}
    put(output / "delivery.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "convert"):
        child = commands.add_parser(command)
        child.add_argument("--profile", choices=PROFILES, required=True)
        child.add_argument("--source", type=Path, required=True)
        child.add_argument("--workspace", type=Path, required=True)
        child.add_argument("--tools", type=Path, help="Defaults to the workspace build/environment.json tool root")
        if command == "convert":
            child.add_argument("--output", type=Path, required=True, help="New directory outside the PC input")
    commands.add_parser("verify").add_argument("package", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "verify":
            result = verify_archive(args.package)
        else:
            profile = PROFILES[args.profile]
            before = calibrated_input(args.source, profile)
            work, tools, pc = environment(args.workspace.resolve(), args.tools, profile["character"])
            result = ({"profile": args.profile, "source": before["root"], "source_files": len(before["files"]),
                       "game_version": GAME, "required_manager_version": LOADER, "tools": str(tools), "ready": True}
                      if args.command == "check" else convert(args, before, work, tools, pc))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, RuntimeError, zipfile.BadZipFile) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
