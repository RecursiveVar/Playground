# CodeGraph — Multi-Stack Code Graph Skill

[中文说明](./README.zh-CN.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../LICENSE)
![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)
![Zero Dependencies](https://img.shields.io/badge/Dependencies-None-success)

Turn **any** repository into an interactive code-graph workbench (`.codegraph/graph.html`): an infinite canvas plus project file tree, fuzzy search and data-flow animation — all in a single self-contained offline HTML file. Double-click to open, zero dependencies.

It auto-detects the project type and routes to a dedicated rule pack — **JVM backends** (SpringBoot), **web frontends** (React/Vue/Svelte/Next/Nuxt) and **Node services**, **mobile apps** (Flutter/Android/iOS/React Native), **microservice systems** (gateways, config/registry centers, Go/Rust/Node quick rules), and **Python data work** (pandas/sklearn/Jupyter notebooks, Django/FastAPI).

Beyond code structure and databases, it recognizes and visualizes middleware dependencies — **message queues** (Kafka / RocketMQ / RabbitMQ / ActiveMQ / Pulsar / SQS), **Redis caching**, the **Elasticsearch / ELK** stack, **cloud services** (S3 / OSS / COS / MinIO / SMS / email), plus frontend pages/components/state stores, mobile local storage, vector databases and file-based datasets (csv/parquet/model artifacts) — with dedicated node and edge semantics for publish/subscribe, cache reads/writes, log pipelines and data I/O.

## Features

- **Nodes are the real files**: pages, components & state stores, controllers, services, repositories, MyBatis interfaces & XML, config fragments, datasets, notebooks, databases, middleware and clients; pure data shapes degrade into clickable model annotations.
- **Method-level call chains**: edges anchor to concrete argument/return ports; parameter and return types open model field tables on click; methods are listed in source-file order. Frontend render/callback relations use the same call edges.
- **Full data-access shapes on the graph**: XML dynamic statements, MyBatis-Plus / annotation SQL / JPA derived queries — the actually-executed SQL is always spelled out (dynamic conditions fully expanded, `?` placeholders); REST/GraphQL requests carry method + full path + payload; file reads/writes label the actual operation — shown via the "SQL" port or the edge label.
- **17 node types / 18 edge semantics**: page / notebook / dataset join class / interface / abstract / config / database / mq / cache / search / cloud / external / client / admin / xml; call / implements / inject / config / ORM / SQL / HTTP / WebSocket / aspect / bind / message / cache / search / SDK / log / data-I/O / state / launch — animation distinguishes continuous transfer, one-shot application and static association, while implements renders as a wide gradient band from interface to implementation with flowing streams inside.
- **5 technology packs**: SpringBoot / frontend / mobile / microservices / Python-data, each answering entry points, element→type mapping, edge rules, model demotion, data-access shapes, middleware, layout order and security red lines.
- **Workbench interactions**: drag, zoom, Ctrl rubber-band multi-select, right-click menus (node → file, edge → locate caller/callee with a 3× flash on the target row), layout save/export, undo, per-type show/hide from the legend (eye toggles + hide-all), fuzzy search, one-click dark/light theme toggle (top-bar button; follows system preference and remembers your choice), and node right-click "Show related nodes only" to focus a subgraph (restore via the top-bar button or right-click on empty canvas).
- **Bilingual UI & data**: the UI ships in Chinese and English (top-right 中/EN switch). Graph text follows the language you invoke the skill in; fields can also carry both languages as `{ "zh": "…", "en": "…" }` so one graph serves both.
- **Smooth on large graphs**: path sampling lookup tables, off-screen edge culling and incremental redraw while dragging.

## Repository layout

```
CodeGraph/
├── .agents/skills/codegraph/               # The skill itself
│   ├── SKILL.md                           # Workflow: detect type → analyze → orchestrate → build → self-check
│   ├── references/
│   │   ├── graph-schema.md                # graph.json four-section data format spec
│   │   ├── analysis-guide.md              # Language-neutral analysis rules (map / demote / wire / layout)
│   │   └── packs/                         # Per-stack rule packs
│   │       ├── springboot.md              # SpringBoot / JVM services
│   │       ├── frontend.md                # React / Vue / Svelte / Next / Nuxt
│   │       ├── mobile.md                  # Flutter / Android / iOS / React Native
│   │       ├── microservices.md           # Multi-service systems + Go/Rust/Node quick rules
│   │       └── python-data.md             # pandas / sklearn / Jupyter + Django / FastAPI
│   ├── scripts/
│   │   └── build_graph_html.py            # Template + graph.json → self-contained graph.html (with validation)
│   └── assets/
│       └── graph.template.html            # Renderer template (the __GRAPH_DATA__ injection point)
├── demo/
│   └── canvas-demo.html                   # Full workbench demo (order module), open directly in a browser
├── example/.codegraph/                    # Sample output (order module: 33 nodes / 47 edges / 8 models)
│   ├── graph.json                         # Data source
│   └── graph.html                         # Double-click to open
├── README.md
└── README.zh-CN.md
```

## Requirements

- [Python 3.9+](https://www.python.org/) — only for the build script (`scripts/build_graph_html.py`); your project itself can be any language.
- Any modern browser — to open the generated `graph.html`. No internet connection, server or dependencies required.

## Install

The skill is a directory containing `SKILL.md`. Pick your agent:

### Claude Code

Copy it to `.claude/skills/codegraph/` (project) or `~/.claude/skills/codegraph/` (personal). See the [Agent Skills docs](https://code.claude.com/docs/en/skills).

### OpenCode

Copy it to `.opencode/skills/codegraph/` (project) or `~/.config/opencode/skills/codegraph/` (global). See the [OpenCode skills docs](https://opencode.ai/docs/skills).

### Codex CLI / Gemini CLI / Cursor (prompt-based agents)

These tools use command/prompt files rather than SKILL.md. Clone this repository (or copy `.agents/skills/codegraph/`) into your project, then register a command that points the agent at the skill:

**Codex CLI** — save as `~/.codex/prompts/codegraph.md`:
```md
Read .agents/skills/codegraph/SKILL.md and follow it exactly to turn this repository into a code graph (.codegraph/graph.json + graph.html).
```

**Gemini CLI** — save as `~/.gemini/commands/codegraph.toml`:
```toml
description = "Build a multi-stack code graph"
prompt = "Read .agents/skills/codegraph/SKILL.md and follow it exactly to turn this repository into a code graph (.codegraph/graph.json + graph.html)."
```

**Cursor** — save as `.cursor/commands/codegraph.md` with the same body as the Codex prompt above.

### ZCode

Copy the directory into your project at `.agents/skills/codegraph/`, or user-wide into `~/.agents/skills/codegraph/` (Windows: `C:\Users\<you>\.agents\skills\`). ZCode discovers it automatically.

## Upgrading from 1.x to 2.0

The skill was renamed `springboot-codegraph` → `codegraph` in 2.0 and generalized to all stacks. Existing `springboot-codegraph` copies are **not** updated by installing 2.0 — an old copy alongside the new one makes skill triggering ambiguous, so remove the old one:

**User-level install:**
```
:: Windows (cmd)
rmdir /s /q C:\Users\<you>\.agents\skills\springboot-codegraph

# bash / zsh (macOS / Linux / Git Bash / WSL)
rm -rf ~/.agents/skills/springboot-codegraph
```
**Project-level install:**
```
:: Windows (cmd)
rmdir /s /q <project>\.agents\skills\springboot-codegraph

# bash / zsh
rm -rf <project>/.agents/skills/springboot-codegraph
```
For other agents, apply the same cleanup under their skill roots (`~/.claude/skills/`, `~/.config/opencode/skills/`, `.opencode/skills/`, …). Existing `.codegraph/` outputs keep working: 2.0 renders all 1.x graph.json data unchanged (page layout localStorage keys are unaffected by the rename).

## Usage

In any repository that has the skill installed, just ask your agent — e.g.:

- "draw the code graph of this project" / "map this project as a code graph"
- "map this React app as a component / data-flow graph"
- "draw the architecture of our microservice system (gateway + services)"
- "把订单服务的调用关系画成图谱"（中文触发同样有效）

The graph text language follows the language of your request.

You can also build by hand:

```bash
# 1. Author <project-root>/.codegraph/graph.json per the skill docs
# 2. Build the page
python .agents/skills/codegraph/scripts/build_graph_html.py <project-root>/.codegraph/graph.json
# 3. Open <project-root>/.codegraph/graph.html
```

## Artifacts

| File | Purpose |
|---|---|
| `.codegraph/graph.json` | Single source of truth: all nodes / models / edges, including the generated layout |
| `.codegraph/graph.html` | Self-contained renderer (template + injected graph.json); do not hand-edit |
| `.codegraph/layout.user.json` | Optional: layout exported after manual arranging; merged back on regeneration |

## License

[MIT](../LICENSE) © RecursiveVar
