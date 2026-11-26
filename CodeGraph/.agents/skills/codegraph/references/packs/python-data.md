# packs/python-data.md —— Python 数据分析（pandas / sklearn / Jupyter）+ Django/FastAPI 服务端

Python 数据分析与 Python Web 服务端的专属判定规则。语言无关总则见 analysis-guide；本册回答 8 问。

## 1. 入口与业务主干

- `*.ipynb` → `notebook` 节点（方法行 = notebook 中的函数定义与关键管道步骤，**按 cell 执行顺序**排列，name=步骤名如 `load_raw`/`train`，sig=代码摘要，tag=cell 编号）。
  **顶层 cell 步骤行细则**：无 `def` 包裹的顶层 cell，name 用动宾短语概括该 cell 唯一主行为（`load_raw`/`clean`/`train`）；sig 摘该 cell 的关键调用原文（`pd.read_csv('data/building_1.csv', parse_dates=['timestamp'])`）；tag 写 cell 序号（`cell 3`），**序号按 notebook 实际执行序逐一核对**；该 cell 产出的被下游消费的对象写进 `outs`（args=产物，如 `{ "label": "DataFrame df", "model": … }`），无产出写 `{"args": []}`。
- 仓库型入口（`train.py` / DAG 定义 / Makefile 目标）→ `class` 节点（方法行=task/函数）。
- FastAPI/Django 路由 = 入口（tag `GET /orders`）。

主干 = 入口 → 转换/特征模块 → data/DB/模型产物。

**多主题文章合集仓的取舍口径**（几十个独立主题目录、每个各管各的场景）：默认只入**有跨文件依赖的主题**——某主题目录的代码被其它入图文件 import，或其产物被其它主题读取（经共享 data 节点成链）；完全独立的单文件演示默认不入图。每个入选主题只画主干管线代表（入口→转换→产物），并在交付说明里声明「共 N 个主题目录，入图 M 个，其余为无跨文件依赖的独立演示」。

**读路径不在仓库**（代码 `read_csv('data/building_1.csv')` 而数据未随仓分发）：`data` 节点照建，path 写代码引用的原始路径，desc 注明「仓库内不存在该文件（数据未随仓分发）」——**不得**改写成仓库里另一个真实文件路径（那是编造依赖）；io 读边照常画。

**只读产物**（results/metrics 等只有读者没有写者的文件）：被入图代码读取 → 上图（读边成链）；既无人读取、又非管线终点交付物 → 不上图。

## 2. 代码元素 → 节点类型映射表

| 代码元素 | 处理 |
|---|---|
| notebook | `notebook`（方法行=cell 步骤） |
| 函数库模块（`features.py` 等） | `class`（标题=文件名含扩展名，方法行=被跨节点调用的函数） |
| 类 | `class` |
| `Protocol` / ABC | `interface`（罕见） |
| dataclass / pydantic 模型 / TypedDict | `models`（见 §4） |
| 数据文件（csv/parquet/Excel/json） | `data`（kv 行=列名与类型，tag 注明行数量级） |
| 模型产物（pkl/joblib/onnx） | `data`（tag『模型产物』，kv 行=算法/版本/指标） |
| SQLite/MySQL/PG | `database` |
| 训练脚本 / 服务入口 | `class` |

## 3. 连线判定

- 脚本/notebook 读写数据文件 = `io`，**锚定形态固定为两种合法写法**：读 = `fromNode`(data 节点) + `to:[节点,方法行]`（label `读 · read_csv`）；写 = `from:[节点,方法,outs索引]`（args=写出的对象）+ `toNode`(data 节点)（label `写 · to_parquet`）——方向即语义总则适用，**不得**把读边反转为二元 from 数组（校验器仅允许 res 行使用二元 from）。
- ORM（Django ORM / SQLAlchemy / peewee / Tortoise）→ `database` = `sql` 边（fromPortId 绑定方法行 SQL 端口）。
- notebook 间经中间产物（parquet）衔接 = 经共享 `data` 节点两段 io 闭环。
- FastAPI/Django 视图 → 外部 = `http`。
- 对象存储（S3/OSS/MinIO 数据桶）→ `cloud`+`sdk`。
- MLflow/W&B tracking → `external`+`http`。
- 向量库（Milvus/FAISS/Qdrant）→ `search`（res 行=collection，ret=向量维度/文档实体）。

## 4. 纯数据结构 → models

dataclass / pydantic `BaseModel` 仅数据 → `models`（**`file` 必写**）；pydantic 带被外部调用的校验方法 → 双轨（同 Java 规则，见 analysis-guide §3）；DataFrame 不是 model——用 `ret.label` 轻标注（`DataFrame · 12 列`）。

## 5. 数据访问等价物（SQL 等价物）

Django queryset / SQLAlchemy 链式 / pandas `read_sql` → 展开为最终 SQL（参数 `?` 占位）写入方法行 `sql` 字段，`sql` 边到 database；禁止「ORM 查询」「QuerySet 查询」占位话术（与 MyBatis 规则同源同口径，见 packs/springboot.md §5）。

## 6. 中间件与外部依赖

数据文件（本地/挂载）→ `data`+`io`；数据库 → `database`+`sql`；对象存储 → `cloud`+`sdk`（仓外大数据集可用 `data` 节点 + path 连接串，不进文件树）；调度器（Airflow/Prefect）→ `external`，DAG 任务与其连 `call`。

## 7. 布局列序

入口（notebook/脚本/API 路由）最左 → 转换/特征/训练模块列 → `data`/`database`/模型产物**资源列** → **数据消费者（下游 notebook、推理服务、报表脚本）在资源列右侧再起一列**（复用“中间件/数据的消费者在资源列右侧再起一列”通则，analysis-guide §5），使读边（data→消费者）继续向右流动，避免横穿全图的回流边；多级管道（清洗→特征→训练→评估）按产物流向逐级右移，每级消费者在其数据源右侧起列。

## 8. 安全红线

DB 连接密码、云 AK/SK、`.env`、W&B/LangSmith 等 API key 一律 `****`；样本数据中的个人敏感字段在 kv 行只写列名与类型，不写样例值。
