---
name: genshin-mod-upgrade
description: "适配、修复和修改 PC、Android、iOS 原神 MOD，包括几何/材质、披风错图、配色/透明和攻击特效；支持已校准 PC→安卓转换及 iOS 原生资源与 Metal 特效修复流程。按目标加载器和资源链验证。启动器、登录及服务端故障不属于本技能。"
---

# 原神 MOD 适配、修复与跨平台修改

调用名继续使用 `$genshin-mod-upgrade`。交付符合用户目标、有依据且可回退的 MOD：PC/Android/iOS 版本适配、外观/特效修改，或 PC→移动端资源转换。用户只要求同平台改色、部件或效果时，沿用当前客户端；不自动扩展为跨平台转换。

GitHub 安装版携带完整 PC 离线资料。安装、更新及移动端后端/输入的获取方式见 [GitHub 工作区说明](references/github-workspace.md)；原案例路径是来源坐标，接收机器使用自己的工作区与工具目录。

## 先确定任务和平台

| 任务 | 工作重点 | 阅读材料 |
| --- | --- | --- |
| 同为 PC，旧 MOD 适配新版原神/GIMI | 资源匹配、绘制范围、缓冲区容量、骨骼索引、材质槽和库调用 | [PC 差异定位与修改](references/pc-migration.md) |
| 同版本故障修复或定向修改 | 按目标调整贴图配色、材质、部件/选项、几何或透明双面；先定位负责的资源和绘制 | [MOD 定向修改](references/mod-editing.md)，涉及 PC 几何/材质时按需读 PC 参考 |
| PC 攻击/技能特效失效、部分失效或改色 | 动作与 draw 对应、Shader/纹理/常量、作用范围、ShaderRegex 与库冲突 | [PC 特效修改与修复](references/pc-effects.md) |
| 明确要求 PC MOD 转安卓、制作 `.lunamod` | 原生资料对照、预设适用性、外部转换、独立封装与加载器兼容 | [PC→安卓转换](references/pc-to-android.md)；内含检查/转换/校验入口，以及新增角色的接入流程 |
| Android MOD 修改或客户端升级 | 资源封装、Mesh/Material/Shader 布局、贴图格式、运行时接口及对象生命周期 | [安卓资源与修改](references/android-migration.md)；不把 PC Shader 文件直接当安卓补丁 |
| iOS MOD 错图、披风/材质或攻击特效修复；PC→iOS 资源适配 | 原生对象身份、共享引用、材质状态、Metal/AIR 程序及 R8 资源路由 | [iOS 原生 MOD 与特效](references/ios-mods.md)；已验收的固定流浪者流程见案例，自动安卓入口不支持 iOS |
| 无游戏环境、或需要已提取的目标版本资料 | 先核对资料包的 target/coverage，按角色读取原生网格、骨架、材质和捕获证据 | [离线版本资料](references/reference-data.md)，当前附 PC 7.0 原生角色/服装资料及四个已验收 MOD 配置 |
| 需要已留证的案例 | 温迪几何/材质适配；PC 流浪者 ShaderRegex 排错；iOS 流浪者披风与 Metal 特效实机通过 | [温迪案例](references/venti-case.md) · [PC 流浪者特效](references/wanderer-fx-case.md) · [iOS 披风与特效](references/ios-wanderer-cape-fx-case.md) |

只读取当前任务需要的分支。普通 PC 工作不自动启动安卓移植；游戏尚未正常进场时，先区分启动故障与 MOD 问题。修改技能自身不构成修改其他 MOD、驱动、网络或服务端的授权。

## 执行顺序

