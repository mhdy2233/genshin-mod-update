# genshin-mod-reference-v2 数据格式

UTF-8 JSON，入口为 `index.json`。`format` 为 `genshin-mod-reference-v2`；它与游戏版本、资源修订分别记录。读取工具仍接受原 v1 数据。v2 增加原生资源图，并允许只有原生资料的角色将 `example_mod` 设为 `null`。

## 查找顺序

1. 核对 `target` 的平台、游戏版本、图形接口和三个资源 revision，读取 `coverage` 的实际范围。
2. `characters/<id>.json` 提供角色入口；`native_profiles` 指向本体、服装和形态的资料。`native/characters.tsv` 是可用表格软件阅读的总表。
3. `native/profiles/<id>.json` 列出实际提取到的 prefab 变体；按 `variant_suffix` 区分本体、`_Edit`、`_Remote`、`_Kanban`、`_Manekin`、`_Model` 等，不把它们当作相同渲染状态。
4. prefab 的 `mesh_ref`、`material_refs` 通过 `native.json.objects` 查找网格、材质、贴图或 Shader 引用。
5. 用 `files` 中的长度和 SHA256 检查所有文件。画面验收仍由目标客户端完成。

所有文件路径相对资料包根目录。`files` 列出除根索引本身外的完整文件集合；来源路径仅用于追溯，不要求接收机器拥有原游戏目录。

## 原生数据

| 文件或字段 | 含义 |
| --- | --- |
| `native.json` | 目标版本、profile 和对象索引、扫描结果、数量、解析状态及缺口 |
| `native/sources.json` | 每个 CAB 的安装块相对路径、段 offset/length、加密段及解包 CAB 的 SHA256、Unity 版本、平台码和外部引用表；Unity 内置文件单独记录完整文件摘要 |
| 原生对象 `id` | `cab-name:decimal-path-id`。PathID 以十进制字符串保存，避免 JavaScript 等环境丢失 64 位精度；它不是 GIMI 的 hash |
| `native/prefabs/*.json` | 实际对象名称、变体、Transform 的父子关系/局部位姿/完整名称路径、SkinnedMeshRenderer 的骨骼顺序和材质槽，以及静态 MeshFilter/LOD 网格引用 |
| `renderers[].bones/bone_names/bone_paths` | 同一骨骼槽的原始 PPtr、名称和层级路径，顺序完全一致。`PathID=0` 是空槽，名称/路径为 `null`，不能替换为骨骼 0 或删除槽位 |
| `native/meshes/*.json` | 原生网格名称、submesh、索引类型和范围、顶点通道/流、skin、bindpose、骨骼名称 hash、blendshape 和各字段字节范围 |
| `native/mesh-data/*.bin` | 未修改的单个 Unity 序列化 Mesh 对象，按原始 SHA256 去重；不是 Blender 文件，也不是可直接替换的 GIMI Position/Blend 文件 |
| `layout.*.offset/bytes/stride/count` | 数组 payload 在对应 `.bin` 中的字节起点、长度、元素步长和数量，offset 已跳过数组长度字段。均为小端，不能再加 4 |
| `layout.vertex_streams` | 每流的 stride、长度、相对 vertex_data 的偏移及相对原始 Mesh 的绝对偏移；流之间按本版的 16 字节规则排列。`channels` 给出实际格式及每通道偏移 |
| `layout.skin` | 每项 `float32[4]` 权重加 `uint32[4]` 骨骼索引，32 字节；`count=0` 表示该数组未提供权重，不能据此生成全零 skin |
| `layout.bindpose_matrices_row_major` | 本版原生 bindpose 的 16 个 float32 值，按行排列；与 renderer 的骨骼槽一同使用，不能代替旧版骨架 |
| `layout.submeshes[].first_index` | 从原生 `first_byte` 和 16/32 位索引格式换算；这是该 native Mesh 的分段，需先对应真实绘制对象，才能用于 GIMI 的 `match_first_index` |
| `native/materials/*.json` | Shader PPtr、keywords、队列、tags、禁用 pass、浮点/颜色属性、纹理属性/缩放/偏移，以及解析后的资源引用；未推导运行时的 D3D11 `ps-tN` 槽 |
| `native/textures/*.json` | Texture2D 的尺寸、格式、mip、颜色空间、过滤和资源位置等元数据。3 个 Cubemap 仅保存名称、类型、源摘要与引用，`header_fields_decoded=false`；不含像素 |
| `native/shader_references/*.json` | 材质引用到的 Unity Shader 对象 ID、类型和原始摘要；`compiled_code_included=false`。这些不是新增的 DXBC/ASM 程序 |
| `native/roster.json` | 本地社区服务端名录和已有中文名表的辅助映射及来源摘要。`AVATAR_FORMAL` 是名录字段，不是这次证明的可玩状态 |

