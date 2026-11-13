# UI000｜纯边框、独立图标与面板光影分层验收 V1.2

> **适用范围**：001系统后台/门户/登录组件、002可视化大屏中，设计原图存在渐变明暗、切角、金属反光、局部发光、内外多条线、上框与左右边连成一体的**视觉装饰边框**。这是跨案例通用的「装饰边框图层」资产策略，**不是要求所有普通边框都切PNG**。
>
> 依据：用户明确指出某些面板边缘属于同一个完整视觉整体，使用HTML简单`border`替代会丢失原图明暗与转角结构。对应设计师必须按**认可原图**确认这些面板的完整边框几何并执行本规则。

## FBG0｜切图前的资产语义分类

| 原稿中的对象 | 推荐实现 | 关键理由 |
| --- | --- | --- |
| 简单单色直线、常规规则描边、纯色圆角矩形 | CSS `border` / `outline` | 可等价、可伸缩，无必要制造PNG |
| **独特形状、斜切角、边缘明暗渐变/镀铬材质/局部高光、单个面板四边互相关联的整体装饰框** | **独立透明PNG**，`component_type: ornamental_frame` | 几何和光影关系是一个整体，不能退化为四条CSS直线 |
| 面板内部纯色/简单渐变底 | CSS `background`，作为PNG下层 | 不应与装饰框及图表内容烘焙到一起 |
| 面板标题、数字、折线/饼图数据、按钮/箭头交互 | HTML/SVG/Canvas/JS | 保留可读、可选、可操作、可更新，不烘焙进边框图 |
| 原图直接包含整幅纹理的特殊完整面板 | 依据源图层分别处理**装饰边框PNG+必要内容底纹** | 不把整块含文字/数据的截图伪称边框PNG |

**语义优先于文件名**：一块面板对应一份**完整视觉边框单元**；多个面板若完全相同且尺寸兼容，可以复用一份PNG/9-slice，不能为了凑数量重复导出相同素材，也不能强行共用不同形体导致透视和高光错位。

## FBG1｜从正确源层取得“完整一圈框”

- 首选设计源文件中的**边框/高光/拐角/外影完整关联图层**，原位导出`RGBA`，同时保留顶部、左右、底部及其连接转角；边缘外扩发光要留足透明安全区。
- 原图为合成扁平PNG时，面板框与背景/文字已叠加，**直接裁整个矩形不是提取边框**；需要从可编辑层获取，或使用高保真遮罩、矢量路径、分层重建。应记录`source_kind=masked/reconstructed`及仍不可无损还原的区域。
- **框自身可以明暗不同，但不能暗部被当作透明垃圾删掉**。从原图取样金属亮边、暗边、斜切拐角和外发光，别统一替换成单色青/灰CSS描边。
- **边框四边须作为一个复合资产验收**；不得上、左、右、下独立随机裁再随意拼接，出现断点、粗细突变、斜角错位。允许可编辑SVG作为生产源，但**用户明确要求PNG时最终必须提供真实PNG**。

## FBG2｜独立PNG的真实内容

- 推荐`assets/components/frame_*.png`，其`component_type`是`ornamental_frame`，不是`icon`或全屏`background`。
- **纯边框不是“带底色的空心面板”**：整张框PNG除了四周狭窄的描边、切角及其必要高光/羽化阴影外，**其他像素Alpha必须为0**。不得包含黑色/灰色面板背景、顶部实心标题背景、半透明内区底纹、图表/文字、任何独立图标（包括标题前的装饰符号和右侧按钮图标）。简单的内部规则分割线如需要，单独归CSS/图层，不属于纯边框PNG。边框光影可以有真实暗色像素，但不等于允许做黑色底板。
- **图标必须与边框拆成不同PNG**：每个业务/装饰/按钮图标以`assets/icons/icon_*.png`单独导出，真正透明并符合I0～I5；一张`frame_*.png`不得把图标、文字或数据烘焙进去。界面中存在几个需要图标PNG的对象，就各自建立独立图标资源映射；同一图标可跨同型面板复用。
- 有背板填充时，简单底色/渐变由下层CSS绘制；复杂独有纹理由独立背景组件提供。不能为了制造透明孔一刀切所有黑色——可能毁掉原本暗色边沿与原生阴影。
- `frame_inner_rect`为旧版透明内区检查辅助，**不能当作允许在它外部填充面板背景的借口**。新版额外要求`frame_perimeter_px`定义框线/柔光占用的狭窄周边带，带以内的中央范围真实Alpha=0；带宽不能事后扩大来包住图标或背景，实际边框与光影宽度仍由金样确定。
- 不应用普通前景icon的紧裁/内容居中工具对完整框进行二次裁剪、移动；它使用**原面板尺寸和空间锚点**。整个边框属于完整视觉单元，不是四根无关联的线条。

