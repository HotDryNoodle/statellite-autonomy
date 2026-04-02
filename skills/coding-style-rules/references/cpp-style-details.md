# Coding Style Details

## Doxygen 与追踪标签

- 默认使用块注释 `/** ... */`
- 标准标签可包含 `@brief`、`@param`、`@return`、`@note`、`@warning`
- 追踪标签必须使用 brace form：
  - `@contract{ClauseId}`
  - `@verify{ClauseId}`
  - `@covers{ApiSymbol}`

### 有效示例

- `@contract{TimeSys_6_2}`
- `@verify{RefSys_3_1}`
- `@covers{orbit::ref::RefSys::GetTransform}`

### 无效示例

- `@contract docs/requirements/RefSys.contract.md#3.1`
- `@verify RefSys_3_1`
- `@covers orbit::time::TimeSys::Set`

## 数学注释

- 行内公式使用 `\f$ ... \f$`
- 块公式使用 `\f[ ... \f]`
- 关键符号和单位至少在文件级或公共 API 级定义一次

## 测试注释

- 每个 `TEST()` / `TEST_F()` 必须在最近注释块中包含至少一个 `@verify{...}` 与 `@covers{...}`
- 推荐补充：
  - `@par 测试场景：`
  - `@par 测试内容：`
  - `@par 失败判定：`
  - `@par 备注：`

## 错误处理

- 合同要求显式失败时，禁止 silent fallback
- API 公开错误形式应在模块内部保持一致
