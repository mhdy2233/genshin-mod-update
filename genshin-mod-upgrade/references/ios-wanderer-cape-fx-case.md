# 已验收案例：iOS R8 流浪者披风与暗红攻击特效

适用于学习披风串图定位、共享资源身份和 iOS Metal 特效转换。一般流程见 [iOS 原生 MOD](ios-mods.md)，PC 的 ShaderRegex 案例见 [PC 流浪者特效](wanderer-fx-case.md)。本页的程序索引、对象名与数量属于此固定输入。

## 交付与验收身份

用户于 **2026-11-14** 反馈：“昨晚的披风修复和攻击特效通过了, 整理一下给 $genshin-mod-upgrade 技能升级”。据此登记披风修复、攻击特效为用户实机验收通过；反馈所指测试发生在前一晚，未提供逐动作、图形档位或新设备日志。

| 项目 | 已核对值 |
| --- | --- |
| 目标 | iOS 7.0.0 / build 1224，资源修订 47194594，R8 + LC1 + DATA1 完整 IPA |
| 主程序 UUID | `63993c95d3b238c0987912bce81270e9` |
| 包版本 / ID | `R8-WANDERER-CAPE-FX1-20261113.1` / `wandererblackred-7-0-0-ios-cape-fx1` |
| 文件 | `WandererBlackRed-7.0.0-ios-cape-fx1.lunamod`，12,858,981 bytes |
| 最终 SHA256 | `0b54f9a546d5adf0c8ee5ba0fffe4d9e4221817e5e937f6a2becbdd0b0780fd7` |
| 格式 | `luna-ios-mod-v1` / `shared-native-v1`，资源平台 9 |
| 来源 | PC 黑红流浪者外观，iOS shared1 为皮肤基线；Metal/材质/特效来自实际 iOS 资源 |

最终项目包与下载副本在技能升级时重新核对到同一大小/SHA256。旧名称修正前包的 `7a7e738b…` 不属于本次验收身份。构建回执中的待测字段保留当时事实，最新状态由 `receipts/user-acceptance-20261114.json` 与当前 `delivery.json` 记录；没有借用户反馈补造设备缓存摘要或新 PID。

## 披风：已有图像，新增对象身份与状态不完整

用户背面截图的格子、紫色挂饰和米色图案可对应 `WandererBodyDiffuse` 右半图集；PC 披风位于独立 Hat 网格，目标是 `WandererHatHeadDiffuse` 右半的长条纹样。两张图像在共享版里都存在，网格/UV 也无需重做。

最终同时做了三项修正：

1. Hat 专属材质从 Body 同名克隆改为 `Avatar_Boy_Catalyst_Wanderer_Mat_Hat_LunaBlackRed`，六种 Hat renderer 继续引用其独立 PathID。
2. Body/Hat 的 `_EnablePerformance` 设为 0，与已经移除的 `ENABLE_PERFORMANCE_ON` 一致；保留此前已校准的法线相关属性与关键词。
3. 十个贴图对象原来都叫 `Avatar_Boy_Catalyst_Wanderer_Tex_Hair_Diffuse`。保留原头发对象名，其余九个按 `LunaBlackRed_` 加输入文件 stem 命名，名称互不重复。

最终两张转换网格、骨骼、UV 和十份 ASTC 图像/mip 保持原字节。名称修正比上一候选仅增加 134 bytes，58 个 FX 资源文件逐字节复用；六种披风引用逐一从最终包读回。用户接受的是这组三项修正的结果，运行时究竟由哪条材质/纹理更新导致旧串图未单独证明。

## 攻击特效：私有 Metal 程序与公共材质

原 iOS 包明确保留原版攻击/技能特效，因此问题是尚未移植该功能。皮肤贴图修正不能补齐它。新包从 iOS 专属 FX prefab 进入，复制所需 Shader/材质为私有对象，定向改 renderer 指针。

| 范围 | 数量与结果 |
| --- | --- |
| 原始定位 | 58 个 prefab、569 个 renderer、137 份材质 |
| 实际改动 | 57 个 prefab、520 个 renderer、538 个材质槽 |
| 共享私有对象 | 13 个 Shader、128 份材质，各复制一次 |
| 全包 | 69 个资源；70 个内部节点通过原版名称解析 |
| 程序读回 | 2,151 个子程序，924 个改色 fragment 变体，去重后实际改写 618 份 Metal 程序 |
| 当前材质覆盖 | 57 套关键词，114 项 vertex/fragment 精确对照，包括空名称颜色 pass |

公共对象放入原 CAB `cab-07563548a90dc5800761fa9bff2b2470` 的新增 PathID，原对象保留；预制体以外部 FileID/PathID 引用并补齐预载表。原环模型表面、不可见触发器和扭曲材质保持原入口，官方共享 Shader 没有被全局改色。

