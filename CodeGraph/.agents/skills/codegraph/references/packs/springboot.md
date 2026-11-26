# packs/springboot.md —— SpringBoot / JVM 服务

SpringBoot（Maven/Gradle、Spring MVC、MyBatis/JPA）仓库的专属判定规则。语言无关总则见 analysis-guide；本册回答 8 问 + 识别词表。

## 1. 入口与业务主干

`@RestController` / `@Controller` 即入口；业务主干 = Controller → Service 接口/实现 → 持久层（JPA Repository / MyBatis 接口与 XML）→ 数据/中间件。侦察时找：`src/main/java` 包结构、Controller / Service 接口与实现 / Repository(JPA) / MyBatis 接口与 XML / @Aspect 切面 / DTO·VO·PO·事件 / 配置文件（yml/properties）；数据源（jdbc/数据库）、对外 HTTP 调用（RestTemplate/RestClient/WebClient/Feign）、WebSocket 端点、前端工程（客户端/管理端目录）。

## 2. 代码元素 → 节点类型映射表

| 代码元素 | 处理 |
|---|---|
| @RestController / @Controller | 上图，type=class，方法行带路由 tag（GET /orders） |
| Service 接口 | 上图，type=interface，作为调用边的落点 |
| Service 实现 | 上图，type=class，与接口间连 implements；实现方法行承接 outs（它发起调用） |
| 抽象基类（模板方法等） | 在主流程上才上图，type=abstract |
| JPA Repository | 上图，type=interface，与数据库连 orm |
| MyBatis 接口 + XML | 各一个节点（interface + xml），之间连 bind；调用边落在 **XML 语句行**上 |
| MyBatis-Plus / 注解 SQL 的 Mapper（无 XML） | 只有 interface 节点，方法行带 `sql` 字段与「SQL」端口，`sql` 边从方法行直连数据库（见 §5） |
| @Aspect 切面 | 上图，type=class，tagline 标注 @Aspect；advice 作为方法行（tag=@Around 等）；到命中目标连 aspect |
| DTO / VO / PO / 领域事件 | **不作为节点** → 注册 models（见 §4） |
| 工具类 / Converter / Mapper | 在主调用链上才上图（如 OrderConverter.toVO 被调用） |
| application.yml 等配置 | 按片段拆成多个 config 节点（path `文件#片段`） |
| @Configuration / 工具 / 异常 / 启动类 | 默认不上图 |

## 3. 连线判定（怎么找）

| 连线 | 怎么找 |
|---|---|
| call | 方法体里对**其它节点**公开方法的调用：`from=[调用者, 方法名, outs索引]`，`to=[被调者, 方法名]`。传参写实际表达式/参数名，类型可从 model 引用时写 `类型 名`。调用指向接口而非实现 |
| implements | `class X implements Y` / `extends abstract` → X 到 Y |
| inject | 字段或构造器注入的依赖（@Autowired 等）：依赖节点 → 持有者。同一持有者多于 3 条时可只保留主链路依赖 |
| config | 配置片段 → 消费它的组件/数据源 |
| orm | JPA 实体（通常是 models 里的 PO）→ 对应表。从 Repository 节点连到 database |
| sql | 每条真正落库的访问一条线到 database，带 fromPortId：XML 语句行 / 带内联 SQL 的方法行（见 §5） |
| http | 浏览器/前端 → Controller（HTTPS·路由）；RestTemplate/RestClient/WebClient/Feign 调用 → external 节点 |
| ws | WebSocketHandler/ServerEndpoint → 通道；通道 → 订阅的客户端 |
| aspect | @Aspect 每个 advice 的切点表达式 → 命中的包/类节点，label 写 `织入 · 切点摘要` |
| bind | MyBatis 接口 ↔ 同 namespace 的 XML |
| mq / cache / search / sdk / log | 见 §6 与 analysis-guide §5 |

## 4. 纯数据结构 → models

判定“纯数据类”：除 getter/setter/构造器/equals/hashCode/toString 外没有业务方法，或业务方法未被外部调用。

- 降级 → 注册进 `models`，字段三列（名称/类型/含义）；含义来自字段注释或业务理解，不要留空。
- **双轨例外**：若该类存在会被其它类调用的业务方法（如带校验的工厂方法、聚合行为），则同时作为节点出现——此时节点只展示方法，不展示字段；字段仍只在 models 弹窗里。
- 在端口类型标注中引用：`{ "label": "CreateOrderCmd cmd", "model": "CreateOrderCmd" }`。
- Java 栈 `file` 字段可省略（渲染器按包名 `path` 推导 `src/main/java/…/类名.java`，v1 行为兼容）；显式写 `file` 时以它为准。

