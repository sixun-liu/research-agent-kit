# 工作流演进治理

工作流可以持续改进，但演进本身必须可审计、可回滚，并且不能改变已经冻结实验的解释口径。
本机制管理 workflow repo 的变化，不授权 agent 自动改变项目目标、科学裁决或运行中的实验。

## 1. 不可破坏的边界

1. 只在实验边界评估和采用工作流更新；active/frozen 实验继续使用冻结时的版本。
2. 每个 formal/replication freeze 记录 workflow remote、commit、版本和 dirty 状态。
3. agent 可以发现问题、起草提案、实现分支和运行测试，但不能自行合并高风险修改、发布版本或让项目自动升级。
4. 工作流更新不得追溯改写历史 registry、verdict、freeze event 或证据权限。
5. 项目级 `AGENTS.md` 可以收紧通用规则；向 kit 反向推广前必须证明具有跨项目价值。

## 2. 什么时候值得修改

满足以下任一条件时才创建 workflow feedback：

- provenance、实验安全或可恢复性存在明确缺口；
- 同一摩擦在多个 cycle 或项目中重复出现；
- 现有规则互相冲突、无法执行或产生稳定误判；
- 可以用测试、审计结果或实际项目记录证明新机制降低成本或提高证据质量。

单次个人偏好、仅改变措辞且没有歧义、尚未发生的假想复杂度，不应立即扩展工作流。先使用项目局部
约定；确认可迁移后再提升到 kit。

## 3. 演进流程

```text
project feedback -> issue/RFC -> kit branch -> tests -> dogfood
                 -> reviewed release -> explicit project adoption
```

提案至少写清：

- 观察到的事实与可复现案例；
- 当前规则为什么不足；
- 建议改变的行为和保持不变的行为；
- agent 负担、兼容性、迁移和回滚影响；
- 验收测试与至少一个反例；
- 风险等级和需要谁确认。

实现使用 `fix/short-slug`、`feat/short-slug` 或 `docs/short-slug` 分支。先通过单元测试、skill
validation、`git diff --check` 和安装检查，再在非 active 项目或下一个新 cycle 上 dogfood。

## 4. 风险与权限

| 等级 | 示例 | 合并与采用 |
|---|---|---|
| low | 错别字、无语义变化的说明、实现 bug | 正常 review；patch release |
| medium | 新的可选字段、向后兼容命令、审计 warning | review + 测试 + dogfood；minor release |
| high | schema、生命周期、verdict、provenance、自动调度权限变化 | 用户明确确认；迁移脚本、回滚说明和 major release |

安全、成本或外部写入 hook 永远默认关闭。任何更新都不能扩大 agent 的服务器执行权、外部发布权或
科学裁决权，除非项目所有者明确修改项目契约。

## 5. 版本与采用

使用 SemVer annotated tag：

- `patch`：修复或文档澄清，不改变研究语义；
- `minor`：向后兼容的新能力或可选字段；
- `major`：需要迁移的 schema、生命周期或裁决语义变化。

在 `1.0.0` 前允许快速演进，但仍按上述三类记录影响。项目升级必须是显式 control event 或迁移
commit，包含旧版本、新版本、采用时间、迁移结果和回滚点。仅更新全局安装或软链接不等于项目采用。

## 6. 控制复杂度

演进不是只增不删。每次 release 都检查：

- 能否合并重复规则或删除已被更高层 invariant 覆盖的条目；
- 是否把罕见领域细节错误放进所有项目的必经路径；
- 新字段能否自动推导，是否真的需要人工填写；
- 命令、文档入口和状态真源是否仍然唯一；
- 旧兼容层是否达到预先声明的移除条件。

删除或合并规则也需要证据、deprecation 窗口和迁移说明。目标是让默认路径保持短，把领域细节留在
profile/reference，把异常流程留在按需文档。

## 7. 发布检查

发布前确认：

1. 工作树 clean，相关测试和 quick validation 通过；
2. changelog/RFC 说明行为、兼容性和迁移；
3. 高风险修改已有用户确认和可执行回滚；
4. 至少一个实际项目完成边界 dogfood；
5. annotated tag 不移动，发布 commit 已推送；
6. 项目不会自动跟随 `main`、`latest` 或可移动软链接升级。