`uninterpreted_trailer_hex` 原样保留已定位主体字段之后的字节。当前 SkinnedMeshRenderer 尾部 24 字节、部分内嵌图片后的 16 字节、LOD 组中未解释的字段均不伪造语义。

## 既有 GIMI 数据与历史对照

| 数据 | 用法和边界 |
| --- | --- |
| `characters[].game_draw_targets` | 仍是四个具名已验收 MOD 的 Position/Blend/Texcoord/IB/VertexLimitRaise hash、分段和材质调用。其他角色为空数组，`draw_hash_status=not_captured_on_target` |
| `example_mod.resources` | 特定 MOD 的资产摘要、stride/数量、索引范围、图片头；不是官方 Mesh 的通用数量 |
| `shaders.json`、`shaders/` | 1,102 份既有捕获汇编，ID 是 `stage:16位hash`，保留声明、纹理槽和常量布局 |
| `captures.json`、`captures/` | 5 帧/1,496 个原生 draw，保留绑定 hash、调用参数及源行；不完整模拟 MOD CommandList，四份重击/E 帧没有逐帧动作标签 |
| `effects/` | 21 条流浪者特效规则、纹理条件、匹配帧、替换与验收范围；静态条件回放不计算动态皮肤/全局开关 |
| `mappings/` | 一个受原始 Blend SHA256 限定的温迪映射；新增 native 骨架不会把它自动变成任意旧 MOD 都能使用的映射 |
| `prior-draws.json`、`prior-draws/` | 固定提交的 135 份社区 GIMI 表，源提交说明只到 6.7。查询结果始终附带来源版本和 `target_runtime_verified=false`，不能用包的 7.0 标签替它背书 |
| `game.json`、`catalogs/`、`libraries.json` | 既有安装清单、版本/本地二进制指纹、实际加载器与库源码。资源清单 hash、MD5、SHA256、Unity PathID、GIMI hash 各自独立 |

## 离线命令

`SKILL_DIR` 是接收机器上的技能路径，`PACK` 指向其版本数据目录。Python 3.11+ 标准库即可，无需游戏、网络、桌面、UnityPy 或解包工具。

```sh
python3 "$SKILL_DIR/scripts/reference_pack.py" verify "$PACK" --expect-version 7.0.0
python3 "$SKILL_DIR/scripts/reference_pack.py" show "$PACK" character ayaka
python3 "$SKILL_DIR/scripts/reference_pack.py" show "$PACK" profile ayaka
python3 "$SKILL_DIR/scripts/reference_pack.py" show "$PACK" native 'cab-name:decimal-path-id'
python3 "$SKILL_DIR/scripts/reference_pack.py" show "$PACK" prior-draw KamisatoAyaka
```

最后一个 native ID 是字段格式示意，应从所选 prefab 的 `mesh_ref` 或 `material_refs` 取真实 ID。`verify` 校验文件、对象引用、父子层级、骨骼顺序、bindpose 域、源 PPtr 以及既有特效条件；它不证明新 MOD 的画面效果。
