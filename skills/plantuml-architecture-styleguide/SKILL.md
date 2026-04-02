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

## TL;DR

- 只在 PlantUML 架构图任务中加载。
- 最终输出必须且只包含一个完整 `plantuml` 代码块。
- 强制项：正交走线、细线条、黑字高对比、主流程少标签、次要依赖虚线、优先 floating notes。

## Load When

- 根据模块分层/依赖关系生成 PlantUML 架构图
- 重写已有 PlantUML 图为论文风格
- 需要控制标注与布局避免箭头文字干扰

## Must Follow

- `skinparam linetype ortho`
- 主流程边尽量无 label，次要依赖用虚线
- 组件标题加粗，职责关键词限制在 2-3 行
- 箭头附近拥挤时，禁止把标注直接写在线上
- 语义说明优先 `note left/right/top/bottom of`

## Enforced By

- Rendering target: `plantuml`
- Header / layout / examples: `references/layout-and-examples.md`

## References

- `references/layout-and-examples.md`
- `references/sample.md`
