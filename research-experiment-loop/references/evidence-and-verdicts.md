# 证据与裁决规范

## 证据四联

### 1. 数值 / 概率

报告主指标及分布，不只给单个均值。相关性用于发现关系，不能单独证明因果或有效性。
二维图像信号的统计必须说明采样单位、有效区域、对齐方式和参照标签。

### 2. 空间 / 视觉

把信号或 mask 叠在输入图上，检查坐标错位、投影边界、背景误删、动态漏删和纹理偏置。
最终 mapping 必须看 render；涉及几何污染时补 reference depth、rendered depth 和 diff。

### 3. 时序 / 上尾

报告 median、RMSE、max、最差窗口、失败持续时间和恢复行为。闭环系统尤其关注动作后的
未来信号变化；单帧图不能证明在线稳定性。

### 4. 因果干预

固定其余条件，只改变一个动作或消费路径。离线 oracle、drop-mask 和反事实重放可用于
估计上限，但必须标为 debug/oracle，不能冒充 strict-online headline。

## 对称裁决

正结果和负结果使用相同门槛：

- provenance 不完整时，两者都只能是历史线索；
- 视觉失败不能被 ATE 改善掩盖，ATE 失败也不能直接否定信号的 mapping 信息；
- 不因结果符合预期而省略重复 run 或安全集；
- 不因某个 consumer 失败就宣称原始 signal 无信息。

## 五层故障拆分

在给信号判死刑前逐层检查：

1. **Information**：原始信号是否含有目标信息？
2. **Calibration**：分数是否跨帧/跨序列可比较？
3. **Alignment**：reference/current、坐标和时序是否正确？
4. **Consumption**：soft tracking、hard mapping、lifecycle 的语义是否匹配？
5. **Feedback**：online 动作是否改变未来 pose/depth/signal 并形成恶性循环？

## Verdict 建议

- `promote`：满足项目晋级门槛，可进入更大验证或主线。
- `promising_unresolved`：效应重要，但 provenance 或机制仍未闭合。
- `needs_more_evidence`：现有证据无法区分主要解释，且有明确的下一判别实验。
- `negative`：在有效 provenance 和匹配 consumer 下被受控实验否定。
- `inconclusive`：实验设计或数据分辨率不足，无法裁决。
- `invalid_provenance`：外部 prior、代码漂移、错误参照或不完整口径使结果失效。

## 主张成熟度

Machine registry 中的 claim 至少区分：

- `hypothesis`；
- `supported-working-claim`；
- `replicated`；
- `paper-ready`；
- `retracted`。

`paper-ready` 需要跨序列、受控干预、图证和明确限制，不由单个漂亮数字触发。
