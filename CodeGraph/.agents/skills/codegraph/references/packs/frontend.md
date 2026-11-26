# packs/frontend.md —— Web 前端（React / Vue / Svelte / Next / Nuxt）

Web 前端仓库的专属判定规则。语言无关总则见 analysis-guide；本册回答 8 问 + UI 节点方法行结构约定。

## UI 节点方法行结构约定（call 边两端必须真实存在方法行并通过校验）

- **页面/组件节点 = 源文件级**；分区 label 如实描述内容：「导出 · n」（文件有显式导出，n=导出数）或「setup · n」（Vue `<script setup>`，对外面 = 全部顶层声明，n=顶层声明数）——不得为了凑「导出 · n」而漏行或多行。
- **入口行**：name = 组件/页面函数名（PascalCase，如 `OrderList`；Vue SFC 用文件名对应的组件名）；`sig` = **源码真实形态**——React 写函数签名（`function OrderList(props: OrderListProps): JSX.Element`），Vue `<script setup>` 无函数签名，sig 写 `<script setup> · src/views/OrderList.vue`，**禁止把 SFC 虚构成 React 函数签名**；tag = 路由（页面行，`/orders · lazy`）或框架标记；`ret.label` = **props 类型**（可挂 `model:` 引用——渲染边落在左端口，呈现“传进来的东西”，与 res 行“左侧标注=传的什么”惯例一致）；无 props 的组件省略 `ret`（左端口仍在，标注为空，不新造哨兵词）。
- **渲染关系（父→子 call 边）**：父入口行的 `outs` 追加一项，`args` = 本次传入的 props（每 prop 一项，≥2 渲染为胶囊端口；回调 prop 写 `() => onSelect` 形态）；call 边 `from:[父, 组件名, outs索引]` → `to:[子, 组件名]`。
- **回调（子→父 call 边）**：父组件文件中被传入的处理函数（`handleSelect` 等，含**非导出**的组件内函数——被传给其它节点即算参与跨节点调用）列为父节点方法行（被调用 → 左端口）；子组件入口行 `outs` 追加对应调用项（args=回调载荷）；call 边 from 子 to 父的处理函数行。**复用组件的回调槽位被多个父级共享时**：子组件同一次调用（同一 outs 索引）发多条 call 边到各父的处理函数行，是合法形态。
- **Pinia store**：`state` 工厂函数建为一条方法行（name=`state`，sig=工厂原文，`ret` 挂 store state 形状的 model 引用——state 形状注册进 models）；getters / actions 各自方法行（name=函数名，sig 原文）。
- **同文件其他导出**（自定义 hook、工具函数）被跨节点调用时列为方法行；未被跨节点调用不上图。

## 1. 入口与业务主干

路由表即入口清单——react-router `routes`、vue-router `routes`、Next `app/`/`pages/`、Nuxt `pages/`；每个路由级页面一个 `page` 节点。业务主干 = 路由入口 → 页面 → 组合的组件 → 状态/hook → api 模块 → 后端/external。单页无路由器的小工程：App 根组件为唯一 `page`。

**路由演示页降级标准**（路由表很大、过半为演示/占位页时）：逐路由判断——页面内有真实数据流（调 api / 读写 store / 提交动作 / 权限控制）→ 入图；纯静态演示页（只渲染文案或组件库示例、无跨节点数据流）→ 默认不入图，但需在交付说明里声明「共 N 条路由，入图 M 条，其余为演示/占位页」；路由总数 ≤ 10 的小工程全量入图。路由计数以路由表源码逐一清点为准（自检清单「图内计数逐一实测」）。

## 2. 代码元素 → 节点类型映射表

