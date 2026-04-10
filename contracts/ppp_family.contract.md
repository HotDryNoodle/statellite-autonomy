@page requirements_ppp_family_contract PppFamily Contract
@ingroup requirements

# PPP Family Contract

## 1. 目标

冻结本项目 PPP family 的权威知识源、PPP-AR 核心运行边界、输入输出约束，以及与 LEO 精密定轨工作流的 coupling entry。

当前阶段只收口 family 级 contracts 与专家知识调度，不在 `product/` 内实现新的 PPP 求解模块。

## 2. 模块定位（Module Scope）

- PPP family 归属于 Navigation 层，由全局 `pride-pppar-expert` 提供算法与实现证据支撑。
- 本项目当前 PPP family 以 PRIDE-PPPAR 为权威实现样本，用于解释、合同冻结、expert handoff 与后续产品化设计。
- PPP family 负责 GNSS PPP / PPP-AR 的运行链路、观测建模入口、模糊度处理入口与结果诊断边界。

不负责：

- RD-POD 动力学建模与验证闭环
- Prediction / Mission Planning 业务逻辑
- 直接替代 PRIDE-PPPAR 上游项目维护其独立实现

## 3. 术语与假设（Terms & Assumptions）

- `pppar_expert_agent` 的默认知识入口固定为 Obsidian `expert-system` vault 中 `wiki/pppar/` 允许范围。
- PRIDE-PPPAR 权威源码树固定为 `/home/hotdry/Documents/expert-system/raw/pppar/sources/PRIDE/`，仅在 wiki 缺失、过时或需要源码级实现细节时回退。
- 本项目对 PPP family 的证据优先级为：指定 Obsidian wiki 范围 -> raw/pppar/sources/PRIDE -> 本地 runtime (`toolchain/` + `data/`)。
- PPP family 仍受 `contracts/navigation.contract.md` 的 Navigation 层边界约束。

## 4. 数据输入（Inputs）


| 名称                          | 来源                 | 说明                                                     | 备注                        |
| --------------------------- | ------------------ | ------------------------------------------------------ | ------------------------- |
| RINEX Observation           | 外部会话输入             | GNSS 观测数据                                              | `pdp3.sh` 最终消费对象          |
| RINEX Navigation / BRDM     | 外部会话输入             | 广播星历或导航文件                                              | 由预处理阶段准备                  |
| Control File                | PRIDE config       | PPP/PPP-AR 模式、频点、模型与输出选项                               | `pdp3.sh` 与 `get_ctrl` 消费 |
| Precise Products            | 上游产品中心             | Orbit / Clock / ERP / Bias / Quaternion / optional GIM | 缺失时必须显式失败                 |
| Table Assets                | `table/`           | ANTEX、leap second、潮汐与站星参数等                             | `PrepareTables` 阶段装载      |
| Prior Trajectory / Attitude | LEO coupling entry | `kin_*`、`pso_*` 或 quaternion inputs                    | 仅冻结入口，不冻结 LEO 动力学细节       |


## 5. 数据处理与设计约束（Contracts）

### 5.1 权威知识源与证据顺序

@contract{PppFamily_5_1}

Contract：

- PPP family 的默认知识源为 `/home/hotdry/Documents/expert-system/wiki/pppar` 指定范围；源码与手册证据回退到 `/home/hotdry/Documents/expert-system/raw/pppar/sources/PRIDE`。
- 任何 PPP family 解释、handoff、contract 更新或后续产品化设计，都必须先在允许的 Obsidian wiki 范围内检索；仅在 wiki 缺失、过时或不足以支撑实现细节时，才回退到 PRIDE 源码模块与运行脚本。
- 本地 runtime 仓库 `/home/hotdry/projects/PRIDE-PPPAR` 只作为执行环境，不再作为源码权威。

### 5.2 PPP-AR 运行拓扑

@contract{PppFamily_5_2}

Contract：

- `scripts/pdp3.sh` 是 PPP family 的顶层运行编排入口。
- PPP family 的主链路至少包含：`PrepareTables -> PrepareRinexNav -> PrepareProducts -> spp -> tedit -> lsq/redig 迭代 -> optional arsig -> final lsq -> outputs`。
- `arsig` 负责在 float ambiguity 之后生成整数约束，并把约束重新喂回 `lsq`；`arsig` 不是独立于 `lsq` 的最终求解器。

### 5.3 输入依赖与失败语义

@contract{PppFamily_5_3}

Contract：

- PPP family 运行前必须显式准备观测文件、控制文件、精密 orbit/clock/ERP/bias 产品和 `table/` 依赖。
- 当 PPP-AR 开启时，缺失 bias / ambiguity-resolution 所需产品必须显式失败，不允许 silent fallback 为“看似固定、实则未固定”的结果。
- 缺失表文件、精密产品、姿态产品或 prior trajectory 时，失败语义必须能够映射回 `CheckExecutables`、`PrepareTables`、`PrepareProducts` 或 `ProcessSingleSession` 阶段之一。

