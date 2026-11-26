# graph.json 数据格式规范

graph.json 由四段组成：`meta` / `models` / `nodes` / `edges`。文本字段的语言跟随会话（见 analysis-guide §0），代码原文（文件名、方法名、类型名）保持原样。下面用“订单模块”示例说明每个字段。

### 可翻译字段与多语言

图谱正文的**语言跟随用户调用技能时的会话语言**（中文会话生成中文图谱，英文会话生成英文图谱）。需要同一图谱支持中/英切换时，把自然语言字段写成双语对象 `{ "zh": "…", "en": "…" }`——渲染器按页面右上角当前界面语言取值，缺该语言时回退 zh → 首个可用值（单语言图谱切 UI 语言时正文保持原语言）。

可翻译字段（均可字符串或 `{zh,en}` 对象）：`node.title`（仅外部服务/中间件等描述性标题；代码文件名保持原文）、`node.tagline` / `node.desc` / `node.tags[]`、`sections[].label`、条目的 `desc` / `tag` / `sig`（res 行的操作形态说明；代码签名保持原文）、`ret.label` / `recv.label` / `args[].label` / `params[].label`、`kv.k`（端点/通道等描述性键名；配置键保持原文）与 `kv.v`、`model.stereo` / `model.desc` / `model.fields[][2]`、`edge.label`。**不翻译**（代码原文）：代码文件名、方法名、SQL、类型名、path、真实配置键。搜索索引包含全部语言，任何语言都能搜到。

```jsonc
{
  "meta": {
    "project": "demo-order",          // 项目名（同时是页面布局 localStorage 的键，必须与仓库名一致且保持稳定）
    "version": 1,                     // 图谱数据格式版本
    "generator": "codegraph@2.0",
    "generatedAt": "2026-10-17T12:00:00+08:00",
    "updatedAt": "2026-10-17T12:00:00+08:00"
  },
  "models": { /* 模型类注册表，见 §2 */ },
  "nodes": [ /* 节点数组，见 §3 */ ],
  "edges": [ /* 连线数组，见 §4 */ ]
}
```

## §1 节点类型（node.type）

| type | 标签 | 颜色 | 用于 |
|---|---|---|---|
| `class` | 类 | #2563eb | Controller、Service 实现、客户端类、切面类等 |
| `interface` | 接口 | #059669 | Service 契约、Repository、MyBatis 接口 |
| `abstract` | 抽象类 | #d97706 | 抽象基类 |
| `page` | 页面 | #0ea5e9 | 路由页面/屏幕（前端与移动端流量入口，见 packs/frontend、packs/mobile） |
| `notebook` | 笔记本 | #f59e0b | Jupyter notebook（方法行=cell 步骤，见 packs/python-data） |
| `data` | 数据集 | #64748b | 文件型数据（csv/parquet/模型产物），kv 行=列 schema，读写用 io 边（见 packs/python-data） |
| `config` | 配置 | #475569 | yml/properties/logback 配置片段（按片段拆分，见分析规则） |
| `database` | 数据库 | #db2777 | 数据库实例，rows 列出关键表的列；SQLite/Realm/CoreData 等嵌入式与移动端数据库（packs/mobile） |
| `mq` | 消息队列 | #ca8a04 | Kafka / RocketMQ / RabbitMQ / ActiveMQ / Pulsar / SQS 等 broker 实例，rows 列出 Topic / Queue（见 §5） |
| `cache` | 缓存 | #dc2626 | Redis / Memcached 实例，rows 列出 key 模式与数据结构（见 §5）；浏览器 localStorage/IndexedDB、移动端 SharedPreferences/NSDefaults/AsyncStorage 等本地键值存储（packs/frontend、packs/mobile） |
| `search` | 搜索引擎 | #14b8a6 | Elasticsearch / OpenSearch 集群，rows 列出索引（见 §5）；Milvus/FAISS/Qdrant 等向量库（packs/python-data） |
| `cloud` | 云服务 | #a21caf | S3 / OSS / COS / MinIO、短信、邮件、推送等云上托管服务（见 §5） |
| `external` | 外部服务 | #0891b2 | 第三方/内部微服务、WS 网关、Logstash / Kibana 等自建服务端；GraphQL 端点、mock 服务、平台通道（channel://）、配置/注册中心、托管网关（见各 pack） |
| `client` | 客户端 | #a855f7 | C 端应用（App/Web 前台） |
| `admin` | 管理端 | #6366f1 | 运营/后台管理界面 |
| `xml` | XML 文件 | #9a3412 | *.xml（如 *Mapper.xml），每条 SQL 一个语句行 |

