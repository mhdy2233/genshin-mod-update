# PC 原神 7.0 离线 MOD 参考数据

目标：`OSRELWin7.0.0` / D3D11，res/data revision `47194594`，silence revision `46814653`。格式为 `genshin-mod-reference-v2`。

本版从安装文件提取了 **131 个角色／模型条目，连同服装共 161 组**，包括 1,034 个 prefab、3,110 个 Mesh、825 个 Material、1,587 个 Texture2D 的元数据和 3 个 Cubemap 引用。网格保存原始序列化二进制及可读布局；骨骼记录顺序、名称、层级和 bindpose。

先读 [index.json](index.json) 的 target/coverage，再查看 [角色总表](native/characters.tsv)、[原生资源索引](native.json) 和 [字段格式](FORMAT.md)。目录可以随技能复制到无游戏环境；查询只依赖 Python 标准库。

原有 4 个已验收 MOD 配置、1,102 份捕获 Shader、5 帧/1,496 个 draw 和 21 条流浪者特效规则全部保留。67 个新增原生 Shader 引用仅记录身份和摘要，不是额外的汇编。

新增原生资料没有增加游戏实测范围，也没有为所有角色生成已验证的 GIMI 绘制 hash。另附固定提交的 135 份社区 hash 表，其源说明只到 6.7，读取时保留这一版本限制。原生分段和骨架可用于比较；旧 MOD 到新骨架的映射仍需对应旧输入。

131 条中有 120 条与本地服务端 `AVATAR_FORMAL` 的角色名称对应，另外 11 条为剧情、特殊形态或其他模型。该名录中的 `MannequinBoy`、`MannequinGirl`、`Vesna`、`Vodyanitsa` 尚未对应到同名客户端 prefab；这不等于证明客户端没有别名资源。贴图像素、所有动作的实际绘制和新增 Shader 字节码未包含。

`examples/` 只含配置参考，不是可安装 MOD。所有文件和原始资料来源有摘要；修改候选后仍需在目标客户端验收。
