# 局部精准修改的几何测量与发布门禁

适用范围：已认可UI图稿的精确像素位置、可见边框粗细、直角、指定参照物净空、垂直居中、占容器比例、局部颜色。补充 skills/precise-local-edit/SKILL.md V2.0，不引入具体页面、品牌色或坐标的公共规则。

## 失败根因与工具能力门禁

用户要求精确局部修改时，整图生成不是可靠的精修手段。即使显示了新图，也不能证明指定几何已达标或其它文字纹理没有漂移。开始前必须查找最后认可的原生图/编辑源，核验文件SHA256、画布和坐标系；分别命名目标与实际定位参照物（例如某条分隔线，不是邻近的首个标签），锁定旧/新位置允许ROI和剩余冻结区域。缺少这些事实即不得宣称严格精准。

优先选择源码HTML/CSS的目标选择器编辑、分层/矢量源图层调整、或对认可位图进行确定性局部合成。清除旧位置必须使用可信背景，禁止随意猜补。生成式编辑只能作为候选；如果平台自动展示/只能整图生成、无法先验收、或始终无法保留非目标像素，就停止重复该失败路径，明确能力边界并提供可测的源码或局部确定性编辑方案，不能声称覆盖平台工具规则。

完整发布前需同时运行：
- scripts/verify_micro_edit.py：针对认可源与候选，验证目标改动、旧/新位置必改与冻结区零差异。
- scripts/audit_ui_geometry.py：针对同一对文件，验证批准源SHA256以及候选可见边框、净空、居中、比例、取样颜色。

**两项均通过仍不等于图稿已经由用户验收。**

## 可复用的测量契约

按真正的原生画布像素标定[ x, y, width, height ]。水平净空 = 右实体可见bbox的左边界 - 左实体可见bbox的独占右边界；不允许改用另一个附近对象来代替指定参照物。用户要求“8px”的例子属于Issue #28，并非通用默认数字。

audit_ui_geometry.py 复用 verify_micro_edit.py 的 plan.json，在原字段之外增加：

    "approved_baseline_sha256": "<approved-original-PNG的64位小写SHA256>",
    "geometry": {
      "entities": {
        "target_border": {"roi":[35,15,67,70], "color_rgba":[241,121,34,255], "tolerance":0},
        "named_divider": {"roi":[107,0,3,100], "color_rgba":[50,60,70,255], "tolerance":0}
      },
      "constraints": [
        {"id":"border", "type":"rect_border", "entity":"target_border", "thickness_px":1},
        {"id":"clearance", "type":"horizontal_gap", "left":"target_border", "right":"named_divider", "expected_px":8},
        {"id":"center", "type":"vertical_center", "entity":"target_border", "container_rect":[20,10,85,80], "tolerance_px":0},
        {"id":"height", "type":"height_fraction", "entity":"target_border", "container_rect":[20,10,85,80], "expected":0.75},
        {"id":"fill", "type":"color_samples", "entity":"target_border", "color_rgba":[255,255,255,255], "offsets":[[2,2],[30,30]]}
      ]
    }

以上数值和RGBA均为**合成说明**，不是用户真实图稿的测量。geometry.entities 使用真实候选PNG在预先锁定ROI中按RGBA匹配测出可见bbox，并非直接信任计划填写目标坐标。一个ROI中存在多个相近色物体会污染测量，应合理缩小ROI或回到真实DOM/图层测量；不能为了通过检查随意放宽阈值。

通用断言：
- rect_border：四边和直角完整，并检测四侧中点内侧是否超出目标边框厚度；复杂渐变/抗锯齿金属框须另行ROI和人工验收。
- horizontal_gap：左右实体的可见像素净空及方向。
- vertical_center：实体bbox中心相对容器中心偏差。
- height_fraction：实体可见高度占容器的比例。
- color_samples：实体内特定位置的实际RGBA，不能证明所有底色、透明纹理或光影已经正确。

## 命令与PASS条件

在项目根目录、Pillow可用的环境中运行：

    python scripts/verify_micro_edit.py --before approved.png --after candidate.png --plan plan.json
    python scripts/audit_ui_geometry.py --before approved.png --after candidate.png --plan plan.json

可用 --report 路径保存分别的JSON结果。几何检查器退出码：0表示本工具配置的断言PASS，1表示断言FAIL，2表示输入无效或执行错误。第一条工具的退出码以原脚本为准。

两份报告与认可源身份、被测候选、同倍率/字体/视口、源码diff、旧位置清除、新位置出现、非目标零差异、真实HTML交互检查应当共同保存。SHA256相同只说明文件字节匹配，是否是用户认可源仍需原始交接证据。不支持的渐变/透明材质/阴影/纹理需单独可复核人工对照；没有原图不允许声称图稿已修。

## 合成回归与业务边界

    python -m unittest discover -s tests -p "test_audit_ui_geometry.py" -v
    python -m unittest discover -s tests -p "test_verify_micro_edit.py" -v

合成测试覆盖正确/错误净空、边框粗细、直角、居中、比例、白底、参照物找不到、基线哈希不匹配、画布不符和ROI越界。测试不包含用户的工作台原稿。001、002及之后获授权的设计执行员工共享同一通用门禁；当前真实设计返工由003在自己的任务环境完成。问题与实例仍在 Issue #28 追踪：https://github.com/764052243/UI/issues/28
