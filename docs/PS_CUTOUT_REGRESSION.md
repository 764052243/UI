# UI000｜Photoshop级切图、完整视觉单元与原生分辨率回归 V1.0

> 此文为规范与验证，不是已经替002修复了原大屏。**不会上传用户高清图、PSD、PNG或文件夹截图到公开仓库**。本轮只在当前会话私有环境读取到用户提交的 `deco_business_plinth_shared.png` 真实PNG用于测量。

## 1. 本轮真实原PNG检测

| 证据 | 实测 | 解释 |
|---|---|---|
| `deco_business_plinth_shared.png` | PNG，132×102，RGBA | 并非高清独立复合业务图标 |
| 非零Alpha有效包围框 | (2,29)～(130,100)，宽128、高71 | 图片上部有29px透明区，下部2px、左右各2px |
| 主体几何中心 | 比文件中心向下13.5px | 如果当成“独立紧裁的完整图标”，居中不通过 |
| 全透明像素 | 约51.6% | 存在独立Alpha，但不证明没有毛边 |
| 视觉意义 | 这是底托单独层，并非已认可金样中的“符号＋立体底托”整体 | 可以作为层叠资产，但不能冒充完整底部业务图标 |

**重要辨析**：29px顶部透明区可能是刻意为上方人物、货车等符号保留的叠加锚点。在`layer_anchor`模式不直接强行去掉，以免HTML层叠错位；但必须证明同组glyph存在、复合预览存在、最终HTML还原完整。用户若要求独立完整单件PNG，则应把整个业务图形（含顶层符号和底座）从源设计导出，并重新核对边缘。

当前没有PSD源层和实际HTML DOM坐标，**不能仅从这张PNG推断其黑色侧壁是否为脏边**；平台黑色体块可能是原设计的合法3D厚度。不能全黑删除。

## 2. 质量验证要求

实际编辑优先读取 `skills/photoshop-grade-asset-extraction/SKILL.md`，按 R0～R7 执行，工具只做数学证据。用于提交资源的 `cutout-quality-plan.json` 示例：

```json
{
  "schema_version": "1.0",
  "assets": [
    {
      "asset_path": "assets/components/deco_business_plinth_shared.png",
      "visual_unit": "bottom-business-customer",
      "layer_role": "plinth",
      "alignment_mode": "layer_anchor",
      "target_css_px": [100, 70],
      "target_dpr": 2,
      "source_native_px": [132, 102],
      "source_kind": "masked",
      "composite_preview": "preview/bottom-business-customer-composite.png"
    },
    {
      "asset_path": "assets/icons/icon_business_customer.png",
      "visual_unit": "bottom-business-customer",
      "layer_role": "glyph",
      "alignment_mode": "layer_anchor",
      "target_css_px": [100, 70],
      "target_dpr": 2,
      "source_native_px": [400, 280],
      "source_kind": "layer_export",
      "composite_preview": "preview/bottom-business-customer-composite.png"
    }
  ]
}
```

`100×70@2x`只是**验证公式示例**，不是从用户大屏推断出来的真实CSS尺寸。在此示例下，底托的原生132×102只有至少要求的200×140的约0.66倍（最短轴比），属于**原始像素不足**，不能通过小图放大到528×408来获得真实细节。实际需要002从HTML计算真实显示宽高和DPR，并在源PSD/矢量/3D工程记录native像素来源，不得编造。

```bash
python -m pip install Pillow
python scripts/audit_cutout_source_quality.py cutout-quality-plan.json \
  --root delivery --report working/cutout-source-qa.json
python -m unittest discover -s tests -p 'test_audit_cutout_source_quality.py' -v
```

`PASS`仅代表数学结构/同组素材/分辨率声明检查合规，**不代表PS已经运行、蒙版干净、真实原生像素已验证、视觉无毛边、用户已经认可**。

## 3. PA-01～PA-14 回归案例

| 用例 | 失败或验收场景 | 通过条件 |
|---|---|---|
| PA-01 | 底托PNG无上方业务符号但称“完整图标” | 同组glyph＋plinth＋完整复合预览；若用户要单张则另交完整复合PNG |
| PA-02 | 底托顶部透明空白29px强行裁掉 | layer_anchor应保护原锚点并复核层叠；独立tight才紧裁 |
| PA-03 | 文件内主体几何偏心且没有组装理由 | tight检查必须失败并返工 |
| PA-04 | 132×102低精度贴图直接放大4倍 | 原生像素不足不得称高清；回PSD/矢量/3D输出 |
| PA-05 | 所有黑色直接转透明导致底座实体缺失 | 非破坏层蒙版保留真实暗部，金样无缺层 |
| PA-06 | 发光边缘锐切导致蓝色光圈不完整 | 单独保留soft glow和半透明边，在黑白棋盘核对 |
| PA-07 | 斜边锯齿和错色 | 源分辨率/蒙版与抗锯齿修复后100%/400%可验 |
| PA-08 | 反复输出截图又重新抠图 | 以可编辑层/智能对象/矢量源导出，记录native尺寸 |
| PA-09 | 仅PS候选文件未实际在浏览器合成 | F0～F5真实HTML同画布截图必做 |
| PA-10 | 组件分层准确但缺整体复合预览 | 不能声称完整视觉单元验收通过 |
| PA-11 | 完整复合图PNG仍有外部黑底矩形 | 回原层或精修mask，不得改名冒充素材 |
| PA-12 | PS无法访问却声称PS已修复 | 明确未运行编辑器，记录R0/R2/R3/R4未测 |
| PA-13 | 所有底托切成多份重复PNG | 共享可复用底托；不同业务glyph分别导出/组合 |
| PA-14 | 用户已确认其他模块被顺手改色/变形 | 保留认可金样与非目标区域像素和布局，不允许改版 |

## 4. 002下一次返工实际完成标准

002读取可编辑源图层与实际PNG → 确认独立glyph、完整底托与完整视觉单元的交付目标 → 在PS或等效编辑器从真实层导出足够像素密度的alpha PNG → 修复蒙版毛边及光晕 → 提供分层/复合PNG、三底色质量预览、原生来源和目标DPR证据 → 在真实HTML重新组合并与认可原图逐区验收 → 交完整ZIP。任一关键项未完成必须标记未通过，不再以“切出PNG数量、脚本合成测试PASS”冒充用户真实交付。

**本轮000真实工作**：测量用户上传的底托PNG，修订规范和自动检查脚本及单元测试；**未接入Adobe Photoshop可操作插件，未打开PSD或修改用户原PNG，也未取得002的HTML工程**。
