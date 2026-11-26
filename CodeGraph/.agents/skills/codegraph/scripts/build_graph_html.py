#!/usr/bin/env python3
"""从 assets/graph.template.html + .codegraph/graph.json 生成自包含的 graph.html。

用法:
    python build_graph_html.py <path/to/.codegraph/graph.json>

输出:
    与 graph.json 同目录下的 graph.html（数据已注入，双击即可离线打开）
"""
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "assets" / "graph.template.html"
MARKER = "/*__GRAPH_DATA__*/ null"

# 词表单一事实源在 references/graph-schema.md §1/§4；改动须同步：template TYPES/TYPE_LABELS/EDGE_KINDS/EDGE_LABELS/FILE_NODE_TYPES、本文件 NODE_TYPES/REL_KINDS、SKILL.md 速查、packs/*.md 映射表
NODE_TYPES = {
    "class", "interface", "abstract", "page", "notebook", "data", "config",
    "database", "mq", "cache", "search", "cloud", "external", "client",
    "admin", "xml",
}
REL_KINDS = {
    "implements", "inject", "config", "orm", "sql", "http", "ws", "aspect",
    "bind", "mq", "cache", "search", "sdk", "log", "io", "state", "launch",
}


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("用法: python build_graph_html.py <path/to/.codegraph/graph.json>")
    graph_path = Path(sys.argv[1]).resolve()
    if not graph_path.exists():
        sys.exit(f"找不到 {graph_path}")
    if not TEMPLATE.exists():
        sys.exit(f"找不到模板 {TEMPLATE}")

    graph = json.loads(graph_path.read_text(encoding="utf-8"))

    # ---- 基本校验：越早失败越好 ----
    for key in ("nodes", "edges"):
        if key not in graph:
            sys.exit(f"graph.json 缺少必需字段: {key}")
    node_ids = {n.get("id") for n in graph["nodes"]}
    if None in node_ids:
        sys.exit("存在缺少 id 的节点")
    if len(node_ids) != len(graph["nodes"]):
        sys.exit("存在重复的节点 id")

    def method_names(node_id: str) -> set:
        names = set()
        for n in graph["nodes"]:
            if n["id"] == node_id:
                for sec in n.get("sections", []):
                    for it in sec.get("items", []):
                        if it.get("kind") in ("method", "sql"):
                            names.add(it["name"])
        return names

    def row_info(node_id: str) -> dict:
        """返回 {行名: kind}，含 method/sql/res 行，用于锚点校验"""
        info = {}
        for n in graph["nodes"]:
            if n["id"] == node_id:
                for sec in n.get("sections", []):
                    for it in sec.get("items", []):
                        k = it.get("kind")
                        if k in ("method", "sql", "res"):
                            info[it["name"]] = k
        return info

    def out_count(node_id: str, method: str) -> int:
        for n in graph["nodes"]:
            if n["id"] == node_id:
                for sec in n.get("sections", []):
                    for it in sec.get("items", []):
                        if it.get("kind") == "method" and it["name"] == method:
                            return len(it.get("outs") or [])
        return -1

    problems = []
    for n in graph["nodes"]:
        if n.get("type") not in NODE_TYPES:
            problems.append(f"节点 {n.get('id')} 的 type 非法: {n.get('type')}")
    method_cache: dict[str, set] = {}
    for e in graph["edges"]:
        if e.get("k") == "call":
            f, t = e["from"], e["to"]
            for node_id in (f[0], t[0]):
                if node_id not in node_ids:
                    problems.append(f"call 边引用了不存在的节点: {node_id}")
            for node_id in (f[0], t[0]):
                if node_id not in method_cache:
                    method_cache[node_id] = method_names(node_id)
            if f[1] not in method_cache.get(f[0], set()):
                problems.append(f"call 边 from 方法不存在: {f[0]}.{f[1]}")
            if t[1] not in method_cache.get(t[0], set()):
                problems.append(f"call 边 to 方法不存在: {t[0]}.{t[1]}")
        elif e.get("k") == "rel":
            if e.get("kind") not in REL_KINDS:
                problems.append(f"rel 边的 kind 非法: {e.get('kind')}")
            for key in ("fromNode", "toNode"):
                if e.get(key) is not None and e.get(key) not in node_ids:
                    problems.append(f"rel 边引用了不存在的节点: {e.get(key)}")
            # 数组锚点：from = [节点, 方法名, outs索引]（方法出参端口）或 [节点, 资源行名]（资源出端口）；
            # to = [节点, 行名]（方法/资源行的入端口）
            if e.get("from") is not None:
                f = e["from"]
                if not (isinstance(f, list) and f[0] in node_ids and len(f) in (2, 3)):
                    problems.append(f"rel 边 from 锚点非法: {f}")
                else:
                    rows = row_info(f[0])
                    if len(f) == 3:
                        if rows.get(f[1]) != "method":
                            problems.append(f"rel 边 from 锚点 {f[0]}.{f[1]} 不是方法行（三元锚点仅用于方法出参端口）")
                        elif not (isinstance(f[2], int) and 0 <= f[2] < out_count(f[0], f[1])):
                            problems.append(f"rel 边 from 锚点 {f[0]}.{f[1]}[{f[2]}] 超出 outs 数量")
                    elif rows.get(f[1]) != "res":
                        problems.append(f"rel 边 from 锚点 {f[0]}.{f[1]} 不是资源行（二元锚点仅用于 res 行出端口）")
            if e.get("to") is not None:
                t = e["to"]
                if not (isinstance(t, list) and len(t) == 2 and t[0] in node_ids):
                    problems.append(f"rel 边 to 锚点非法: {t}")
                elif row_info(t[0]).get(t[1]) not in ("method", "sql", "res"):
                    problems.append(f"rel 边 to 锚点 {t[0]}.{t[1]} 的行不存在")
            if e.get("fromPortId") is not None and e.get("fromNode") not in node_ids:
                problems.append(f"rel 边 fromPortId 缺少合法 fromNode: {e.get('fromNode')}")
            if e.get("toPortId") is not None and e.get("toNode") not in node_ids:
                problems.append(f"rel 边 toPortId 缺少合法 toNode: {e.get('toNode')}")
        else:
            problems.append(f"边的 k 非法（应为 call 或 rel）: {e.get('k')}")
    models = set(graph.get("models", {}))
    for n in graph["nodes"]:
        for sec in n.get("sections", []):
            for it in sec.get("items", []):
                # outs 结构校验：无参调用唯一合法写法 args: []（渲染为无标注端口）；有参调用每项 {label: …}
                if it.get("kind") == "method":
                    for oi, o in enumerate(it.get("outs") or []):
                        if not isinstance(o, dict) or not isinstance(o.get("args"), list):
                            problems.append(
                                f"{n['id']}.{it.get('name')} outs[{oi}] 非法"
                                '（无参调用写 {"args": []}，有参调用 args 每项 {"label": …}，见 graph-schema §3）'
                            )
                        for arg in o.get("args", []):
                            if not isinstance(arg, dict) or not arg.get("label"):
                                problems.append(f"{n['id']}.{it.get('name')} outs[{oi}] 参数缺 label")
                if it.get("ret", {}).get("model") and it["ret"]["model"] not in models:
                    problems.append(f"{n['id']}.{it.get('name')} ret.model 未注册: {it['ret']['model']}")
                if it.get("recv", {}).get("model") and it["recv"]["model"] not in models:
                    problems.append(f"{n['id']}.{it.get('name')} recv.model 未注册: {it['recv']['model']}")
                for a in it.get("outs", []) or []:
                    for arg in a.get("args", []):
                        if arg.get("model") and arg["model"] not in models:
                            problems.append(f"{n['id']}.{it.get('name')} 参数 model 未注册: {arg['model']}")
                for p in it.get("params", []) or []:
                    if p.get("model") and p["model"] not in models:
                        problems.append(f"{n['id']}.{it.get('name')} params.model 未注册: {p['model']}")
    if problems:
        sys.exit("graph.json 校验失败:\n  - " + "\n  - ".join(problems))

    # ---- 布局重叠预警（估算高度与 analysis-guide §7 公式一致；近似值，仅提示不阻断） ----
    def est_height(node):
        h = 130
        for sec in node.get("sections", []):
            rows = 0
            for it in sec.get("items", []):
                rows += 1
                if it.get("kind") == "method":
                    rows += max(0, len(it.get("outs") or []) - 1)  # 每次对外调用额外加高
            h += 24 + 30 * rows
        return h

    warns = []
    ns = graph["nodes"]
    for i, a in enumerate(ns):
        ha = est_height(a)
        for b in ns[i + 1:]:
            ax, ay, aw = a.get("x") or 0, a.get("y") or 0, a.get("w") or 270
            bx, by, bw = b.get("x") or 0, b.get("y") or 0, b.get("w") or 270
            if ax < bx + bw and bx < ax + aw and ay < by + est_height(b) and by < ay + ha:
                warns.append(f"{a['id']} 与 {b['id']} 估算卡片重叠（检查 y 间距：估算高 {ha}/{est_height(b)}）")
    if warns:
        print("布局预警（估算值，不阻断生成；调大同列 y 间距）:", file=sys.stderr)
        for w in warns:
            print(f"  - {w}", file=sys.stderr)

    template = TEMPLATE.read_text(encoding="utf-8")
    if MARKER not in template:
        sys.exit("模板中未找到注入标记 " + MARKER)
    payload = json.dumps(graph, ensure_ascii=False, indent=2)
    out = template.replace(MARKER, "/*__GRAPH_DATA__*/ " + payload, 1)

    out_path = graph_path.parent / "graph.html"
    out_path.write_text(out, encoding="utf-8")
    print(f"已生成 {out_path}（{len(graph['nodes'])} 节点 / {len(graph['edges'])} 连线 / {len(models)} 模型）")


if __name__ == "__main__":
    main()
