# UI000｜图标原图色彩、脏黑描边与HTML视觉居中专项 V1.0

适用：002大屏、001业务系统的PNG/SVG资源与HTML。用户本轮反馈新矢量图标比认可原图“失真、颜色有差异、破败感”，第四张HTML中指定位置不居中。**第三张原图为唯一已认可视觉金样**，前两张成品和第四张HTML是待修正候选。不得以它们覆盖原图基线。

## 一、具体根因：不能拿高清替代高保真

- 新SVG边缘虽锐利，但如果随意选“通用蓝”“通用橙”，丢失原版多层高光、内阴影和材质亮度，仍是严重失真；必须从**用户认可原图的同一区域**取样sRGB主色、饱和度、渐变位置及高光强度，禁止脱离基线套主题色。
- 黑色/灰黑描边或“破败感”可能源自截图抠图残留、半透明边RGB污染、插值锐化噪声或SVG笔画几何错误；也可能是原版合法的深色3D侧壁。**不得整体删黑或整图模糊**，只能按金样确定边缘属性，从真Alpha SVG/3D源重渲染、局部修正。
- Windows资源管理器缩略图不是颜色准确性验收环境；必须将实际PNG在透明棋盘、白/深色底和真正HTML原背景上查看，与认可原图同视口截图逐ROI复核。
- HTML里的 img 元素矩形居中不等于**PNG非零Alpha可见主体**居中。底部每个业务模块应以**独立图标视觉槽slot**作为中心，不能错误地要求图标居中于包含右侧文字的整卡片。若原图要求图标相对于槽位有偏移，应锁定期望偏移而不是强制归零。

## 二、CF0～CF7（色彩、边缘和布局三路验收）

| 关口 | 实际动作 | 失败标准 |
| --- | --- | --- |
| CF0 金样身份 | 锁定本轮用户第三张已认可原图；分别定义KPI、状态、底部业务五组图标的原图ROI | 用失败旧稿替代原图 |
| CF1 原图色彩 | 在原图同坐标区域锁定主色与高光/渐变、明暗对比、原始阴影；从实际sRGB取样 | 图标泛蓝、色相漂移、发灰、变旧 |
| CF2 真Alpha与脏边 | 矢量路径/蒙版分离合法暗实体、原有描边、柔性光晕和多余截图黑边；三底色检查 | 黑色脏外圈、暗色矩形背景、锯齿或乱删暗侧壁 |
| CF3 高清源码 | 从可编辑矢量/程序化3D真实源按CSS×DPR输出PNG，不重复放大低清截图 | 像素尺寸提高但几何/材质变形 |
| CF4 页面原位 | 复核原图同尺度下图标组合坐标和视觉槽；不得为美化对齐而移动已认可非目标区 | 全页看着差不多但图标比例/位置偏 |
| CF5 DOM可见中心 | 捕获浏览器真实slot、img矩形及PNG Alpha有效范围；比较可见主体中心与锁定slot偏移 | CSS居中但PNG内容依然偏心 |
| CF6 颜色差分 | 金样与HTML同视口、同DPR、逐个局部ROI核验彩色前景RGB差异、超差像素和整块ROI差异 | 图标色相不一致、发灰、黑边被整页均值掩盖 |
| CF7 双证据签收 | 保存HTML浏览器截图、DOM测量JSON、PNG与SVG源、金样diff和人工边缘报告；关键图标不合格继续返工 | 仅凭目录PNG数量/文件尺寸宣布完成 |

**工具范围**：scripts/normalize_ui_icons.py只用于独立前景符号；3D底托、发光与有空间锚点的层不强制自动紧裁。颜色、布局容差在检查前依据用户认可原图固定，不能为了通过测试扩大阈值。

## 三、新增可执行的色彩及HTML视觉几何门禁

1. scripts/capture_ui_alignment.js 在实际浏览器页面读出slot与图标img的getBoundingClientRect，利用同源图像Canvas像素Alpha得到**可见主体矩形**，同时报告DPR、object-fit、路径。跨域、CSS transform、非img等无法可靠获取的情况应报错，禁止编造布局数据。
2. scripts/audit_color_layout.py 接受金样截图、实际浏览器截图和浏览器布局JSON，对每张彩色/亮色前景逐ROI计算RGB误差与超差占比、整个ROI变化率，再对可见图形中心与对应slot中心做水平及垂直误差检查。不能把整个业务卡片作为图标槽位。
3. 只处理用户指明的异常区域，其他图层锁定；整页误差和上述局部ROI误差并行复验。脚本PASS仅说明结构/颜色数值满足输入门限，**不等于美术质量已被认可**。

