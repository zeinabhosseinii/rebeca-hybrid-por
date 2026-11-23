# Opt-in AST property filter in the production FTTS generator

This promotes the tested native candidate filter into an explicit generator option. It remains experimental and restricted. The default generator behavior is unchanged; no default switch, static priorities, C1 relation, proviso rule, full-expansion barrier, assertion handler or deadlock exception is changed.

## Usage and contract

```bash
java -jar target/rmc-2.14.jar -s MODEL.rebeca -p MODEL.property -e TIMED_REBECA -v 2.3 --aria --aria-property-filter -o OUTPUT
```

The option requires ARIA, an external property and timed FTTS. Symmetry, JSON dependencies and trace/TTS modes are excluded. Main/class/method/constructor annotations are refused rather than silently retaining existing static scheduling priorities. Configuration errors specific to this feature print their explanation and exit with status 2, so a shell `&&` chain cannot silently compile stale output after rejection. This does not change legacy error handling for unrelated CLI options.

Partial candidate permissions are enabled only for the exact reviewed unannotated CellRegisterObserved source digest `e8e0a20c1af6af94fb02c59ff7ad2f9b33a84dd6b55872ee3b5cb89135a325f6`, with a supported external state assertion. This explicit allowlist is intentional: passing an AST shape check is not a general dependency proof. A comment or line-ending change also misses that digest and conservatively disables partial permissions. Do not remove the allowlist to make counts smaller.

For other unannotated sources, unknown property/effect shapes, or incomplete metadata, all partial candidates are denied. The existing scheduler explores full choices and still actually evaluates the property and source assertions. It does not report an unsupported predicate as true. It does not undo a pre-existing static annotation; hence annotated inputs are rejected.

## Metadata and native rule

PropertyObservationMetadata is the shared production typed-AST implementation. The diagnostic PropertyEffectAstAudit is now a thin adapter to that same implementation, eliminating the duplicate extractor. Its existing primitive/scalar/property fragment is unchanged. It is independent per invocation; no mutable static analysis state is introduced.

The generator maps main-instance order to native actor IDs and declaration order (base 1, with inheritance refused by the metadata fragment) to native message IDs. It emits a constant invisible-action table only when the option is selected. Message ID zero and unused IDs are always false. Truncated ID spaces, malformed metadata and rejected shapes return an entirely false table.

Each existing native candidate still first passes the existing dependency/C1 machinery. An exhaustive candidate may proceed because it removes no enabled scheduler choice. A partial candidate is allowed only when it has alternatives and every alternative has a known in-range ID and writes no property-observed field. This applies to mixed actor unions too. Rejected candidates fall through to later candidates or the original full fallback. Every actual trial still passes the existing proviso. Isolated/passive and completed-full barrier gates remain disabled by the external-property configuration.

This is a restriction of existing candidates, not a new dependency relation or source-level proof of assertion invariance. It creates no additional candidates. Native verification needs no full graph; complete graphs are used only in post-run finite validation.

## Linux validation

Both complete Maven executable builds passed on Java 17. The final native matrix includes two variants per row: actual opt-in generated C++ and its same-generated PO-off control.

| Case | Both outcomes | Control states/steps | Opt-in states/steps |
|---|---|---:|---:|
| NoEarlyStore | assertion failed: NoEarlyStore | 5/7 | 5/7 |
| StoredBounds | satisfied | 12/28 | 12/30 |
| Unreviewed source, false property | assertion failed: NoEarlyStore | 5/7 | 5/7 |
| Unreviewed source, healthy property | satisfied | 12/28 | 12/28 |
| Unsupported property arithmetic | assertion failed: NoEarlyStore | 5/7 | 5/7 |
| Terminating negative control | deadlock | 11/13 | 11/13 |
| Failing source assertion | assertion failed | 4/6 | 4/6 |

The source assertion variant replaces the original bound with value == 0, leaving the external healthy bound enabled. It verifies that a source-level assertion violation is still a real first error. All error/deadlock runs have nonempty counterexamples. The terminating fixture removes the pre-existing self-loop solely as a negative control; it does not replace or alter the benchmark source.

The healthy filtered graph passes C0, exact retained action outcomes, finite dependency/observation certificates and the strong sufficient cycle condition against the same-generated control. It has 12 raw states, 11 reviewed projected states, eleven semantically full raw vertices and one partial STARTWORKERS choice. The unreviewed healthy source (comment-only change) has every raw vertex semantically full and covers all projected control states. This is actual production refusal behavior, not a synthetic PO-off substitute.

Default generated programs without the option were byte-identical across every C++/header file to both pre-integration external-property fixtures. A final annotation/exit-status guard was added after the native matrix; regenerating all seven opt-in cases from the final executable yielded byte-identical native programs to those already tested. The final artifact also explicitly rejected missing ARIA, missing property, symmetry and annotated input with exit status 2. Both tested and final executable digests are retained in the result.

Thirteen compiler-AST mutation cases pass against the shared production extractor. A Java API test checks actor/message mapping, disabled/missing-property/truncated-ID refusal, 32 concurrent mixed calls and isolation from caller mutations. The seven existing search, proviso and first-error tests pass. No generic correctness theorem follows from this finite matrix.

No state-count improvement is claimed. Solver transitions include trial/fallback work; 30 versus 28 is not a semantic edge reduction or a speed result. No new performance benchmark was run. The static external-property counterexample and conservative ARIA export remain separately documented.

## Reproduce

```bash
bash tests/check_property_filter_integration.sh
```

The wrapper builds RMC, runs the production metadata API/concurrency check, thirteen compiler-AST cases, fourteen native case/control executions, the healthy finite graph audit, four invalid-input checks and the seven search tests. Fresh output directories retain generated C++, permissions, exports, compile/error logs and native reports. The default byte comparison is additionally performed when pre-integration experiment artifacts exist locally.

Archived observations are in `results/property_filter_integration_linux_20261123.json` and `results/property_filter_production_ast_checks_linux_20261123.json`. These are Linux observations. The source allowlist and supported-property contract remain explicit limitations; broadening them requires additional proof and native validation rather than removing a gate.
