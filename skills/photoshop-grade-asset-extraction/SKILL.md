---
name: photoshop-grade-asset-extraction
description: UI设计师001/002从已认可设计中提取高清透明PNG、分离立体图标/底托、修复低清毛边和组件只剩半截时必读。定义Photoshop或等效分层编辑器的非破坏性精修操作、原生像素分辨率及完整视觉单元验收；并非宣称Photoshop插件已连接。
---

# Photoshop 级精细切图与完整视觉单元保护 V1.0

> **作用边界**：这是供实际可以使用 Photoshop、Affinity Photo、Photopea、Figma、Illustrator、Blender 或等效源文件编辑器的设计师执行的**专业工作流 SKILL**，不是已安装的 Adobe Photoshop 远程操作插件。若当前执行环境无PSD源层或无法启动编辑器，必须标记“原始图层未获得/PS未实际执行”，不得写“已PS精修”或把模糊截图放大冒充高清。
>
> **无PSD时的正式替代路线（强制）**：没有PSD/PSB/原始3D或编辑器**不等于不能制作高清PNG**。若只剩合成截图，立即转到[无PSD高清重建SKILL](../source-free-hd-reconstruction/SKILL.md)：SVG几何重绘、程序化3D/光影重建、必要时AI候选＋人工精修，导出实际足够像素的PNG并对认可金样校验。不得只要求用户提供PSD后停止，也不得把重建谎称无损提取原层。Photoshop只是可选实现路径，不是交付前置依赖。
>
> **触发**：用户指出“只有一半、缺层、PNG不完整、不高清、毛边、锯齿、黑白脏边、底托与图标分开后少一半、图片未居中”，或需要从原效果图高清导出独立资源。必须先读取 [语义切图 SKILL](../semantic-asset-export/SKILL.md)、[资产角色与边缘规范](../../docs/ASSET_ROLE_AND_EDGE_QA.md) 与本 SKILL。认可原稿是唯一视觉金样，不因精修重设计。

## A. 第一优先级：识别“完整视觉单元”，不能过度拆分

先把“用户看到的完整东西”写成 `visual_unit`，再决定它需拆几层：

- 底部「人物/货车/生产/仓储/供应链」在用户认可稿中是**图形符号＋发光底托＋暗部厚度/倒角＋软阴影**组成的完整视觉单元。把 `deco_business_plinth_shared.png` 与 `icon_business_customer.png` 分开有利于前端复用，**但不能把单独底托称为完成的“业务图标”**。
- **最低可验证交付**：`glyph.png`（独立透明前景）、`plinth.png`（真正完整的复用底托，确有必要时）、`composite-preview.png`（同位叠加后的完整视觉单元检查图，用户要求独立完整PNG时交付可用`composite.png`）。所有层的锚点、大小、层级需要在 HTML 与资产清单中映射。
- 如果用户实际要求的是“单张可独立使用的完整立体图标”，应**直接导出完整复合PNG**，可另外附分层资源；**不能只交半个底托**。如果用户只要求独立业务符号，保留纯glyph，但最终页面要还原整套视觉单元。
- 纯黑背景、普通圆盘或可由CSS等价实现的底色不需要额外PNG；真实立体底托、复杂地图舞台不因“能分层”而被拆坏。复用组件不能缺失倒角、底面或反射层。
- 对任何“完整单元”的修复，先用原图金样检查：上、中、下三个部位是否齐全，有没有被遮挡/被抠掉的像素；不能拿已经缺半截的PNG继续裁边以求居中。

## B. R0～R7：真实分层精修流程（无源图层不能假报通过）