## FBG2.1｜“纯边框”不能误执行成“删除面板原有光影”

**通用缺口**：除了边框外，已认可面板还可能包含标题金属反光、渐层高光、内阴影、面内软辉光、实体暗部过渡。若为满足边框PNG零背景与窄周边带规则，直接删除这些非周边亮暗信息，而不是归入正确的独立视觉层，最终HTML会变得平、暗、光影不明显。

| 视觉职责 | 资产归属 | 约束 |
| --- | --- | --- |
| 描边、切角、紧贴边缘的亮线/暗线/窄辉光 | **纯边框PNG** `frame_*.png` | 不含背景色、图标或宽范围内容区光影 |
| 标题条金属反光、宽于边框的受光、面内漫射光、阴影层次 | **独立材质/光效层**：简单可等价用CSS，复杂则独立透明PNG `assets/components/effect_*.png` | 既不是边框，也不是背景底色；不含图标、文本、实心色块，记录原始Alpha/柔化程度与层锚点 |
| 基础底色、普通渐变/纹理 | CSS背景或独立背景 | 不混入纯边框 |
| 标题/状态/操作图标 | 独立`assets/icons/icon_*.png` | 绝不嵌入边框或材质层 |
| 数字、文本、表格与动态数据 | DOM/图表层 | 不预先烘焙到装饰PNG |

**前两轮规则同时有效**：保持“纯边框+独立图标PNG”，同时必须**完整保留原图的材质/光影表现**。既不能把光影全部塞回边框，也不能为“干净分层”把光影删除。不能用整页亮度提升、通用霓虹CSS阴影去伪造原稿独特高光。

## FBG3｜固定尺寸、可变尺寸的PNG装配策略

**固定尺寸、形体独特（默认）**：导出完整框PNG，按原稿面板的同一矩形定位，不改变宽高比。常规层次按金样实际层叠关系为：**底色/背景→材质与非边缘光影层（必要时独立effect PNG）→纯边框PNG→独立图标PNG和标题/数字/图表/交互（DOM、SVG/Canvas）**。可能存在光效覆盖于框上方的情况，按原稿实际遮挡关系调整z-index，不能机械套一套层次；框与光效装饰层均不得吃点击事件。

```html
<section class="panel">
  <!-- 仅在有复杂面内光影时输出独立effect PNG，无则删除这一行 -->
  <img class="panel-effect" src="assets/components/effect_metrics.png"
       alt="" aria-hidden="true">
  <img class="panel-frame" src="assets/components/frame_metrics.png"
       alt="" aria-hidden="true">
  <header class="panel-title"><img class="panel-icon" src="assets/icons/icon_panel_metrics.png" alt="" aria-hidden="true">实时指标</header>
  <div class="panel-content"><!-- 真正的DOM或可交互图表 --></div>
</section>
```

```css
.panel { position: relative; background: #071922; }
.panel-frame {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  pointer-events: none; z-index: 1;
}
.panel-effect {
  position: absolute; inset: 0; width: 100%; height: 100%;
  opacity: 1; pointer-events: none; z-index: 1;
  /* 未经原稿证据，不擅自叠加mix-blend-mode/filter/额外透明度 */
}
.panel-frame { z-index: 2; }
.panel-title, .panel-content { position: relative; z-index: 3; }
.panel-icon { display: inline-block; width: 20px; height: 20px; object-fit: contain; vertical-align: middle; margin-right: 8px; }
/* icon_panel_metrics.png与frame_metrics.png必须是两个真实且不同的PNG */
/* 本类复杂边框不要另外叠加 border: 1px solid... */
```

上述`effect_metrics.png`只是复杂材质光影分层的示例：存在才作为独立`role=component`透明PNG登记并实际引用；不存在时删除该图层，不得留下404。层级和属性依据认可原稿，不是统一的默认美术配置。

上述`width:100%;height:100%`仅适用于**导出框与目标面板宽高比和原稿一致**的情形；若设计允许响应式高度/宽度变化而出现失真，需重新导出适配尺寸，或采用经验证的9-slice。

**尺寸可变且图案允许拼接**：由同一完整PNG做CSS`border-image-source:url(...)`的**9-slice**，固定四角和不可拉伸的高光端点，边沿仅在经验证的中间可拉伸/重复带变更尺寸。这里`border-image`是**使用PNG像素绘制复杂边框**，而不是用普通CSS`border-color/box-shadow`近似替代。若顶部有完整非线性高光/特殊拐角、边沿不可平铺，则**禁止强行9-slice**，改为按每个真实目标尺寸独立导出完整框PNG。

## FBG4｜交付manifest（1.1兼容扩展）与静态门禁

仅针对确需保真的边框（或用户明确要求PNG框）登记下列字段；不改变普通图标/地图/全页背景规则：