不存在“记录类/record”类型：纯数据类一律降级进 `models`。
中间件按**功能**归类而非按厂商：AWS SQS 用 `mq`、云 Redis 用 `cache`、阿里云 ES 用 `search`，厂商放 tags（`AWS`、`阿里云`）。

## §2 models —— 模型类注册表

DTO / VO / PO / 领域事件等纯数据类（各栈数据载体：Java Bean、TS interface、dataclass、proto 等）不作为节点，注册为可点击的端口标注。键为类名。

`models` 允许为空对象 `{}`：纯过程式仓库（脚本、面向过程代码）没有可降级的数据类时，这是合法形态，端口标注不挂 `model:` 引用即可。

```jsonc
"models": {
  "CreateOrderCmd": {
    "stereo": "DTO · 命令对象",        // 惯用：DTO/VO/PO/事件 + 一句定位
    "path": "com.demo.order.api.dto",   // 来源定位：Java 包名或按 pack 约定的模块路径
    "file": "src/main/java/com/demo/order/api/dto/CreateOrderCmd.java",
                                         // 可选：仓库相对路径。非 Java 栈必写，用于文件树定位；
                                         // 缺省时渲染器按 Java 包名推导（src/main/java/ + path 转目录 + 类名.java，兼容 v1 数据）
    "desc": "下单请求的命令对象，由请求体反序列化而来。",
    "fields": [
      ["userId", "Long", "下单用户"],   // [字段名, 类型, 含义说明]
      ["sku", "String", "商品 SKU 编码"]
    ]
  }
}
```

节点数据里凡出现 `"model": "类名"`，都必须能在 models 中找到。

## §3 nodes —— 节点

```jsonc
{
  "id": "impl",                          // 稳定标识：差量更新与用户布局都靠它，一旦发布不要改
  "type": "class",                       // 见 §1
  "title": "OrderServiceImpl.java",      // 文件名（含扩展名）；外部资源用服务名
  "tagline": "业务实现",                  // 一行内的角色定位
  "path": "src/main/java/com/demo/order/service/impl/OrderServiceImpl.java",
  // path 规则：项目内文件用仓库相对路径（必须真实存在，不得虚构）；配置片段用 文件#锚点；
  // 数据库用 jdbc:…；消息队列 kafka://…；缓存 redis://…；搜索引擎 es://…；
  // 云服务 oss://bucket、s3://bucket；外部服务 https://…；WS 用 wss://…；
  // 客户端/管理端（client/admin）是合成节点，不对应仓库文件：path 只写连接串
  // （browser://<origin>、ls://<origin> 等）或显式留空，禁止臆造 apps/… 之类仓库路径
  "desc": "OrderService 默认实现：编排仓储、支付与事件推送；写路径带事务与幂等保护。",
  "tags": ["@Service", "事务", "订单"],   // 检索关键词：注解、框架、模块名
  "x": 800, "y": 340, "w": 270,          // 生成时布局；w 统一为 270（可省略，缺省即 270），首图按 270 排布；
                                         // 用户在页面手动调宽后经「保存/导出布局」回写，Ctrl+Z 可撤销调宽
  "collapsed": false,                    // 可选：初始折叠（仍显示简介与标签）
  "sections": [ /* 内容分区，见下 */ ]
}
```

### sections 分区与条目

每个分区 `{ "label": "方法 · 3", "items": [...] }`。常见分区：方法 / 字段 / 配置项 / SQL 语句 / 表结构 / 织入点 / 端点 / 通道 / Topic / Key 模式 / 索引。条目有六种 kind：

**method（方法行）** —— 只有参与跨节点调用的方法才出现：

```jsonc
{
  "kind": "method",
  "name": "placeOrder",                          // 画布行上显示的名称，也是连线引用的键
  "sig": "+ placeOrder(CreateOrderCmd cmd) : Order",  // 真实签名（各语言原生形态：Java UML 式、TS/Go/Dart 原生、Python def 形态），点击弹窗展示
  "tag": "@Transactional",                       // 可选小标签：路由(GET /orders)、注解等
  "desc": "校验并落库新订单，随后发起支付扣款并广播订单创建事件。",
  "ret":  { "label": "Order", "model": "Order" },// 返回值标注（model 可省略）
  "outs": [                                       // 每次对外调用一项 → 右侧一个端口
    { "args": [ { "label": "Order order", "model": "Order" } ] },
    { "args": [ { "label": "PaymentCmd payment", "model": "PaymentCmd" },
                { "label": "String idempotencyKey" } ] }   // ≥2 参 → 渲染为胶囊端口
  ]
}
```

