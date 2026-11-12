# UI000｜装饰面板整体边框PNG资产与HTML复合验收 V1.0

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
- 中部数据/文本容纳区**真正透明**，不应混进黑色矩形、图表、文字、可交互内容。可以包含原稿的顶部装饰线、金属标题条、高光和柔光，但具体文字属于DOM。
- 有背板填充时，简单底色/渐变由下层CSS绘制；复杂独有纹理由独立背景组件提供。不能为了制造透明孔一刀切所有黑色——可能毁掉原本暗色边沿与原生阴影。
- `frame_inner_rect`标出**应该可透视的内部内容安全区**，范围不应为了通过测试缩到很小。装饰光效向内延伸的部分要依据原金样精确调整该安全区。
- 不应用普通前景icon的紧裁/内容居中工具对完整框进行二次裁剪、移动；它使用**原面板尺寸和空间锚点**。整个边框属于完整视觉单元，不是四根无关联的线条。

## FBG3｜固定尺寸、可变尺寸的PNG装配策略

**固定尺寸、形体独特（默认）**：导出完整框PNG，按原稿面板的同一矩形定位，不改变宽高比。常规层次为：底色/底纹（CSS或背景层）→完整框PNG（绝对定位、纯装饰）→标题/数字/图表/交互（DOM、SVG/Canvas）。框层不吃点击事件，内部DOM不能被框PNG覆盖。

```html
<section class="panel">
  <img class="panel-frame" src="assets/components/frame_metrics.png"
       alt="" aria-hidden="true">
  <header class="panel-title">实时指标</header>
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
.panel-title, .panel-content { position: relative; z-index: 2; }
/* 本类复杂边框不要另外叠加 border: 1px solid... */
```

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
      "frame_inner_rect": [12, 36, 620, 340]
    }
  ]
}
```

这段是**字段片段**，而非完整交付manifest。真实交付还必须包含`canvas/entry_html/css/js/preview/required_text/required_interactions`等字段。坐标均为示例，不是用户当前图稿实测。

- `required_frame_asset_ids`：该任务明确需要的框资产ID清单。逐个必须存在真实PNG，并声明`role=component`、`component_type=ornamental_frame`；不可只在CSS里写border后删除必需项。**具体多少块面板**由001/002从本次用户认可图稿建立清单，不在公共SKILL写死。
- `frame_inner_rect`：PNG内部内容安全区`[left,top,right,bottom]`，要求足够大且大多数像素透明，阻断把含完整背景/文字的截图当作空心边框。
- `frame_render_strategy`：`fixed_overlay`或`nine_slice`；选`nine_slice`时必填`frame_slice_px: [top,right,bottom,left]`，值必须对应实际切片。静态检查仅验证合法参数，**不能证明切片后光影不变**。
- `edge_policy`遵循已有完整组件规则；框有意延伸到资产画布边缘才可使用`intentional_bleed`，应有金样依据。
- [完整交付检查器](../scripts/verify_ui_delivery.py)已识别上述声明，检查**必需资产存在、HTML/CSS真正引用、透明内区、四边和四角可见像素、切片参数、常规组件裁断风险**。全部检测为保守结构检查，不能自动证明原图装饰线条、精细材质与HTML渲染视觉一致。

## FBG5｜最重要的实际视觉回归

1. 在认可原图锁定**整个面板边框ROI**，包含上下左右、所有斜切角、暗色边缘、柔光、顶部接缝及四周留白；不能只截较亮的一小段来宣称通过。
2. 真实HTML原视口渲染该面板，输出`GOLD / FRAME PNG / HTML / DIFF`并逐边比对暗线亮线、转角、连续性、线宽、厚度、透明边缘、坐标和遮挡关系。可复用[严格原图逐ROI检查器](../scripts/audit_strict_1to1.py)或按已认可的视觉容差报告；不能以整页均值掩盖细框错位。
3. 检查**底色与框分离后**是否会出现双边框、顶部亮边被CSS覆盖、底部暗边消失、边角间光断裂、缩放糊/扭曲；不允许再叠加一层`border:1px solid`冒充缺失部分。
4. 验证标题、数据和图表仍为真正HTML/SVG/Canvas，按钮仍能操作；装饰图不得截取整块含数据的面板。
5. 审查复用和尺寸策略：固定框不拉伸错比例；9-slice各尺寸检查左右/顶部与角部高光接缝，边缘是否完整；宽度/高度改变后的结果仍需对照相应认可基线。
6. 若源图只有合成位图且仍有背景分离误差，应标记“框图层尚未高保真提取/重建”，而不是隐藏问题用CSS实线替代。

## FBG6｜通用回归（FBR-01～FBR-10）

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

**责任与状态**：000负责通用门禁与可执行检查器，001/002负责本项目真实边框素材、源HTML/实际截图和最终用户验收。新增公共规范不能宣称原来错用CSS边框的页面已经被实际修复。
