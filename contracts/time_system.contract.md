@page requirements_timesys_contract TimeSys Contract
@ingroup requirements

# TimeSys Contract

## 1. 模块定位（Module Scope）

`unit::time` 模块负责在本项目中提供统一、可验证的时间表示与显式时间尺度转换。

- 为公共层和 Navigation / Prediction / Mission Planning 提供一致时间基准。
- 负责 UTC、UT1、TAI、TT、GPST、BDT 的时间表达与显式转换。
- 负责消费闰秒表和 UT1-UTC 差值。

不负责：

- 坐标变换
- 轨道动力学
- EOP 生成或预测

## 2. 术语与假设（Terms & Assumptions）

- 秒为基准单位，`frac_day = seconds / 86400`。
- UTC 仅作为输入/输出尺度，内部计算基于连续时间尺度。
- 闰秒必须来自显式数据表，禁止在逻辑中预测。
- 未提供 UT1-UTC 时，任何 UT1 读取必须失败。

## 3. 数据输入（Inputs）

| 名称 | 来源 | 说明 | 单位 | 类型 |
| --- | --- | --- | --- | --- |
| LeapSecondTable | 数据文件 | 闰秒表快照 | s | 表格 |
| UT1_UTC | EOP / 上游模块 | UT1-UTC 差值 | s | double |
| CivilTime | 外部接口 | UTC civil 时间 | s | struct |
| TimeScaleValue | 外部模块 | UTC/UT1/TAI/TT/GPST/BDT 输入 | - | struct |

## 4. 数据处理与设计约束（Contracts）

### 4.1 接口契约
@contract{TimeSys_4_1}

Contract：

- `TimeSys::Set<T>()` 只接受显式时间尺度类型。
- `TimeSys::Get<T>()` 不允许隐式转换。
- `TimeSys +/- duration` 与 `TimeSys - TimeSys` 都以 TAI 为内部计算基准。
- 未初始化对象参与运算时必须返回显式失败。

### 4.2 状态有效性
@contract{TimeSys_4_2}

Contract：

- `TimeSys` 必须处于 `kUninitialized`、`kValid`、`kInvalid` 三态之一。
- `Get<T>()` 在 `Invalid` / `Uninitialized` 状态下必须显式失败。

### 4.3 UTC / TAI / TT 转换
@contract{TimeSys_4_4_3}

Contract：

- UTC 必须通过闰秒表与 TAI 显式互转。
- TT = TAI + 32.184s。
- `UTC -> TAI -> UTC` 在闰秒定义域内必须可逆。

### 4.4 UT1 约束
@contract{TimeSys_4_4_4}

Contract：

- UT1 = UTC + (UT1-UTC)。
- 未提供 `UT1-UTC` 时，UT1 读取必须返回失败。
- 禁止默认假设 `UT1 = UTC`。

### 4.5 GPST / BDT 约束
@contract{TimeSys_4_4_5}

Contract：

- GPST / BDT 不包含闰秒。
- week/sec 表示必须连续。
- `sec` 必须位于 `[0, 604800)`。

### 4.6 闰秒数据与行为
@contract{TimeSys_4_6_1}
@contract{TimeSys_4_6_2}

Contract：

- 闰秒表必须通过数据文件或显式快照加载。
- UTC civil time 在合法闰秒插入点允许 `23:59:60`。
- 非 UTC 时间尺度不允许闰秒表示。

### 4.7 错误处理规范
@contract{TimeSys_4_7_1}

以下情况必须失败，不允许 silent fallback：

- 未提供闰秒表却请求 UTC 相关设置或读取
- 未提供 UT1-UTC 却请求 UT1
- CivilTime 非法
- MJD 非法
- week/sec 越界
- 模板接口类型不匹配
- 超出闰秒表覆盖区间

## 5. 数据输出（Outputs）

| 名称 | 去向 | 说明 | 单位 | 类型 |
| --- | --- | --- | --- | --- |
| UTC_MJD | 上游模块 | UTC 的 MJD 表示 | day | struct |
| UT1_MJD | 上游模块 | UT1 的 MJD 表示 | day | struct |
| TAI_MJD | 上游模块 | TAI 的 MJD 表示 | day | struct |
| TT_MJD | 上游模块 | TT 的 MJD 表示 | day | struct |
| GPST_WeekSec | 上游模块 | GPS 周秒 | s | struct |
| BDT_WeekSec | 上游模块 | BDS 周秒 | s | struct |
| TimeDelta | 上游模块 | `TimeSys - TimeSys` 秒差 | s | duration |

## 6. 测试要求（verify）

@verify{TimeSys_6_1}

- 目的：验证 UTC / TT / GPST / BDT 的 round-trip 一致性。
- 关联合同：`@contract{TimeSys_4_1}` `@contract{TimeSys_4_4_3}` `@contract{TimeSys_4_4_5}`

@verify{TimeSys_6_2}

- 目的：验证非法闰秒输入会失败。
- 关联合同：`@contract{TimeSys_4_6_2}` `@contract{TimeSys_4_7_1}`

@verify{TimeSys_6_3}

- 目的：验证合法闰秒边界行为。
- 关联合同：`@contract{TimeSys_4_4_3}` `@contract{TimeSys_4_6_2}`

@verify{TimeSys_6_4}

- 目的：验证未提供 `UT1-UTC` 时失败，提供后成功。
- 关联合同：`@contract{TimeSys_4_4_4}` `@contract{TimeSys_4_7_1}`

@verify{TimeSys_6_5}

- 目的：验证模板类型不匹配失败。
- 关联合同：`@contract{TimeSys_4_1}` `@contract{TimeSys_4_7_1}`

@verify{TimeSys_6_6}

- 目的：验证连续尺度单调性。
- 关联合同：`@contract{TimeSys_4_4_3}` `@contract{TimeSys_4_4_5}`

@verify{TimeSys_6_7}

- 目的：验证 `std::chrono` 运算与秒差行为。
- 关联合同：`@contract{TimeSys_4_1}`

@verify{TimeSys_6_8}

- 目的：验证非法输入、缺失依赖和越界错误。
- 关联合同：`@contract{TimeSys_4_7_1}`

## 附录A：设计约束表

| ClauseId | 说明 |
| --- | --- |
| `@contract{TimeSys_4_1}` | 接口契约 |
| `@contract{TimeSys_4_2}` | 状态有效性 |
| `@contract{TimeSys_4_4_3}` | UTC / TAI / TT 转换 |
| `@contract{TimeSys_4_4_4}` | UT1 约束 |
| `@contract{TimeSys_4_4_5}` | GPST / BDT 约束 |
| `@contract{TimeSys_4_6_1}` | 闰秒数据来源 |
| `@contract{TimeSys_4_6_2}` | 闰秒行为 |
| `@contract{TimeSys_4_7_1}` | 错误处理 |

## 附录B：测试验证表

| verify-ID | 说明 |
| --- | --- |
| `@verify{TimeSys_6_1}` | round-trip 一致性 |
| `@verify{TimeSys_6_2}` | 非法闰秒失败 |
| `@verify{TimeSys_6_3}` | 闰秒边界行为 |
| `@verify{TimeSys_6_4}` | UT1 依赖行为 |
| `@verify{TimeSys_6_5}` | 模板类型不匹配 |
| `@verify{TimeSys_6_6}` | 连续尺度单调性 |
| `@verify{TimeSys_6_7}` | chrono 运算 |
| `@verify{TimeSys_6_8}` | 非法输入与缺失依赖 |
