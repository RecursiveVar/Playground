# packs/mobile.md —— 移动端（Flutter / Android / iOS / React Native）

移动端仓库的专属判定规则。语言无关总则见 analysis-guide；本册回答 8 问 + UI 节点方法行结构约定。

## UI 节点方法行结构约定（call 边两端必须真实存在方法行并通过校验）

- **页面/组件节点 = 源文件级**；分区 label 用「导出 · n」（文件的导出即对外面）。
- **入口行**：name = Screen 类名或路由 Widget 函数名；`sig` 用 Kotlin/Swift/Dart 原生签名（如 `class OrderScreen(navArgs: OrderRouteArgs) : Screen`）；tag = 路由/深链（`orders/:id`）；`ret.label` = **props/构造参数类型**（可挂 `model:` 引用）；无 props 的组件省略 `ret`。
- **渲染关系（父→子 call 边）**：父入口行的 `outs` 追加一项，`args` = 本次传入的 props（每 prop 一项，≥2 渲染为胶囊端口；回调 prop 写 `() => onSelect` 形态）；call 边 `from:[父, 组件名, outs索引]` → `to:[子, 组件名]`。**无参调用 outs 写 `{"args": []}`**（graph-schema §3 唯一合法写法，渲染为无标注端口）。
- **回调（子→父 call 边）**：父组件文件中被传入的处理函数列为父节点方法行（被调用 → 左端口）；子组件入口行 `outs` 追加对应调用项（args=回调载荷）；call 边 from 子 to 父的处理函数行。
- **状态属性行（val uiState 等）**：VM/Bloc 暴露的可订阅状态建为 **res 行**——name=属性名（`uiState`），sig 写源码原生声明（`val uiState: StateFlow<TasksUiState>`），`ret` = 状态承载的数据类型（可挂 model），desc 写初值与更新来源；该行右端口经 `state` 边回流到 View（见 §3）。
- **Kotlin private 方法**：默认不上图（与 Java 同）；仅当被跨节点触发（框架回调、挂起入口等）时按 analysis-guide §2「参与跨节点调用」总则上图——private 与否不改变判定，跨节点与否才改变。
- **导航跳屏** = 页面入口行 `outs`（args=路由参数）+ call 边到目标页面入口行。
- **同文件其他导出**被跨节点调用时列为方法行；未被跨节点调用不上图。

## 1. 入口与业务主干

- Android = Manifest 的 launcher Activity + 导航图（NavGraph/路由）；
- Flutter = `MaterialApp` routes / go_router 路由表；
- iOS = SceneDelegate/TabView 根控制器；
- RN = navigator 路由。

每个屏一个 `page` 节点（tag 写路由/深链 `orders/:id`）。主干 = page → 子组件 → ViewModel/Bloc/Provider → Repository → 本地 DB/网络 → 后端/云。

## 2. 代码元素 → 节点类型映射表

| 代码元素 | 处理 |
|---|---|
| Activity / Fragment / Screen / Page / 路由级 Widget | `page` |
| 复用 Widget / 自定义 View / 组合组件 | `class` + tag『组件』 |
| ViewModel / Bloc / Riverpod provider / GetX controller | `class`（方法行=事件处理与状态变更，VM 方法行承接 View 的 call 边；状态属性行见方法行结构约定） |
| Repository / Service / 用例类 | `class` |
| DI 模块（Hilt `@Module` / Koin module） | `class`（方法行 = `@Provides` 提供函数）；被 `@Inject` 构造注入的依赖用 `inject` 边（analysis-guide §4 构造注入总则）；**同一文件多个 module 用单节点多分区表达，不拆同名卡**（自检清单同条口径） |
| Room DAO / drift | `interface`（方法行带 `sql` 字段，见 §5） |
| SQLite / Realm / CoreData | `database` |
| SharedPreferences / NSDefaults / AsyncStorage / secure_storage | `cache`（res 行=key） |
| protobuf / dataclass | `models`（见 §4） |
| 平台通道对侧原生模块 | `class`（或 tag『组件』，按侧别） |

## 3. 连线判定

