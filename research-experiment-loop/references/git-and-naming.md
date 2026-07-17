# Git 与命名契约

本规范补足实验生命周期之外的仓库生命周期。项目级 `AGENTS.md` 可收紧规则，但不得削弱
formal/replication 的 provenance 要求。

## 目录

1. 仓库角色
2. 分支生命周期
3. Commit、merge 与 tag
4. 标识符与文件名
5. 配置变量与单位
6. Freeze 前检查
7. 历史项目迁移

## 1. 仓库角色

明确区分以下角色，不能把 remote、commit 和 dirty 状态混写成一个 `repo`：

| 角色 | 职责 | Git 策略 |
|---|---|---|
| control repo | `research/`、热控制文档、配置、分析脚本、轻量审查产物 | 自有 `origin`，日常协作主仓 |
| runtime repo | 实际训练/评估代码 | 固定 commit；作者仓只读，修改走 fork 或 patch |
| third-party repo | 参考实现和依赖源码 | 只记录 remote/commit/license，默认不改 |
| artifact store | run、checkpoint、dataset、完整日志和大图 | 不进入 control Git，用 registry + hash 关联 |
| workflow repo | 可复用研究工具 | 独立版本；项目 freeze 记录所用版本/hash |

自有仓的 remote 使用 `origin`。作者或公共上游使用 `upstream`；如果 runtime repo 完全独立于
control repo，则在 lineage manifest 中记录上游，不为凑形式添加 remote。

## 2. 分支生命周期

推荐分支：

| 类型 | 格式 | 示例 |
|---|---|---|
| 主线 | `main` | 已闭环、可审计状态 |
| 实验 | `exp/EXP-####-short-slug` | `exp/EXP-0004-dqn-5m-updates` |
| 修复 | `fix/short-slug` | `fix/jax-sm120-runtime` |
| 文献/文档 | `docs/source-topic-date` | `docs/claude-dreamerv3-202607` |
| 基础设施 | `infra/short-slug` | `infra/repo-bootstrap` |
| 发布准备 | `release/short-slug` | `release/reproduction-v1` |

规则：

1. 只有代码、协议、分析或正式文档发生变化时才建分支；同一代码的不同 seed/run 不建分支。
2. 一个 active experiment 对应至多一个实验分支。只运行已冻结代码时可停留在 clean main。
3. preregistration 前可整理/rebase；provenance freeze 后分支历史不可 rebase、squash 或 force-push。
4. 长 run 使用冻结 worktree；需要同时修改文档或分析时，使用另一个 worktree，不能污染运行 worktree。
5. 结案、artifact 登记和 strict audit 完成后再合并主线。

## 3. Commit、merge 与 tag

建议 commit 主题：

```text
chore(repo): bootstrap reproduction control plane
docs(ref): ingest verified DreamerV3 reading snapshot
exp(EXP-0004): preregister long baseline
fix(runtime): make compatibility patch default-off
result(EXP-0004): close long baseline
```

- freeze 前至少有一个包含 executor、展开配置来源和实验卡的 commit。
- 重构与行为改变分开提交；重构使用行为锚点证明 parity。
- freeze 后使用 `--no-ff` 合并，保留被 registry 引用的 commit；不要 squash 掉证据 commit。
- 可创建不可移动的 annotated tag：`exp-####-freeze`、`exp-####-closed`。
- result commit 可以晚于运行，但不能反向声称它是运行时源码；freeze event 才是运行 provenance。

## 4. 标识符与文件名

机器 ID 保持短、稳定、无语义漂移；语义写入字段和 slug：

| 对象 | ID/名称 | 说明 |
|---|---|---|
| Project | lowercase kebab | `dreamerv3-reproduction` |
| Baseline | `BASE-####` 或项目已有稳定 ID | 名称、版本、协议独立成字段 |
| Experiment | `EXP-####` | 一个可证伪问题，不等于一次进程 |
| Event | `EVT-####` | append-only 生命周期事件 |
| Artifact | `ART-####` | 已存在的证据产物 |
| Claim | `C-####` | 可修订但不可覆盖的主张 |
| Task | `TASK-####` | advisory 跨循环任务 |

在引入正式 run registry 之前，运行 tag 必须以 experiment ID 开头，并包含任务、seed、预算语义和
UTC 时间：

```text
EXP-0004__breakout__s000__5050k-dec__20260717T120000Z
```

一个 experiment 可以有多个运行 tag。禁止 `final`、`new`、`latest2`、仅月日 `0717` 等不可唯一
定位的名字。`LATEST.md` 只能是指针，不得成为事实真源。

文件命名：

- Python/配置 key：`snake_case`；
- 目录 slug 和 Git 分支 slug：lowercase `kebab-case`；
- 固定控制文档：`README.md`、`PLAN.md`、`TODO.md` 等大写约定名；
- registry/card：保留机器 ID，如 `EXP-0004.md`；
- 人读文档正文可用中文，稳定文件名优先 ASCII，中文交付快照由 manifest 保留原名和 hash；
- 时间统一为 `YYYYMMDDTHHMMSSZ`，展示层可转换本地时区。

## 5. 配置变量与单位

任何预算、长度、容量、频率和 seed 都在名称中写明语义。优先使用：

```text
total_agent_steps
total_env_steps
total_emulator_frames
total_updates
replay_capacity_transitions
epsilon_decay_agent_steps
updates_per_env_step
eval_episodes
train_seed
env_seed
eval_seed
wall_seconds
checkpoint_bytes
```

禁用孤立的 `steps`、`frames`、`size`、`ratio`、`seed`，除非所在 schema 已给出唯一且不可误解的
单位。布尔量用正向语义，如 `use_symlog`、`enable_unimix`；避免 `no_disable_*` 双重否定。

配置应包含 `config_schema_version`。解析后的完整配置写入 run 输出，源配置与解析配置分别 hash。

## 6. Freeze 前检查

formal/replication 的最低门：

1. control/runtime/workflow repo 角色明确；
2. runtime 与分析源码都可由 commit 或独立文件 hash 恢复；
3. tracked worktree clean，关键 source-like untracked 文件为零；
4. branch/commit 已推送或有可恢复 bundle；
5. expanded config 存在，预算单位无歧义；
6. output tag 唯一且目录尚不存在；
7. seed/repetition、reference artifact、acceptance envelope 和停止条件已冻结；
8. compatibility patch 独立、默认关闭，并说明是否改变算法行为。

probe/oracle/instrumentation 若必须使用 dirty patch，保存完整 diff、状态、hash 和原因，证据权限保持
diagnostic/debug-only。

## 7. 历史项目迁移

首次 Git 化晚于实验时不得伪造历史：

- 写 migration note，记录导入日期、原始路径、运行前已有 hash 和缺失项；
- 首次提交命名为 snapshot/import，不声称是 pre-run commit；
- 旧证据继续引用原 freeze/hash；
- 从下一实验起执行 clean-commit-before-freeze；
- 迁移只在实验边界进行，之后运行 strict audit 与 workspace hygiene audit。

