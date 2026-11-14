# 实例：旧神装温迪适配原神7.0

这是**2026-11-07～08的已留证案例**，用户称原MOD曾用于5.5；测试环境为PC原神7.0、GIMI8.9.2。以下hash/地址语义只对该次证据成立，使用其它角色、皮肤、客户端修订或后续版本时重新取证。案例没有附全量骨骼表，不能直接用作批量修复规则。

## 第一轮发现

| 对象 | 原包观察 | 目标/处理依据 |
| --- | --- | --- |
| Position | 1,768,440字节，stride40 | 44,211顶点 |
| Blend | 1,414,752字节，stride32 | 同样44,211顶点，不是骨骼数 |
| Texcoord | 530,532字节，stride12 | 同样44,211顶点 |
| 非索引draw | `44315,0` | 该流只有44,211，确实多104 |
| Head/Body IB | 有效R16；Head7,419索引，Body210,858索引 | 不因女仆参照用R32就改变 |
| 匹配分段 | `match_first_index=0/7419` | 新目标原绘制仍同分段，保留 |
| 顶点扩容 | 缺少VertexLimitRaise | 同目标有效参考和生成器支持补充 |

同角色有效MOD、资产表和修复源码相互印证的hash变化：

| 用途 | 旧 | 当时目标 |
| --- | --- | --- |
| Position | `635466ca` | `09a91a5c` |
| Blend | `fd47c861` | `a6823bb3` |
| Texcoord | `bf8270d3` | `6568ac68` |
| IB | `c314953e` | `1afcf31d`，历史中间值`fbc0ffe1` |
| VertexLimitRaise | 没有 | `0d36f587` |

神装与正常女仆模型匹配1,164个共同顶点，匹配条件含位置、权重及唯一性，均支持现有映射；主要覆盖头部，所以不能仅凭这组匹配证明整件翅膀动画正确。5.7/7.2修复器源码里的117项温迪表相同，它们都不补VertexLimitRaise。工具发行版数字也不是目标游戏版本。

## 最小修复及实际结果

1. 从原包制作独立目录，只改`Venti.ini`与`VentiBlend.buf`。INI更新已验证hash，补扩容，将draw修正为44,211，保留R16与0/7419分段。
2. 对原Blend按已核定旧→新表只重映射有权重的索引，53,486个槽改变；权重、顺序、长度保持。结果SHA256为`6a9848d1450b0aefc118947e3ce5dc4eacce801b236bad31a7ccd20492a55ae4`，并匹配先前保存的正确remap样本。
3. 全新启动后用户确认骨骼正常，但身体/翅膀全白、头发黄绿。此时保留几何，只修材质。
4. Head/Body加入已安装库的`run = CommandList\global\ORFix\NNFix`，移除旧ShadowRamp/MetalMap槽绑定；本包没有NormalMap，不使用有法线贴图的ORFix入口。
5. 材质热重载后截图恢复正常肤色、黑发、金饰和蓝白衣翼。其余11个模型/索引/贴图文件逐字节相同，支持材质问题来自绑定而非DDS内容。

原包SHA256：`8082346a768ff9c1abae2de6e6217d3d786c5a978dfd1c2a6b15ed2a9619c380`。最终INI SHA256：`a0e946d28d854bc5df63acfc2e08cbf10e365dcba750632949505799118fd012`。

## 值得复用的判断

- 早期“跑通用remap仍爆模”的实验遗漏容量与draw修正，不能据此否定整份映射。
- 同角色不同MOD可做参照，但不能互换Blend：女仆47,253顶点与神装44,211不在同一顶点域。
- 扩容在对象创建阶段，几何用新启动验证；材质改动已有实际热重载成功证据，没必要再重启同一候选。
- 不据当前成功声称所有动作、距离、光照或别的版本通过。修改两个文件的交付应报告两个文件，不用“完全无改动移植”概括。

## 来源

自包含案例事实来自项目归档；以下是原工作区内的相对来源坐标，不是技能内文件或执行依赖。公开版已保留本页案例与 PC 参考数据，不要求用户访问原工作区：

- `mod/venti-archon-investigation-20261107.md`
- `mod/venti-archon-repair-20261108.md`
- `backups/venti-archon-repair-20261108/geometry-validation.json`
- `backups/venti-archon-repair-20261108/repair-verification.json`

历史对照来源，可用于查原解释；活动分支/网页内容可能已改变，查新目标须固定提交及适用范围：

- [GIMI工具V6.0发布说明，涉及VertexLimitRaise](https://github.com/SilentNightSound/GI-Model-Importer/releases/tag/V6.0)
- [GIMI角色资产库](https://github.com/SilentNightSound/GI-Model-Importer-Assets)
- [ORFix指南](https://github.com/leotorrez/LeoTools/blob/main/guides/ORFixGuide.md)
- [通用修复工具页面](https://gamebanana.com/tools/16433)
