# Workspace 与目录布局

目录布局的目标是降低入口熵、隔离生命周期和保护 provenance，不是追求最少目录或最大深度。

## 目录

1. 分层原则
2. Control repo 模板
3. 数据盘模板
4. 宽度与深度软约束
5. Staging、canonical 与 archive
6. 整理流程
7. 反模式

## 1. 分层原则

越接近根目录，入口应越少、职责应越稳定；越接近叶子，越允许同类文件高密度聚集。每一层只
回答一个分类问题：

1. 根：信息属于代码、配置、研究状态、文献、讨论还是报告？
2. 第二层：属于哪个用途、来源或生命周期？
3. 第三层：属于哪个实验、批次或主题？
4. 叶子：具体文件。

不要只因文件多就加层。`scores/` 中几十个同 schema JSON 是合理叶子；几十个代码、PDF、日志和
草稿混在一个目录则必须拆分。

## 2. Control repo 模板

```text
project/
├── README.md
├── AGENTS.md
├── CURRENT_STATE.md
├── PLAN.md
├── TODO.md
├── DEVLOG.md
├── RESULTS_SCOREBOARD.md
├── src/
├── tests/
├── configs/
│   ├── baselines/
│   └── experiments/
├── scripts/
│   ├── run/
│   ├── analyze/
│   └── admin/
├── research/
│   ├── project_state.yaml
│   ├── profile.yaml
│   ├── scheduler.yaml
│   ├── experiments.jsonl
│   ├── artifacts.jsonl
│   ├── claims.jsonl
│   ├── insights.jsonl
│   ├── tasks.jsonl
│   └── cards/
├── references/
│   ├── INDEX.md
│   ├── papers/
│   ├── implementations/
│   ├── understanding/
│   ├── surveys/
│   └── manifests/
├── discussion/
│   ├── claude/
│   ├── codex/
│   └── archive/
├── reports/
│   └── daily/
└── figures/
    └── review/
```

已有 runtime repo 不强制改成此结构。推荐新建轻量 control repo，再用 project state 绑定 runtime
repo；不要把大量控制文件无差别塞入作者仓主分支。

## 3. 数据盘模板

```text
/data-root/
├── projects/          # control repos
├── runtime/           # canonical algorithm repos
├── third_party/       # 只读参考实现
├── runs/
│   └── <project>/<EXP-ID>/<run-tag>/
├── artifacts/
│   └── <project>/<EXP-ID>/
├── papers/            # PDF/补充材料，索引和 hash 在 control repo
├── envs/
├── staging/
└── cache/
```

`runs/` 保存原始日志、checkpoint、resolved config 和信标；`artifacts/` 保存由 run 派生的图、表、
摘要和 verdict。不要让同一文件在两处都被当作真源。

## 4. 宽度与深度软约束

这些是触发 review 的 floor-warning，不是自动失败门：

- control repo 根目录通常保持 8--12 个职责目录；
- 人工日常导航路径通常不超过根下 4 层；
- 同一目录出现约 20 个以上异类人写文件时，按稳定维度拆分；
- 同类机器文件可以高 fan-out，不因数量机械加层；
- 连续两层都只有一个子目录时，检查中间层是否有真实语义；
- 根目录 cache、checkpoint、临时传输包或 notebook autosave 触发整理；
- 大于项目阈值的 tracked 文件触发 Git/LFS/外置存储审查。

优先按职责/来源/ID 分类，不优先按日期分类。日期只适用于 batch、日报和 archive。

## 5. Staging、canonical 与 archive

- `staging/<source>/<batch-id>/`：可变交付 inbox，不进正式 claim；默认 Git ignore。
- `references/`：核验后的稳定知识快照，必须有 source-to-destination manifest。
- `discussion/<author>/`：未收敛推理、红队和协作草稿。
- `discussion/archive/YYYY/MM/`：已关闭但仍有历史价值的讨论。
- `reports/daily/YYYY-MM-DD.md`：面向人的日报，不复制 registry 全文。
- run/archive 只改变存储温度，不改变 artifact ID 或历史路径语义。

`archive/` 不是垃圾桶。移入前记录关闭原因、索引入口和恢复方式。

## 6. 整理流程

只在实验边界整理：

1. 运行 `researchctl status`、strict audit 和 hygiene audit；
2. 列出大小、tracked/untracked、路径引用和注册 artifact；
3. 先写 relocation proposal，不直接移动；
4. 对 registry 路径使用正式 relocate/alias 机制；
5. 复制并校验 hash 后再切换 canonical 路径；
6. 不删除 staging、旧 run 或未知 untracked 文件；
7. 复查 Git、registry、review 入口和可恢复性。

同一 frozen dump -> analysis -> validation 周期中禁止重排路径。

## 7. 反模式

- 根目录出现 `final2.csv`、`new_plot.png`、`tmp.md`；
- `docs/` 同时承担文献、日报、运行日志和正式结果；
- 为减少根目录入口建立无语义的 `misc/`、`other/`、`old/`；
- 目录把多个轴重复编码，如 `configs/dqn/breakout/seed0/ablation/lr/`；
- 同一状态同时手写进 README、TODO、STATUS 和多个索引；
- 软链接让 staging 看起来像 canonical references；
- 为“整齐”移动 active run 或清理未登记 artifact。

