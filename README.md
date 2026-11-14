# 原神 MOD 适配、修复与跨平台修改技能

把完整的 `genshin-mod-upgrade` 技能安装到 Codex，即可让 agent 按目标版本适配旧 MOD，修复模型、材质和特效，或修改配色、透明度、部件与开关。调用名为 **`$genshin-mod-upgrade`**。

仓库包含技能说明、Python 工具、案例及完整的 **PC 7.0 离线参考资料**。没有安装游戏的机器也能在资料覆盖范围内制作候选 MOD；最终画面由目标客户端验收。

## 下载与安装

完整技能约 **1.29 GB（1.20 GiB）**，包含 11,206 个参考资料文件。全部文件直接保存在 Git 中，无需 Git LFS 或另外下载数据包。下载、解压和安装时建议预留 **4 GB** 空间。

### 让 Codex 安装

把下面这句话发给 Codex：

```text
使用 $skill-installer 安装 https://github.com/mhdy2233/genshin-mod-update/tree/main/genshin-mod-upgrade ，保留整个技能目录和 assets 资料。
```

也可以运行 Codex 自带的安装器。Linux / macOS / WSL：

```sh
python3 -X utf8 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo mhdy2233/genshin-mod-update \
  --path genshin-mod-upgrade
```

Windows PowerShell：

```powershell
$CodexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { "$HOME/.codex" }
python -X utf8 "$CodexRoot/skills/.system/skill-installer/scripts/install-skill-from-github.py" --repo mhdy2233/genshin-mod-update --path genshin-mod-upgrade
```

安装器需要 Python；技能工具要求 **Python 3.11+**。安装器会拒绝覆盖已有同名技能，已有安装的更新方法见下文。安装后在下一轮对话中调用 `$genshin-mod-upgrade`；客户端未刷新技能列表时，重新打开会话。

### 手动下载

1. 下载 [完整仓库 ZIP](https://github.com/mhdy2233/genshin-mod-update/archive/refs/heads/main.zip)，或执行 `git clone --depth 1 https://github.com/mhdy2233/genshin-mod-update.git`。
2. 将其中的 **`genshin-mod-upgrade` 整个目录**放入 `~/.codex/skills/`。Windows 对应 `%USERPROFILE%\.codex\skills\`；设置过 `CODEX_HOME` 时使用该目录下的 `skills/`。
3. 确认最终入口是 `skills/genshin-mod-upgrade/SKILL.md`，旁边有 `agents/`、`scripts/`、`references/` 和 `assets/`，没有多套一层仓库目录。

没有自带安装器时使用手动方式。其他支持 `SKILL.md` 的 agent 可按其技能目录规则安装同一个完整目录；脚本与资料本身不依赖 Codex API。

## 使用示例

提供原 MOD 路径、角色/服装、目标平台与版本，以及要修复的现象或修改目标：

```text
使用 $genshin-mod-upgrade，把 /path/to/old-mod 适配到国际服 PC 7.0.0 / GIMI。
先核对随技能提供的版本资料，在独立目录输出修改后的 MOD、差异和验证记录。
```

```text
使用 $genshin-mod-upgrade，把这个 MOD 的攻击特效改成暗红色，保留原透明度和衣服配色。
```

```text
使用 $genshin-mod-upgrade，检查这份 iOS 流浪者 MOD 的披风错图，结合原生材质和贴图身份制作修复候选。
```

| 能力 | 当前范围 |
| --- | --- |
| PC 版本适配 | GIMI/3DMigoto 的 INI、绘制范围、缓冲区、骨骼映射和材质绑定 |
| 定向修改 | 配色、贴图、材质、部件/选项、几何、透明双面及攻击/技能特效 |
| 离线资料 | PC `OSRELWin7.0.0`、国际服、D3D11，res/data revision `47194594` |
| Android 转换 | 提供检查/转换/包校验入口；已校准银狼刻晴与黑红流浪者，实际转换另需目标工作区与工具链 |
| iOS 修改 | 提供原生资源、披风错图及 Metal/AIR 特效流程与已验收案例；实际构建另需 iOS 输入和后端 |

移动端依赖与源码获取见 [GitHub 工作区说明](genshin-mod-upgrade/references/github-workspace.md)。技能不会把 PC 数据当成 Android/iOS 原生资源，也不会把历史映射套到任意版本。

## 随包资料

完整覆盖与缺口以 [index.json](genshin-mod-upgrade/assets/reference-data/pc-osrelwin-7.0.0-r47194594-d3d11/index.json) 和 [离线资料指南](genshin-mod-upgrade/references/reference-data.md) 为准：

- 131 个角色／模型条目、161 组服装/变体，3,110 个原生 Mesh。
- 1,034 个 prefab 的骨骼与层级、825 个材质、纹理元数据；不含纹理像素。
- 1,102 份捕获 Shader、5 帧/1,496 个 draw、21 条流浪者特效规则。
- 温迪、刻晴、胡桃、流浪者四个已验收配置；135 份历史社区表的来源说明只到 6.7，不能视作 7.0 实测 hash。

这里的覆盖数量不是全角色、全动作的画面验收。原 MOD、游戏本体、移动端原生资源及加载器安装包需按任务另行提供。

## 验证安装

Linux / macOS / WSL 可执行：

```sh
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/genshin-mod-upgrade"
PACK="$SKILL_DIR/assets/reference-data/pc-osrelwin-7.0.0-r47194594-d3d11"
python3 -X utf8 -B "$SKILL_DIR/scripts/reference_pack.py" verify "$PACK" --expect-version 7.0.0
python3 -X utf8 -B "$SKILL_DIR/scripts/reference_pack.py" show "$PACK" character ayaka
```

Windows 使用 `python -X utf8 -B`，把两个路径替换成实际安装目录。`verify` 校验文件集合、SHA256、对象引用、骨骼/网格边界和既有特效证据，不需要游戏或网络。

开发者可在仓库根目录运行现有工具回归：

```sh
python3 -X utf8 -B -m unittest discover -s genshin-mod-upgrade/scripts -p 'test_*.py' -v
```

## 更新与回退

更新前将旧 `genshin-mod-upgrade` 目录移到 `skills/` **之外**备份，再按安装步骤获取新版本并运行完整资料校验。备份保留在扫描目录之外，可避免旧技能被重复发现；若要回退，将新目录移出，再放回旧目录。

使用 Git 下载的仓库先执行 `git pull --ff-only`，然后按同样方法替换安装副本。不要仅覆盖 `SKILL.md` 或混合两版 `assets/`，否则资料索引与文件摘要可能不一致。安装器也支持 `--ref <提交号>` 固定到指定版本。

## 来源与发布记录

方法、工具和案例整理自维护者的 `yuanshen` 工作区。公开技能内已保留案例说明，使用 PC 工具与随包资料无需访问原工作区。资料包的 `sources.json`、`native/sources.json` 和 `prior-draws.json` 保留原生对象、文件摘要、社区来源与固定提交；原作者署名和已有许可随原文件保留，TexFx 的许可见包内 `libraries/TexFx/LICENSE`。各来源材料的权利归原作者或相应权利人。

本次整理、验证范围和维护步骤见 [PUBLISHING.md](PUBLISHING.md)，机器可读结果见 [verification.json](verification.json)。