## 5. 数据访问等价物（SQL 的完整形态：XML / 注解 / MyBatis-Plus / JPA 派生）

**所有真正连到数据库的访问，无论 SQL 写在哪里，都必须在图谱中写明实际执行的完整 SQL**——读者必须能在图上看到最终发给数据库的 SQL 本身，参数一律 `?` 占位、动态条件全部展开：

- **MyBatis XML**：MyBatis XML 作为 `xml` 类型节点，每条语句一行：左侧结果类型（承接调用连线），右侧固定「SQL」可点击端口（弹窗展示完整拼接 SQL），每条语句一条 `sql` 边连到数据库。`<if>` / `<choose>` / `<foreach>` 在语句行的 `sql` 字段中全部展开拼接成最终形态；WHERE 里所有可选条件按“全部命中”拼出；ORDER BY / LIMIT 全写；`params` 列出参数来源；`ret` 写 resultType（泛型展开，如 `List<Order>`）。
- **注解 SQL**（`@Select` / `@Update` / `@Insert` / `@Delete`，含 `<script>` 动态 SQL）：与 XML 同等对待，不走 xml 节点，展开写进所在方法行的 `sql` 字段。
- **MyBatis-Plus 接口内生成 SQL**（BaseMapper 的 selectById / insert / updateById / deleteById 等、`LambdaQueryWrapper` / `QueryWrapper` 链式条件）：不走 xml 节点。按实体映射与 Wrapper 的**实际调用链**拼出真实 SQL——列名取 `@TableField` 或驼峰转下划线的结果，`@TableLogic` 逻辑删除追加 `deleted = 0`，分页插件追加 `LIMIT`，乐观锁版本条件照拼——写进方法行的 `sql` 字段。例如 `selectById` → `SELECT id, user_id, status, amount FROM orders WHERE id = ? AND deleted = 0`，而不是一句“MP 内置查询”。
- **JPA 派生查询 / @Query**：`findByNameAndStatus` 等派生方法与 JPQL 同样翻译成等价 SQL 写全（表名 / 列名按 orm 映射推断）。

呈现方式：XML 语句行（kind=sql）与带内联 SQL 的方法行（kind=method + `sql` 字段）都在行右侧渲染「SQL」可点击端口，弹窗展示完整 SQL；`sql` 连线分别从语句行 / 方法行的 SQL 端口连到数据库节点。方法行 `desc` 用一句话说明访问来源（如「MyBatis-Plus 按主键查 orders 表」），完整 SQL 放 `sql` 字段。**禁止**用「BaseMapper 内置」「Wrapper 动态拼接」这类占位话术代替 SQL 本身。

## 6. 中间件与外部依赖（识别词表见文末；建模总则见 analysis-guide §5）

### 6.1 消息队列（Kafka / RocketMQ / RabbitMQ / ActiveMQ / Pulsar / SQS / Spring Cloud Stream）

- **拓扑形态分两档**：
  - 单一 broker 型（Kafka / RocketMQ / Pulsar / SQS）：一个 `mq` 节点，Topic 用 **res 行**（name = topic，ret = 消息体类型，tag 注明分区/消费组），title `Kafka · prod-cluster`，path `kafka://host:9092`；
  - 交换机型（RabbitMQ / AMQP）：**Exchange 与 Queue 各建一个 `mq` 节点**（tagline 标明 `交换机 · Direct/Fanout/Topic` 或 `队列`），Exchange 节点的 res 行 name = 路由键（ret = 消息体），Queue 节点的 res 行 name = 队列名（ret = 队列里的消息类型）；Exchange → Queue 用 `bind` 边，label 写路由键（`绑定 · rk=order.created`）。Exchange/Queue 声明代码（`@Bean Queue/TopicExchange` + Binding）就是拓扑的判定来源。
- 死信、重试队列也要列（可作为独立 Queue 节点或 Topic res 行）。
- **生产者**：发送方法所在类的该方法行增加一个 out 项，参数 =（目标，消息体）：Kafka 写 `String topic · order-events` + `OrderCreatedEvent event`；RabbitMQ 写 `String rk · order.created` + 消息体——**路由键就在出参端口上呈现**。连线 `from:[类,方法,outs索引]` → `to:[broker/交换机节点, res行名]`，kind `mq`，label `发布 · order-events` / `发布 · rk=order.created`。
- **消费者**：连线 `from:[队列/broker节点, res行名]` → `to:[监听器类, 方法名]`，label `订阅 · order-events（消费组 order-svc）`；监听方法行的 `recv` 字段标注收到的消息类型（左侧端口旁显示 `OrderCreatedEvent`），tag 写注解（`@KafkaListener(topics="order-events")`）。监听方法即使没有 outs 也上图（它是中间件连线的落点）。它再调用 Service 的边照常画 `call`。
- 消息体（OrderCreatedEvent 等）降级进 `models`，在 res 行 ret、方法 recv、out 参数处以 `model:` 引用。
- 同一业务链路的发布边与订阅边让“异步链路”在图上闭环：`生产方法 → Topic/Exchange → Queue → 监听方法`。

