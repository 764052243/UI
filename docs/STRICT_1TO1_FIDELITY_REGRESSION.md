# UI000｜原图1:1视觉复现的真实验收门禁（2026-11-12）

## 本轮用户反馈与证据边界

- 用户提供了**一张1484×836的对比截图**：其中包含完整大屏的视觉背景、居中的2345看图王窗口，窗口里为缩小的1672×941原图，红箭头指向外部大屏与原版的差异。**这张拼接/查看器截图不能作为原生金样**，因为浏览器/图片查看器窗口、箭头和缩放会污染原图像素。必须使用单独可解码的原始1672×941设计PNG或已认可源文件；若002此前会话已得到原件，应直接读取已有原件，不重复让用户提交。
- **红箭头的用户主诉**：左侧“平均响应”雷电图标与顶部KPI“总业务量”橙色叠层图标，以及底部生产调度、物流服务、仓储管理、供应链协同、客户服务五组蓝色立体视觉单元，存在轮廓/色彩/透视/厚度/外发光差异。用户认为这些依旧严重失真。**上述7个区域均为独立关键失败项**，不允许总体RGB平均值合格覆盖它们。
- 观察能确认的是视觉上的**差异风险和本轮用户否定**，不能仅靠画中画缩略图得出精确像素差值、哪位SVG节点错或误差百分比。002需取得原始金样、实际候选HTML截图与素材源，才可计算严格ROI误差。

## 两个不同目标不可混淆

| 目标 | 允许方法 | 验收结论的范围 |
| --- | --- | --- |
| **原始整屏静态像素外观复现** | 使用原生完整PNG做**对照/静态预览**，不修改其像素 | 在相同画布条件下可能全页零差异，但这**不算独立语义PNG切图**、更不算HTML互动 |
| **用户要求的HTML+语义图标可维护复现** | 源PSD/矢量/3D层原位导出优先；缺源时局部保真提取＋SVG/3D逐项重建 | 从已扁平化合成图不能唯一恢复Alpha、原层和被遮挡像素；若逐ROI仍不一致应标**未达到1:1**，不可把“高清”“相似”冒充严格还原 |

## 严格1:1检查器

`scripts/audit_strict_1to1.py` 需要：原金样PNG真实本地路径、原始SHA256、原生尺寸、非查看器拼图来源声明、同画布实际浏览器截图，以及**预先登记的所有关键ROI**。严格模式零容差逐像素RGBA差异，单个像素改变也判ROI失败；如整屏要求还原则`fidelity_scope=full_page`整屏还需零差异。

配置示例（**坐标为人工合成示例，绝不是这张大屏的真实ROI**）：

```json
{
  "schema_version": "1.0",
  "reference_id": "approved-native-bigscreen-v1",
  "reference_origin": "original_export",
  "reference_overlay_free": true,
  "reference_png": "reference/approved-native.png",
  "reference_sha256": "将此处替换为真实原图文件SHA256",
  "reference_native_size": [1672, 941],
  "actual_browser_png": "preview/actual-browser.png",
  "claim": "strict_pixel_1to1",
  "fidelity_scope": "critical_regions",
  "required_region_ids": [
    "status-lightning", "kpi-total",
    "business-production", "business-logistics",
    "business-warehouse", "business-supply", "business-customer"
  ],
  "regions": [
    {"id":"status-lightning","box":[10,10,50,50]},
    {"id":"kpi-total","box":[60,10,100,50]},
    {"id":"business-production","box":[10,70,50,120]},
    {"id":"business-logistics","box":[55,70,95,120]},
    {"id":"business-warehouse","box":[100,70,140,120]},
    {"id":"business-supply","box":[145,70,185,120]},
    {"id":"business-customer","box":[190,70,230,120]}
  ]
}
```

这里的SHA256文本不是有效哈希，需取真实文件摘要。示例box完全没有对应当前大屏的实际内容，只展示格式，**不能直接用来验收或宣称通过**。

```bash
python scripts/audit_strict_1to1.py delivery/strict-fidelity-plan.json \
  --root delivery --report working/strict-fidelity-qa.json
python -m unittest discover -s tests -p 'test_audit_strict_1to1.py' -v
```

## 002强制回归案例 PP-01～PP-14

| 用例 | 必须阻止或验收 |
| --- | --- |
| PP-01 | 从看图王窗口的缩小截图放大“原图”作为金样：拒绝 |
| PP-02 | 红箭头、滚动条、文件名栏污染对比图：拒绝进入严格测试 |
| PP-03 | 原设计真实1672×941图被改字节/换版本：SHA256失败 |
| PP-04 | 雷电图标略有色差、亮青轮廓/圆底错：局部ROI失败 |
| PP-05 | 橙色叠层图标材质/形体偏移：局部ROI失败 |
| PP-06 | 生产立体图标底座倾角、蓝光范围不一致：ROI失败 |
| PP-07 | 物流货车图标造型/厚度不一致：ROI失败 |
| PP-08 | 仓储立方体轮廓、底托不一致：ROI失败 |
| PP-09 | 供应链多块蓝色立方体光影不同：ROI失败 |
| PP-10 | 客服人物的外发光/立体底座偏差：ROI失败 |
| PP-11 | 省掉最后一个失败ROI后宣称全通过：覆盖范围不全失败 |
| PP-12 | 全屏几乎一样但仅1像素关键图标错：关键ROI失败 |
| PP-13 | HTML画布被缩放到与参考图差不多：分辨率不同失败，禁止拉伸比较 |
| PP-14 | 用整页PNG作HTML背景假装完成真实切图：像素比较可能PASS，但语义切图/交互门禁必须FAIL |

## 真实完成标准与限制

002在真正的原图、PNG资产、HTML项目上工作，交付逐ROI`GOLD / HTML / DIFF`证据、导出可编辑源、透明PNG、HTML/CSS/JS与ZIP及实际运行日志。**严格像素1:1会对浏览器字体/抗锯齿等产生零容差失败**：不能任意放宽后继续报“像素完全一致”，而是据实报告该差异和视觉容差是否经用户认可。单张扁平图无法数学上保证透明光晕与遮挡背景准确复原，必须诚实说明原生素材缺口、交付高保真近似而非谎称绝对无损1:1。

**本轮000完成范围**：SKILL、脚本、合成测试与GitHub规则接入；未实际接收002独立原始PNG/HTML或完成用户真实7处重绘，因此不声称视觉缺陷已解决。
