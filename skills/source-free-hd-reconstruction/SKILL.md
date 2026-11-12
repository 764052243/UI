---
name: source-free-hd-reconstruction
description: 001/002在只有低清扁平效果图、没有PSD/PSB/矢量/3D源层时，按用户已认可金样高保真重新制作独立SVG、程序化几何/3D及高清透明PNG的强制工作流。不是要求安装Photoshop，也不允许把位图放大冒充重建。
---

# 无PSD条件下的高清语义切图与重建 SKILL V1.0

> **适用与优先级**：当用户要求切图/HTML，但只能访问完整合成效果图（例如1672×941），无法获得PSD/PSB、矢量或3D工程时，001/002必须加载本SKILL，与[语义切图](../semantic-asset-export/SKILL.md)、[视觉金样回归](../../docs/ASSET_FIDELITY_REGRESSION.md)一起执行。**没有Photoshop不能成为停止制作高清资源的理由**；只有原像素不能无损恢复才是事实限制。
>
> **与PS级SKILL的关系**：[Photoshop级SKILL](../photoshop-grade-asset-extraction/SKILL.md)适用于有可编辑源或可使用分层编辑器时的精修路径；**可选增强，不是高分辨率交付的必要前提**。本SKILL同样必须做到可编辑来源、单独透明图标、完整视觉单元、浏览器和用户金样验收。

**1:1还原的前置否决**：在无PSD条件下可用SVG/3D真实高清重建，但**不可把“新绘得更清楚”叫1:1**。用户已有认可原图且反复投诉造型/颜色失真时，先加载[严格1:1金样还原SKILL](../strict-one-to-one-fidelity/SKILL.md)，优先可追溯的原位像素/源资产复用；每个用户指定原图ROI必须逐件核对，失败继续修正或明确无法达到原层无损精度。不能用看图窗口里的缩放原图做参考，也不得用整页背景PNG冒充HTML语义复现。

## 0. 先锁定原图与资源目标，禁止重设计

- 用户已认可的整张效果图是**视觉金样**；记录尺寸、版本、原图位置、图标所在原图ROI、目标HTML实际CSS尺寸、DPR，锁定其它区域和业务文字。不能将失败的旧切图或一次AI重绘稿改为新基线。
- 对每个元素先判 `html_text/css/icon/component/background/preview`。CSS能忠实实现的简单背景、圆盘和普通按钮形状不切PNG；需要透明独立资源的导航/业务符号、复杂地图、立体底托按需制作。用户明确要求的PNG资源优先于自动分类优化。
- 区分**原图精确提取**（像素保真上限等于现有像素）、**高保真重建**（从几何/矢量/三维重新生成可缩放源）和**AI辅助候选**（必须人工审图）。不把新生成的高清像素等同于原设计的每个不可见细节都真实恢复。

## 1. HD0～HD6 实际制作路线

| 阶段 | 实际动作 | 通过依据 |
|---|---|---|
| **HD0 参考/验收锁定** | 以认可图为金样，逐资源标记ROI、尺寸、重心、角度、体块、阴影、色彩、发光，明确需要完整合成版还是独立glyph | 可追溯参考图/需要的输出清单，不能使用旧失败图 |
| **HD1 技术分流** | 按下面类型选 `vector_redraw/procedural_3d/pixel_restoration/ai_assisted` 等方法 | 每张PNG能解释为什么使用该技术，源文件可再生成 |
| **HD2 高精度源构建** | SVG/矢量形状、CSS+SVG程序化几何、Blender或等效3D建模渲染；复杂纹理可手工画图/AI生成候选+修订 | 存在真实可编辑矢量/3D/绘制源，不是把小PNG塞进SVG放大 |
| **HD3 真实高清导出** | 从SVG/3D/程序化源按HTML显示尺寸×DPR生成透明PNG，必要时1x/2x/4x；正确sRGB、Alpha与线性边缘抗锯齿 | PNG有效像素密度达到目标；不能靠源小位图双三次插值冒充 |
| **HD4 组合与边缘修正** | 前景glyph与完整plinth/阴影/发光组合，提供完整视觉单元；棋盘/浅色/深色下检查边缘和视觉中心 | 不缺半截、不带底色矩形、无白黑毛边；完整组合可单独查看 |
| **HD5 浏览器金样复核** | 实际HTML引用资源、冻结动态内容、同画布/DPR截图，与已认可图逐导航/地图/底托等ROI对照并人工评审 | 不允许只交PNG或只看整体RGB均值；关键小区失败不算通过 |
| **HD6 交付与来源诚实** | 交必要高清PNG、可编辑SVG/建模/程序源、组合预览、HTML/CSS/JS、ZIP和审查记录 | 标记重建来源、不能恢复的细节、真实已测与未测 |

### 按视觉元素选择方法