| 关口 | 操作与必须提供的证据 | 关键失败 |
| --- | --- | --- |
| **R0 来源分级** | 按优先级读取 **PSD/PSB原图层/智能对象/AI或SVG矢量/3D工程** → 高清透明源渲染 → 高清平面源图 → 截图。记录`source_kind`、源文件真实尺寸与来源。 | 使用聊天缩略图/被缩过的小截图冒充高清PSD源层 |
| **R1 完整单元** | 记录`visual_unit`、组成部件、分层锚点，输出完整合成检查图；若要求单件完整图就必须生成独立完整复合PNG。 | 只导出发光平台/只剩“半截”，缺上方业务符号和原版光影 |
| **R2 非破坏分离** | 在源PS工程的复制件中，优先选择原图层或智能对象；位图才用蒙版、路径及Select and Mask精修，保留原图和可回退蒙版，不能“全黑一键透明”。 | 抹掉有效黑色阴影/底托、把背景烘焙为矩形，蒙版硬锯齿 |
| **R3 边缘像素精修** | **硬质等距/斜边**用路径/矢量干净勾边；**发光/阴影**另保留连续半透明蒙版，区分前景与底色污染；检查去色边、Premultiplied/straight Alpha处理、100%及400%清晰度。 | 毛边、脏黑白边、羽化变糊、硬直边被无意义高斯模糊 |
| **R4 导出原生清晰度** | 从PSD智能对象/矢量/3D原分辨率分别导出PNG RGBA，保留sRGB一致的颜色；按实际CSS显示大小和DPR核对源有效像素密度，支持1x/2x/4x**仅从足够高精度的源导出**。 | 132×102截图插值为528×408后宣称“4x高清” |
| **R5 裁边与对齐** | 完整复合图的几何框与视觉中心和金样一致。单独glyph使用真实Alpha紧裁；为层叠而保留的底托`layer_anchor`画布允许顶部空间，**但必须有同组的复合预览**证明无缺层。 | 把层叠画布留白当“单独底托半截可直接使用”，或强行裁掉发光 |
| **R6 叠底验收** | 每张PNG展示棋盘/白底/黑底，原生100%与400%边缘局部；检查缺边、锯齿、低分辨率、半透明外发光、阴影。用现有`audit_asset_edges.py`诊断、人工逐件审稿。 | 只通过Alpha数值/边距校验即宣称毛边解决 |
| **R7 HTML金样验收** | 在目标浏览器尺寸和DPR实际组装页面，验证底托+图标对齐；原稿与浏览器截图按导航、左/右面板、中央地图、底部业务单元逐区比对。 | PSD单图看起来不错，HTML显示“缺半截/错位/发虚”仍宣称成功 |

### PS/分层编辑器操作要点（实际执行者按照版本和工程调整）

1. **建立工作副本**，保留原PSD/PSB、图层组、智能对象、调整层、阴影/辉光图层；原工程不能直接覆盖。把用户认可效果图置于只读参考层。
2. 在原图层列表找到业务符号、底托、地面投影和辉光；能直接隔离图层就**关闭其他可见层导出**，不要先“栅格化整屏截图再抠图”。
3. 扁平位图不得静默无损拆层：对硬几何边缘可用钢笔路径/矢量重建蒙版；软边用`Select and Mask`多个背景视图、边缘修整；检查黑/白/透明三底。原像素缺失时须从源设计重绘，标`reconstructed`。PS的自动背景删除、增强边缘/AI生成可作为候选，**不能作为无需对照的最终验收**，也不保证缺失的立体面能真实恢复。
4. 导出时可用 `File > Export > Export As` 选择PNG透明、相应色彩空间与需要的大小；工程里的智能对象、图层必须保留。仅允许源图具有足够细节时导出2x/4x：把小位图放进智能对象或用PS“提高分辨率”**不会产生真实缺失的金样细节**。
5. 若素材的黑/蓝发光边出现白灰/黑色毛边，先排查原背景颜色污染及Alpha预乘方式，再人工精修边缘RGB与蒙版；**不是直接整体模糊或全局羽化**。局部实际显示再验收。

