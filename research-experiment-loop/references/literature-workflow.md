# 文献调研与理解工作流

文献工作负责建立可追溯的事实基座，为论文理解、协议恢复、实现选型和实验解释服务。它不是
experiment：检索或阅读不创建 `EXP`，也不能仅凭综述笔记晋升实验结论。

## 两层目录

- **Staging inbox**：协作者同步中的原始交付区，例如 `docs_from_<author>/` 或项目已有 inbox。
  内容可能变化，只用于交接；不得作为正式 claim 的稳定路径。
- **Canonical references**：项目 `references/`。只保存经过点名接收的快照、索引和 manifest；
  原始 PDF 等大文件可以保留在数据盘，索引记录绝对路径和 SHA256。

收纳是 snapshot，不是 move。确认没有传输进程后，复制命名明确的稳定输出，忽略 cache 和
checkpoint，记录 source、destination、author、source class、ingested_at 和 SHA256。除非交付方
明确确认，不删除 inbox，也不用软链接让 staging 冒充 canonical。

## 来源分级

| Source class | 定义 | 可支持的证据 |
|---|---|---|
| `primary` | 论文、补充材料、原始数据/曲线、原始代码发布 | 版本与 hash 核验后可支持事实和 claim |
| `author` | 作者维护的重实现、项目页、演讲或后续澄清 | 支持谱系与上下文；必须显式说明协议漂移 |
| `third_party` | 社区实现、独立复现、benchmark 或综述 | 比较和交叉验证，不能冒充原始协议 |
| `internal_synthesis` | 用户或 agent 的研读报告、代码映射和综合笔记 | 导航、解释候选和假说生成 |
| `lead` | 搜索结果、记忆、未核 URL 或推荐 | 只进入待核池，不支持事实主张 |

同一材料可从 `lead` 晋升为其他类别，但必须追加直接取证；不能因作者语气确定或多人重复而晋升。

## 六阶段闭环

### 1. Question And Search Plan

先写清研究问题、使用场景、包含/排除边界、目标时间范围和停止条件。记录检索端点、查询串、
检索日期和语言；不要用漫无边际的“找相关论文”替代问题。

### 2. Source Pool

建立候选 source ledger。每项至少记录 title、authors、venue、DOI/arXiv/URL、版本日期、来源类别、
检索位置和当前状态。此时默认是 `lead`，重复项按稳定标识合并但保留发现路径。

### 3. Screening

按预先声明的标准标记 include、exclude 或 pending，并给出一句理由。题名摘要筛选和全文筛选分开；
协议或实现选型问题优先保留原始论文、作者材料与可执行代码。

### 4. Extraction

从纳入来源提取可核验单元，而不是只写整篇摘要。每条至少包含：

- source ID、版本/hash、页码/章节/公式/图表或代码行锚点；
- 原文事实或短引文，以及独立的解释字段；
- 对应 claim、协议字段、实现差异或未决问题；
- 核验状态和下一取证动作。

论文事实、代码事实、本地复现观察和解释必须分栏。未知字段写 `unknown`，不能靠记忆补齐。

### 5. Synthesis

围绕问题综合共识、分歧、版本漂移、证据空白和替代解释。优先产出 source ledger、筛选记录、
extraction table、claim-protocol matrix 更新和一项最便宜的下一取证动作；避免堆叠逐篇摘要。

### 6. Claim Promotion And Closure

`lead` 或 `internal_synthesis` 不能直接支撑正式 claim。晋升前核对稳定来源、版本/hash、精确锚点、
直接证据和冲突来源。满足条件后，把事实写入 claim-protocol matrix；有实验产物时再通过
`register_artifact.py` / `register_claim.py` 闭环。结案记录：回答了什么、仍未知什么、排除了哪些
材料、适用版本和下一次重新检索触发条件。

## 推荐输出

```text
references/
├── INDEX.md
├── papers/                 # 主论文索引与轻量文本快照
├── implementations/        # code lineage、commit、license、协议漂移
├── understanding/          # 经快照的内部研读与代码映射
├── surveys/                # 问题级检索、筛选、摘录和综合
└── manifests/              # 每批 ingestion 的 source -> destination hash
```

大 PDF、代码仓和数据不必复制进控制面，只在索引中固定路径、版本和 SHA256。`references/` 是稳定
知识入口，不替代 `research/` registry、`DEVLOG.md` 或实验 artifact。

## 外部调研工作流适配契约

Claude 或其他工具可以保留自己的检索与深研步骤，不要求内部命令与 `researchctl` 一致。导入项目
时只需交付以下稳定字段：

1. question、scope、search endpoints、query strings 和 search date；
2. source ledger、screening decision/reason 和去重标识；
3. source version、URL/DOI、license（实现类材料）和 retrieval hash；
4. extraction table，带页/节/公式/图表/代码锚点；
5. synthesis：共识、冲突、证据缺口、替代解释和未决问题；
6. 明确区分 `verified`、`unverified lead` 与 `internal interpretation`。

接收方独立抽验关键来源和 hash 后再晋升。适配器可以转换文件格式，但不得自动把调研结论写成
canonical claim，也不得启动实验或改变项目 stage。

## 质量门

一次文献周期至少满足以下条件才算关闭：

- 问题和排除边界明确，查询可重复；
- 每个关键事实都有稳定 source ID、版本/hash 和精确锚点；
- 直接事实与解释分离，冲突来源未被隐藏；
- 实现推荐含 commit/tag、license、论文谱系和协议漂移；
- 输出进入 `references/` 并有 ingestion provenance；
- 有一个明确答案或诚实的 `unknown`，以及唯一下一取证动作。

