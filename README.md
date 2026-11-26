# Playground

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)

个人小工具与实验性项目的集合仓库，收录日常开发与效率提升相关的轻量工具。

## 工具列表

| 目录 | 简介 | 技术栈 / 依赖 | 文档 |
| --- | --- | --- | --- |
| [`CodeGraph`](./CodeGraph) | 多技术栈代码图谱 Agent Skill，将任意代码仓库转换为可交互、离线自包含的单文件代码图谱工作台（`.codegraph/graph.html`） | Python 3.9+（零外部依赖） | [English](./CodeGraph/README.md) · [中文](./CodeGraph/README.zh-CN.md) |
| [`VideoTool`](./VideoTool) | 单文件视频体积诊断、无损提取（remux）与受控重编码压缩工具，附带零依赖本地网页面板 | Python 3.8+、ffmpeg（按需自动下载） | [中文文档](./VideoTool/README.md) |

## 目录结构

```
Playground/
├── CodeGraph/         # 多技术栈代码图谱 Skill 与离线工作台演示
├── VideoTool/         # MP4 体积分析与压缩命令行工具 + 本地 Web UI
├── LICENSE            # MIT 许可证
├── .gitignore
└── README.md
```

## 快速开始

请进入对应工具子目录查看各自的使用说明：

- **CodeGraph**：参见 [CodeGraph/README.zh-CN.md](./CodeGraph/README.zh-CN.md)
- **VideoTool**：参见 [VideoTool/README.md](./VideoTool/README.md)

## 许可证

本仓库及所有子项目统一采用 [MIT License](./LICENSE) © 2026 RecursiveVar
