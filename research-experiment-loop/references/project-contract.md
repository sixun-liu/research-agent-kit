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
│   ├── scheduler.yaml
│   ├── tasks.jsonl
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

## 信息所有权

| 入口 | 唯一职责 | 更新时机 | 不应保存 |
|---|---|---|---|
| `project_state.yaml` + JSONL | stage、baseline、实验/任务事件和 provenance 的机器真源 | 每个生命周期动作 | 人工长篇解释 |
| `CURRENT_STATE.md` | 一句话判断、当前主要矛盾、下一项决策 | 综合或方向变化时 | stage/commit/active ID 等可查询字段 |
| `PLAN.md` | 阶段目标、候选路线、退出门和 parked lanes | 阶段切换或 `SYNTHESIS` | 逐 run 日志和参数表 |
| `TODO.md` | 近期 3-7 个可执行动作、等待条件 | 开卡、结案、任务 defer/complete | 完成历史和实验结论全文 |
| `DEVLOG.md` | 持久决策、路线升降级、机制结论及证据 ID | 有可复用结论时 | stdout、逐帧数据和无裁决 brainstorm |
| `RESULTS_SCOREBOARD.md` | 协议一致的 formal 数字、图和竞品比较 | 正式结果闭环时 | probe/oracle 数字和不可比历史线索 |
| `discussion/` | 子 agent、红队和未收敛草稿 | 按需 | 正典 claim 和唯一状态 |

一次正常循环中，TODO 选择问题并链接新 `EXP`；运行事实只进 event/artifact；结案后按需要更新
scoreboard 和 DEVLOG，并把 TODO 收敛为唯一下一问题。PLAN 只在主要矛盾、路线地位或阶段退出门
变化时更新。不要为了“同步”在每轮机械重写全部文档。

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
- Research task：`TASK-####`
- Task event：`TEVT-####`

JSONL 每行一个 object，第一行是 `registry_meta`。追加记录优于重写历史；更正记录用
`supersedes` 指向旧 ID。记录值可以使用项目语言，schema key 保持英文。

历史查询使用动态入口，不维护手写索引：`researchctl.py list`、`show` 和 `find`。静态 Markdown
索引只适合稳定专题，不应用来复制 experiment/artifact/claim/task registry。

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

Schema v3 增加跨循环调度：实验预注册记录 `hypothesis_family/work_mode`，结案记录
`progress_type/failure_axis/wall_hours/compute_hours`；`scheduler.yaml` 保存项目阈值，
`tasks.jsonl` 保存 advisory task。调度器默认只读，显式 `--enqueue` 也不得自动启动实验。

实验可附带 `cycle_class=formal|probe|oracle|instrumentation`。后三类自动补全通用控制项，证据
权限是 diagnostic/debug-only，不能 `promote`。长任务使用 `checkpoint` event 追加进展和
compute delta；结案默认从 checkpoint 汇总 compute，并从预注册时间计算 wall time。调度任务
可 `deferred`、`waived` 或 `merged`，但必须记录原因，deferred 还必须记录恢复条件。

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
