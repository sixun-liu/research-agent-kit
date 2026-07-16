# Research Agent Kit

本仓库存放可迁移的本地研究 agent 工具，不包含具体论文项目的运行时代码或实验数据。

当前 skill：

- `research-experiment-loop/`：阶段收敛、canonical baseline、实验预注册、冻结 provenance、
  证据四联、轻量诊断模板、长任务 checkpoint、跨循环中断调度、理论/实践平衡、数据散步、
  artifact/claim 注册、动态索引、机器审计和人工 review 入口；日常统一从 `researchctl.py` 进入。

## 安装

```bash
git clone <private-repository-url> research-agent-kit
cd research-agent-kit
./install.sh
./install.sh --check
```

安装器只建立两个非破坏性软链接：

- `$CODEX_HOME/skills/research-experiment-loop`；
- `~/.local/bin/researchctl`，可用 `--bin-dir` 改到其他 PATH 目录。

依赖为 Python 3、Git 和 PyYAML。已有目标若不是本仓库的软链接，安装器会拒绝覆盖。

## 项目迁移

研究项目应把工具、控制面、算法代码和大数据分开管理：

1. clone 本工具仓库并运行 `./install.sh`；
2. clone 项目的算法仓库，并 checkout 控制面记录的 commit；
3. clone 或复制轻量控制面仓库（热文档、`docs/`、`research/`）；
4. 在新控制面根目录运行：

```bash
researchctl relocate --repo /new/path/to/canonical-repo
researchctl audit --strict
researchctl status
```

`relocate` 更新可变的当前路径，并为 JSONL 中的历史绝对路径增加映射，不会重写
append-only registry。dataset、output、checkpoint、`video.npz` 和完整 figure 树不进入
工具仓库或控制面 Git，按需要用 `rsync`、对象存储或共享数据盘单独迁移。

未配置 Git remote 时，可先用标准 Git bundle 离线迁移：

```bash
git bundle create research-agent-kit.bundle --all
git clone research-agent-kit.bundle research-agent-kit
```

项目级 `AGENTS.md` 始终优先于这里的通用工作流。