### 6.2 Redis / 缓存（Redis / Redisson / Memcached / Spring Cache）

- 一个实例/db 一个 `cache` 节点：`Redis · db0`，path `redis://host:6379/0`。
- **key 模式一条 res 行**：name = key 模式（`order:detail:{id}`），tag = 结构与 TTL（`STRING · TTL 10m`），**ret = 值对象类型**（`{"label":"OrderVO","model":"OrderVO"}`，点击弹字段表）——「存到哪个键、读回什么对象」在行上直接可读。锁、计数器、ZSet 排行各占一行（ret 写 `String · 锁 token` / `Long · score` 这类轻标注）。
- **读写连线精确到端口**：操作方法增加一个 out 项（参数写 key 表达式，如 `String key · order:detail:{id}`），连线 `from:[类,方法,outs索引]` → `to:[redis节点, key行名]`，kind `cache`，label 写操作：`读 · GET`、`写 · SETEX`、`删 · DEL`、`锁 · Redisson tryLock`。同一方法对多个 key 的操作各自一条 out + 一条边。
- 项目若有 CacheService / RedisService 封装类：封装类上图，业务类 `call` 它，由封装类的方法连 cache——不要每处都直连。
- 纯 `@Cacheable` 声明式缓存：边从被注解的方法所在类连出（仍锚定方法出参端口），方法行 tag 写 `@Cacheable`，label `缓存 · @Cacheable("order")`。

### 6.3 Elasticsearch / ELK 三件套

Elasticsearch 在仓库里有两种角色，分开判定：

**A. 业务检索（spring-data-elasticsearch / ES Java Client）**
- 集群一个 `search` 节点（`Elasticsearch · demo-es`，path `es://host:9200`），**索引用 res 行**（name = 索引名，ret = 文档实体，tag 注明分片）；`@Document` 实体降级进 models；读写连线锚定 `from:[类,方法,outs索引]` → `to:[es节点, 索引行名]`，kind `search`，label `索引 · orders`（写）或 `检索 · orders`（读）。
- DB → ES 同步器（canal/定时任务/事件监听重投）单独成节点，画出「DB 读 → 同步器 → ES 写」两段。

**B. 日志管道（ELK：Logstash + Kibana）**
- Logstash 一个 `external` 节点（`Logstash · 日志管道`）；logback 拆出 `logback-spring.xml#LOGSTASH` 配置片段节点 → Logstash，kind `log`，label `TCP 4560 · JSON`；Logstash → ES 节点 kind `search`，label `bulk 索引`；Kibana 可选一个 `external` 节点 → ES，label `查询 · 仪表盘`（仅当值得展示观测链路时画）。
- Filebeat 等仓库外的采集器不画；需要时在 Logstash 节点 tagline 提一句。若日志走 Kafka 则按 §6.1 建模。

### 6.4 云服务（S3 / OSS / COS / MinIO / 短信 / 邮件 / 推送）

- 一个云资源一个 `cloud` 节点：`OSS · demo-bucket`，path `oss://demo-bucket`；kv 行列 endpoint / bucket / region，**凭证一律 `****`**。
- SDK 封装类（FileStorageService、SmsService…）作为节点（type=class），业务类 `call` 它；封装类 → cloud 节点 kind `sdk`，label 写操作：`SDK · putObject`、`SDK · 发送短信`。上传/下载箭头都是 应用 → 云，用 label 区分。
- REST 风格的第三方开放平台（无官方 SDK、走 HTTP）仍用 `external` + `http` 边，不建 cloud 节点。

## 7. 布局列序

从左到右按数据流分列：**用户端（客户端/管理端） → Controller → Service 接口与实现 → 持久层（Repository / MyBatis 接口与 XML） → 基础设施（数据库/缓存/消息队列/搜索/云服务，最右列；MQ 消费者在队列右侧再起一列，ELK 管线沿底部横排）**；配置片段节点放在它服务的对象附近（中间件的放对应中间件节点左下方）。

## 8. 安全红线

AK/SK、密码、token、连接串中的凭证一律写 `****`，绝不进图谱。

## 识别词表