1. **固定基线与目标。**核实实际启用目录、角色/皮肤、客户端版本/修订、平台与加载器/扩展库。记录用户要恢复的行为或要改成的效果，以及适用部件/动作；版本迁移再补旧版信息。保存原包与 SHA256，识别已有修改、映射和禁用副本。已有信息先核实，缺少会改变实现的要求才问。
2. **定位控制点。**修复用真实异常与有效目标的对照；定向修改用用户目标决定设计，用资源和绘制证据决定改哪里。按需检查 hash/分段、buffer/骨骼、纹理通道、材质/pass、Shader 与条件变量。不要把“想改成暗红”写成发现了原作者的历史色值，也不要因没有换版差异就停止修改。
3. **实施独立候选。**在已有授权内完成修改，不停留在方案或分析。优先调整现有配置、资源或输出中足够实现目标的位置；需要改贴图/几何时修改对应资产并记录。保留原件和未受影响内容；正常皮肤仅特效有问题时，沿特效链处理，不顺带重映射骨骼或修正常材质。没有新证据不重复批量修复器。
4. **验证实际行为。**文件/格式与加载器语法→真实对象或 draw 命中→目标画面。运行中配置重载与对象创建是两回事，按实际机制选热重载或重新创建。只改 RGB 时检查原 alpha；修改透明度则检查其目标 alpha、混合、深度与描边。按变化验证开关恢复、其他绘制或重建状态，不重复已经通过且未改变的测试。用户明确反馈通过时，将反馈、对应交付版和范围登记为用户实机验收；保留原构建回执，不因缺少新日志把已通过的结果重新列为待测，也不扩展成全部动作/档位通过。
5. **同步交付。**保存候选目录或用户所需包、可读 diff、文件摘要、依据、已做/未做的测试及回退方法。核对实际启用文件、压缩包内容、说明和交付回执属于同一版；诊断结束后按本轮差异撤回临时设置并保留证据。界面“已应用”、构建成功或 DLL 加载都不能替代画面验收。

PC→安卓优先复用已验证的外部转换核心。自动入口目前覆盖银狼刻晴与黑红流浪者的固定配置及同结构资源变体；其它角色或 INI 语义先按转换参考补齐适配，不能只改角色名或给 PC 文件改扩展名。新生成包保持待实机验证状态，不继承示例包的画面验收结论。

iOS 分支使用本平台原生资源和 Metal 程序；同名 `.lunamod` 扩展名不代表与安卓清单、加载器或 Shader 通用。当前 iOS 流浪者披风与攻击特效有用户实机验收，复用时按案例核对源身份和依赖；技能内的 PC 数据包不包含 iOS 原生资源及 LLVM 工具链。

遵守项目规则及会话已有授权；“只分析”就只分析，已同意的修复或修改不逐步骤重复索要同意。项目禁止子代理或要求用户完成触摸/游戏前台操作时照做。用户暂缓的细节保持暂缓。

## 无游戏环境

先使用随技能提供或用户提供的[版本资料包](references/reference-data.md)，以及待修 MOD 本身；不把“本机未安装游戏”当作不能进行文件修改的理由。PC 7.0 的 v2 数据可按角色→服装/变体→renderer→mesh/material 查到原生网格、骨骼顺序/层级和材质属性。资料足够就制作离线候选，资料不足则列出缺失的目标资源/捕获。

原生资源数据、已验收 GIMI 配置和历史社区表有不同的证据范围：新增骨架不自动产生任意旧 Blend 的映射；原生 PathID、文件摘要也不是 GIMI 绘制 hash。随包的历史 hash 表只注明到 6.7，不因放进 7.0 包就变成 7.0 实测值。示例 MOD 顶点数与原生 Mesh 顶点数分别存放，画面验收由目标游戏机器完成。

## 快速定位

