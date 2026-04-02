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

## Scope

These rules apply to C++17 code in this repository (implementation + tests), unless a `*.contract.md` explicitly overrides them.

## Language (mandatory)

- Responses should be in Chinese by default.
- Code comments should be in Chinese unless the project explicitly requires English.

## Formatting (mandatory)

- Use the repository `.clang-format` as the source of truth.
- If you modify C++ files, they must be clang-formatted before considering work done.

## Doxygen comment style (mandatory, high priority)

- Use block-style Doxygen comments as the default style:
  - `/** ... */`
- Avoid using per-line `///` style for new/updated comments unless a file already requires it for local consistency.
- This style applies to both production code and tests.

Supported standard Doxygen tags (non-exhaustive):

- `@brief`
- `@param` / `@tparam`
- `@return`
- `@note` / `@warning`
- `@file` / `@ingroup`

Traceability tags coexist in the same Doxygen block:

- `@contract{ClauseId}`
- `@verify{ClauseId}`
- `@covers{ApiSymbol}`

## Naming (mandatory)

- Functions: PascalCase (e.g., `ComputeU`, `ICRFToITRF`)
- Types: PascalCase (e.g., `TimeSys`, `EopProvider`)
- Variables: lower_snake_case OR existing project convention (do not mix within the same file).
- Constants: kPascalCase (e.g., `kSecPerDay`) OR existing project convention (do not mix within the same file).

If the repository already uses a different convention in a specific module, follow the local convention and record it under Conformance -> Known deviations.

## Design rules (mandatory)

- Follow C++ Core Guidelines: ownership, RAII, error handling, and API design.
- Avoid hidden global state for physics/data dependencies (e.g., EOP, leap seconds); prefer explicit injection or explicit object state.
- Prefer types that make units/time-scale/frame explicit (names, structs, or strong typedefs).

## Comments & docs (mandatory)

Use Doxygen-style comments for public types/functions and for any API that represents a contract boundary.

### Math in comments (required)

For code that implements mathematical transformations, models, or derivations, document the math using LaTeX notation inside Doxygen comments.

Rules:
- Prefer Doxygen math environments so LaTeX commands render correctly in HTML:
  - Inline math: `\f$ ... \f$`
  - Block math: `\f[ ... \f]`
- Define symbols and units locally when not obvious (at least once per file or per public API).

### Traceability tags (required)

This repository's info system requires stable anchor IDs for API/Test/Contract traceability.
Use only the brace form tags below:

- `@contract{ClauseId}` for source/API contract mapping.
- `@verify{ClauseId}` for per-test clause verification mapping.
- `@covers{ApiSymbol}` for per-test API coverage mapping.

Anchor format constraints:

- `ClauseId` must match `[A-Za-z][A-Za-z0-9_]*` (e.g., `RefSys_3_1`, `TimeSys_6_2`).
- `ApiSymbol` should be fully-qualified where possible (e.g., `orbit::time::TimeSys::Set`).

Placement constraints:

- For production code (`source/`), place `@contract{...}` in the closest Doxygen block for the API/type/function implementing the clause.
- For tests (`tests/`), each `TEST()` / `TEST_F()` must include at least one `@verify{...}` and one `@covers{...}` in the nearest comment block.
- For tests (`tests/`), the nearest Doxygen comment block should include structured `@par` sections for readability:
  - `@par 测试场景：`
  - `@par 测试内容：`
  - `@par 失败判定：`
  - `@par 备注：`

Valid examples:

- `@contract{TimeSys_6_2}`
- `@verify{RefSys_3_1}`
- `@covers{orbit::ref::RefSys::GetTransform}`

Invalid examples:

- `@contract docs/requirements/RefSys.contract.md#3.1`
- `@verify RefSys_3_1`
- `@covers orbit::time::TimeSys::Set`

Keep tags near the enforcing code/test logic. Do not use free-text alternatives like `CONTRACT xxx` in source comments.

## Error handling

- No silent fallback for missing external data/inputs when contracts require explicit failure.
- Prefer explicit status/exception types as appropriate to the module's public API; be consistent within a module.