- `ret` 只在方法**被画布内其它方法调用**时渲染为左侧端口；label 为 `（无返回值）` 表示 void——该标记由渲染器按界面语言本地化（英文界面显示 `(no return value)`），数据里中英任一写法均可。JS/TS 的 `Promise<void>`、Python 无返回值等场景，行标注一律用哨兵写法，sig 内保留语言原生形态。
- 画布上的方法行按段分配：左·返回值类型 / 中·方法名与标签 / 右·出参类型，三段俱全时各占行宽 1/3；**左侧无返回值（未被调用）或右侧无出参（无对外调用）时对应段不渲染，剩余两段各占 1/2**（两段皆空时方法名占满行宽），任何宽度下互不重叠；段内放不下时省略号截断。节点卡片初始宽度统一 **270px**（首图布局按 270 排布），用户可在页面右缘手动调宽调窄（220–640，Ctrl+Z 可撤销）。
- `sql`（可选）：该方法**直接向数据库发出 SQL**（MyBatis-Plus BaseMapper/Wrapper、`@Select` 注解、JPA 派生查询等，不走 XML）时填写，值 = 实际执行的完整 SQL（展开规则见 packs/springboot.md）。带此字段的方法行右侧渲染「SQL」可点击端口（弹窗展示完整 SQL 与入参），`sql` 连线从该端口连到数据库节点，效果等价于 XML 语句行。
- `recv`（可选）：方法作为**中间件连线落点**（MQ 消费、回调）时，渲染在左侧端口旁的"入口消息"标注，形如 `{ "label": "OrderCreatedEvent", "model": "OrderCreatedEvent" }`——展示消费者取到的消息类型，优先于 `ret` 展示。
- `outs[i].args` 是第 i 次调用传入的全部参数；连线用索引 i 引用。
- **无参调用的唯一合法写法是 `"args": []`**（渲染为无标注的出端口）。禁止伪造占位参数（如 `{ "label": "无参 · clearTabs()" }`）——端口标注只写真实传参，编造参数形态即编造调用事实。校验器会拦截缺 `args` 或非数组的 outs 条目。
- 没有任何 outs 且未被调用、也未被中间件连线指向的方法不上图。

**field（字段行）**：`{ "kind": "field", "name": "orderRepository", "t": "OrderRepository" }` —— 仅列注入依赖等关键字段。

**kv（键值行）**：配置项 `{ "kind": "kv", "k": "app.payment.timeout", "v": "3s" }`；表结构 `{ "kind": "kv", "k": "status", "v": "VARCHAR(20) · 状态机" }`；端点、通道同理。

**sql（XML 语句行）**：

```jsonc
{
  "kind": "sql",
  "name": "selectByCondition",              // 调用连线与 SQL 连线的引用键
  "tag": "<select>", "sqltag": true,
  "sig": "<select id=\"selectByCondition\" parameterType=\"map\" resultType=\"Order\">",
  "desc": "动态 SQL：按状态 / 时间 / 用户组合条件检索订单并 LIMIT 限流（全部条件拼接后的完整形态）。",
  "ret":    { "label": "List<Order>", "model": "Order" },   // 左侧结果类型
  "params": [ { "label": "OrderQuery query", "model": "OrderQuery" }, { "label": "int limit" } ],
  "sql": "SELECT id, user_id, status, amount, version\n  FROM orders\n WHERE status = ?\n   AND user_id = ?\n   AND created_at BETWEEN ? AND ?\n ORDER BY created_at DESC\n LIMIT ?"
  // sql 必须是“全部动态条件拼接后的完整形态”，参数一律写 ? 占位；<if>/<choose> 全部展开
}
```

**res（资源行）** —— 中间件节点（mq/cache/search/cloud）里的 key / Topic / 队列 / 路由键 / 索引，呈现方式与方法行一致：左侧类型标注 + 入端口，右侧出端口。也可用于**状态源行**（VM/Store 暴露的可订阅状态，见 `state` 连线与 packs/mobile §3）：