Adobe官方可核验的操作说明：
- [图层蒙版和非破坏编辑](https://helpx.adobe.com/photoshop/desktop/create-masks/layer-masks/edit-and-refine-layer-masks.html)
- [Select and Mask 不同背景视图](https://helpx.adobe.com/photoshop/desktop/make-selections/refine-modify-selections/refine-your-selection-and-mask.html)
- [智能对象保留源质量](https://helpx.adobe.com/photoshop/desktop/create-manage-layers/smart-objects/smart-objects-overview-and-benefits.html)
- [Export As可导出多个尺寸](https://helpx.adobe.com/photoshop/desktop/save-and-export/export-files-to-different-formats/fine-tune-your-export-settings-using-the-export-as-option.html)

## C. 实际PNG层级与可见性诊断

适用于**任何**仅有底托、符号、外光层或阴影层的切图。获取真实原PNG后记录画布尺寸、RGBA模式、非零Alpha包围框、四侧留白、可见主体视觉中心与导出锚点。不能仅根据一侧透明空间较大就认定“未居中”：可能是有意保留的复合层锚点；也不能将只有底托的单层PNG当成含前景符号的完整视觉单元。

实际像素不足时，无法从低清裁片凭空恢复独立高频细节；应优先从原始分层/可编辑矢量/程序化几何源重新导出。深色像素可能是合法的实体侧壁或非法混入的背景，必须依据认可原图和三底色检查区分。真实历史PNG尺寸及实测记录留在对应任务Issue/验收报告，**不写进公共SKILL**。

## D. 可执行的分辨率/完整单元验收

**光晕与黑边通用标准**：独立业务符号可紧裁，但**3D底托、投影、外发光层不得按普通icon自动裁边/再居中**，必须保留原图锚点并用可编辑几何源重新输出；只有真实视觉单元重组后与认可原图逐ROI复合验证、并在白/暗/棋盘底人工检查预乘Alpha与黑边才算通过。详见[HG0～HG6](../../docs/VISUAL_UNIT_GLOW_REGRESSION.md)。

对应辅助检查器：`scripts/audit_cutout_source_quality.py`，实际回归证据见[PS切图与完整视觉单元回归](../../docs/PS_CUTOUT_REGRESSION.md)。

- 用 JSON 记录每项 `asset_path`、`role`、`visual_unit`、`layer_role`（`glyph/plinth/composite/map/standalone`）、`alignment_mode`（`tight/layer_anchor`）、`target_css_px`、`target_dpr`、`source_native_px` 和可选 `composite_preview`。导出完整图与独立源层必须保持同一个`visual_unit`。
- 必须比较**实际文件像素**与**显示像素×DPR**。如果文件不足，则FAIL；如果仅靠小位图插值“放大”但源像素不足，也必须FAIL。无`source_native_px`需标未验证来源，不能谎称原生高清。
- 单独`plinth`声明`alignment_mode: layer_anchor`时，只有提供同组的`glyph`（或其他上层）与真正的`composite_preview`及实际组装审查，才允许保留上部留白；如果写`tight`则需要内容包围框实际居中。
- 检查工具只验证**分辨率元数据、透明边界和同组文件存在**，不会自动证明“平台厚度完整、图形不毛躁或复合比例正确”；这些必须由R2/R3/R6/R7真实操作和人工金样比较完成。
- **没有Photoshop编辑器/PSD/源图层时**：输出`R0/R2/R3/R4未执行`和真实报告；可以提出重建方案但不能装作已修复。002需将实际PNG、PSD图层和浏览器截图拿到有编辑器的执行环境。

## E. 交付协议与禁止事项

- 保存原文件和可编辑 PSD/PSB/矢量/3D源（仅在用户授权和可安全交付时），`assets/icons`、`assets/components`、完整视觉复合预览、HTML/CSS/JS、完整ZIP和`reports/cutout-source-qa.json`。
- **不要求所有资源都切PNG**；纯CSS背景、KPI纯色圆盘不重复切。只是用户明确需要“单件完整底部业务图标”时，必须连底托＋glyph合在**一个可独立使用的复合PNG**，可以另有分层素材。
- 不在缺失源图时硬编缺失的底座结构，**不盲目放大低分辨率，不用羽化把锯齿涂糊，不删除原本合法的黑色实体阴影**。
- 用户已经认可的顶部/地图/底部等非目标部分继续锁定；需要修复的是图层、源精度和切图质量，不是重设计。