### 5.4 状态参数与观测方程家族

@contract{PppFamily_5_4}

Contract：

- PPP family 的核心状态族至少包括：坐标、接收机钟差 / ISB、对流层 / 梯度（非 LEO）、以及按观测弧段动态生灭的 ambiguity 参数。
- 核心观测注入必须以 ionosphere-free code / phase 方程、精密 orbit/clock、更正模型和参数表映射为基础进入 `lsq` 正规方程。
- ambiguity 参数必须由编辑结果驱动创建与移除，不能被建模为与弧段无关的静态常量，也不能退化为仅 epoch-local 标记。

### 5.5 输出与诊断产物

@contract{PppFamily_5_5}

Contract：

- PPP family 运行后至少应产生位置 / 轨迹、残差、ambiguity、状态统计和接收机钟差等结果或诊断产物，例如 `kin_*`、`pos_*`、`res_*`、`amb_*`、`stt_*`、`rck_*`。
- 阶段性失败必须通过日志或报错文本暴露在可定位的运行阶段，而不是仅表现为结果文件缺失。
- expert 对 PPP family 的诊断说明必须能把缺失产物回溯到对应运行阶段和上游依赖类别。

### 5.6 LEO coupling entry

@contract{PppFamily_5_6}

Contract：

- PPP family 必须保留 LEO 精密定轨的 coupling entry，证据入口为 `pdp3.sh` 的 `L` mode、相关 `table` 配置以及姿态 / 先验轨道输入。
- 在 LEO mode 下，PPP family 可消费 `pso_*` 转换得到的 `kin_*` 先验轨迹和 quaternion / attitude 产品作为观测建模入口。
- 本条款只冻结 LEO 输入接口、模式入口和依赖边界；不冻结 RD-POD 动力学模型、力模型、传播器实现或完整验证标准。

### 5.7 当前边界与非目标

@contract{PppFamily_5_7}

Contract：

- 本轮 PPP family 只冻结 family 级合同、expert 知识入口和运行边界，不新增 `product/` 业务实现。
- PPP family 与 RD-POD family 继续分离；任何超出 LEO coupling entry 的内容都必须在 `contracts/rdpod_family.contract.md` 冻结后再扩展。
- Prediction / Mission Planning 只可消费未来冻结后的稳定 handoff，不得直接依赖 PRIDE 的内部文件格式或私有中间状态。

## 6. 测试要求（verify）

@verify{PppFamily_6_1}

- 目的：验证 PPP family 的权威知识源顺序与 supplemental knowledge 边界被保持。
- 关联合同：`@contract{PppFamily_5_1}`

@verify{PppFamily_6_2}

- 目的：验证 `pppar_expert_agent` 只能触达 PPP family 合同并通过独立 expert session 调度。
- 关联合同：`@contract{PppFamily_5_1}` `@contract{PppFamily_5_7}`

@verify{PppFamily_6_3}

- 目的：验证 PPP-AR 运行拓扑、阶段失败语义和输出诊断映射可被保留。
- 关联合同：`@contract{PppFamily_5_2}` `@contract{PppFamily_5_3}` `@contract{PppFamily_5_5}`

@verify{PppFamily_6_4}

- 目的：验证 LEO coupling entry 被保留，但不会越界冻结 RD-POD 业务实现。
- 关联合同：`@contract{PppFamily_5_6}` `@contract{PppFamily_5_7}`

## 附录A：设计约束表


| ClauseId                   | 说明                 |
| -------------------------- | ------------------ |
| `@contract{PppFamily_5_1}` | 权威知识源与证据顺序         |
| `@contract{PppFamily_5_2}` | PPP-AR 运行拓扑        |
| `@contract{PppFamily_5_3}` | 输入依赖与失败语义          |
| `@contract{PppFamily_5_4}` | 状态参数与观测方程家族        |
| `@contract{PppFamily_5_5}` | 输出与诊断产物            |
| `@contract{PppFamily_5_6}` | LEO coupling entry |
| `@contract{PppFamily_5_7}` | 当前边界与非目标           |


## 附录B：测试验证表


| verify-ID                | 说明                    |
| ------------------------ | --------------------- |
| `@verify{PppFamily_6_1}` | 权威知识源顺序               |
| `@verify{PppFamily_6_2}` | expert 调度与会话隔离        |
| `@verify{PppFamily_6_3}` | 运行拓扑与失败语义             |
| `@verify{PppFamily_6_4}` | LEO coupling entry 边界 |