| 代码元素 | 处理 |
|---|---|
| 路由页面 | `page`（tag 写路由） |
| 可复用组件 | `class` + tag『组件』（页面私有子组件仅在承担数据流时上图，同样 class+tag；tagline 写“可复用组件：xxx”） |
| store 模块（Pinia / Redux slice / Zustand） | `class`（方法行 = actions/getters，结构按上方方法行约定） |
| hooks / composables | `class`（仅当被跨节点调用） |
| api 封装模块（axios 实例 / fetch 包装） | `class`，tag『API 客户端』 |
| 工具函数库 | 默认不上图 |
| vite/webpack/next.config 等构建配置 | `config` 片段 |
| `.env` | `config` 片段（值脱敏） |
| 样式 / 静态资源 / i18n 资源 | 不上图 |

## 3. 连线判定

| 关系 | 连线 |
|---|---|
| 页面渲染组件 | `call`（锚定形态见方法行结构约定，label 可写 `渲染`） |
| 子→父事件回调 | `call`（label `回调 · onSubmit`） |
| 组件 → store action/getter | `call` |
| 导航/跳屏（router.push / navigate） | `call`（落点 = 目标页面入口行） |
| 任何模块 → api 模块 | `call` |
| api 模块 → 后端（同仓 monorepo 直接是节点）或 external | `http`（label `GET /api/orders`） |
| GraphQL 端点 | 一个 `external` 节点（kv 行=查询/变更名）+ `http` 边 |
| mock（MSW handler、json-server） | `external` 节点 + `http` 边（label 注明 mock） |
| 同源静态 mock（public/ 下 JSON 的相对路径 GET） | `data` 节点（path=仓库相对路径）+ `io` 边（label `读 · fetch GET /mock/user.json`），**不建 external + http**——仓库内文件读取不算出网（analysis-guide §6） |
| localStorage/sessionStorage/IndexedDB | `cache` 节点（title `localStorage`，path `ls://<origin>`；res 行 = key 模式 / object store 名，ret=值对象）+ `cache` 边（label `读 · getItem` / `写 · setItem` / `删 · removeItem`） |
| WebSocket/SSE 订阅 | `external`（通道）+ `ws` |
| SSR/BFF 转发 | `http` |
| 微前端子应用边界 | 子应用整体一个节点（tag『微前端子应用』） |

**导航/跳屏 call 边示例**（落点必须是目标页面的入口方法行）：

```jsonc
// 页面 OrderList.vue 的入口行（节选）：第 0 次 outs = 导航调用，args = 目标路由与参数
{ "kind": "method", "name": "OrderList", "tag": "/orders · lazy",
  "outs": [ { "args": [ { "label": "route · /orders/:id", "model": "OrderRoute" } ] } ] }
// 对应连线：from = 本页入口行 outs[0] → to = 目标页入口行
{ "k": "call", "from": ["orderList", "OrderList", 0], "to": ["orderDetail", "OrderDetail"], "label": "导航 · /orders/:id" }
```

## 4. 纯数据结构 → models

TS `interface`/`type`/`enum`/zod schema 仅作数据形状 → `models`（**`file` 必写**）；props 类型、API DTO、store state 形状在端口 `model:` 引用；React `props.children` 等框架槽位不单列。

## 5. 数据访问等价物（出网请求的完整形态）

api 模块每个方法行 `sig` 必须写完整请求形态 `GET /api/orders?status={status} → Order[]`（方法+完整路径+查询参数+请求体结构+响应类型），禁止只写“调用订单接口”；GraphQL 在方法行 sig 写完整 query/mutation 文本；http 边 label 与之一致。

## 6. 中间件与外部依赖

后端 API（跨仓）→ `external`+`http`；后端 API（同仓）→ 直接节点；CDN/对象存储静态资源上传 → `cloud`+`sdk`；三方登录/支付/地图 → `external`+`http`；WebSocket 网关 → `external`+`ws`。

## 7. 布局列序（按 type + tag 判定）

`client`（若有独立端）→ page 列（按路由分组）→ tag『组件』的页面私有组件列 → 共享组件/状态列（tag『组件』与 store 类按是否共享分列）→ api 模块列 → `external`/后端/`cache` 最右列。

## 8. 安全红线

`.env` 中的 key、token、三方 secret 一律 `****`；内网域名可保留。
