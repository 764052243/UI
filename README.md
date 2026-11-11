# UI 设计师｜规范与设计资料库

本仓库用于保存 UI设计师项目的正式规范、专业 SKILL，以及经用户明确批准归档的设计资料。**指定存储位置不等于自动归档授权**；设计稿、历史图片和代码只有获得该批次明确批准后才能上传。

## 正式文档入口（以当前分支的实际文件为准）

- [项目提示词 V3.0](PROJECT_INSTRUCTIONS_V3.0.md)：精简的任务调度入口；只有用户在 ChatGPT 项目设置实际保存后才成为项目指令。
- [共同设计公约 V2.0](UI_DESIGN_CONVENTION.md)：跨大屏与业务系统的基线、参考图、配色、验收与归档规则。
- [共用需求理解 SKILL](skills/design-requirement-understanding/SKILL.md)：001/002 都需先定位用户指代、反馈问题、变更维度和验收边界。
- [复杂设计分层 SKILL（Instant 优先）](skills/complex-design-instant/SKILL.md)：多参考图、多页面、多状态、严格还原、复杂大屏及连续纠错时加载；把复杂任务拆成可验收阶段。
- [语义切图、PNG资源与HTML交付 SKILL](skills/semantic-asset-export/SKILL.md)：要求切图、透明图标、独立背景、HTML/ZIP时必读；禁止矩形截图冒充素材。[交付契约](docs/SEMANTIC_SLICING_DELIVERY.md)、[SL回归案例](docs/SEMANTIC_SLICING_REGRESSION.md)、[金样视觉一致性与RV回归](docs/ASSET_FIDELITY_REGRESSION.md)、[静态验证器](scripts/verify_ui_delivery.py)、[实际HTML截图差异检测](scripts/verify_visual_reconstruction.py)。
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
