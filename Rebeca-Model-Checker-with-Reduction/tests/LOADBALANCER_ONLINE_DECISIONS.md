# LoadBalancer online selection audit

This audit changes diagnostics only. It does not remove dependencies, change scheduling,
relax the BFS proviso, or alter exceptions/deadlock stopping.

## Reproduce with the complete Java generator

```bash
bash tests/diagnose_loadbalancer.sh
```

The script builds and runs the original four modes, then audits AST and JSON online
traces. `tmp/LoadBalancerSmall_diagnostics/decisions.json` retains candidate order,
actor eligibility, dependency blockers (including their current queue heads),
proviso rejections, accepted trials and full expansions. The Markdown sibling
contains one row per expanded state. Both files are included in the diagnostics ZIP.
The parser rejects missing/incomplete decisions and checks that a satisfied run
has one decision per reached state. It does not compare numeric IDs across runs.

## Locally executed evidence

The table below is a replay of previously generated LoadBalancer C++ with the new
logging inserted, compiled with `g++ -std=c++11 -pthread -O2 -DPOR_DIAGNOSTICS`.
It is not a fresh end-to-end Java generation: the original compiler Maven artifact
is unavailable on this host. Run the command above for that integration check.
The replay remains satisfied, 38 states / 46 transitions, matching its control.

- 26 expansions accepted a reduced actor set; 12 expanded fully.
- Full reasons: dependency only 10; dependency plus proviso 1; proviso only 1.
- Hub is blocked 33 times by Bootstrapper.INITIALIZE while Bootstrapper's queue
  head is zero. The global method check intentionally includes future methods.
  Empty now alone does not justify declaring a method permanently unreachable.
- In state 37, PrimaryRelay is rejected by the closed-successor proviso, then
  PrimarySrc is accepted. States 36 and 38 fall back to full expansion.
- No evidence here justifies deleting proviso or imposing static priorities to
  obtain 22 states. Static priorities select a different set of interleavings.
- Next semantic question: certify that a blocker cannot reappear along paths
  avoiding the candidate (Bootstrapper.Initialize in this model), including
  potential senders and queue changes. Separately, Hub's two distinct handlers
  still require an action-level independence certificate for feedback sends.
  Neither change is implemented by this audit.

# Per-state replay decisions

State IDs are run-local. All events are preserved in JSON.

## load_decisions

| State | Outcome | Accepted actor | Dependency blockers | Closed successors |
|---|---|---|---|---|
| 1 | full |  | Bootstrapper:1 <- Hub:1 (head 0) |  |
| 2 | reduced | PrimarySrc |  |  |
| 3 | reduced | PrimaryRelay |  |  |
| 4 | reduced | SecondarySrc | Hub:2 <- Bootstrapper:1 (head 0) |  |
| 5 | reduced | SecondaryRelay | Hub:2 <- Bootstrapper:1 (head 0) |  |
| 6 | full |  | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 7 | reduced | PrimarySrc | Hub:2 <- Bootstrapper:1 (head 0) |  |
| 8 | reduced | SecondarySrc | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 9 | reduced | PrimaryRelay | Hub:2 <- Bootstrapper:1 (head 0) |  |
| 10 | reduced | SecondaryRelay | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 11 | full |  | Hub:2 <- Bootstrapper:1 (head 0) |  |
| 12 | full |  | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 13 | reduced | SecondarySrc | Hub:2 <- Bootstrapper:1 (head 0) |  |
| 14 | reduced | PrimarySrc | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 15 | reduced | SecondaryRelay | Hub:2 <- Bootstrapper:1 (head 0) |  |
| 16 | reduced | PrimaryRelay | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 17 | full |  | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 18 | reduced | PrimarySrc | Hub:2 <- Bootstrapper:1 (head 0) |  |
| 19 | reduced | SecondarySrc | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 20 | reduced | PrimaryRelay | Hub:2 <- Bootstrapper:1 (head 0) |  |
| 21 | reduced | SecondaryRelay | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 22 | full |  | Hub:2 <- Bootstrapper:1 (head 0) |  |
| 23 | full |  | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 24 | reduced | SecondarySrc | Hub:2 <- Bootstrapper:1 (head 0) |  |
| 25 | reduced | PrimarySrc | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 26 | reduced | SecondaryRelay | Hub:2 <- Bootstrapper:1 (head 0) |  |
| 27 | reduced | PrimaryRelay | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 28 | full |  | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 29 | reduced | PrimarySrc | Hub:2 <- Bootstrapper:1 (head 0) |  |
| 30 | reduced | SecondarySrc | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 31 | reduced | PrimaryRelay | Hub:2 <- Bootstrapper:1 (head 0) |  |
| 32 | reduced | SecondaryRelay | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 33 | full |  | Hub:2 <- Bootstrapper:1 (head 0) |  |
| 34 | full |  | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 35 | reduced | PrimarySrc | Hub:1 <- Bootstrapper:1 (head 0) |  |
| 36 | full |  | Hub:1 <- Bootstrapper:1 (head 0) | PrimaryRelay -> 6 |
| 37 | reduced | PrimarySrc |  | PrimaryRelay -> 7 |
| 38 | full |  |  | PrimaryRelay -> 9 |