| 关系 | 连线 |
|---|---|
| 用户启动 App（冷启动 → launcher Activity） | `launch`（client → 入口页，label `启动 · launcher intent`；**不是 HTTP 请求，勿借用 http 边**） |
| 导航跳屏 | `call`（args=路由参数） |
| 渲染子组件 | `call`（args=props） |
| View → VM 事件（调用方法） | `call` |
| **VM → View 状态回流**（StateFlow/State 订阅） | `state`：VM 状态属性行（res 行，见方法行结构约定）→ View 入口方法行，label 写收集方式 |
| Repository 调用 | `call` |
| 网络层 → 后端 | `http` |
| MethodChannel / EventChannel | `external` 节点（通道，path `channel://<name>`）+ `ws` 边连接 Dart 侧与原生侧节点 |
| 推送 / 深链 | `cloud`+`sdk` / `http` |

**VM ↔ View 双向绑定示例**（事件 call + 状态 state，两条边缺一不可，否则核心绑定不可见）：

```jsonc
// VM 节点（节选）：状态属性行 + 事件方法行
{ "kind": "res", "name": "uiState", "sig": "val uiState: StateFlow<TasksUiState>",
  "ret": { "label": "TasksUiState", "model": "TasksUiState" }, "desc": "初值 Loading；addTask/refresh 成功后更新列表" }
{ "kind": "method", "name": "addTask", "sig": "fun addTask(task: Task)", "outs": [ { "args": [ { "label": "Task task", "model": "Task" } ] } ] }
// View 节点入口行承接两条边：
{ "k": "call",   "from": ["tasksScreen", "TasksScreen", 0], "to": ["tasksVm", "addTask"], "label": "事件 · addTask" }
{ "k": "rel",    "kind": "state", "from": ["tasksVm", "uiState"], "to": ["tasksScreen", "TasksScreen"], "label": "collectAsStateWithLifecycle" }
```

## 4. 纯数据结构 → models

Kotlin `data class`、Swift `struct`（纯数据）、`@Parcelable`、protobuf 生成类 → `models`（**`file` 必写**；protobuf 写 proto 源文件路径，fields=proto 字段与编号）。

## 5. 数据访问等价物（SQL 等价物）

- Room `@Query` → 展开 SQL 写入 DAO 方法行 `sql` 字段 + `sql` 边到 database；
- Room `@Insert` / `@Update` / `@Delete` / `@Upsert` 等注解方法 → 按注解语义展开为 SQLite 实际形态写入 `sql` 字段（`@Insert` = `INSERT INTO tasks (…) VALUES (…)`；`@Upsert` = `INSERT INTO tasks (…) VALUES (…) ON CONFLICT(id) DO UPDATE SET …`；`@Delete` = `DELETE FROM tasks WHERE id = ?`；实体表名/主键以 `@Entity(tableName=…)`/`@PrimaryKey` 源码为准），禁止只写注解名当形态；
- drift 链式 → 按实际调用链拼最终 SQL；
- CoreData/Realm 查询 → 写等价查询形态（谓词原文）；
- 禁止“ORM 查询”占位。

## 6. 中间件与外部依赖

推送（FCM/APNs/JPush）→ `cloud`+`sdk`；埋点/分析（Firebase/Sensors）→ `cloud`+`sdk`；后端 API → `external`+`http`；本地文件（导出/下载目录）→ `data` 节点 + `io` 边（锚定形态按 analysis-guide §4 / graph-schema §4：读=`fromNode`(data)+`to:[节点,方法行]`，写=`from:[节点,方法,outs索引]`+`toNode`(data)）。

**fake / 内存数据源**（FakeXxxRepository、进程内列表实现等不出网的测试替身）：普通 `class` 节点 + tag『模拟』，照常承接 Repository 一侧的 `call` 边，desc 注明「进程内模拟，不出网」；**不建 `external` 节点、不发 `http` 边**——没有真实网络调用就不画网络边（否则误导读者以为存在出网依赖）。

## 7. 布局列序

page 列 → tag『组件』组件列 → 状态层（VM/Bloc）列 → Repository/网络层列 → `database`/`cache`/`external`/`cloud` 最右；平台通道 external 节点放在 Dart 与原生两组之间。

## 8. 安全红线

apiKey（地图/推送/统计）、签名 keystore 信息、证书密码 `****`。
