# UI设计师｜语义切图与 HTML 完整交付契约 V1.0

**适用**：用户要求切 PNG 图标/背景、图形资源、HTML 还原或可运行 ZIP。此契约必须与 [语义切图 SKILL](../skills/semantic-asset-export/SKILL.md) 配合使用。

## 一、交付“完成”的判定不是 PNG 数量

过去把一张大屏切成约25个矩形截图并打包，本质上只完成了**矩形视觉分块**，没有独立透明图标、干净背景图，也没有用户要求的 HTML。今后下列四类必须区分：

| 资产角色 | 文件例子 | 验收 |
|---|---|---|
| `background` | `assets/backgrounds/bg_dashboard.png` | 按目标画布全幅输出，背景能独立铺设；不得含原前景菜单、标题和图标 |
| `icon` | `assets/icons/icon_nav_ops.png` | 单个视觉图形、真正 RGBA 透明背景，不能整条带字导航截图 |
| `component` | `assets/components/deco_map.png` | 必要的复杂装饰/地图图层，业务数据与交互不能全部烘焙到图片 |
| `component`（`ornamental_frame`） | `assets/components/frame_panel.png` | 四边连贯、明暗复杂的特殊面板装饰框，PNG内容区保持透明，叠放在独立底色与真正DOM之间；不能用普通CSS边框代替 |
| `preview` | `preview/full-page.png` | 完整视觉对照稿，用于参考，不可作为HTML唯一可见主体 |

用户要求 HTML 时必须同时交付 `index.html`、`css/style.css`、`js/app.js`、引用的独立 PNG 资源和完整 ZIP。纯视觉稿不是功能源码；静态 HTML 的可运行范围需明示。

**源素材真实性**：扁平 PNG 无法无损分离已遮住的底图和文字，必要时须从原始设计分层导出或重建，并标明高保真重建而非精确原层提取；用户已认可的色彩/比例/造型不自动变更。

## 二、最简资源清单 asset-manifest.json

此 JSON 放在 `delivery/` 根目录，由实际导出文件填写，不能列不存在的资产。示例为字段说明，**不是已经生成的用户页面**：

```json
{
  "schema_version": "1.1",
  "canvas": {"width": 1920, "height": 1080},
  "background_strategy": "css",
  "entry_html": "index.html",
  "css": ["css/style.css"],
  "js": ["js/app.js"],
  "preview": "preview/full-page.png",
  "assets": [
    {
      "id": "overview-nav-icon",
      "role": "icon",
      "path": "assets/icons/icon_nav_overview.png",
      "source_kind": "layer_export",
      "reason_png": "independent glowing navigation symbol"
    }
  ],
  "required_text": ["业务运营可视化平台", "综合概览"],
  "required_interactions": ["navigation"]
}
```

- `canvas.width/height`：正整数；整页 `background` 与 `preview` 需匹配。
- `assets`：列出所有交付并被HTML/CSS/JS使用的 PNG，`role` 为 `background/icon/component`。新任务采用1.1清单：背景可选择CSS策略而**无需任何背景PNG**；只有实际纹理/图层必须以图片还原或用户明确要求背景PNG，才选择image策略并输出一份完整背景。独立图标应按需求提供；旧1.0清单仅保留兼容，不代表新验收标准。图标以独立文件逐个声明。**每个 `role=icon` 的真实PNG还必须通过 I0～I5 规范**（[逐图标紧裁/居中与保真](ICON_ASSET_ALIGNMENT.md)）：不可只满足“有Alpha”，四侧多余透明边距与可见主体偏心必须检测并修复。**当PNG内部仍有不透明黑/白矩形面板时，即使 Alpha 包围框完美居中也必须按B0～B4退回语义分层；图标=前景符号，原金样立体底托/衬底应作为独立组件或CSS层在HTML中重组。**
- `required_text`：必须由 HTML DOM 提供的页面主标题/菜单/关键静态标签；动态指标值由 JS 渲染的，静态校验可能无法断定，需浏览器实测。
- `required_interactions`：用户明确要求的菜单、切换、折叠、筛选等可操作状态名称。静态检测只能查源码存在，不验证事件行为；不能仅凭测试脚本通过说交互通过。
- 页面应按实际素材和业务字段调整；交付者不得通过删掉 required_text、required_interactions 或把图标改 role 为 component 绕开未完成的项目。

### 1.1 资源角色与背景策略（新交付强制）

