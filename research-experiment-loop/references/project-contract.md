# 项目控制契约

## 推荐目录

```text
project/
├── AGENTS.md
├── CURRENT_STATE.md
├── PLAN.md
├── TODO.md
├── DEVLOG.md
├── RESULTS_SCOREBOARD.md
├── research/
│   ├── project_state.yaml
│   ├── profile.yaml
│   ├── experiments.jsonl
│   ├── insights.jsonl
│   ├── claims.jsonl
│   ├── artifacts.jsonl
│   └── cards/
└── figures/review/
    ├── LATEST.md
    ├── index.md
    └── EXP-####-slug/
```

项目已有目录优先，不强制搬迁大型产物。根目录控制文档应短，历史细节进入专题文档或归档。

## Workspace hygiene

目录整理属于 provenance，不是装饰。只在实验周期边界进行，并遵循：

1. 先列目录大小、搜索路径引用、检查所有 repo 的 tracked dirty 和注册 worktree；
2. 根目录只留热控制文档，专题内容通过单一索引进入，不堆兼容软链接；
3. cache、checkpoint、传输包和冷讨论可以进入带日期归档；
4. repo、worktree、dataset、weights、output、`video.npz` 和未登记 figure 默认保护；
5. 整理后复查 registry、artifact path、Git commit/dirty 和 human review 入口；
6. 同一 dump -> offline -> online 冻结周期内不做路径重排。

只有同类整理动作重复出现后才编写自动清理脚本；自动化必须默认 dry-run，不能按文件名猜测
实验产物是否可删。

## ID 与 JSONL

- Experiment：`EXP-####`
- Experiment event：`EVT-####`
- Insight：`I-####`
- Claim：`C-####`
- Artifact：`ART-####`

JSONL 每行一个 object，第一行是 `registry_meta`。追加记录优于重写历史；更正记录用
`supersedes` 指向旧 ID。记录值可以使用项目语言，schema key 保持英文。

## Provenance

最小 provenance：repo、branch、commit、tracked dirty、expanded config、数据切片、
输出路径、strict/online 约束和 external prior 状态。没有 commit 指纹的旧产物标为
`historical_only`，可用于提出假说，不可单独支撑 headline。

Canonical baseline 还必须绑定稳定 ID、commit、展开配置和评测协议。每个 v2 实验记录
`baseline_id`、唯一变量、预期动作和完成正向信号。

## Lifecycle

- 同时最多一个 active experiment；新卡不得覆盖未结案实验。
- 冻结使用 append-only event，保存展开配置 hash、数据切片、输出、seed/repeat 和禁用输入。
- 每个 run 的数据散步观察追加为 event，不改写原始预注册。
- 结案追加 closure event，并清空 active ID；`promote` 必须闭环 scoreboard、claim、artifact
  和 human review。
- 历史 schema v1 保持可读；新 schema v2 才强制阶段和 lifecycle 字段。

## Human Review

`LATEST.md` 指向当前最需要人判断的实验。只有真实图生成后才创建 `LATEST.png`，禁止放
占位图。每个 experiment 记录 `human_visual_confirmation`：`pending`、`confirmed`、
`disagreed` 或 `not_required`。

## Git 纪律

- 不使用 `git add .` 收纳研究目录；精确提交进入当前证据链的文件。
- 不删除不明来源 untracked artifacts。
- dump -> offline analysis -> online validation 尽量在同一 tracked commit 完成。
- runtime patch 默认关闭并有独立配置入口；负结果撤回 patch 或保持 default-off。

## Subagent 角色

- **read-only scout**：定位文件、旧结果和 provenance，不改代码；
- **blind visual observer**：不知道方法标签，独立描述图像现象；
- **mechanism red-team**：寻找泄漏、循环解释、错位和替代机制；
- **provenance auditor**：核对 commit/config/data/runtime prior；
- **synthesis reviewer**：只读 experiment/insight/claim registry，检查是否过度外推。

主 agent 负责修改代码、合并证据和最终裁决。子 agent 的 brainstorm 不能直接进入主线。
