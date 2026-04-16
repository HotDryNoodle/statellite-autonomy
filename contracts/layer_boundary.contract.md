# Layer Boundary Contract

## 1. 目标

冻结 `product/` 内公共层、Navigation、Prediction、Mission Planning 的职责边界。

## 2. 约束

@contract{LayerBoundary_4_1}

- `src/unit/` 承载公共基础模块，不绑定具体业务层。
- `product/src/unit/` 承载公共基础模块，不绑定具体业务层。
- `product/src/navigation/` 负责导航求解家族与编排。
- `product/src/prediction/` 负责状态传播与未来状态估计。
- `product/src/mission_planning/` 负责任务规划。

@contract{LayerBoundary_4_2}

- 公共模块可被业务层消费，业务层不得反向依赖具体上层策略模块。
- 当前 `unit::time` 明确归属公共层。