```jsonc
{
  "kind": "res",
  "name": "order:detail:{id}",                    // 行名 = 资源标识（key 模式 / topic / 队列名 / 路由键）
  "tag": "STRING · TTL 10m",                      // 数据结构 / 分区 / 队列属性等小标签
  "sig": "GET / SETEX order:detail:{id} 600",     // 完整操作形态，点击弹窗展示
  "desc": "订单详情缓存：未命中回源 DB 并以 10 分钟 TTL 写回。",
  "ret": { "label": "OrderVO", "model": "OrderVO" }  // 左侧标注：该资源上传输的对象/消息类型（可挂 model）
}
```

- 左侧 `ret.label` 即"读这个 key 返回什么 / 这条队列里是什么消息"，点击带 `model` 的标注弹字段表；
- 左端口承接应用侧连线（读写/发布），右端口供资源出线（队列 → 消费者、交换机 → 队列绑定）；
- 状态源行（声明式状态属性，如 `val uiState: StateFlow<TasksUiState>`）：name = 属性名，sig 写源码原生声明，`ret` = 状态承载的数据类型（可挂 model），右端口经 `state` 边流向消费方方法行；
- RabbitMQ 交换机节点的 res 行 name = 路由键模式，队列节点的 res 行 name = 队列名。

## §4 edges —— 连线

**call（方法级调用，唯一带端口级锚点的类型）**：

```jsonc
{ "k": "call", "from": ["impl", "placeOrder", 1], "to": ["payment", "charge"] }
// from = [节点id, 方法名, outs 索引]；to = [节点id, 方法名]（落在其左侧返回值端口）
```

调用一律指向**接口/契约**方法（Controller → Service 接口），实现类的方法行只发起调用、不承接调用边；接口与实现之间用 implements 连线表达。

**rel（关系连线）**：默认锚定到节点标题分割线两侧的灰色端点（渲染器自动按相对方位选左右；implements 例外——宽条不占端点，固定接口右缘伸入实现类左缘）；需要精确到方法/资源行时用数组锚点：

```jsonc
{ "k": "rel", "kind": "http",   "fromNode": "client", "toNode": "ctl", "label": "HTTPS · REST API" }        // 节点级（默认）
{ "k": "rel", "kind": "cache",  "from": ["impl", "findById", 2], "to": ["redis", "order:detail:{id}"],
  "label": "读 · GET" }                                                                                     // 方法出参端口 → 资源行入端口
{ "k": "rel", "kind": "mq",     "from": ["kafka", "order-events"], "to": ["listener", "onMessage"],
  "label": "订阅 · order-events" }                                                                          // 资源行出端口 → 方法入端口
{ "k": "rel", "kind": "sql",    "fromNode": "xml", "toNode": "db", "fromPortId": "p|xml|selectByCondition|sql|" }  // SQL 专用端口
```

锚点四种形式（同一方向互斥使用）：

| 形式 | 字段 | 锚定位置 |
|---|---|---|
| 节点级 | `fromNode` / `toNode` | 标题分割线两侧灰色端点 |
| 方法出参 | `from: [节点id, 方法名, outs索引]` | 该方法第 i 次调用的右侧出参端口 |
| 行端口 | `from: [节点id, res行名]`、`to: [节点id, 行名]` | 资源行（res）出/入端口；`to` 也可落方法/sql 行的左侧入端口 |
| SQL 端口 | `fromPortId` / `toPortId` | XML 语句行 / 带 `sql` 字段方法行的 SQL 端口，须配 fromNode/toNode |