### 浏览器实际采集方式

在真实HTML加载 scripts/capture_ui_alignment.js，或通过Playwright的addScriptTag注入，调用：

    await captureUiAlignment([
      {id:"bottom-production",slot:"#production .icon-slot",image:"#production .icon-slot img"},
      {id:"status-availability",slot:"#availability .icon-slot",image:"#availability .icon-slot img"}
    ]);

将返回的真实JSON保存为 delivery/reports/browser-layout.json。这里的选择器只是例子，002必须从**真实现有HTML**选择可见图标及其视觉槽；不允许为了方便检测新建一个虚假外层槽。

### 检查配置结构（值均为示意，不是本轮实测位置）

    {
      "schema_version":"1.0",
      "reference_id":"user-approved-third-image",
      "gold_reference":"reference/gold.png",
      "browser_render":"preview/html-render.png",
      "browser_layout_report":"reports/browser-layout.json",
      "color_regions":[{
        "id":"status-cyan",
        "roi":[10,10,90,90],
        "color_gate":{
          "sample_mode":"saturated",
          "brightness_min":90,
          "min_rgb_chroma":40,
          "min_reference_pixels":20,
          "max_mean_ink_delta":18,
          "per_pixel_tolerance":30,
          "max_outlier_fraction":0.15,
          "full_roi_tolerance":12,
          "max_full_roi_changed_fraction":0.2
        }
      }],
      "layout_checks":[{
        "id":"bottom-production",
        "expected_center_delta_px":[0,0],
        "max_center_error_px":[2,2]
      }]
    }

执行：

    python scripts/audit_color_layout.py delivery/color-layout-plan.json --root delivery --report working/color-layout-qa.json

如果原图前景不够饱和，使用sample_mode=bright或修正ROI，但**空样本不允许PASS**。颜色差分同时受几何偏移影响，失败时先核查DOM坐标，再复核色彩和Alpha。几何项以实际HTML视觉槽为基准，不等同于业务卡片中心。

## 四、本轮真实可读取的PNG信息（边界证据）

用户本轮挂载的 composite_production.png 为**132×117、RGBA**，非零Alpha包围框**(4,2)～(128,101)**，含半透明边缘；只凭此PNG不能证明色彩与第三张认可原图一致，更不能证明第四张HTML里图标的DOM位置居中。资源管理器截图中的其他图标没有逐个原PNG，因此黑色边缘像素仍须002读取真实交付文件复测。

## 五、CR-01～CR-12 具体回归

| 编号 | 场景与标准 |
| --- | --- |
| CR-01 | 原亮青蓝图标变成灰旧蓝，前景颜色门禁FAIL |
| CR-02 | 色相错误但亮度接近，前景RGB差异仍FAIL |
| CR-03 | 外部黑色粗描边不属于原图，ROI整块像素变化FAIL |
| CR-04 | 原图真实黑色3D侧壁不得为去黑边误删 |
| CR-05 | img框已居中，但非零Alpha主体偏心：DOM视觉槽门禁FAIL |
| CR-06 | 水平正确、垂直不居中：垂直偏差FAIL |
| CR-07 | 原金样确有视觉偏移：按锁定的期望偏移验收，禁止强制归零 |
| CR-08 | 把卡片中心误作图标槽中心：定位无效，需重新标slot |
| CR-09 | 跨域/路径/transform导致Alpha无法捕获：标未测，不得编造几何 |
| CR-10 | 原图和HTML截图画布不同：禁止拉伸后算合格 |
| CR-11 | ROI没有足够彩色/高亮原图前景：门禁FAIL，不允许空样本通过 |
| CR-12 | 工具PASS但人工仍见“破败感/形体不一致”：不能标视觉验收通过 |

**状态边界**：000负责规范与工具、合成测试、合并与投递；002负责真实SVG、PNG、HTML/CSS修改和浏览器复核。未取得002可运行HTML/原始资源包，不能声称实际颜色或居中已修复。
