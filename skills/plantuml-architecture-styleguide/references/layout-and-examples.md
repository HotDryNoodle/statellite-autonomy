# PlantUML Architecture StyleGuide References

## 标准头部

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

## 生成步骤

1. 按职责分成 2-4 个 package。
2. 找主流程，尽量直线。
3. 主流程用实线，次要依赖用虚线。
4. 组件标题加粗，职责关键词控制在 2-3 行。
5. 语义说明优先 floating note，必要时才用 `note on link`。

## 参考样例

- `references/sample.md`