| kind | 标签 | 动画语义 | 判定来源（详见 analysis-guide） |
|---|---|---|---|
| `implements` | implements | 宽条 | 类 implements 接口；渲染为宽条连接（接口节点右缘 → 实现类节点左缘，两侧实线 + 中间半透明渐变 + 条内流线，不占端口） |
| `inject` | 注入 | 虚线流动 | 字段/构造器注入（@Autowired 等，识别词表见 packs/springboot.md），方向：被注入者 → 持有者；构造注入语义适用于任何 DI 框架（含 NestJS，见 packs/microservices） |
| `config` | 配置 | 虚线流动 | 配置片段 → 消费它的组件/数据源 |
| `orm` | ORM 映射 | 静态虚线 | JPA 实体 → 表 |
| `sql` | SQL 查询 | 圆点流动 | XML 语句行或内联 SQL 方法行 → 数据库；须带 `fromPortId: "p\|<节点id>\|<语句名或方法名>\|sql\|"`（完整 SQL 写法见 packs/springboot.md） |
| `http` | HTTP 请求 | 圆点流动 | 客户端/管理端 → Controller；HTTP 客户端 → 外部服务 |
| `ws` | WebSocket | 圆点流动 | WS Handler → 通道，通道 → 订阅端 |
| `aspect` | 织入 | 虚线流动 | 切面 → 切点命中的包/类（@Aspect，识别词表见 packs/springboot.md） |
| `bind` | 绑定 | 静态虚线 | MyBatis 接口 ↔ 同 namespace 的 XML（识别词表见 packs/springboot.md） |
| `mq` | 消息 | 圆点流动 | 发布：`from:[生产者,方法,outs索引]` → Topic/交换机 res 行（out 参数 = 目标 + 消息体，路由键写在参数或 label）；订阅：队列 res 行 → 监听方法（`to:[节点,方法]`，方法 recv 标注消息类型）；交换机 → 队列绑定用 `bind` |
| `cache` | 缓存读写 | 圆点流动 | `from:[类,方法,outs索引]` → key res 行，label 写 `读 · GET` / `写 · SETEX` / `删 · DEL`（浏览器/本地存储用 `读 · getItem` / `写 · setItem` / `删 · removeItem`）/ `锁 · Redisson` / `缓存 · @Cacheable`；res 行 ret 标注值对象类型 |
| `search` | 索引/检索 | 圆点流动 | 读写方 → 索引 res 行（ret = 文档实体）；Logstash bulk 写入、Kibana 查询同理 |
| `sdk` | SDK 调用 | 圆点流动 | 云 SDK 封装类 → cloud 节点（节点级或 bucket/目录 res 行），label 写操作名（`SDK · putObject`） |
| `log` | 日志流 | 圆点流动 | logback 配置片段 → Logstash（TCP/JSON 日志流） |
| `io` | 数据读写 | 圆点流动 | 应用 ↔ `data` 节点的文件读写：读=`fromNode`(data)+`to:[节点,方法行]`，写=`from:[节点,方法,outs索引]`+`toNode`(data)，label 写操作，见 packs/python-data——二元 from 数组仅限 res 行，io 不得使用 |
| `state` | 状态流 | 圆点流动 | 声明式状态回流：状态源 res 行出端口 → 消费方方法/入口行入端口（VM `uiState` → Screen 入口行、store `$state` → 组件），label 写收集方式（`collectAsStateWithLifecycle` / `subscribe`）；事件方向（View → VM）仍用 `call`，见 packs/mobile §3 |
| `launch` | 启动 | 圆点流动 | 用户端 client → 应用入口页（移动端冷启动 launcher intent、桌面/CLI 启动——不是 HTTP 请求，勿借用 `http` 边），label 写 `启动 · launcher intent` 等 |

动画语义四档（渲染器固定实现，编排时无需配置）：**圆点流动** = 连续数据传输（call/sql/http/ws/mq/cache/search/sdk/log/io/state/launch）；**虚线流动** = 一次性应用（inject/config/aspect）；**静态虚线** = 纯逻辑关联（orm/bind）；**宽条** = 实现关系（implements）——接口右缘伸入实现类左缘的宽带，条内若干两端透明中间实线的细线从接口端流向实现端；不走端口锚点，方向由两端节点类型判定（接口/抽象类一侧出线），数据里 fromNode/toNode 写反也不影响画向；页面右键菜单按 **接口 = 调用方 / 实现类 = 被调用方** 呈现。

**出网/入图边的锚定优先级**：能定位到方法行就一律用数组锚点（`from:[节点,方法,outs索引]` / `to:[节点,行名]`）精确到端口；节点级 `fromNode`/`toNode` 只用于粗粒度关系（config/log）或**总览档 kv-only 服务卡**（无方法行可锚，如服务 → 数据库、启动时读入数据文件的 io 边）——与 analysis-guide §5「精确锚定」总则一致。

`label` 可选，覆盖默认标签；hover 任意连线会在光标旁显示该标注。

## §5 中间件节点编排示例

