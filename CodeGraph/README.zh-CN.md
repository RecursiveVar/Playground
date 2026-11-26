# CodeGraph —— 多技术栈代码图谱 Skill

[English](./README.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../LICENSE)
![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)
![Zero Dependencies](https://img.shields.io/badge/Dependencies-None-success)

把**任意**代码仓库转换为可交互的代码图谱工作台（`.codegraph/graph.html`）：无限画布 + 项目文件树 + 模糊搜索 + 数据流动画，单文件离线自包含，双击即开、无任何外部依赖。

技能自动识别项目类型并路由专属规则包——**JVM 后端**（SpringBoot）、**Web 前端**（React/Vue/Svelte/Next/Nuxt）与 **Node 服务端**、**移动端**（Flutter/Android/iOS/React Native）、**微服务系统**（网关、配置/注册中心、Go/Rust/Node 速查规则）、**Python 数据分析**（pandas/sklearn/Jupyter notebook、Django/FastAPI）。

除代码结构与数据库外，还能识别并展示**消息队列**（Kafka/RocketMQ/RabbitMQ/ActiveMQ/Pulsar/SQS）、**Redis 缓存**、**Elasticsearch / ELK 三件套**、**云服务**（S3/OSS/COS/MinIO/短信/邮件）等中间件依赖，以及前端页面/组件/状态管理、移动端本地存储、向量库与文件型数据集（csv/parquet/模型产物），发布/订阅、缓存读写、日志管道、数据读写各有专属节点与连线语义。

## 特性

- **节点即文件**：页面 / 组件与状态管理 / Controller / Service 接口与实现 / Repository / MyBatis 接口与 XML / 配置片段 / 数据集 / notebook / 数据库 / 中间件 / 客户端，各按代码文件原样呈现；纯数据形状降级为可点击的模型标注。
- **方法级调用链**：连线两端锚定在具体方法的出参 / 入参端口，参数与返回值类型可点击查看模型字段表；方法按源文件定义顺序列举；前端渲染/回调关系复用同一套 call 边。
- **完整数据访问形态上图**：XML 动态语句、MyBatis-Plus / 注解 SQL / JPA 派生查询，一律写明实际执行的完整 SQL（动态条件全展开、`?` 占位）；REST/GraphQL 请求写方法 + 完整路径 + 载荷；文件读写标注实际操作——经「SQL」端口或连线标注呈现。
- **17 种节点类型 / 18 种连线语义**：页面 / 笔记本 / 数据集加入 类 / 接口 / 抽象类 / 配置 / 数据库 / 消息队列 / 缓存 / 搜索 / 云服务 / 外部服务 / 客户端 / 管理端 / XML；调用 / 实现 / 注入 / 配置 / ORM / SQL / HTTP / WebSocket / 织入 / 绑定 / 消息 / 缓存 / 检索 / SDK / 日志 / 数据读写 / 状态流 / 启动，动画区分连续传输、一次性应用与纯逻辑关联，implements 则渲染为接口 → 实现类的渐变宽条（条内流线流动）。
- **5 个技术栈规则包**：SpringBoot / 前端 / 移动端 / 微服务 / Python 数据，每册统一回答入口、元素映射、连线判定、模型降级、数据访问形态、中间件、布局列序与安全红线。
- **工作台交互**：拖拽 / 缩放 / Ctrl 框选多选 / 右键菜单（节点 → 文件、连线 → 定位调用方与被调用方并闪烁目标行）/ 布局保存与导出 / 撤销 / 图例按类型整类显隐（眼睛开关 + 全部隐藏）/ 模糊搜索 / 深 / 浅色主题一键切换（顶栏按钮，跟随系统偏好并记忆）/ 节点右键「仅显示相关节点」聚焦子图（工具栏按钮或画布空白右键恢复全部）。
- **界面与图谱双语**：UI 内置中/英文，右上角一键切换；图谱正文语言跟随调用技能时所用的语言，字段也可写 `{ "zh": "…", "en": "…" }` 双语对象，一份图谱两种语言。
- **大图流畅**：路径采样查表、视口外连线剔除、拖拽增量重绘。

## 仓库结构

```
CodeGraph/
├── .agents/skills/codegraph/               # 技能本体
│   ├── SKILL.md                           # 工作流程：识别类型 → 分析仓库 → 编排数据 → 生成 → 自检
│   ├── references/
│   │   ├── graph-schema.md                # graph.json 四段式数据格式规范
│   │   ├── analysis-guide.md              # 语言无关判定规则（上图/降级/连线/布局）
│   │   └── packs/                         # 各技术栈规则包
│   │       ├── springboot.md              # SpringBoot / JVM 服务
│   │       ├── frontend.md                # React / Vue / Svelte / Next / Nuxt
│   │       ├── mobile.md                  # Flutter / Android / iOS / React Native
│   │       ├── microservices.md           # 多服务系统 + Go/Rust/Node 速查
│   │       └── python-data.md             # pandas / sklearn / Jupyter + Django / FastAPI
│   ├── scripts/
│   │   └── build_graph_html.py            # 模板 + graph.json → 自包含 graph.html（含校验）
│   └── assets/
│       └── graph.template.html            # 渲染器模板（__GRAPH_DATA__ 注入点）
├── demo/
│   └── canvas-demo.html                   # 订单模块完整工作台演示，浏览器直接打开
├── example/.codegraph/                    # 产物示例（订单模块：33 节点 / 47 连线 / 8 模型）
│   ├── graph.json                         # 数据源
│   └── graph.html                         # 双击即可打开
├── README.md
└── README.zh-CN.md
```

## 环境要求

- [Python 3.9+](https://www.python.org/) —— 仅构建脚本（`scripts/build_graph_html.py`）需要；被分析的项目本身不限语言。
- 任意现代浏览器 —— 打开生成的 `graph.html`。离线可用，无需服务器与任何依赖。

## 安装

技能就是一个含 `SKILL.md` 的目录，按你使用的 Agent 选择位置：

### Claude Code

复制到 `.claude/skills/codegraph/`（项目级）或 `~/.claude/skills/codegraph/`（用户级）。参见 [Agent Skills 文档](https://code.claude.com/docs/en/skills)。

### OpenCode

复制到 `.opencode/skills/codegraph/`（项目级）或 `~/.config/opencode/skills/codegraph/`（全局）。参见 [OpenCode skills 文档](https://opencode.ai/docs/skills)。

### Codex CLI / Gemini CLI / Cursor（提示词型 Agent）

这三类工具用命令/提示词文件而非 SKILL.md。先把本仓库（或仅 `.agents/skills/codegraph/` 目录）放进项目，再注册一条指向技能的命令：

**Codex CLI** —— 存为 `~/.codex/prompts/codegraph.md`：
```md
阅读 .agents/skills/codegraph/SKILL.md 并严格按其流程，把当前仓库转换为代码图谱（.codegraph/graph.json + graph.html）。
```

**Gemini CLI** —— 存为 `~/.gemini/commands/codegraph.toml`：
```toml
description = "构建多技术栈代码图谱"
prompt = "阅读 .agents/skills/codegraph/SKILL.md 并严格按其流程，把当前仓库转换为代码图谱（.codegraph/graph.json + graph.html）。"
```

**Cursor** —— 存为 `.cursor/commands/codegraph.md`，内容同 Codex 的提示词。

### ZCode

复制到项目级 `.agents/skills/codegraph/`，或用户级 `~/.agents/skills/codegraph/`（Windows 为 `C:\Users\<你>\.agents\skills\`），ZCode 自动发现。

## 从 1.x 升级到 2.0

2.0 将技能由 `springboot-codegraph` 更名为 `codegraph` 并泛化到全部技术栈。安装 2.0 **不会**自动更新已存在的 `springboot-codegraph` 旧副本——旧副本与新技能并存会导致触发歧义，请删除旧副本：

**用户级安装：**
```
:: Windows（cmd）
rmdir /s /q C:\Users\<你>\.agents\skills\springboot-codegraph

# bash / zsh（macOS / Linux / Git Bash / WSL）
rm -rf ~/.agents/skills/springboot-codegraph
```
**项目级安装：**
```
:: Windows（cmd）
rmdir /s /q <项目>\.agents\skills\springboot-codegraph

# bash / zsh
rm -rf <项目>/.agents/skills/springboot-codegraph
```
其它 Agent 在各自的技能根目录（`~/.claude/skills/`、`~/.config/opencode/skills/`、`.opencode/skills/`…）做同样清理。已有的 `.codegraph/` 产物不受影响：2.0 对 1.x graph.json 数据原样渲染（页面布局 localStorage 键不随更名变化）。

## 使用

在装好技能的仓库里对 Agent 说，例如：

- 「给这个项目画代码图谱」/ "map this project as a code graph"
- "map this React app as a component / data-flow graph"
- "draw the architecture of our microservice system (gateway + services)"
- 「把订单服务的调用关系画成图谱」

图谱正文语言跟随你提问所用的语言。也可以手工执行：

```bash
# 1. 按技能文档编写 <项目根>/.codegraph/graph.json
# 2. 生成页面
python .agents/skills/codegraph/scripts/build_graph_html.py <项目根>/.codegraph/graph.json
# 3. 双击打开 <项目根>/.codegraph/graph.html
```

## 产物说明

| 文件 | 说明 |
|---|---|
| `.codegraph/graph.json` | 唯一事实源：节点 / 模型 / 连线全部数据，含生成时布局 |
| `.codegraph/graph.html` | 自包含渲染页（模板 + graph.json 注入），勿手工编辑 |
| `.codegraph/layout.user.json` | 可选：用户手动编排后导出的布局，再次生成时自动合并 |

## 许可证

[MIT](../LICENSE) © RecursiveVar
