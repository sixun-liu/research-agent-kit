# Research Agent Kit

本仓库存放可迁移的本地研究 agent 工具，不包含具体论文项目的运行时代码或实验数据。

当前 skill：

- `research-experiment-loop/`：阶段收敛、canonical baseline、实验预注册、冻结 provenance、
  证据四联、轻量诊断模板、长任务 checkpoint、跨循环中断调度、理论/实践平衡、数据散步、
  artifact/claim 注册、动态索引、机器审计和人工 review 入口；日常统一从 `researchctl.py` 进入。

安装方式：将 skill 目录软链接到 `$CODEX_HOME/skills/`，并将 `bin/researchctl` 软链接到
`~/.local/bin/researchctl` 或其他 PATH 目录。项目级 `AGENTS.md` 始终优先于这里的通用工作流。