中间件实例 = 节点，逻辑资源（Topic、key 模式、索引、bucket）= 节点内 **res 资源行**（呈现与方法行一致：左侧类型标注 + 端口）。消息队列、缓存、搜索引擎各举一例：

```jsonc
// 消息队列：单一 broker（Kafka/RocketMQ）的 Topic 用 res 行，ret 标注消息体类型
{
  "id": "kafka", "type": "mq",
  "title": "Kafka · prod-cluster",          // 中间件标题 = 技术 · 实例名
  "tagline": "订单事件总线",
  "path": "kafka://kafka.demo.local:9092",
  "desc": "承载订单域事件的生产与消费，含死信队列。",
  "tags": ["Kafka", "事件驱动", "异步"],
  "sections": [
    { "label": "Topic · 3", "items": [
      { "kind": "res", "name": "order-events", "tag": "Topic · 3 分区",
        "ret": { "label": "OrderCreatedEvent", "model": "OrderCreatedEvent" },
        "desc": "订单创建事件；消费组 order-svc。" },
      { "kind": "res", "name": "order-events-dlq", "tag": "Topic · 死信",
        "ret": { "label": "OrderCreatedEvent", "model": "OrderCreatedEvent" },
        "desc": "重试 3 次仍失败的消息进入，人工处理。" }
    ] }
  ]
}

// 缓存：res 行 name = key 模式，ret = 值对象类型，tag = 结构与 TTL
{
  "id": "redis", "type": "cache",
  "title": "Redis · db0", "tagline": "缓存与分布式锁",
  "path": "redis://redis.demo.local:6379/0",
  "tags": ["Redis", "缓存", "分布式锁"],
  "sections": [
    { "label": "Key 模式 · 2", "items": [
      { "kind": "res", "name": "order:detail:{id}", "tag": "STRING · TTL 10m",
        "sig": "GET / SETEX order:detail:{id} 600",
        "ret": { "label": "OrderVO", "model": "OrderVO" },
        "desc": "订单详情缓存：未命中回源 DB 并写回。" },
      { "kind": "res", "name": "stock:lock:{sku}", "tag": "LOCK · Redisson",
        "ret": { "label": "String · 锁 token" },
        "desc": "秒杀库存锁，看门狗续期。" }
    ] }
  ]
}

// 搜索引擎：res 行 name = 索引名，ret = 文档实体
{
  "id": "es", "type": "search",
  "title": "Elasticsearch · demo-es", "tagline": "订单检索与日志索引",
  "path": "es://es.demo.local:9200",
  "tags": ["Elasticsearch", "ELK", "检索"],
  "sections": [
    { "label": "Index · 2", "items": [
      { "kind": "res", "name": "orders", "tag": "Index · 5 分片",
        "ret": { "label": "OrderDoc", "model": "OrderDoc" } },
      { "kind": "res", "name": "order-audit", "tag": "Index · 日志 · 1 分片",
        "ret": { "label": "JSON 日志" } }
    ] }
  ]
}
```

```jsonc
// 数据集：文件型数据（csv/parquet/模型产物），kv 行 = 列 schema，读写用 io 边（锚定形态见 §4）
{
  "id": "ordersCsv", "type": "data",
  "title": "orders.csv", "tagline": "原始订单数据",
  "path": "data/orders.csv",
  "tags": ["csv", "原始数据"],
  "sections": [
    { "label": "列 · 2", "items": [
      { "kind": "kv", "k": "id", "v": "int · 主键" },
      { "kind": "kv", "k": "amount", "v": "float · 订单金额" }
    ] }
  ]
}
// 对应的两条 io 边：读 = data 节点级出锚点 + 方法行入端口；写 = 方法出参三元锚点 + data 节点级入锚点
{ "k": "rel", "kind": "io", "fromNode": "ordersCsv", "to": ["nb01", "load_raw"], "label": "读 · read_csv" }
{ "k": "rel", "kind": "io", "from": ["train", "train_model", 0], "toNode": "modelArtifact", "label": "写 · joblib.dump" }
```

RabbitMQ 等需要拓扑的场景用**多个 mq 节点**表达：交换机一个节点（res 行 = 路由键），队列各一个节点（res 行 = 队列名，ret = 消息类型），交换机 → 队列用 `bind` 边（label 写路由键）。云服务节点（`cloud`）的资源配置（endpoint/bucket/凭证）用 kv 行即可，**密钥一律写 `****`**（见 analysis-guide §5 安全规则）。
