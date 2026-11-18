# `myrmex` Engineering Standards

Applies to all implementation code built for `myrmex` (`packages/mcp`, `packages/runner`, and `benchmarks/bench-01`).

## Quality Thresholds

- **Cyclomatic Complexity**: `<= 10` per function.
- **Mutation Testing**: Zero surviving mutants on core domain and protocol logic.
- **Type Safety**: Strict static typing with zero type-escape hatches.
- **Error Handling**: Return explicit typed result/status variants for expected domain failures (lease conflicts, merge conflicts, gate failures) rather than throwing untyped exceptions.
- **Slice Size**: `<= 20 LOC` net production increment per ticket during `/mnb-slice` execution.
