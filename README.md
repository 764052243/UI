# UI 设计师｜规范与设计资料库

本仓库用于保存 UI设计师项目的正式规范、专业 SKILL，以及经用户明确批准归档的设计资料。**指定存储位置不等于自动归档授权**；设计稿、历史图片和代码只有获得该批次明确批准后才能上传。

## 正式文档入口（以当前分支的实际文件为准）

- [项目提示词 V3.0](PROJECT_INSTRUCTIONS_V3.0.md)：精简的任务调度入口；只有用户在 ChatGPT 项目设置实际保存后才成为项目指令。
- [共同设计公约 V2.0](UI_DESIGN_CONVENTION.md)：跨大屏与业务系统的基线、参考图、配色、验收与归档规则。
- [严格1:1原图还原与资产证据 SKILL](skills/strict-one-to-one-fidelity/SKILL.md)：对“图标/立体底托仍与原图严重失真”等反馈，优先回真正原始PNG/源图层、锁定7处关键ROI并逐件对照，不得拿含看图器窗口或箭头的比较截图当原生金样；[零容差ROI检查器](scripts/audit_strict_1to1.py)、[PP-01～PP-14回归](docs/STRICT_1TO1_FIDELITY_REGRESSION.md)。**高清/重建/相似不等于1:1通过，静态整图像素一致也不等于HTML语义交付**。
- [局部精准修改与防需求倒退 SKILL](skills/precise-local-edit/SKILL.md)：跨001/002通用PLE0～PLE6最小变更契约；累计保留所有未通过属性，精准限定授权范围，验证目标确实改变及非目标冻结；[PNG微变更检查器](scripts/verify_micro_edit.py)支持旧/新位置变化、错误方向和越界修改检查。**具体页面/图标返工在对应设计师任务记录中处理，不写入公共SKILL。**
- [共用需求理解 SKILL](skills/design-requirement-understanding/SKILL.md)：001/002 都需先定位用户指代、反馈问题、变更维度和验收边界。
- [复杂设计分层 SKILL（Instant 优先）](skills/complex-design-instant/SKILL.md)：多参考图、多页面、多状态、严格还原、复杂大屏及连续纠错时加载；把复杂任务拆成可验收阶段。
- [整体装饰边框PNG与HTML叠层门禁](docs/ORNAMENTAL_FRAME_ASSET_QA.md)：原稿中具有切角、明暗过渡、金属高光及四边连续结构的面板框应按完整视觉单元切`assets/components/frame_*.png`，不得直接用普通CSS `border`替代；仍保留CSS用于简单规则描边。[交付检查器](scripts/verify_ui_delivery.py)支持`ornamental_frame`**纯边框PNG不带背景色、不带图标**，图标另交独立透明PNG；检测窄周边带外Alpha必须为0、框/图标文件分离、完整四边四角、资源引用和9-slice参数；**面板内大范围金属反射/漫射光不能因纯边框而删除**，复杂效果独立`effect_*.png`或等价CSS，实际HTML通过[局部光影亮度保留ROI检查](scripts/verify_visual_reconstruction.py)与人工原图对照。
- [图标原图色彩、脏黑描边和HTML可见主体居中专项](docs/COLOR_FIDELITY_HTML_ALIGNMENT.md)：新增CF0～CF7和CR-01～CR-12；[颜色与DOM视觉中心检查器](scripts/audit_color_layout.py)、[真实浏览器PNG Alpha与slot几何采集脚本](scripts/capture_ui_alignment.js)，防止“PNG很高清但色彩发灰/破败、CSS框居中但图形偏心”。
- [立体底座光晕裁断与黑边专项验收](docs/VISUAL_UNIT_GLOW_REGRESSION.md)：针对底部业务完整视觉单元的真实角度、暗色实体侧壁、外发光安全边、错位和金样ROI差异；[图层复合与原图ROI检查器](scripts/audit_visual_unit_composite.py)需要同视口原图与隐藏目标图层的浏览器underlay，不再用全页RGB均值掩盖底部错误。
- [无PSD高清切图与重建 SKILL](skills/source-free-hd-reconstruction/SKILL.md)：仅有合成图/低清截图、没有PSD/3D源层时**必须执行**，SVG精确重绘、程序化立体重建、从可编辑源导出高清PNG并与认可金样验收；**不能因为没有Photoshop停止制作**。[重建资源结构验证](scripts/verify_reconstruction_assets.py)、[无PSD高清重建12项回归](docs/NO_PSD_HD_RECONSTRUCTION_REGRESSION.md)。
- [Photoshop级精细切图与完整视觉单元 SKILL](skills/photoshop-grade-asset-extraction/SKILL.md)：用户指出图形只剩半截、底托分离后缺上方图标、PNG不清晰/毛边时强制加载；优先PSD/PSB/矢量/3D源层非破坏导出，不能把小图插值放大冒充高清。配套[原生像素与组合完整性检查器](scripts/audit_cutout_source_quality.py)、[真实底托测量与14项回归](docs/PS_CUTOUT_REGRESSION.md)。**此SKILL是工作流程，不等于已连接Photoshop编辑器。**
- [语义切图、PNG资源与HTML交付 SKILL](skills/semantic-asset-export/SKILL.md)：要求切图、透明图标、独立背景、HTML/ZIP时必读；禁止矩形截图冒充素材。[交付契约](docs/SEMANTIC_SLICING_DELIVERY.md)、[资产是否需要PNG、背景与毛边专项](docs/ASSET_ROLE_AND_EDGE_QA.md)、[PNG边缘诊断与三底色预览](scripts/audit_asset_edges.py)、[SL回归案例](docs/SEMANTIC_SLICING_REGRESSION.md)、[逐图标紧裁/居中标准](docs/ICON_ASSET_ALIGNMENT.md)、[非破坏性图标检查与归一化工具](scripts/normalize_ui_icons.py)、[金样视觉一致性与RV回归](docs/ASSET_FIDELITY_REGRESSION.md)、[静态验证器](scripts/verify_ui_delivery.py)、[实际HTML截图差异检测](scripts/verify_visual_reconstruction.py)。
- [高清与锁定区域保护 SKILL](skills/visual-fidelity-lock/SKILL.md)：**凡交付设计图或编辑已认可版本都必须执行**，核对真实清晰度、正确画布及无关设计冻结；[回归案例](docs/VISUAL_FIDELITY_REGRESSION.md)与[只读校验脚本](scripts/verify_ui_artifact.py)提供实际检测。
- [复杂设计分层方法论](docs/COMPLEX_DESIGN_METHOD.md)：ANCHOR→MAP→LAYOUT→VISUAL→VERIFY 的详细操作方式。
- [复杂设计回归案例](docs/COMPLEX_DESIGN_REGRESSION.md)：12项高风险场景，用真实设计输出检验，而非静态文档自称效果。
- [即时模式质量门禁 V1.0](docs/INSTANT_DESIGN_QUALITY_GATE.md)：风险分层、Q0～Q3验收、失败回退；复杂设计、严格还原和交付时按需读取。
- [即时模式设计回归用例](docs/INSTANT_DESIGN_REGRESSION.md)：12个待实测视觉、数据、交互与交付案例；不得把文档通过当作模型质量通过。
- [大屏设计 SKILL](skills/big-screen-design/SKILL.md)：数据驾驶舱、指挥中心、数据图表、工业监控。
- [系统 UI 设计 SKILL](skills/system-ui-design/SKILL.md)：登录、导航、门户、工作台、表单、查询、后台。
- [风格参考图目录](assets/style-previews/README.md)：仅存真实且已获授权的样图；暂无图片时不伪造链接。
- [V3.0 迁移说明](docs/V3.0_MIGRATION.md)：旧约束保留、文件映射与验证事项。
- [原 V1.0 公约留档](docs/archive/UI_DESIGN_CONVENTION_V1.0.md)：保留全文备查。

