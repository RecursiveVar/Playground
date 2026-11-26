---
name: codegraph
description: 将任意代码仓库——SpringBoot 等 JVM 后端、Web 前端（React/Vue）与 Node 服务端、移动端（Flutter/Android/iOS/RN）、微服务系统、Python 数据分析——转换为可交互的代码图谱工作台（.codegraph/graph.html）。当用户要求绘制代码图谱、生成架构图 / 依赖图 / 调用关系图 / 数据流图、可视化整个项目结构、看清模块间调用与数据流，或要求更新、重绘、修复已有的 .codegraph 图谱时使用——即使没有明说"图谱"，只要目标是把仓库画成一张可浏览的图，都应使用本技能。自动识别项目类型并路由专属规则包：支持数据库、消息队列（Kafka/RocketMQ/RabbitMQ）、Redis、Elasticsearch/ELK、云服务（S3/OSS）等中间件，前端页面/组件/状态管理与 REST/GraphQL 端点，移动端页面与本地存储，微服务拓扑与网关，以及 notebook/数据文件/ORM 查询等数据管线。
---

# 代码图谱（CodeGraph）

把任意技术栈的仓库编排成可交互的图谱工作台：左侧项目文件树、中间无限画布（节点 = 代码文件 / 资源 / 数据库 / 用户端，连线 = 调用与关系，带数据流动画）、顶部模糊搜索。产物保存在项目根目录 `.codegraph/` 下，`graph.html` 双击即可离线打开，无任何外部依赖。

**第 0 步自检（仅当新旧并存）**：若会话可见的技能列表中仍存在旧版 `springboot-codegraph`，把删除命令**交给用户自己执行**——删除用户/项目目录是破坏性操作，agent 不得代删（只读、并行、权限不足的环境一律不可执行）。命令（`<技能根>` 为实际安装位置，如 `~/.agents/skills` 或 `<项目>/.agents/skills`）：

- Windows cmd：`rmdir /s /q <技能根>\springboot-codegraph`
- bash / zsh：`rm -rf <技能根>/springboot-codegraph`

用户删除后再继续。用户暂不删除时：提示新旧并存会导致技能触发歧义（可能命中旧版拿不到 2.0 能力），随即按本册继续，不阻塞任务。

## 产出物与目录规范

```
.codegraph/
├── graph.json         # 唯一数据源，由 Agent 生成与更新（含生成时的原始布局）
├── layout.user.json   # 用户手动调整后的布局（可选，由用户从页面导出）
└── graph.html         # 自包含渲染页（模板 + graph.json 注入，勿手工编辑）
```

**graph.json 是唯一事实源**。更新图谱时只修改 graph.json，然后重建 graph.html；graph.html 里的数据是注入的副本。

**布局双轨制**（用户布局与生成布局都要保留）：

- graph.json 中每个节点的 `x/y` 是“生成时布局”，页面里“布局 → 重置布局”会回到它；
- 用户拖动节点后可用“布局 → 保存布局”（Ctrl+S，存浏览器 localStorage）与“布局 → 导出布局文件”（得到 `layout.user.json` 放入 `.codegraph/`）；
- **再次生成或更新图谱时**：若 `.codegraph/layout.user.json` 存在，先把其中的坐标与节点宽度应用到仍然存在的节点 id 上（新增节点沿用本次生成的坐标），将合并结果写回 graph.json 的 `x/y/w`，最后重建 graph.html。这保证用户的手工编排不会因为代码更新而丢失。

## 项目类型识别矩阵

| 仓库标记 | 判定 | 规则包 |
|---|---|---|
| `pom.xml` / `build.gradle` 且存在 `src/main/java` + spring 依赖 | SpringBoot/JVM 服务 | packs/springboot.md |
| `package.json` 且为**页面工程**（react/vue/svelte/next/nuxt/remix 依赖，或存在 `index.html` + `src/pages\|app\|views` 目录） | Web 前端（SPA/SSR/组件库） | packs/frontend.md |
| `package.json` 且为**服务端**（nest/express/koa/fastify/egg 依赖或 `bin` 字段，且无上行的页面工程特征） | Node 后端服务 | packs/microservices.md（Node 速查节） |
| `pubspec.yaml` | Flutter/Dart | packs/mobile.md |
| `AndroidManifest.xml` / `*.xcodeproj` / `Podfile`，或 `build.gradle(.kts)` 含 `android {}` 块 | Android / iOS 原生 | packs/mobile.md |
| `app.json`+`react-native` 依赖 / `app.config.*` | React Native/Expo | packs/mobile.md |
| `go.mod` / `Cargo.toml` | Go / Rust 服务 | packs/microservices.md（速查节） |
| 多个 `Dockerfile` + `docker-compose`/k8s manifests，或 `*.proto` 多服务共用、OpenAPI 聚合仓库 | 多服务系统/服务契约仓 | packs/microservices.md |
| `requirements.txt` / `pyproject.toml` / `setup.py` | Python 工程 | packs/python-data.md |
| 存在 `*.ipynb`（notebooks/ 目录或根） | Python 数据分析 | packs/python-data.md |

