# PC MOD 转安卓专用包

适用：明确要求将PC GIMI/3DMigoto MOD转换为安卓资源，或维护转换器/安卓包。产物是加载器能识别的`.lunamod`，包含原生Mesh/Texture/Material/Shader资源与相对路径清单。PC INI用于解释作者意图；手机不会执行ShaderRegex或把BUF/DDS直接当原生资源加载。

本页依次说明自动预设、命令/环境、资源约定、新角色接入，以及已证实的运行时坑。

## 自动预设与边界

| 预设 | 当前支持内容 | 重要差异 |
| --- | --- | --- |
| `keqing-silverwolf` | 银狼刻晴：Body三段、脸部、发色/虹膜与徽章选项 | Position/Blend/Texcoord为40/32/20；按原生槽绑定Diffuse/LightMap，旧MetalMap/ShadowRamp不直接搬作纹理槽补丁 |
| `wanderer-blackred` | 黑红流浪者：Body、独立Hat、脸部及原包暗红FX适配 | Body为40/32/12，原生UV流36；保留颜色/UV0并为已验证材质变体补其余UV。帽子单独骨架；FX另转安卓程序 |

目标固定为Android原神`7.0.0_47144228_47194594`、v12基线，使用Luna MOD Manager **0.4.3或更高兼容版**。原生资料必须属于同一目标；不能只凭“7.0”替换修订或平台。

自动入口核对预设INI的完整SHA256及INI集合，允许同名、同结构BUF/IB/贴图资源变化，但不把新的条件、Shader、文件引用或额外INI当成已支持。配置不符时停止自动套用，按下文补适配；不要关闭检查来强行通过。现有预设是两套MOD的校准结果，不是任意刻晴/流浪者包的通用解释器。

原刻晴和流浪者皮肤已由用户确认加载正常；新转换候选仍标为`runtimeVerified=false`。FX已做离线程序/资源检查并有绑定事件，但各动作画面和完整生命周期没有全部验收。

## 可执行入口

`scripts/convert_android.py`为标准库驱动，复用目标工作区的已验证转换核心。无需先修改原PC目录，也不安装或操作手机。

```sh
python3 -B "$SKILL_DIR/scripts/convert_android.py" check \
  --profile keqing-silverwolf --source "/path/to/KeqingSilverWolf-7.0.0" \
  --workspace "/path/to/yuanshen"

python3 -B "$SKILL_DIR/scripts/convert_android.py" convert \
  --profile keqing-silverwolf --source "/path/to/KeqingSilverWolf-7.0.0" \
  --workspace "/path/to/yuanshen" --output "/path/to/new-keqing-output"

python3 -B "$SKILL_DIR/scripts/convert_android.py" convert \
  --profile wanderer-blackred --source "/path/to/WandererBlackRed-7.0.0" \
  --workspace "/path/to/yuanshen" --output "/path/to/new-wanderer-output"

python3 -B "$SKILL_DIR/scripts/convert_android.py" verify \
  "/path/to/new-wanderer-output/WandererBlackRed-7.0.0-android.lunamod"
```

输出目录必须新建且位于PC输入之外。`--tools /path/to/toolchain`可显式指定工具链；省略时读取工作区`client-v3/mod-manager-v3/build/environment.json`中的实际目录并检查存在性。同一工具目录按顺序转换，Java输出和纹理编码缓存是共享的。

`convert`顺序执行输入盘点、几何/纹理转换、流浪者FX转换、独立原生资源检查，再封装ZIP并校验。最后得到：

- `*-android/`：原生资源目录、manifest、转换记录和包含原作者声明的README。
- `*-android.lunamod`：清单置首、资源摘要匹配的成品候选。
- `evidence/`：输入前后快照/差异、转换日志、Blb3与原生检查、FX程序记录。
- `delivery.json`：精确路径/SHA256、目标版本、最低管理器版本、后端摘要和验证范围。

转换失败时保留当前独立输出的日志和中间证据，不覆盖原输入或旧成品；确认原因后使用新的输出目录。没有交付回执就不将中间目录作为完成的包交付。`verify`只做加载器ZIP封装、长度和SHA256校验；完整Mesh/Shader检查在`convert`内部，游戏效果还需客户端验收。

## 工作区和工具链

