# Three-path model measurements

Counts on error runs describe exploration before the first error, not full spaces.
Wall time includes native startup; peak RSS is process memory, solver bytes are an internal estimate.
Tiny models and three repetitions do not support a general performance ranking.

| Model | Mode | Result | States | Transitions | Complete | Wall median (s) | Peak RSS median (KiB) |
|---|---|---|---:|---:|---|---:|---:|
| LoadBalancerSmall | full | satisfied | 101 | 202 | True | 0.4099 | 1705748 |
| LoadBalancerSmall | static | satisfied | 22 | 26 | True | 0.2841 | 1705748 |
| LoadBalancerSmall | dynamic | satisfied | 27 | 31 | True | 0.3600 | 1705748 |
| QuiescenceResend | full | satisfied | 1041 | 4062 | True | 0.4446 | 1706004 |
| QuiescenceResend | static | satisfied | 22 | 26 | True | 0.2968 | 1705748 |
| QuiescenceResend | dynamic | satisfied | 201 | 328 | True | 0.3212 | 1705748 |
| QuiescenceFuturePending | full | satisfied | 19 | 20 | True | 0.2990 | 1705748 |
| QuiescenceFuturePending | static | satisfied | 19 | 20 | True | 0.4546 | 1705748 |
| QuiescenceFuturePending | dynamic | satisfied | 18 | 19 | True | 0.3997 | 1705748 |
| QuiescenceTerminates | full | deadlock | 38 | 61 | False | 0.2918 | 1705876 |
| QuiescenceTerminates | static | deadlock | 14 | 15 | False | 0.3352 | 1705876 |
| QuiescenceTerminates | dynamic | deadlock | 14 | 14 | False | 0.4757 | 1705876 |
| QuiescenceAssertion | full | assertion failed | 13 | 16 | False | 0.3264 | 1705876 |
| QuiescenceAssertion | static | assertion failed | 6 | 6 | False | 0.2901 | 1705876 |
| QuiescenceAssertion | dynamic | assertion failed | 6 | 6 | False | 0.3042 | 1705876 |
| PassiveSendIndependent | full | deadlock | 9 | 11 | False | 0.1234 | 657168 |
| PassiveSendIndependent | static | deadlock | 5 | 5 | False | 0.1291 | 657168 |
| PassiveSendIndependent | dynamic | deadlock | 5 | 5 | False | 0.1137 | 657168 |