暗红公式为 `max(original RGB) * (0.650, 0.008, 0.028)`。只改颜色 pass 的 fragment 颜色目标 0；从原返回向量插入 RGB 三项，保留 alpha、其它输出、原计算、材质参数/关键词、纹理及粒子动画。LLVM 14 保留 typed-pointer AIR、`air64-apple-ios11.0.0` 和 Metal 2.0 元数据；MTLB/AIR 包装的长度、SHA256 与私有程序缓存标记同步更新。

离线覆盖针对当前材质的 primary 变体。额外压缩变体未纳入，不能扩展为全部雾效、半分辨率/MSAA 与图形档位均已等效。用户反馈确认本次披风和攻击特效通过，没有逐项报告全部动作、原装恢复或长期运行。新角色/新包需要独立校准和验收。

## 已走过的错误路径

| 错误或观察 | 证据与修正 | 可复用判断 |
| --- | --- | --- |
| 静态 Hat 材质指针已存在，游戏仍串图 | 新增材质/十个贴图对象同名；性能属性与关键词不一致；联合修正后用户确认通过 | 指针、对象名、状态与像素一起查；无需重复改正常骨骼/UV |
| fragment 索引解析到 vertex | Liquid 的 additional 索引 13 被当作 primary，AIR 检查报 `Only fragment AIR may be tinted` | 按所属程序表解析，并核对真实阶段 |
| 覆盖统计漏掉颜色 pass | 只选择 `MAIN` 等名字会遗漏空名称；按实际 LightMode/输出检查后得到 114 项对照 | 检查必须有实际覆盖，不能空集通过 |
| 普攻第二段写外部引用失败 | 第一项是非零 GUID 的 `library/unity default resources` | 选本例适用的零 GUID/type 0 普通 CAB 模板，保留内置引用 |
| 更高版本 LLVM 改变 AIR 格式 | LLVM 19 将 typed pointer 升级为 opaque pointer | 使用已验证的 LLVM 14；版本按目标样本决定 |
| 把 class 200 当附加代码 | 实际是 ShaderVariantCollection | 先确认类型，不按文件所在 CAB 推断 |
| 旧 `.luna.resS` 能被自己的读取器解析却无法进场 | 原游戏 GUID 解析拒绝；规范 `.resS` 与完整 Texture2D 流路径同步后通过 | 最终消费端规则独立校验，外层 `.blk` 改名无效 |

## 原始证据与复现入口

工作区根目录相对路径为 `client-ios-v1/r8/fixes/wanderer-cape-fx-v1-20261113/`；源码获取及缺失输入见 [GitHub 工作区说明](github-workspace.md)。这是来源坐标，技能迁移到别处后不要将原主机绝对路径当成内置依赖。该目录中的关键文件：

- `README.md` / `INSTALL.md`：原诊断、输入来源、完整复现顺序和回退。
- `conversion-changes.patch` / `proposed-tools/shared_converter.py`：只针对流浪者的三项披风修正。正式 `r8/tools/shared_converter.py` 尚不含这组修正；复现时选已验收候选实现，不能只重跑正式旧入口。
- `tools/build-skin.py` → `tools/check-material-coverage.py` → `tools/build-wanderer.py` → `tools/verify-wanderer.py`：皮肤、程序覆盖、FX 构建和最终独立读回；`tools/metal_programs.py` 为 AIR 修改核心。
- `receipts/fx-assets.json` / `fx-shaders.json` / `material-primary-coverage.json`：实际源对象、程序和关键词覆盖。
- `receipts/texture-name-correction.json` / `failed-builds.json` / `engine-name-check.json`：名称保持对照、两次失败和原 ARM64 名称检查。
- `artifacts/verification.json` / `artifacts/wanderer-cape-fx-conversion.json`：构建时的完整离线结果；`receipts/user-acceptance-20261114.json`：后续用户实机通过。

工具使用 UnityPy 1.25.4、AnimeStudio/Ooz、已有 Shader 布局读写器和生产 C ZIP 读取器。本机保留环境在 `/tmp/luna-ios-r8-mod-guid-20261112`；LLVM 14 库在 `/tmp/luna-ios-air-20261113/llvm14/usr/lib/x86_64-linux-gnu/libLLVM-14.so.1`，SHA256 为 `ccce431f05a3d35ef57db281637506c793731c5b7ca08c7e0f6a7b5d5fdc97c7`。来源/恢复依据见本例 `receipts/llvm-toolchain.json` 和相邻 GUID1 目录的 `receipts/reader-source.json`。先确认 `/tmp` 文件仍存在，只恢复缺失依赖，不替换系统 LLVM。

这些构建脚本仍有指向原案例 `FIX/artifacts`、输入、回执的固定路径；仅传 `--output` 不能完整重定位所有阶段。重建前在独立副本中统一调整输入/输出/回执路径，保留已验收包。只有验证现存包时，可使用 `verify-wanderer.py --reader-tools <当前环境> --report <新的报告路径>`。技能整包只携带本页经验与原有 PC 数据，iOS 原生输入和上述工作区后端另行提供。

回退操作为在 R8 面板恢复流浪者原装或选择保留旧包，再完整退出游戏实例和 LiveContainer 后重开。本次技能整理不改变已验收包，也不将候选工具合入正式转换器。
