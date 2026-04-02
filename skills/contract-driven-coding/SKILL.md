---
name: contract-driven-coding
description: Contract-driven coding workflow. Use when implementing any module/features based on one or more *.contract.md documents; enforces Preconditions/Conformance sections and clause traceability.
version: 1.0.0
depends_on: []
tools:
  - contracts/*.contract.md
triggers:
  - implementation
  - contract-driven
  - feature
---

# Contract-Driven Coding Skill (v1.0)

## When to use

Use this skill whenever the user asks to design/implement/refactor code and they provide (or imply) one or more `*.contract.md` files as the source of truth.

## Language (mandatory)

- Use Chinese for responses by default.
- Code comments should be in Chinese unless a contract requires English.

## Preconditions (must print before work)

At the beginning of your response, print exactly:

Preconditions:
- ContractDrivenCoding.skill v1.0
- CodingStyleRules.skill v1.0
- Active contracts:
  - <contract-1>
  - <contract-2>

If the user did not specify active contracts, stop and ask them to list the `*.contract.md` files for this task.

## Workflow (must follow)

1. Load contracts: read only the active `*.contract.md` files needed for the task.
2. Extract contracts into a checklist:
   - physical assumptions / scope
   - units & conventions (time scale, frames, sign conventions)
   - API contract (inputs/outputs/errors)
   - Failure Contract (explicit failure semantics)
   - Test Obligation (what must be testable)
3. Detect conflicts/ambiguity:
   - if contracts conflict, stop and ask for a ruling
   - if a clause is underspecified (e.g., tolerances), mark it as "needs confirmation" before coding
4. Implement by clause:
   - map each key clause -> code location(s) (file/function/type)
   - ensure no silent fallback for missing dependencies/data
5. Minimal verification:
   - ensure failure paths are reachable (return code/exception/state)
   - ensure units and frame/time-scale boundaries are explicit in names/types/comments
6. Source traceability tag is mandatory:
   - for each contract-driven API/type/function, add `@contract{ClauseId}` in the nearest Doxygen comment block
   - `ClauseId` format: `[A-Za-z][A-Za-z0-9_]*`
   - do not use path/section forms like `@contract docs/requirements/RefSys.contract.md#3.1`

## Conformance (must print at end)

At the end of your response, print:

Conformance:
- Contract clauses covered: <list of contract section IDs you implemented/changed>
- Style rules enforced: CodingStyleRules.skill v1.0
- Known deviations: <None | bullet list with justification>

Notes:
- If you cannot cover some clauses in this change, list them explicitly under "Known deviations" with justification and the missing evidence.

## Output discipline

- Do not restate whole contracts; only cite clause IDs and summarize what you did.
- If you add new behavior, it must be justified by an explicit contract clause (or be called out as a deviation).