从 GitHub 安装后，按 [工作区与输入说明](github-workspace.md) 核对用户提供的后端源码和资料；本公开技能不附移动端后端、原生输入或工具链。

当前复用的后端在`client-v3/mod-manager-v3/tools/`：

- `convert_native_packages.py`支持`--source`与独立`--report`，不再要求输入固定在项目Mods目录。
- `port_wanderer_fx.py`支持`--report-dir`，完整转换已校准的暗红FX，不覆盖历史FX回执。
- `verify_native_packages.py`支持`--pc-reference`与`--report`，按本次输入路径核对真实几何/贴图/骨骼和源摘要。

后端依赖完整的目标工作区：`research/native-packages-20261109/android-native/`和`android-scan/cabs/`、现有Blb3/Texture模板、Shader布局工具，以及`shader-location.json`指向的原模板块。只需要该流程依赖的已提取资料，已有有效资料时不重新扫描全部游戏块。技能附带的PC参考包用于官方PC/Android对象对照，不能替代安卓资料。

工具链采用工作区下载/构建回执指定的版本，包括UnityPy 1.25.4、Pillow、AnimeStudio/ooz、Java、`libtexture-host.so`；FX还用旧SMOL-V编码器和SPIR-V校验器。依赖和固定来源见该工作区的`research/native-packages-20261109/tool-downloads.json`、`tool-environment.json`、`build/environment.json`。`/tmp`可能已清理，先核对实际文件，只恢复缺失部分；不把旧环境JSON当成工具仍存在的证据，也不默认安装全局依赖或搬到云端。

## 新角色或新配置接入

已有自动预设不适用时，继续以下资源适配工作；不通过更名或改哈希伪装成现有角色。

1. **证明目标原生链。**从目标安卓块提取角色/服装Prefab → Renderer → Mesh/骨架 → Material/Texture/Shader。保留CAB、PathID、原字节SHA和布局。PC资料包提供对照，实际安卓对象才决定目标；可参考工作区`scan_android.py`、`export_android.py`和`native_layout.py`的已有解析流程。
2. **解释PC配置。**使用`inspect_mod.py`盘点BUF/IB/DDS、所有INI和选项。记录每个部件、draw分段、贴图通道、透明/双面及FX条件；不运行INI中的命令。现有三个官方对象（刻晴Body、流浪者Body/Hat）PC与Android原始Mesh和骨骼顺序逐字节相同，这个结论不扩展到其它对象。
3. **适配几何。**核对Position/Texcoord stream、索引格式、submesh、权重和骨骼语义。保留作者位置/法线/切线/权重/索引和原生bindposes/骨骼顺序；非零权重索引必须在palette范围内。当前实现为R16、最多65,535顶点；其它布局先扩展适配。流浪者UV12→36仅适用于已核对的非打包法线变体，不能对新模型盲目复制UV或补零。
4. **适配材质和纹理。**以原生槽和Shader采样语义决定绑定。当前预设为最长边2048、保持比例、ASTC 6×6 RGBA及完整mip链；Diffuse用sRGB，LightMap/Normal线性。报告缩小/重压缩差异。透明、描边、双面、发光等另按真实pass适配，不能凭PC的NNFix/ORFix名称推断已等效。
5. **独立处理FX。**PC ShaderRegex/hash规则用于定位意图，不在安卓执行。已有流浪者流程按专属效果Prefab/材质做独立副本，RGB为`max(original RGB)*(0.650,0.008,0.028)`，保留alpha、扭曲向量及非目标表面。保留SPIR-V ID、GPU绑定尾表、pass元数据和正确SMOL-V版本；细节见[安卓资源参考](android-migration.md)。原包有FX时不默默交付只含皮肤的结果。
6. **同时接通加载器。**当前`luna-android-mod-v1`实现只接受Keqing/Wanderer。新增角色要补Java角色/清单解析、JNI/native目标归属、按角色状态、材质独占、原装恢复及重建补绑；生成新包本身不会让旧插件识别新角色。沿用已验证的转换核心和接口，完成角色校准后才把新预设加入自动入口。
7. **逐层验证并交付。**先做原样本往返与离线对象检查，再校验实际ZIP，最后验证加载、对应对象、用户画面、选项/FX/恢复和重建。实际授权了安装/ADB重启就沿用；未授权的设备动作不由转换技能隐含授权。将完成范围和未验收范围分开记在本轮文档。