- `background_strategy: "css"`：CSS实际绘制简单底色/渐变，不需要任何背景 PNG；若偷偷保留冗余PNG，资源目录检查会失败。
- `background_strategy: "image"`：只有不可替代图像背景或用户明确要求背景PNG时使用；此时必须交全画布、无透明洞的真正背景PNG。需要PNG但纯色背景的情况，应在`required_asset_roles`中记录用户明确的背景要求。
- **整体装饰面板框专用**：复杂渐变明暗、切角、四边连贯的完整面板框不是CSS普通`border`。在1.1清单的`required_frame_asset_ids`登记确需PNG的每个面板框ID；对应资源填写`role:component`、`component_type:ornamental_frame`、`frame_inner_rect:[x0,y0,x1,y1]`、`frame_render_strategy:fixed_overlay|nine_slice`。9-slice需补`frame_slice_px:[top,right,bottom,left]`。边框PNG只能保留四周完整边线、切角与光晕，**不可带任何面板背景色、顶部背景条或图标**。必须额外填写`frame_perimeter_px`（非周边透明）和`frame_icon_asset_ids`（关联的独立图标ID，若无则`[]`），图标逐一声明`role:icon`并输出不同的透明PNG；内容背景由CSS或独立背景负责，文字图表由DOM负责。详见[FBG0～FBG6纯边框与图标分离验收](ORNAMENTAL_FRAME_ASSET_QA.md)。
- `source_kind`：每张PNG记录`layer_export / masked / reconstructed`；背景若仅从合成截图蒙版抠取不能直接签收；仍需源层或高保真重建与人工核对。
- `reason_png`：每张PNG需要具体说明为什么不能稳定用DOM/CSS复现；不能按素材数量交差。复杂组件还需`edge_policy: "closed"`或有金样依据的`"intentional_bleed"`。
- 需要交PNG背景的用户明确要求应写进`required_asset_roles: ["background"]`，不得因为CSS方案方便而遗漏。
- 优先阅读[资产裁切角色与边缘质量](ASSET_ROLE_AND_EDGE_QA.md)，对可复用3D底托去重，检查中央地图与底座是否完整；文件名含`masked`不代表遮罩已经正确。
- 旧 `schema_version:"1.0"` 保持兼容，**不能当作新交付不做资产必要性/边缘检查的借口**。

## 三、可复用的静态校验

脚本：`scripts/verify_ui_delivery.py`，依赖 Pillow；以单个交付目录为输入，**只读**检查：

```bash
python -m pip install Pillow
python scripts/verify_ui_delivery.py delivery/
python scripts/verify_ui_delivery.py delivery/ --zip delivery.zip
python scripts/audit_asset_edges.py delivery/asset-manifest.json --root delivery --contact-sheet working/edge-review.png
python -m unittest discover -s tests -p "test_verify_ui_delivery.py" -v
```

检查：清单 schema 与相对路径、HTML/CSS/JS/preview 是否存在、PNG可解码、背景与画布尺寸、透明 icon 的像素 Alpha、资源在HTML/CSS/JS的实际路径引用、核心文字在 HTML 文本节点、ZIP 目录内容完整且不含路径穿越或缺失成员。

**不会自动检查的事项**：原图遮挡区域的真实性、是否残留文字/菜单黑底、图标美感、真实交互是否能点击、绘图/数据是否准确、浏览器视觉基线一致、用户实际下载。必须另按 [F0～F5金样视觉回归](ASSET_FIDELITY_REGRESSION.md) 对真实HTML截图、关键图标、地图与底座材质进行分区检查。**S0～S5通过不等于F0～F5通过，用户要求高保真时缺F4浏览器视觉对照不得宣称切图还原完成。**这些须通过100%实际 PNG审查、浏览器截图、逐一点击交互及用户验收核对。

静态脚本失败的输出应直接标 S1/S2/S3/S5 未通过；通过只是“静态交付结构可用”，不能代替 S4 浏览器运行和视觉/用户认可。

## 四、验收记录模板

```text
原图/用户已确认版本（来源与实际尺寸）：
本次要求：背景PNG、单个PNG图标、复杂装饰、HTML+CSS+JS、ZIP（分别列）
背景：文件路径/宽高/是否已人工确认无前景内容：
图标：数量/每个独立RGBA/是否残留底色与文字/实际被HTML使用：
组件：数量/是否原件或高保真重建：
页面：index.html、css、js 是否存在；业务文字是否DOM、资源路径是否有效：
交互：导航、菜单、筛选等逐项点击测试/未实现：
浏览器：运行方式/分辨率/截图/错误：
自动验证：命令/退出码/JSON结果：
ZIP：文件名、文件数、完整性检查：
用户端下载：已验证/未验证：
剩余失败项：
```

## 五、例外与防止钻空子

- 如果用户只要求一张“原图拆分成多个区域的矩形分块”，可按具体需求分块；**不可将矩形分块包装成独立图标/背景/HTML**。
- 如果原截图仅有一张，且无法获取隐藏图层，必须诚实标出“需要源图或视觉重建”而不是承诺无损提取。
- 如果用户没要求源码，按用户明确输出；如果提出了 `HTML`，**没有真实 HTML 就不得写交付完成**。
- 复杂高光阴影可以采用 CSS + 透明PNG 混合还原；小图标只应包含该图标可见的边缘/投影，不应把整条导航背景扣进图标。
- 已认可整图、背景、组件比例、色彩必须守住；切图和HTML重建并不授权重新设计页面。
