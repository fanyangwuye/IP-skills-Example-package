# Agent 配置说明

本文说明如何让不同 agent 调用本仓库的 IP skills。核心原则：先安装依赖，再让 agent 能读取 `skills/*/SKILL.md`，并允许它运行对应 `scripts/*.py`。

## 1. Codex

Codex 支持把 skills 安装到用户级 skills 目录。clone 仓库后执行：

```powershell
cd "E:\Plans for 2026\ip-skills"
python -m pip install -r requirements.txt
python scripts/install_agent_skills.py --force
```

默认安装到：

```text
C:\Users\<用户名>\.codex\skills
```

之后新窗口可以直接说：

```text
使用已安装的 IP skills 跑完整流程，不要跳过角色图、场景图、故事板/拍摄表、首帧关键帧、I2V、尾帧衔接和连续性检查。
```

更新仓库后重新执行：

```powershell
python scripts/install_agent_skills.py --force
```

## 2. Claude Code

Claude Code 项目级推荐方式是让它读取仓库根目录的 `CLAUDE.md`。本仓库已经提供 `CLAUDE.md`，里面会指向四个 skill：

```text
skills/ip-copy-skill/SKILL.md
skills/ip-image-skill/SKILL.md
skills/ip-music-skill/SKILL.md
skills/ip-video-skill/SKILL.md
```

使用步骤：

```powershell
git clone <repo-url>
cd ip-skills
python -m pip install -r requirements.txt
```

然后在 Claude Code 中打开这个仓库目录。开始任务时可以说：

```text
按 CLAUDE.md 使用本仓库 IP skills 跑完整流程。
```

如果 Claude Code 没有自动加载项目文件，就手动把 `CLAUDE.md` 内容贴到项目说明/上下文里，或明确要求：

```text
先阅读 CLAUDE.md，然后读取 skills/ip-copy-skill/SKILL.md、skills/ip-image-skill/SKILL.md、skills/ip-music-skill/SKILL.md、skills/ip-video-skill/SKILL.md。
```

说明：`.claude/skills` 可以作为本机 Claude Code 的技能目录或符号链接目录，但它是机器本地配置，默认不提交；跨机器复用时以 `CLAUDE.md` 和 `skills/*/SKILL.md` 为准。

## 3. OpenClaw

OpenClaw 如果支持导入本地 skill/tool 目录，直接把以下四个目录加入 OpenClaw 的技能/工具目录：

```text
<repo>\skills\ip-copy-skill
<repo>\skills\ip-image-skill
<repo>\skills\ip-music-skill
<repo>\skills\ip-video-skill
```

每个目录都包含 `SKILL.md` 和可执行脚本。配置后给 OpenClaw 的调用句：

```text
使用 IP skills 的完整流程：文案/资产包 -> 角色图 -> 场景图 -> 故事板/拍摄表 -> 首帧关键帧 -> I2V -> 尾帧衔接 -> 下一段视频连续性检查。
```

如果 OpenClaw 需要把技能复制到指定目录，可以使用：

```powershell
python scripts/install_agent_skills.py --target "OpenClaw 的 skills/tools 目录" --force
```

如果 OpenClaw 不支持 `SKILL.md` 自动发现，就把 `AGENTS.md` 或本文件内容加入 OpenClaw 的项目知识/系统说明，并允许它运行仓库里的 Python 脚本。

## 4. 其他 Agent

通用接入方式：

1. clone 仓库。
2. 安装依赖：`python -m pip install -r requirements.txt`。
3. 让 agent 读取 `AGENTS.md`。
4. 让 agent 读取对应任务的 `skills/*/SKILL.md`。
5. 配置 API key 到环境变量，不要写入仓库。
6. 先跑离线测试，再做 live 小样。

通用调用句：

```text
使用本仓库 IP skills 跑完整 IP 生产流程，不要跳过角色设定、场景参考、故事板/拍摄表、关键帧、视频生成、尾帧衔接和连续性检查。
```