- **导航小图标、人物、货车、闪电、立方体、服务状态符号**：优先SVG路径/基本几何重绘，多层描边、轮廓、透视和渐变按金样描摹；用SVG栅格化至所需DPR的PNG。图标虽小，仍需按原图形体逐一比较，**禁止自动替换成看似接近的通用图库图标**。
- **底部业务立体底托、环形舞台、科技发光线条**：优先程序化SVG等距几何、多层矢量形状与高光遮罩；复杂透视可用Blender/3D场景。底托必须完整且和前景glyph有对齐锚点，可复用同一源文件。单独底托不等于完整业务图标。
- **中央中国3D地图及光线网络**：使用正确矢量区域边界/真实几何数据生成轮廓，再用高度、材质、光源和连接线路构建；不能只靠放大已认可截图获得新清晰细节。地理边界/数据来源应有合法可用证据；如无法忠实重建复杂纹理，应明确部分为高保真近似、金样未通过时继续修订。
- **复杂背景材质/阴影**：优先CSS或SVG/Canvas程序化生成；不可逆遮挡区只能补绘重建，不得称“原图层无损提取”。
- **AI辅助（可选）**：适合复杂纹理或缺失高频细节候选，需手工遮罩/结构锁定、去除文字幻觉和错位。输出必须回到已确认金样核对，不能以“高清感”替代形状、数据、颜色和比例一致。

### 无PSD时最重要的两个区别

**高清 ≠ 原像素100%一致**：从43×48原ROI重建SVG，可以生成真正几何清晰的2x/4x PNG；但原图中未提供的每条阴影细节无法证明严格相同。需要同时交“可缩放高清源”和“逐项还原差异报告”。

**紧裁PNG ≠ 视觉完整**：分离glyph/plinth后必须再组合并检查。重建完整图标时，可提供单张 `composite.png` + 拆分的 `glyph.png` 与 `plinth.png`，具体由用户需要决定；不得把任何仅包含局部底托的低分辨率裁片冒充完整高清复合单元。

## 2. 可验证的交付结构

推荐在002实际任务目录私有创建：

```text
delivery/
  index.html
  css/style.css
  js/app.js
  assets/icons/                    # 语义前景透明PNG
  assets/components/               # 完整地图/底托等必要复杂组件
  sources/vector/                  # SVG可编辑重绘源
  sources/procedural/              # 用于再生成的真实脚本/建模工程
  preview/full-page.png
  preview/html-render.png
  preview/visual-unit-*.png        # 前景与底托的合成对照
  reconstruction-plan.json
  reports/reconstruction-qa.json
  asset-manifest.json
  README.txt
```

示例 `reconstruction-plan.json`（**只为说明字段，数值不是002用户实际图片坐标**）：

```json
{
  "schema_version": "1.0",
  "reference_id": "user-approved-screen-v1",
  "assets": [
    {
      "id": "nav-truck",
      "method": "vector_redraw",
      "source_path": "sources/vector/nav-truck.svg",
      "export_png": "assets/icons/nav-truck@2x.png",
      "target_css_px": [32, 32],
      "target_dpr": 2,
      "visual_unit": "nav-logistics",
      "source_kind": "reconstructed"
    }
  ]
}
```

**可执行检查**：运行 `python scripts/verify_reconstruction_assets.py delivery/reconstruction-plan.json --root delivery`。它检查可编辑源与PNG存在、SVG真实矢量节点（拒绝只嵌入截图的伪SVG）、目标CSS×DPR是否满足、Alpha是否有非透明主体及资源方法声明；**不判断SVG是否真像原图、毛边是否视觉合格**。之后仍必须运行原`verify_ui_delivery.py`、`audit_asset_edges.py`、`verify_visual_reconstruction.py`及浏览器交互验收。

**禁止伪造验收**：PNG由SVG重建生成≠自动确认1:1；在未读取用户源图、未实际运行浏览器时必须标`HD5未测`；工具“结构通过”不代表用户图片的真实矢量/3D已经制作，更不能声称PSD已导出。

## 3. 无PSD重建任务的通用最低验收

**色彩与视觉对齐**：SVG/程序化重建只能从用户认可金样抽样颜色、渐变与暗边，不能以失败候选为调色源。按[CF0～CF7色彩与HTML视觉中心专项](../../docs/COLOR_FIDELITY_HTML_ALIGNMENT.md)对实际图标的ROI色彩、边缘污染及专属slot内可见前景位置双检，保存[颜色/DOM检查器](../../scripts/audit_color_layout.py)证据。

**立体复合组件**：有几何底托、软阴影或外发光的资产按[HG0～HG6立体底托/黑边专项](../../docs/VISUAL_UNIT_GLOW_REGRESSION.md)保留完整透视结构、实体厚度与外扩柔光；此类组件不执行普通图标紧裁。用[原图ROI合成检查器](../../scripts/audit_visual_unit_composite.py)在真实浏览器同视口underlay上逐视觉单元验收，不能凭整页RGB均值放行。

1. 认可金样固定，不改版、不把标题、数据、地图形体或底部业务单元换成另一套效果。
2. 有原源图层直接导出；无源图层**不能停止**，依HD1逐件重建SVG/程序化/3D源并导出够分辨率的PNG。
3. 必要PNG逐张在棋盘、白底、深色底查看，逐张核对原图形状、厚度、光晕、锚点、裁断；复合立体图标必须有完整组合预览。
4. HTML实际引用这些文件、在目标画布运行，交同视口截图和金样分区对比；差异不达标时记录并继续修复，**不靠提高分辨率掩盖还原偏差**。
5. 出具“原图精确提取/矢量重绘/程序3D重建/AI辅助候选”等真实来源标识、分辨率和未解决细节；ZIP内有实际源码及文件，不以计划代替完成。

这套流程**不需要 Photoshop 或 PSD 文件**，但需要真正执行几何重绘/程序建模/图片复核。用户原图中的遮挡像素和细节无法被无损恢复；允许高保真重建，不允许夸大为原图层无损切取。