- **MQ 依赖**：`spring-kafka`、`spring-boot-starter-amqp`、`rocketmq-spring-boot-starter`、`spring-boot-starter-activemq`、`pulsar-spring-boot-starter`、AWS SDK（SqsClient/SnsClient）、`spring-cloud-stream`。
- **MQ 代码**：`KafkaTemplate` / `RocketMQTemplate` / `RabbitTemplate` / `JmsTemplate` 的 send/convertAndSend；监听注解 `@KafkaListener`、`@RocketMQMessageListener`、`@RabbitListener`、`@JmsListener`、`@SqsListener`、`@PulsarListener`、`@StreamListener` / `StreamBridge.send`；RabbitMQ 的 Exchange/Queue 声明（`@Bean Queue/TopicExchange` + Binding）。
- **缓存依赖**：`spring-boot-starter-data-redis`、`redisson`、`spring-boot-starter-cache`、`memcached` 客户端。
- **缓存代码**：`StringRedisTemplate` / `RedisTemplate` / `ReactiveRedisTemplate` 的 opsFor*；`RedissonClient`（分布式锁 RLock/RPermitExpirableSemaphore）；`@Cacheable` / `@CacheEvict` / `@CachePut`（CacheManager 为 Redis 时）；`RedisMessageListenerContainer`（pub/sub，按 §6.1 处理）。
- **ES 依赖/代码**：`spring-boot-starter-data-elasticsearch`；`@Document(indexName=…)` 实体、`ElasticsearchRepository` 接口、`ElasticsearchOperations` / `ElasticsearchClient` / `RestHighLevelClient`。
- **ELK**：`logstash-logback-encoder`；`logback-spring.xml` 里的 `LogstashTcpSocketAppender` / `<destination>`；spring.kafka 日志 topic。
- **云服务**：`software.amazon.awssdk`（S3Client/SesClient/SnsClient…）、`aliyun-sdk-oss`（OSS）、`cos_api`（腾讯云 COS）、`minio` 客户端、`spring-cloud-starter-alicloud`、各厂商短信/邮件/推送 SDK；配置键 `oss.endpoint` / `aws.region` / `access-key` / `sms.*` 等；调用点 `OSSClient.putObject` / `S3Client.putObject` / `AmazonS3` 等。
- **中间件识别路径**：先看 pom/build.gradle 依赖与配置键（spring.data.redis / spring.kafka / rocketmq.* / spring.elasticsearch / *.oss.* / aws.*），再全文检索客户端类与注解定位用点；只有配置没有代码用点的依赖不上图。

## 迁移对照表（原 analysis-guide@1.4 → 本册；语义零丢失验收口径）

| 原 analysis-guide 章节 | 本册落点 |
|---|---|
| §1 节点判定表 18 行 | §2 映射表（逐行迁入） |
| §2 方法判定（私有方法不上图/参与跨节点/sig/field 注入/源文件顺序） | analysis-guide §2（总则化）+ §1 入口（Controller 方法 tag 路由）+ §3 inject 行 |
| §3 模型类降级 | §4（原文迁移 + file 可省略说明） |
| §4 配置片段化 | analysis-guide §1（总则化，path `文件#片段` 格式保留） |
| §5 连线判定速查表（call/implements/inject/config/orm/sql/http/ws/aspect/bind） | §3 连线判定（“怎么找”列原文迁入） |
| §6.0 中间件总则 | analysis-guide §5（总则化） |
| §6.1 消息队列 | §6.1（含双档拓扑/死信/生产者/消费者/闭环） |
| §6.2 Redis 缓存 | §6.2（含 key res 行/端口锚定/封装收敛/@Cacheable） |
| §6.3 ES / ELK | §6.3（含 DB→ES 同步器/日志管道/Filebeat 不画） |
| §6.4 云服务 | §6.4（含 REST 第三方用 external+http） |
| §6.5 中间件布局 | §7 布局列序 + analysis-guide §5 布局通则 |
| §7 SQL 完整形态四分支 | §5（逐字迁移：XML 展开/注解 SQL/MyBatis-Plus/JPA 派生 + 呈现方式 + 禁止占位话术） |
| §8 布局编排首句（Spring 列序） | §7 |
| §9 差量更新 | analysis-guide §8（原文整段保留） |
| 原 SKILL.md 编排速查：XML/SQL 条 | §5 |
| 原 SKILL.md 编排速查：中间件建模条（res 行/bind/recv/脱敏） | §6.1/§6.2/§8 |
| 原 SKILL.md 自检清单 MyBatis-Plus/注解 SQL/JPA 专项 | §5（口径同一：“展开后的完整最终 SQL、无占位话术”） |
