# 控制文档与写作策略

控制文档是机器 registry 的人读视图，不是第二套状态机。目标是让人和 agent 在一分钟内恢复方向，
同时避免每个生命周期动作机械改写六份 Markdown。

## 1. 三条原则

1. `research/project_state.yaml` 与 JSONL registry 保存机器事实；Markdown 只综合、导航和解释。
2. 按事件触发更新，不按命令触发更新。checkpoint、stdout 和逐点指标不进入根文档。
3. 同一事实只指定一个真源；其他文档使用 ID、路径或链接引用，不复制完整参数和时间线。

## 2. 文档职责

| 文档 | 唯一职责 | 更新触发 | 不应写入 |
|---|---|---|---|
| `AGENTS.md` | 权限、稳定契约、安全和目录边界 | 人员分工、执行权或基础设施边界改变 | 当前分数、逐 run 状态 |
| `CURRENT_STATE.md` | 当前判断、主要矛盾、唯一下一决策 | stage/主要矛盾变化，或实验结案改变判断 | commit、PID、完整历史 |
| `PLAN.md` | stage、北极星、退出门、活动路线、parked lanes | stage/gate/路线地位变化 | 已完成 run 时间线 |
| `TODO.md` | 近期未完成动作、owner、触发条件 | 任务产生、完成、阻塞或等待条件变化 | 结论全文和长期完成清单 |
| `DEVLOG.md` | 可复用决策、协议变化、结果裁决、迁移 | 发生持久决策或正式结案 | stdout、checkpoint 流水账 |
| `RESULTS_SCOREBOARD.md` | 已闭环且协议可比较的结果 | formal/replication 结案或被 supersede | probe 和不可比线索 |
| `runs/STATUS.md` | 进程、信标、进度和恢复点 | 进程启动、停止、完成、异常 | 科学裁决全文 |
| `reports/daily/` | 面向导师的当日叙事 | 需要交付日报 | 新的机器事实 |

不要为了“保持同步”在每次 new/freeze/checkpoint/close 后重写全部文档。通常一个实验结案只需要：
registry event、必要的 scoreboard 行、一个 DEVLOG 事件、CURRENT_STATE 和 TODO 的下一动作。

## 3. 统一页头

除 `AGENTS.md` 外，热控制文档使用三行页头：

```markdown
> Updated: 2026-07-17T03:57:38Z
> Maintainer: codex
> Source of truth: research/experiments.jsonl
```

- 时间使用 UTC `YYYY-MM-DDTHH:MM:SSZ`；需要展示本地时间时在正文补充。
- Maintainer 使用稳定角色：`user`、`codex`、`claude` 或项目约定名称，不写临时模型版本。
- Source of truth 指向机器真源；没有单一机器真源时写 `project contract` 或 `manual synthesis`。

## 4. DEVLOG 事件

DEVLOG 只追加少量持久事件。日期作为二级标题，事件使用：

```markdown
## 2026-07-17

### 2026-07-17T03:57:38Z | result | EXP-0003

- Actor: codex
- Summary: replay/epsilon 单位修正通过预注册稳定性门槛。
- Evidence: EVT-0025, ART-0012, ART-0015
- Next: 用户复核后决定是否预注册长程运行。
- Approval: not-required
- Git: control@21cc937; runtime-sha256=b8bea12b...
```

前四项必填；`Approval` 只在用户裁决、高风险变更或人工复核相关时填写；`Git` 只在代码、协议、
freeze、迁移或发布相关时填写。允许的常用 kind 为 `decision`、`protocol`、`result`、`migration`、
`workflow`。分支名表达工作内容，不包含 agent 名；作者和审批者写在事件或 PR 元数据中。

## 5. TODO 与协作

TODO 保持 3--7 个未完成动作，格式优先为：

```markdown
- [ ] [codex] 核对官方 DMC JSON 生成协议；trigger: 用户完成曲线复核。
- [ ] [claude] 整理 RSSM 研读稿；trigger: primary source 锚点核验完成。
```

短任务不另造 ID；跨 cycle 或需要 defer/resume 的任务进入 `research/tasks.jsonl` 并使用 `TASK-####`。
完成项在实验边界从 TODO 删除；持久结论进入 DEVLOG，普通完成历史由 Git 保存。

同一热文档在同一时段只设一个 owner。Claude 交付先进入 staging/discussion；Codex 核验后提升到
references 或控制文档。不要让两个 agent 同时直接修改 `CURRENT_STATE.md`、`TODO.md` 或 registry。

## 6. Git 与时间

- kit 的行为或规范变化走 branch + review；项目协议/运行代码走 `exp/EXP-####-slug`。
- 小型文字修正可在无 active experiment 且 owner 唯一时直接提交。
- 长 run 使用冻结 worktree；文档和分析在另一个 worktree/branch 更新。
- freeze 前分支和 commit 必须已推送；freeze 后不 rebase、squash 或 force-push。
- DEVLOG 不重复每个 commit。只有行为、协议、迁移或裁决与 Git 状态相关时记录 branch/commit。

## 7. 日报

日报从 registry、DEVLOG、scoreboard 和 run STATUS 汇总，不产生新事实。推荐结构：今日目标、完成与
证据、关键结果及权限、风险/阻塞、算力账、下一步、agent 分工说明。模板位于
`assets/project-template/control-docs/DAILY_REPORT.md.tmpl`。

## 8. 审计

运行 `researchctl docs` 检查：必需文档、统一页头、必需章节、PLAN stage、一页长度、TODO 已完成
积压、DEVLOG 事件字段和 `LATEST.md` 人工复核指针。命令只读；warning 不授权自动改写人工判断。

`researchctl docs --strict` 可用于发布或 freeze 前 gate。历史项目先 dogfood 并人工整理，不为通过
审计而删除仍有 provenance 价值的内容。

