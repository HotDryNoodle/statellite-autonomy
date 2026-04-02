---
name: plantuml-architecture-styleguide
description: 论文级 PlantUML 架构图绘制助教。用于根据用户提供的模块分层/依赖关系/现有 PlantUML，生成或改写成符合论文排版的 PlantUML component/package 架构图：正交走线、细线条、高对比度黑字，模块标题加粗且略大；主流程边尽量无 label，次要依赖用虚线弱化；任何可能与线条干涉的箭头标注禁止写在箭头上，必须改为 note on link；语义说明优先用浮动 note（note left/right/top/bottom of）；使用 <<core>> <<algo>> <<util>> stereotype 配色，并用隐藏连线固定对齐；顶层图每个模块最多 2–3 行职责关键词，函数级细节移到子图或 note；输出必须且只包含一个完整 PlantUML 代码块。
version: 1.0.0
depends_on: []
tools:
  - plantuml
triggers:
  - architecture-diagram
  - plantuml
  - documentation
---

# PlantUML Architecture StyleGuide

## Overview

将“模块分层 + 依赖关系”转换为可直接用于论文/报告的高可读 PlantUML 架构图（component/package），并在不丢失语义的前提下强制统一排版风格与标注规则。

## Hard Requirements (Must Follow)

输出与风格约束（违反任意一条就必须重做）：

- **Only one code block**：最终输出只包含一个 ```plantuml 代码块（含 `@startuml`/`@enduml`），不附加解释文字。
- **Orthogonal routing**：必须 `skinparam linetype ortho`。
- **Thin + high-contrast**：线条细（`LineThickness`/`ArrowThickness` ~ 0.8），文字黑色（`defaultFontColor #000000`），尽量白底。
- **Bold module title**：组件标题使用 `<size:14><b>Title</b></size>`，职责关键词 2–3 行内（不要函数级细节）。
- **Main flow no labels**：主流程边尽量不加 `: label`。
- **Secondary deps dashed**：非主流程/弱依赖使用虚线（例如 `..>`）。
- **No arrow labels in cluttered routes**：任何可能与线条干涉的箭头标注禁止放在箭头上；必须改为 `note on link of A -> B`。
- **Prefer floating notes**：语义解释优先用 `note left/right/top/bottom of <component>`；只有在“必须绑定到某条边”的情况下才用 `note on link`。
- **Stereotype palette**：必须使用 `<<core>> <<algo>> <<util>>` 并设置各自背景/边框色。
- **Alignment helpers**：用 `-[hidden]->` 固定对齐与层次，不要靠大量交叉线“硬连”。

## Workflow (How to Generate the Diagram)

1. **Identify layers**：把模块分成 2–4 个 package（例如 Core Flow / Dynamics & Frames / Utilities / IO）。
2. **Choose the main flow**：找出 1 条从入口到核心输出的主路径（尽量直线、少拐弯）。
3. **Place components**：每个模块写成一个 `component`，内部只写 2–3 行职责关键词。
4. **Draw main flow edges**：主流程使用实线箭头，尽量无 label（需要解释就用 floating note）。
5. **Add secondary edges**：次要依赖用虚线（`..>`），必要时用隐藏连线对齐。
6. **Annotate safely**：
   - 语义解释：优先 floating note。
   - 必须绑定到边且会干扰走线：用 `note on link of A -> B`，内容短且不遮挡。

## Standard Header Snippet (Copy as-is)

始终从这个头部开始（可改 `title` 与布局方向，其它尽量不动）：

```plantuml
@startuml architecture
!theme aws-orange

skinparam componentStyle rectangle
skinparam defaultFontSize 11
skinparam defaultFontColor #000000
skinparam componentFontColor #000000
skinparam linetype ortho
skinparam ArrowThickness 0.8
skinparam LineThickness 0.8
skinparam ranksep 28
skinparam nodesep 20
skinparam shadowing false
skinparam DefaultTextAlignment left

skinparam note {
  BackgroundColor #FFFFFF
  BorderColor #BBBBBB
  FontColor #444444
}

skinparam componentBackgroundColor<<core>> #FFF3CD
skinparam componentBorderColor<<core>>     #C88719
skinparam componentBackgroundColor<<algo>> #E3F2FD
skinparam componentBorderColor<<algo>>     #1565C0
skinparam componentBackgroundColor<<util>> #F2F2F2
skinparam componentBorderColor<<util>>     #616161

top to bottom direction
title Your Paper Figure Title Here
@enduml
```

## Reference Sample

当用户没有明确给出布局时，优先参照：
- `references/sample.md`

## Trigger Examples

这些请求应触发本 skill：
- “根据这些模块分层和依赖关系，给我一张论文排版的 PlantUML 架构图（component/package）。”
- “把我现有的 PlantUML 架构图改成正交走线、细线条、黑字高对比度、主流程无 label、次要依赖虚线，并用 <<core>> <<algo>> <<util>> 配色。”
- “标注不要压在线上；需要标注关系时用 note on link，语义说明用浮动 note。”
