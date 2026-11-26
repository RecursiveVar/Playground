# packs/microservices.md —— 多服务系统 / 网关 / 配置中心 + Go/Rust/Node 后端速查

多服务系统与 Go/Rust/Node 后端的专属判定规则。语言无关总则见 analysis-guide；本册回答 8 问 + Go/Rust/Node 速查。

## 0. 粒度双档（本册核心决策）

- **单服务详图**（默认）：对选定服务按其语言路由——Java→packs/springboot.md、Python→packs/python-data.md、Go/Rust/Node→本册速查节。
- **系统总览图**（服务数 > 5 或用户问“整体架构/服务拓扑”时）：每个服务一个节点——`class` + tag『微服务』+ tagline 一句职责 + kv 行（端口/框架/暴露 API 数），服务间 = `http` 边（label=协议+端点，Feign/gRPC/REST 注明）。
- 两档不混用于同一张图。

**总览档补充口径**（消解 kv-only 服务卡与详图规则的结构性冲突）：

- **契约 models 的注册与孤儿判定**：总览档把服务间契约（proto / 事件 schema / Feign DTO）注册进 `models` 是**规定动作**——它们是图上 http 边与 API 清单的数据载体，即使没有 `model:` 端口引用也不算孤儿（SKILL.md 自检清单孤儿条款：带真实 `file` 的契约类视为文件树需要，可保留）。
- **数据依赖的边与锚点**：服务 → 数据库用 `sql`、缓存 `cache`、搜索 `search`、对象存储 `sdk`，与详图同 kind；区别仅在锚点——总览档服务卡无方法行，一律用**节点级锚点**（`fromNode`/`toNode`，graph-schema §4 明确允许），不必降级成 kv 描述。
- **启动时读入的数据文件**（如启动加载 products.json 预热）：文件在仓库内 → `data` 节点 + `io` 边（节点级锚点）；文件在镜像/仓外 → `data` 节点 path 写代码引用的路径并在 desc 注明来源。
- **节点 desc 的事实纪律**：总览档信息密度低，最容易用想象补细节——tagline/desc 里每句机制叙述（生成算法、编排顺序、缺陷声明）必须能在该服务源码中指出对应行，指不出就只写「负责 X 的一句职责」（analysis-guide §0 事实核对总则）。

## 1. 入口与业务主干

网关路由规则（Spring Cloud Gateway predicates / Nginx ingress / Kong）为流量入口；总览图主干 = 网关 → 核心域服务 → 支撑服务 → 共享基础设施。

## 2. 代码元素 → 节点类型映射表

| 代码元素 | 处理 |
|---|---|
| 网关（自建代码） | `class`（tag『网关』，方法行=路由规则） |
| 托管网关 SaaS | `external` |
| 各服务 | 详图按各 pack；总览为 `class`+tag『微服务』 |
| 配置中心（Nacos / Apollo / Consul / etcd） | `external` 节点 |
| 注册中心 | `external` 节点 |
| **k8s manifests（Deployment/Service/Ingress 等 yaml）** | `config` 片段节点——按资源拆（`k8s/emailservice.yaml#Service`、`…#Deployment`），kv 行列 port/targetPort/replicas/env 关键项，Service 的 port→targetPort 映射如实转写（这是核对链路的证据，不得臆写「错配」）；`config` 边 → 对应服务 |
| **压测器（Locust / k6 / JMeter / Gatling 脚本）** | `client` 节点（tag『压测』，path 留空或连接串）+ `http` 边到被压入口（label 注明工具与场景） |
| sidecar / Envoy / Service Mesh 基础设施 | 默认不上图（噪音）；用户明确要求时按 `external` 补充 |

## 3. 连线判定

| 关系 | 连线 |
|---|---|
| 服务间同步调用（同仓 monorepo 内可直接定位代码） | `call` |
| 服务间调用（跨仓/总览档） | `http`（label `gRPC · OrderService/Create` / `Feign · /api/orders`） |
| 服务 → 注册中心（注册与发现拉取） | `config`（启动一次性，虚线流动档吻合） |
| 各服务 bootstrap/本地配置片段 → 配置中心 | `config` |
| 异步解耦 | `mq`（识别词表沿用 packs/springboot.md §6.1） |
| 服务 → 数据库/缓存/搜索 | `sql` / `cache` / `search` |

## 4. 纯数据结构 → models

服务间契约（Feign DTO、proto 文件、事件 schema）→ `models`（`file` 指向契约源文件）；proto 在总览档可作为 external 节点的 kv 行列出。

## 5. 数据访问等价物（SQL 等价物）

详图档按各语言 pack 规则执行；总览档不涉及 SQL；跨服务查询聚合（BFF）在 BFF 节点 desc 写清编排的下游调用序列。

## 6. 中间件与外部依赖

配置中心/注册中心 = `external` + `config` 边（见 §3）；MQ/缓存/搜索/云服务按 analysis-guide §5 总则建模，识别词表沿用 packs/springboot.md §6（Node 对应物见速查节）。

## 7. 布局列序

网关最左 → 按依赖拓扑排服务列（被依赖者在右）→ 共享基础设施（DB/MQ/配置中心/注册中心）最右；异步消费者队列右侧再起一列（沿用总则）。

## 8. 安全红线

注册中心/配置中心凭证、服务间 mTLS 密钥、Nacos namespace 密钥 `****`。

## Go / Rust / Node 后端速查（单服务详图用）

- **Go**：`struct`+方法 = `class`、`interface` = `interface`；导出函数上图门槛 = 被跨包调用；`database/sql` 与 GORM 链式 → 完整 SQL 展开进方法行 `sql` 字段 + `sql` 边；gin/echo handler = 入口（tag 路由）；grpc-go 服务 = `interface` + 方法行。
- **Rust**：`struct`+`impl` = `class`、`trait` = `interface`；sqlx/diesel → 完整 SQL 展开；axum/actix handler = 入口。
- **Node（NestJS / Express / Koa，FastAPI 类比见 python-data 册）**：controller/router 模块 = `class`（方法行 tag 写路由 `GET /orders`）；provider/service = `class`；**构造注入 = `inject` 边**（NestJS constructor injection 与 Spring 语义同构，直接复用 kind）；TypeORM/Prisma/Sequelize → 完整 SQL 展开进方法行 `sql` 字段 + `sql` 边到 `database`；**Mongoose 等 NoSQL：方法行 `sql` 字段写实际执行的查询形态（filter/projection/sort 的 JSON 原文），`sql` 边照常使用**——“SQL 等价物”口径 = 最终发给存储的查询本体，弹窗照常展示；中间件识别（BullMQ→mq、ioredis→cache）沿用 springboot 册词表的 Node 对应物。
