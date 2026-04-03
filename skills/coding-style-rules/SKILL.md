---
name: coding-style-rules
description: C++17 coding style rules for this repository; enforce .clang-format, PascalCase naming, C++ Core Guidelines, and Doxygen with contract reference tags.
version: 1.0.0
depends_on: []
tools:
  - .clang-format
triggers:
  - c++
  - style
  - review
---

# Coding Style Rules (v1.0)

## TL;DR

- 只在 C++ 实现、C++ 测试、代码 review 时加载。
- 强制项：`.clang-format`、PascalCase 类型/函数命名、Doxygen、`@contract/@verify/@covers`
- 若修改 C++ 文件，完成前必须保证格式与注释规则一致。

## Load When

- 新增或修改 `product/src/**/*.h`、`product/src/**/*.cpp`
- 新增或修改 `product/tests/**/*.cpp`
- 审查 C++ 风格、一致性、注释与追踪标签

## Must Follow

- 默认中文回复；代码注释默认中文，除非合同要求英文。
- 使用仓库 `.clang-format` 作为格式来源。
- 公共 API 和 contract boundary 使用 Doxygen 块注释 `/** ... */`
- 函数/类型优先 PascalCase；局部变量与常量遵循模块既有一致性。
- 禁止 silent fallback；时间尺度、坐标系、单位等依赖应显式化。

## Enforced By

- Format source of truth: `.clang-format`
- Detailed traceability / comment rules: `references/cpp-style-details.md`

## References

- `references/cpp-style-details.md`