**独立图标质量及回退门禁**：图标切出后发虚/少笔画，首先区分资源管理器缩略图插值与PNG文件本身缺失；有清楚的原源图标应保留复用，不从低清截图二次切出。详见[图标原生源、完整形体与锐度验收](docs/ICON_ASSET_ALIGNMENT.md)，对于真独立RGBA源图层可用[无损可见像素检查](scripts/audit_cutout_source_quality.py)阻断二次模糊/裁断/变色；无源层仍须逐图金样人工验收。**000只提升通用规则/工具，具体系统图标修复归负责该页面的设计师。**

## PNG 图标裁边与居中验收

用户反馈导出的 `assets/icons` PNG **仍有冗余空白、主体偏心、大小不统一或黑色底块残留**时，优先读取 [图标紧裁、背景分离与居中规范](docs/ICON_ASSET_ALIGNMENT.md)，使用 [不覆盖源图的批量检查/紧裁工具](scripts/normalize_ui_icons.py) 对**实际原PNG**逐个检查和归一化，再运行 [完整切图包验证器](scripts/verify_ui_delivery.py)；最后还要与用户认可视觉金样进行人工逐图标/浏览器对照，不能将“Alpha/像素框合格”说成高保真完成。

切图验证脚本的合成单元测试可运行 `python -m unittest discover -s tests -p "test_*.py" -v`。相关 PR/主分支改动按 [.github/workflows/ui-asset-quality.yml](.github/workflows/ui-asset-quality.yml) 配置自动测试；**只有实际运行并取得结果才能声称 CI 通过**，仓库没有用户真实素材也就不能替001/002验收真实切图。