路由优先级：① 多标记混合仓（如 package.json + pom.xml 前后端一体）：按用户提问对象选主 pack，全仓图组合使用（前端节点规则取 frontend、后端取 springboot，client/admin 用户端机制衔接两册）；② Python 仓同时有 web 框架特征（django settings / fastapi 实例）与 notebook：以流量入口定——有 API 入口按 python-data 的服务端节，纯分析按 notebook 主干；③ 矩阵仍无法判定（罕见栈/无标记仓库）时读 analysis-guide §1 总则按“行为单元/入口/资源”兜底，并在生成后向用户确认——③ 仅在矩阵**确实无行可匹配**时触发，矩阵能判定的（含 Node 服务端行）不得绕过对应 pack。

## 工作流程

### 一、首次生成

1. **侦察仓库**（只读，不要急着写数据）：按上方矩阵判定项目类型；按对应 pack 的映射表与识别词表，找出入口、业务主干、数据访问、中间件与外部依赖、方法级调用链（谁调用了谁、传了什么、返回什么）。
2. **读规则**：先读 `references/analysis-guide.md`（语言无关判定总则），再按矩阵路由读 `references/packs/<对应册>.md`（栈专属映射与识别词表），最后读 `references/graph-schema.md`（JSON 字段格式）。文档是数据正确性的依据，跳过几乎必然编错。
3. **编排数据**：写出 `.codegraph/graph.json`（meta / models / nodes / edges 四段）。**图谱自然语言文本的语言跟随用户调用本技能时所用的会话语言**（中文提问 → 中文图谱，英文提问 → 英文图谱）；需要双语图谱时，把可翻译字段写成 `{ "zh": "…", "en": "…" }` 对象（见 graph-schema「可翻译字段」），页面右上角 中/EN 开关即可整体切换。
4. **生成页面**：`python <skill目录>/scripts/build_graph_html.py <项目根>/.codegraph/graph.json`，得到自包含的 `graph.html`。
5. **自检**（见下文清单），然后告诉用户打开 `.codegraph/graph.html`。

### 二、增量更新（代码变更后）

1. 读取现有 `.codegraph/graph.json`，对照本次代码变更做**差量更新**：只动受影响的节点/连线/模型，未受影响的节点保持原 id 与坐标不动；
2. 若存在 `layout.user.json`，按“布局双轨制”合并用户布局；
3. `meta.updatedAt` 写入本次时间戳；
4. 重建 graph.html 并自检。
5. 绝不重排全部 id——id 稳定是用户布局与差量更新的前提。

## 编排核心规则（速查）

- **降噪优先**：默认只画业务主干（入口 → 契约 → 实现 → 数据/外部），宁缺毋滥；详见 analysis-guide §0。
- **方法上图门槛**：只有参与跨节点调用的方法上图；模块/类内部自调用不画（避免自环）；详见 analysis-guide §2。
- **方法按源文件顺序**：节点内方法严格按代码文件定义顺序排列，不得重排；详见 analysis-guide §2。
- **模型降级**：纯数据结构（各栈数据载体）不作为节点，注册进 `models`，以可点击标注出现在端口类型上；详见 analysis-guide §3。
- **配置片段化**：一个配置文件可拆多个节点，`path` 用 `文件#片段` 区分，只列相关配置项；详见 analysis-guide §1。
- **id 稳定**：节点 id 一经发布不再更改（用类名小驼峰、文件名等天然稳定的词）。
- **差量更新**：代码变更后只动受影响的节点/连线/模型，绝不重写整个 graph.json；详见 analysis-guide §8。
- **布局估算不重叠**：同列节点按估算高度纵向排（卡片高 ≈ 130 + Σ各分区(24 + 30×行数)，下一节点 y ≥ 上节点 y + 估算高 + 60）；详见下方布局通则。