| 现象 | 优先取证 | 不能直接下的结论 |
| --- | --- | --- |
| 完全不生效、只少一个部件 | 当前实际启用目录、include、hash命中、IB起始索引、条件变量、互斥MOD | 一定要重新做模型 |
| 爆点、拉丝、四肢扭曲 | buffer stride/数量、draw越界、输出顶点扩容、非零权重索引、映射方向 | 顶点比官方多就是错误；通用remap一定不对 |
| 模型正确但白色/黄绿色/反光错乱 | 法线贴图是否存在、Diffuse/LightMap/NormalMap真实槽位、旧MetalMap/ShadowRamp、当前ORFix/NNFix | 先重画DDS或再改骨骼 |
| 披风/帽子采样了身体图集，静态指针看似正确 | 目标图像摘要、材质与贴图对象名称、真实槽位、性能属性与关键词一致性；iOS 按原生分支检查 | 贴图一定缺失；指针存在就证明运行时采样正确；所有同名对象都必须重命名 |
| 皮肤正常，攻击没变色或只有普攻生效 | 各动作实际 PS、纹理组合、资源创建时机、激活条件；先区分规则未命中与输出不符 | 整个角色需要 NNFix；一个 PS 或纹理代表所有动作 |
| F10 报错或改色影响了其他效果 | 最新重载段的解析/组装错误、重复 hash、过滤标记、namespace/参数槽及共享 Shader 条件 | 提高优先级消音；只要正则匹配就代表可加载 |
| iOS FX 只改部分效果或程序阶段错配 | 实际材质关键词、LightMode/空名称 pass、primary/additional 程序表及 AIR vertex/fragment 元数据 | 额外表索引可当 primary 使用；包能解析就覆盖所有图形档位 |
| 要改配色、部件或透明度而非换版本 | 目标区域/选项、通道用途、绘制分段、实际 pass 与保存状态 | 必须升级游戏、重做模型或修改所有相关贴图 |
| 初次生效，传送/重启后失效 | 新renderer/material身份、已保存配置、材质槽数、纹理读回及重建补绑 | 仍显示“已应用”就代表新对象正常 |

## 可执行工具

盘点、remap 和资料包脚本使用 Python 3.11+ 标准库；`SKILL_DIR` 表示本 skill 实际目录。给路径加引号，不拼接执行 INI 中的命令。

```sh
python3 "$SKILL_DIR/scripts/inspect_mod.py" snapshot /path/to/original-mod --output /path/to/evidence/original.json --label original
python3 "$SKILL_DIR/scripts/inspect_mod.py" snapshot /path/to/candidate-mod --output /path/to/evidence/candidate.json --label candidate
python3 "$SKILL_DIR/scripts/inspect_mod.py" compare /path/to/evidence/original.json /path/to/evidence/candidate.json --output /path/to/evidence/diff.json
```

`inspect_mod.py`输出文件摘要、INI原文和有序语句、资源引用、按声明stride计算的数量、R16/R32索引范围和DDS/PNG头部信息。它不执行条件或 CommandList，不推测新 hash，也不模拟加载器的 ShaderRegex 分段/组装；零盘点警告不代表特效 INI 合法。快照写在被检查目录之外，已有报表不覆盖；检查单个 MOD，不指向整个游戏安装。

骨骼remap使用[PC参考中的映射格式](references/pc-migration.md#4-骨骼映射及受控修改)，先生成预览，再明确输出独立文件：

```sh
python3 "$SKILL_DIR/scripts/remap_blend.py" /path/to/original/VentiBlend.buf --mapping /path/to/evidence/verified-map.json
python3 "$SKILL_DIR/scripts/remap_blend.py" /path/to/original/VentiBlend.buf --mapping /path/to/evidence/verified-map.json --output /path/to/candidate/VentiBlend.buf --report /path/to/evidence/remap.json
```

该工具只支持**已经确认的32字节小端布局：4个float32权重+4个uint32索引**，仅改非零权重对应的索引。必须匹配源SHA256，输出必须不存在；因此不会覆盖原件，也能拒绝对另一文件或已转换文件重复套表。它验证结构与映射范围，**不证明映射表的生物骨骼语义正确**。

详细的目标、修改和交付字段见[记录格式](references/migration-record.md)。上述脚本的回归可用`python3 "$SKILL_DIR/scripts/test_tools.py"`，不触及真实游戏，也不包含通用特效运行验收。

`scripts/reference_pack.py` 提供离线资料的 `verify`、`summary`、`show`，支持 v1/v2；`show` 可读取 character、profile、native、shader、effect、mapping 和 prior-draw。其标准库回归为 `scripts/test_reference_pack.py`。字段和命令见[离线版本资料](references/reference-data.md)，完整性检查不等于新候选已通过游戏测试。

`scripts/convert_android.py` 提供 `check`、`convert`、`verify`：检查校准配置与环境，调用本地转换/原生资源验证，输出可导入的 `.lunamod`、署名说明和回执。入口及 ZIP 校验使用标准库，实际转换需要目标工作区资料、UnityPy/Pillow、Java 和既有编码工具链；参数、支持范围、环境恢复与新角色接入见[PC→安卓转换](references/pc-to-android.md)。相关边界回归为 `scripts/test_android_conversion.py`。