## 000 / 001 / 002 职责边界

- **000（公共规范维护）**：只负责总结跨任务共性根因，维护README、共同设计公约、通用/专业SKILL、项目提示词归档、通用测试工具和质量门禁；对规则最小修改、运行可复核测试、在授权范围内集成。**不因每次个别画面反馈持续给公共SKILL增加品牌名、像素坐标、色值或单张设计的补丁条款。**
- **001（系统UI执行）**：负责具体登录、门户、后台等系统页的真实图稿/源码修改、浏览器验证、交付和用户验收；具体缺陷继续留在其任务Issue或设计记录中。
- **002（大屏UI执行）**：负责具体大屏图稿、PNG/HTML切图与复现、原图对照、实际运行及用户验收；具体缺陷继续留在其任务Issue或设计记录中。
- 000发现反复失败时优先判断是否存在**跨场景可复用的机制缺陷**；若只是某页未执行、任务没有读取、或源文件缺失，应投递/更新原Issue，**不新建同义SKILL，不用改规则替代设计师真实返工**。Issue通知不自动唤醒任何设计师。

## 双模式读取与任务优先级

先读取共同公约和**共用需求理解 SKILL**，识别用户本轮是询问、反馈、精准修改、严格还原还是自主创作，确定目标区域、允许变更和禁止变更维度；然后再按页面类型加载一个或两个专业 SKILL。简单明确任务在内部快速完成需求定位，不要求用户反复确认；**跨多页/多图、严格还原、复杂业务或数据、连续纠错、视觉+源码混合交付等复杂任务，额外加载复杂设计分层 SKILL**。复杂任务与交付阶段按需读取即时模式质量门禁；**任何设计图交付或已认可稿局部修改还需读取高清与锁定区域保护 SKILL，并对真实最终文件检查清晰度和非目标一致性；涉及切图/PNG图标/背景/HTML源码时强制读取语义切图 SKILL，完成背景、图标、DOM和ZIP的分项验收**。这些机制与专业 SKILL 配合，不需要每轮复述全部规则：

| 专业模式 | 范围 | 应加载 |
| --- | --- | --- |
| 大屏设计 | 驾驶舱、指挥中心、工业监控、态势分析 | 大屏 SKILL |
| 系统设计 | 登录、门户、系统导航、工作台、表单与管理后台 | 系统 UI SKILL |
| 混合任务 | 同项目中同时存在上述页面 | 按页面分别加载，统一品牌但不重复构图 |

本轮用户明确指令、已认可的整张图片与源文件基线优先。**F01—F12** 是固定的主风格编号，**L0—L3** 是独立的立体等级；**BS/SU** 仅为场景分类标签，不能改写既有主风格含义。

仅在自主创作且用户明确要求「选择风格」时开启菜单，按公约为 F01—F12 每类分别展示一张独立原创视觉参考图。仓库无归档图片并不免除本轮展示责任；需在当前会话生成或如实说明未能满足，**不得编造已存在的图片链接**。用户明确认可某张完整图时锁定整张设计，后续只能按指定范围修改。

## 归档和历史保护

规范更新与设计成果归档是不同授权。本次仅处理规则和 SKILL，不上传或重排历史设计成果。既有归档分支 archive/ui-platform-v2-v4-v5-20261109 以及 projects 下的历史文件保持不变。

项目提示词 V3.0 规范文件已通过 [PR #2](https://github.com/764052243/UI/pull/2) 合入 main；公共需求理解 SKILL 已通过 [PR #3](https://github.com/764052243/UI/pull/3) 合入。后续规范改动继续采用独立分支检查；UI000 对本人负责的规范/Skill 已获持续自动合并授权，完成必要验证后可合并，不能覆盖他人改动、越权提交或跳过风险检查。用户已说明曾在 ChatGPT 项目设置保存项目提示词，但仓库文件更新并不会自动同步到该设置；GitHub SKILL 可读不等于工具自动安装，更不等于001/002实际设计已经通过用户验收。