```json
{
  "schema_version": "1.1",
  "background_strategy": "css",
  "required_frame_asset_ids": ["panel-metrics-frame"],
  "assets": [
    {
      "id": "panel-metrics-frame",
      "role": "component",
      "component_type": "ornamental_frame",
      "path": "assets/components/frame_metrics.png",
      "source_kind": "layer_export",
      "reason_png": "Unique continuous metallic bevel and light-to-dark perimeter",
      "edge_policy": "closed",
      "frame_render_strategy": "fixed_overlay",
      "frame_inner_rect": [20, 24, 600, 315],
      "frame_perimeter_px": 18,
      "frame_icon_asset_ids": ["panel-metrics-icon"]
    },
    {
      "id": "panel-metrics-icon",
      "role": "icon",
      "path": "assets/icons/icon_panel_metrics.png",
      "source_kind": "layer_export",
      "reason_png": "separate decorative title glyph with transparent surrounding pixels"
    }
  ]
}
```

这段是**字段片段**，而非完整交付manifest。真实交付还必须包含`canvas/entry_html/css/js/preview/required_text/required_interactions`等字段。坐标均为示例，不是用户当前图稿实测。

- `required_frame_asset_ids`：该任务明确需要的框资产ID清单。逐个必须存在真实PNG，并声明`role=component`、`component_type=ornamental_frame`；不可只在CSS里写border后删除必需项。**具体多少块面板**由001/002从本次用户认可图稿建立清单，不在公共SKILL写死。
- `frame_inner_rect`：PNG内部内容安全区`[left,top,right,bottom]`，要求**完全透明**；不能把画满色块的外圈包在内区之外作为合法背景。
- `frame_perimeter_px`：**必填正整数**，定义整个PNG允许有可见像素的**窄周边带**；带内部区域Alpha必须为零。宽度不大于图像较短边的1/5，阻断以扩大边框带的方式藏进整块背景或内部图标。原图有效外发光跨越该带时应另拆光晕层或采用源设计适配方案并记录差异，不得通过加大阈值冒充“纯边框”。
- `frame_icon_asset_ids`：**必填数组**，把与此框关联的所有独立图标PNG的manifest ID写进去；即使此框原图没有图标，也要明确写`[]`。检查器要求这些ID存在，且属于`role=icon`的**不同PNG文件**。视觉上是否仍把小图案画进周边框带，最终还必须人工以原图检查。
- `frame_render_strategy`：`fixed_overlay`或`nine_slice`；选`nine_slice`时必填`frame_slice_px: [top,right,bottom,left]`，值必须对应实际切片。静态检查仅验证合法参数，**不能证明切片后光影不变**。
- `edge_policy`遵循已有完整组件规则；框有意延伸到资产画布边缘才可使用`intentional_bleed`，应有金样依据。
- [完整交付检查器](../scripts/verify_ui_delivery.py)已识别上述声明，检查**必需资产存在、HTML/CSS真正引用、窄周边以外完全透明、框与图标分属不同PNG、四边和四角可见像素、切片参数及普通组件裁断风险**。全部检测为保守结构检查，不能自动证明原图装饰线条、精细材质与HTML渲染视觉一致。

## FBG5｜最重要的实际视觉回归

1. 在认可原图锁定**整个面板边框ROI**，包含上下左右、所有斜切角、暗色边缘、柔光、顶部接缝及四周留白；不能只截较亮的一小段来宣称通过。
2. 真实HTML原视口渲染该面板，输出`GOLD / FRAME PNG / HTML / DIFF`并逐边比对暗线亮线、转角、连续性、线宽、厚度、透明边缘、坐标和遮挡关系。可复用[严格原图逐ROI检查器](../scripts/audit_strict_1to1.py)或按已认可的视觉容差报告；不能以整页均值掩盖细框错位。
3. 检查**底色与框分离后**是否会出现双边框、顶部亮边被CSS覆盖、底部暗边消失、边角间光断裂、缩放糊/扭曲；不允许再叠加一层`border:1px solid`冒充缺失部分。
4. 验证标题、数据和图表仍为真正HTML/SVG/Canvas，按钮仍能操作；装饰图不得截取整块含数据的面板。
5. 审查复用和尺寸策略：固定框不拉伸错比例；9-slice各尺寸检查左右/顶部与角部高光接缝，边缘是否完整；宽度/高度改变后的结果仍需对照相应认可基线。
6. 若源图只有合成位图且仍有背景分离误差，应标记“框图层尚未高保真提取/重建”，而不是隐藏问题用CSS实线替代。

## FBG5.1｜细微光影的局部亮度保留与复合验收

