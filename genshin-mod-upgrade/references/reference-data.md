# 使用离线版本资料包

技能附带从本机 PC 7.0 安装、已验收 MOD 和真实采集记录提取的资料。整个技能目录可搬到无游戏、无桌面的机器，另行提供待修改 MOD 即可按覆盖范围制作离线候选。

入口：[PC 7.0 索引](../assets/reference-data/pc-osrelwin-7.0.0-r47194594-d3d11/index.json) · [资料说明](../assets/reference-data/pc-osrelwin-7.0.0-r47194594-d3d11/README.md) · [v2 字段格式](../assets/reference-data/pc-osrelwin-7.0.0-r47194594-d3d11/FORMAT.md) · [角色总表](../assets/reference-data/pc-osrelwin-7.0.0-r47194594-d3d11/native/characters.tsv)。

## 现有覆盖

目标为 `OSRELWin7.0.0`、国际服 PC、D3D11；res/data revision `47194594`，silence revision `46814653`。普通 CAB 平台码 19，随游戏附带的共享 Unity 内置资源码 5；两者均按其实际序列化布局读取。

| 数据 | 已提供的范围 |
| --- | --- |
| 角色与服装 | 131 个角色／模型条目，含服装共 161 组；既有温迪、刻晴、胡桃、流浪者配置继续保留 |
| 原生网格 | 3,110 个 Mesh，包含原始序列化二进制、顶点通道/流/stride/offset、索引/分段、权重、bindpose、骨骼 hash 和 blendshape |
| 原生骨架 | 1,034 个 prefab、196,835 个 Transform、7,466 个 SkinnedMeshRenderer 的骨骼顺序、名称、父子关系、局部位姿和资源引用 |
| 材质与纹理 | 825 个 Material 的属性及引用、1,587 个 Texture2D 的尺寸/格式/mip 等元数据、3 个 Cubemap 引用；不含像素 |
| Shader | 1,102 份既有捕获汇编：243 PS、166 VS、693 CS；另外 67 个原生 Shader 引用只记录身份和摘要 |
| 绘制与特效 | 流浪者相关的 5 份完整帧/1,496 个 draw，21 条黑红特效规则和原验收范围 |
| 匹配值 | 四个具名 MOD 的已验收配置，以及 135 份固定提交的历史社区表；社区源说明只到 6.7 |
| 安装与库 | 四份资源清单、版本/本地二进制指纹、实际 GIMI/ORFix 库源码和纹理标记声明 |

131 条中有 120 条与本地服务端正式角色名录同名，另外包含剧情/特殊形态模型。`MannequinBoy`、`MannequinGirl`、`Vesna`、`Vodyanitsa` 尚未对应到同名 prefab，不能据此断定不存在别名资源。完整名单和原始名录字段在包内。

新增资料来自安装提取，没有扩大游戏实测范围。全部动作的绘制 hash、材质运行时的 `ps-tN` 绑定、所有程序变体和新角色画面仍未全覆盖。既有捕获另缺 1 个 PS、2 个 VS 的代码；四份重击/E 帧未逐帧标注动作。

## 查询

先核对 `target/coverage` 并运行 `verify`，再按当前任务读取条目。`SKILL_DIR` 指接收机器上的实际技能目录；工具只用 Python 3.11+ 标准库，不访问导出机器路径或网络。

```sh
PACK="$SKILL_DIR/assets/reference-data/pc-osrelwin-7.0.0-r47194594-d3d11"
python3 "$SKILL_DIR/scripts/reference_pack.py" verify "$PACK" --expect-version 7.0.0
python3 "$SKILL_DIR/scripts/reference_pack.py" show "$PACK" character ayaka
python3 "$SKILL_DIR/scripts/reference_pack.py" show "$PACK" profile ayaka
python3 "$SKILL_DIR/scripts/reference_pack.py" show "$PACK" shader ps:b827bd6f4ca16989
python3 "$SKILL_DIR/scripts/reference_pack.py" show "$PACK" prior-draw KamisatoAyaka
```

从 profile 选择实际 prefab 变体，读取它的 `mesh_ref` 或 `material_refs`，再用 `show "$PACK" native '实际ID'` 查对应对象。对象 ID 是 `cab-name:十进制PathID`，不是 shader/GIMI hash。大文件按需读取，不将全部网格或程序一次装入上下文。

历史表保留上游目录层级；例如希诺宁外套使用 `prior-draw Xilonen/XilonenCoat`，滑轮使用 `prior-draw Xilonen/XilonenSkates`，与本体 `Xilonen` 分开查询。

## 用于修改

- **原生几何**：`raw_binary` 是单个未修改的序列化 Mesh。字段 offset 从该文件开头计算，并已跳过数组长度。结合 `vertex_streams` 和 `channels` 读取所需数据；不要把整份 `.bin` 直接当 GIMI Position/Blend 文件。
- **骨骼**：按所选 renderer 的骨骼槽顺序、完整路径与 Mesh 的 bindpose 对应。空 PPtr 保留为 `null`。新骨架可用于比较，但旧→新的索引映射仍需旧版/原 MOD 证据；现有温迪映射继续受原始 Blend SHA256 限定。
- **hash/分段**：`game_draw_targets` 仍只包含四个已验收配置。其他角色的 native 分段必须先对应到实际绘制对象；`prior-draw` 返回带来源版本的历史候选，不自动认可为目标值。原生数组的 CRC、PathID 和文件 SHA256 均不能直接代替 GIMI hash。
- **材质/配色**：native Material 提供属性、颜色、纹理和 Shader 关系；GIMI 的实际绑定顺序仍看对应 draw/程序/库。已有 NNFix 示例只适用于相应无法线贴图条件。
- **特效**：原有规则可用于继续制作候选，检查 PS、纹理条件及激活范围；新增角色身体资料不等于其全部攻击效果已捕获。

`example_mod.resources` 是该件 MOD 的数据，不是原生模型数量。`examples/` 仅含配置参考，不是可安装 MOD。资料足够时完成候选；缺少特定 draw/旧骨架时明确指出所缺项，画面由目标客户端验收。

## 格式与来源

v2 沿用原来版本、角色、Shader、捕获、映射的入口，并新增 `native_profiles` 和 `documents.native/prior_draws`。原生资料的来源包含块/段位置、段与 CAB 摘要、对象身份；原路径只是追溯提示。

读取工具兼容 v1/v2。新增版本应建立自己的包和来源，不通过改标签复用旧证据。少量未解释尾部原样保留在 `uninterpreted_trailer_hex`，不得自行假定其含义。
