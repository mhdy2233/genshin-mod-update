# GitHub 安装版与移动端工作区

技能仓库：[mhdy2233/genshin-mod-update](https://github.com/mhdy2233/genshin-mod-update)。安装、更新和回退见仓库 README；安装时保留完整 `genshin-mod-upgrade/`，包括 `assets/`。

## 安装后可直接使用

Python 3.11+ 标准库即可运行 `inspect_mod.py`、`remap_blend.py`、`reference_pack.py`，以及 `convert_android.py verify` 的 Android 包封装检查。PC 7.0 资料已经随包提供，不需要原作者的游戏目录或网络。骨骼 remap 仍须用户输入的 MOD 与经核对的映射。

Windows 执行脚本时使用 `python -X utf8`，或启用 Python UTF-8 模式，以正确读写含中文的路径和报告。

## Android / iOS 外部依赖

本公开技能提供移动端操作方法、案例和 Android 转换驱动，**不附移动端转换后端、原生输入与工具链**。实际转换需要用户提供已准备好的兼容工作区；只有 PC MOD 和本技能时，先进行盘点/差异定位，不能声称已经具备移动端构建环境。

原项目归档不保证对匿名用户开放，公开技能不依赖该仓库的访问权限。参考页中的 `client-v3/`、`client-ios-v1/` 等是已有工作区的相对布局，便于用户提供资料后核对，并非已安装到本技能里的文件。缺少后端时，应向该加载器/转换流程的提供者取得对应源码与输入，或另行实现适配；安装更多 Python 包不能替代这些源码和资源。

### Android

按 [PC→安卓转换](pc-to-android.md) 准备对应 `7.0.0_47144228_47194594` 的原生资料、模板和工具，然后运行 `convert_android.py check --workspace /path/to/yuanshen --tools /path/to/toolchain ...`。

已有后端位于工作区 `client-v3/mod-manager-v3/tools/`，至少包含 `convert_native_packages.py`、`verify_native_packages.py`、`port_wanderer_fx.py` 及它们导入的网格/资源布局工具。依赖含 UnityPy 1.25.4、Pillow、Java、AnimeStudio/Ooz、纹理编码器；流浪者 FX 另需对应 SMOL-V/SPIR-V 工具。以参考页和后端检查列出的实际文件为准，不能使用 PC 资料替代 Android 资料。历史环境路径仅用于追溯，接收机器使用自己的 `--workspace` / `--tools`。

### iOS

按 [iOS 原生 MOD](ios-mods.md) 与 [已验收披风/特效案例](ios-wanderer-cape-fx-case.md) 核对用户提供的 iOS 源对象及构建输入。案例源码在原工作区 `client-ios-v1/r8/fixes/wanderer-cape-fx-v1-20261113/`，未随公开技能附带；该目录下的候选工具包含三项已验收披风修正。

Metal/AIR 修改使用案例固定的 LLVM 14、UnityPy/AnimeStudio/Ooz 与资源布局工具。来源和摘要见案例 `receipts/llvm-toolchain.json`，原生读取器来源见相邻 GUID1 记录。原机 `/tmp` 路径不是下载地址；按回执恢复到接收机器实际路径。

iOS 案例构建器尚有固定工作区路径，需在独立副本中统一调整输入、输出和回执路径；它不是本技能内的通用一键转换器。仅改变输出参数不足以完成重定位。

## 资料不足时

先完成已有证据支持的盘点、差异定位和独立候选，说明具体缺少的版本、平台或对象；不凭相同角色名、扩展名或“7.0”标签自动替换原生资源。实际加载、选项/重建和画面验收由目标客户端完成，新生成包不继承示例包的实机结论。