## 包与运行时约定

ZIP首项必须是`manifest.json`；允许的其它非资源条目只有`README.md`和`conversion.json`，不放目录项或额外原PC文件。资源路径为`assets/[a-z0-9-]+.blk`，各项声明字节数、SHA256、类型和对象名；资源最多256项、单项128MiB、合计512MiB。完整字段以工作区`NativePackage.java`为准。

`firstBoneHash`记录骨骼名称数组第一项，根骨骼哈希是另一字段。Body与Hat可有不同骨架；材质可共享来源，但修改必须落到当前renderer独占副本。CAB和AssetBundle身份按内容独立生成，Texture的archive/resS路径必须同步；不要覆盖官方块或把主机绝对资源路径作为手机加载路径。

## 故障与验收记录

| 现象 | 本次已经证实的原因/处理 | 不能省略的边界 |
| --- | --- | --- |
| 刻晴-218 | 只读来源不应被owner一致性限制；名称需识别` (Instance) #数字`及已确认的重复后缀 | 继续核对角色、服装、基名、槽位和对象身份，不做任意前缀通配 |
| 同owner材质“复制”返回自身 | 本版接口存在直接返回源指针分支；创建新材质后复制属性/名称，并读回独立数据与owner | 不能原地改共享材质；接口地址只适用于已核对的引擎 |
| 流浪者-204 | 旧代码用Mesh+0xc0根哈希对比首哈希；本版骨骼数组指针/数量为+0x80/+0x90，0.4.3已修正 | 用具名序列化字段证明布局，保持包的正确骨骼顺序和值 |
| 重启后-220，手动应用曾有效 | 登录时预加载对象在角色出现前失效；0.5.2等待并在Unity tick刷新资源后自动补绑，详见[对象生命周期](android-migration.md) | 无角色的等待不是错误；区分对象身份失效与属性读回失败，重启测试必须进入角色场景且不点应用 |
| 切角色短暂错图；稍后紫/绿覆盖 | 原装Mesh恢复与临时Shader残留是两条不同路径；0.5.3保持Mesh，0.5.5在Shader切换后刷新独占副本，再重套MOD属性 | 关键字关掉不代表Shader已切回；对比默认角色与后来切出的角色，不凭颜色猜元素视野 |
| 流浪者FX无变化 | 复用池激活未经过初次材质解析；0.5.4增加激活绑定，并允许特效根正常换父 | 保留根名/相对路径/材质隔离，FX模板不能被皮肤Shader同步覆盖 |
| UI/旧status与真实结果不一致 | `waiting_for_engine`可能是启动快照；应核对新PID、实际插件版本、绑定与保存事件 | 不用安装成功、无负返回码或旧快照替代用户画面 |
| ADB不能读取导入缓存 | Android允许父目录列名但拒绝遍历私有包目录 | 用外部包SHA、应用自己的资源校验及运行证据；不宣称ADB私有缓存摘要已通过，也不为此擅自改权限 |

项目记录集中在`client-v3/mod-manager-v3/research/native-packages-20261109/`：`import-218-0401`、`import-218-0402`、`wanderer-204-0403`保留证据/差异/复现；`runs/20261110T072419+0800/skin-verification.json`保存两套皮肤与选择成功的早期记录。该阶段FX大量`owner_changed`没有获得完整动作/生命周期验收，后续结果不能倒填到早期回执。

重启-220的诊断与修复见同一工作区的`research/native-restart-220-20261110/`和`runs/20261110T115103+0800/automatic-restart-verification.json`：一次真实重启进场后，两角色共9个部件自动绑定成功，未手动应用。该结论只覆盖自动刷新与绑定；最终皮肤颜色、动作和FX仍按本轮画面证据单独判断。

后续`research/native-switch-material-20261110/`、`research/native-tint-fx-20261110/`、`research/native-material-residual-20261110/`依次记录Mesh即时保持、FX激活/关键字同步、Shader完整状态恢复。最终0.5.5/code41获用户“没问题了”确认；PID25060有54条Shader同步成功，原始选择保留。0.5.4的用户反馈确认当次流浪者皮肤和特效正常；不能扩大到全部动作、所有选项或长时联机。最终包、差异、踩坑、清理及已恢复的过渡期读回告警随`revisions/0.5.5/`与该轮回执保留。