1. 同时保留**独立、无叠窗/红箭头的认可原生设计图**与**真实浏览器同视口同DPR截图**。窗口里缩小的对比图只能定位问题，不能直接做同坐标像素验收。
2. 在修改前针对每个关键**高光带、暗边、标题反光、柔性阴影**固定窄ROI，排除动态文字、图表、数据、图标等干扰。**整卡或全屏RGB均值不代表少量高光细节保留。**
3. 用[原图ROI对照器](../scripts/verify_visual_reconstruction.py)的可选`light_preservation`：从参考ROI中事先按亮度阈值筛选原高光像素，检查HTML同位置的**平均亮度保留比例**与**变暗像素比例**。如果参考ROI没有足够的高光像素就FAIL，不允许降低门槛冒充检测成功。
4. **这只是亮度诊断**。色相、光晕扩散宽度、形状、模糊、位移、HDR材质还需RGB/轮廓差异、`GOLD/HTML/DIFF`和100%/400%人工检查。不能只凭亮度指标自称1:1。
5. 若实际丢光，检查资源导出Alpha与RGB污染、裁边、CSS `opacity/filter/mix-blend-mode/mask`、父元素透明度、`overflow:hidden`、层级与缩放/插值；找到真实根因才修改，不凭经验统一加亮。

配置示意（**纯合成格式示例，不是本轮用户图稿的真实坐标或阈值**），作为`verify_visual_reconstruction.py`原有`regions[]`中的一个对象：

```json
{
  "id": "critical-panel-highlight",
  "box": [10, 10, 110, 30],
  "thresholds": {
    "max_changed_fraction": 0.35,
    "max_mean_rgb_difference": 15,
    "pixel_tolerance": 3,
    "light_preservation": {
      "reference_min_luminance": 100,
      "min_reference_highlight_pixels": 20,
      "min_preserved_luminance_ratio": 0.92,
      "max_lost_highlight_fraction": 0.20,
      "drop_tolerance": 6
    }
  }
}
```

此字段为**可选增强**，老配置依然兼容。新任务要在实际原图和修改前状态上锁定ROI/阈值，配合其它色彩与位置检查，不能事后放宽。

## FBG6｜通用回归（FBR-01～FBR-20）

| 编号 | 必须发现 |
| --- | --- |
| FBR-01 | 用户明确要求PNG整体框，HTML仅用单色CSS边框代替：未交付必需框PNG，FAIL |
| FBR-02 | 只切顶部亮线，左/右/底边和斜角丢失：完整性FAIL |
| FBR-03 | PNG含不透明黑矩形/图表内容而非空心框：透明内区FAIL |
| FBR-04 | 边框四个拐角少一个：四角像素门禁FAIL |
| FBR-05 | 框图文件未被任何HTML/CSS/JS实际引用：FAIL |
| FBR-06 | 独立可复用框被多次重复切同一文件内容：沿用PNG重复检查FAIL |
| FBR-07 | 标记9-slice却缺尺寸或角部切片参数相互覆盖：静态FAIL |
| FBR-08 | CSS框与PNG框重叠造成双边、或CSS缩放使高光变形：实际HTML差分FAIL |
| FBR-09 | 为让边框通过而把内容区ROI缩小到几像素：最小面积约束FAIL |
| FBR-10 | 自动工具通过但框仍与原稿暗亮比例/材质不同：人工与原图ROI仍未通过 |
| FBR-11 | 边框PNG包含面板黑底、顶部色带、透明内区污染：非周边Alpha必须为0，FAIL |
| FBR-12 | 将标题图标、按钮箭头、业务符号烘焙进边框PNG：语义分层FAIL，图标必须独立PNG |
| FBR-13 | 单独图标文件不存在，或被声明成component/与边框共用PNG：资产角色FAIL |
| FBR-14 | 将frame_perimeter_px扩大以藏住背景/图标：宽度门禁FAIL |
| FBR-15 | 看似两张PNG但实际HTML只引用边框或仅截图呈现图标：资源引用与浏览器验收FAIL |
| FBR-16 | 纯框结构通过却把原稿标题区金属反光/大范围软光删除：视觉FAIL |
| FBR-17 | HTML额外opacity、filter、blend或遮罩导致光影变暗：复合截图局部亮度FAIL |
| FBR-18 | 整页RGB平均合格但局部高光明显减弱：独立高光ROI亮度保留FAIL |
| FBR-19 | 用整页加亮/统一box-shadow替代原稿局部材质：非目标冻结与原图差异FAIL |
| FBR-20 | 独立effect层虽存在但Alpha、空间位置、光晕过渡、层级与原稿不符：复合FAIL |

**责任与状态**：000负责通用门禁与可执行检查器，001/002负责本项目真实边框素材、源HTML/实际截图和最终用户验收。新增公共规范不能宣称原来错用CSS边框的页面已经被实际修复。