## 布局编排通则

按数据流从左到右分列排布，同列按依赖顺序纵向排；**各栈列序定义见对应 pack 的「布局列序」节**。相邻列留 120–200px 间距，同列节点留 60–80px；节点宽统一 **270px**。先保证无交叉遮挡，再考虑紧凑；卡片不得重叠（按估算高度直接保证）。

## 自检清单（生成后必做）

- [ ] 路由的 pack 与实际技术栈一致（按项目类型识别矩阵复核）；
- [ ] `edges` 引用的每个 node id / method 名都真实存在，且**每条连线（含 rel）的两端节点都能解析**（页面右键任意连线可「定位到调用方 / 被调用方」）；`call` 边的 `from` 方法声明了对应数量的 `outs`，索引一致；**无参调用的 outs 写 `{"args": []}`**（渲染为无标注端口），禁止伪造「无参 · xxx()」占位参数；
- [ ] **事实核对（最重要）**：desc / tagline / 字段表 / label 里的每条**机制性陈述**（生成算法、缺陷/错配声明、编排顺序、持久化行为）与**转写内容**（列名、引文、URL、签名、cell 序号）逐条回查源码原文——指不出对应代码行的陈述一律删掉或改写为已核实表述；「结构真实、叙述失实」同样是编造；
- [ ] **图内计数逐一实测**：路由数、权限码、菜单项、特征组数、端点数等凡写进图谱的数字，与源码逐一清点一致，不得估算或凭印象；
- [ ] 所有 `model:` 引用的类名都在 `models` 中注册；孤儿判定——无任何 `model:` 引用**且** `file` 不指向仓库内真实文件的条目删除，带真实 `file` 的契约类（proto / 事件 schema 等）视为文件树需要，可保留；
- [ ] 非 Java 栈的 models 条目均带 `file` 字段（仓库相对路径）；
- [ ] 合成节点（client/admin）与仓库外资源不虚构仓库路径：path 只写连接串（`browser://`、`ls://`、`https://`…）或留空，臆造的 `apps/…` 目录即编造；
- [ ] 所有落库 / 落盘 / 出网的数据访问写明实际执行形态（完整 SQL / 完整请求 / 完整读写操作），无占位话术；`sql` 边的 `fromPortId` 与语句行名（或带内联 SQL 的方法行名）一致；
- [ ] 同一**配置**文件拆多个片段节点时标题相同、`path` 带不同 `#` 锚点；非 config 的同文件分组（DI @Module、接口多实现等）用**单节点多分区**表达，不造同名卡；
- [ ] 按估算高度逐列核对 y 间距（完整算例见 analysis-guide §7），任何两张节点卡片不重叠（`build_graph_html.py` 会输出重叠预警）；
- [ ] `python scripts/build_graph_html.py` 成功运行；graph.html 在浏览器打开后：节点数、连线数与 graph.json 一致，无 JS 报错（控制台），动画正常；
- [ ] `meta.project` 与仓库名一致（它是页面布局 localStorage 的键）。

## 参考文档索引

- `references/analysis-guide.md` —— 语言无关判定总则：节点/方法/模型降级/连线语义/中间件建模/数据访问等价物/布局/差量更新。
- `references/graph-schema.md` —— graph.json 数据格式规范：节点类型表、models、方法行六种条目、连线锚点四形式。
- `references/packs/springboot.md` —— SpringBoot/JVM：映射表、MyBatis/JPA SQL 展开、Kafka/Redis/ES/云服务识别词表。
- `references/packs/frontend.md` —— Web 前端：路由入口、组件渲染/回调 call 边、store/api 模块、localStorage 建模。
- `references/packs/mobile.md` —— Flutter/Android/iOS/RN：页面与组件、VM/Repository 分层、平台通道、Room/drift SQL。
- `references/packs/microservices.md` —— 多服务系统：总览/详图双档、网关/配置中心/注册中心、Go/Rust/Node 速查。
- `references/packs/python-data.md` —— pandas/sklearn/Jupyter 与 Django/FastAPI：notebook 步骤行、data 节点与 io 边、ORM SQL 展开。
