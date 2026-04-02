---
name: contract-driven-testing
description: Contract-driven test design workflow. Use when designing/authoring GTest acceptance criteria from one or more *.contract.md documents; enforces Preconditions/Conformance and clause-mapped test cases.
version: 1.0.0
depends_on: []
tools:
  - contracts/*.contract.md
  - tests/
triggers:
  - test-design
  - acceptance
  - contract-driven
---

# Contract-Driven Testing Skill (v1.0)

## When to use

Use this skill whenever the user asks to design tests / acceptance criteria / GTest cases and the requirements are (or should be) defined by `*.contract.md`.

## Language (mandatory)

- Use Chinese for responses by default.
- Code comments should be in Chinese unless a contract requires English.

## Preconditions (must print before work)

At the beginning of your response, print exactly:

Preconditions:
- ContractDrivenTesting.skill v1.0
- CodingStyleRules.skill v1.0
- Active contracts:
  - <contract-1>
  - <contract-2>

If the user did not specify active contracts, stop and ask them to list the `*.contract.md` files for this task.

## Workflow (must follow)

1. Load contracts: read only the active `*.contract.md`.
2. Extract test obligations:
   - invariants / conservation / orthogonality / monotonicity
   - representation consistency / round-trip consistency
   - failure semantics (MissingX, invalid ranges, out-of-domain)
   - data-driven behaviors (EOP interpolation, Bulletin-A mode)
3. Convert each obligation into a test case using a fixed template:
   - Test name
   - Contract mapping (ClauseId IDs)
   - Purpose
   - Arrange / Act / Assert
   - Failure meaning
   - Notes (tolerance provenance, reference impl cross-check, data files)
   - In the nearest Doxygen comment block before each test, include:
     - `@par 测试场景：`
     - `@par 测试内容：`
     - `@par 失败判定：`
     - `@par 备注：`
4. Tolerances:
   - tolerances MUST come from contract; otherwise mark "needs confirmation"
5. Negative testing is mandatory:
   - for each Failure Contract clause, add at least one test that proves the failure is observable (not silent fallback)
6. Traceability tags are mandatory per test:
   - each `TEST()` / `TEST_F()` MUST include `@verify{ClauseId}` (>=1)
   - each `TEST()` / `TEST_F()` MUST include `@covers{ApiSymbol}` (>=1)
   - each `TEST()` / `TEST_F()` MUST include the 4 `@par` sections:
     - `@par 测试场景：`
     - `@par 测试内容：`
     - `@par 失败判定：`
     - `@par 备注：`
   - `ClauseId` format: `[A-Za-z][A-Za-z0-9_]*`
   - `ApiSymbol` should be fully-qualified whenever possible

## Conformance (must print at end)

At the end of your response, print:

Conformance:
- Contract clauses covered: <list of contract section IDs mapped into tests>
- Style rules enforced: CodingStyleRules.skill v1.0
- Known deviations: <None | bullet list with justification>

## Output discipline

- Do not write production code for the modules under test.
- You may show short GTest skeletons (Arrange/Act/Assert), but keep them minimal and implementation-agnostic.

## Tag examples (required style)

Valid:

- `@verify{TimeSys_2_1}`
- `@verify{RefSys_3_1}`
- `@covers{orbit::time::TimeSys::Set}`
- `@covers{orbit::ref::RefSys::GetTransform}`

Invalid:

- `@verify TimeSys_2_1`
- `@covers orbit::time::TimeSys::Set`
- `@verify{docs/requirements/RefSys.contract.md#3.1}`
