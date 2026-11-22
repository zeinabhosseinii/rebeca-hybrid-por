# macOS four-path scaling, 2026-11-23

User-supplied data, one warmup and ten measured runs per mode. Native time only.

| Family | Workers | Mode | States | Transitions | Median seconds | Min–max seconds | RSS median MiB |
|---|---:|---|---:|---:|---:|---|---:|
| independent | 4 | full | 993 | 3233 | 0.15364 | 0.1490–0.1682 | 748.3 |
| independent | 4 | static | 445 | 1353 | 0.15333 | 0.1428–0.1625 | 742.6 |
| independent | 4 | dynamic | 624 | 2001 | 0.15218 | 0.1445–0.1574 | 754.1 |
| independent | 4 | dynamic_no_por | 624 | 2001 | 0.15245 | 0.1477–0.1688 | 752.4 |
| independent | 6 | full | 27153 | 131569 | 0.37135 | 0.3426–0.4172 | 971.1 |
| independent | 6 | static | 7525 | 34141 | 0.25028 | 0.2452–0.3217 | 974.5 |
| independent | 6 | dynamic | 15624 | 75001 | 0.31761 | 0.2859–0.4377 | 1005.3 |
| independent | 6 | dynamic_no_por | 15624 | 75001 | 0.29902 | 0.2854–0.4286 | 969.3 |
| independent | 8 | full | 715713 | 4606785 | 6.47384 | 6.3916–6.6203 | 1065.1 |
| independent | 8 | static | 124765 | 752465 | 1.30485 | 1.2927–1.3718 | 971.3 |
| independent | 8 | dynamic | 390624 | 2500001 | 3.68793 | 3.6555–3.7464 | 975.7 |
| independent | 8 | dynamic_no_por | 390624 | 2500001 | 3.63839 | 3.6157–3.6786 | 1048.3 |
| shared | 2 | full | 157 | 277 | 0.07399 | 0.0698–0.0841 | 897.3 |
| shared | 2 | static | 157 | 265 | 0.07323 | 0.0707–0.0872 | 897.3 |
| shared | 2 | dynamic | 117 | 145 | 0.07774 | 0.0708–0.0973 | 897.3 |
| shared | 2 | dynamic_no_por | 144 | 253 | 0.07357 | 0.0709–0.1025 | 897.3 |
| shared | 4 | full | 8305 | 28609 | 0.16460 | 0.1595–0.1698 | 993.0 |
| shared | 4 | static | 8305 | 25273 | 0.16248 | 0.1576–0.1783 | 987.4 |
| shared | 4 | dynamic | 3069 | 4609 | 0.14092 | 0.1363–0.1580 | 997.1 |
| shared | 4 | dynamic_no_por | 7200 | 24697 | 0.16076 | 0.1551–0.1750 | 993.1 |
| shared | 6 | full | 188641 | 976825 | 1.32212 | 1.3013–1.3715 | 975.0 |
| shared | 6 | static | 188641 | 815893 | 1.17903 | 1.1664–1.3049 | 970.0 |
| shared | 6 | dynamic | 22527 | 36865 | 0.28799 | 0.2719–0.3210 | 932.3 |
| shared | 6 | dynamic_no_por | 117648 | 605053 | 0.91555 | 0.8904–0.9483 | 979.0 |
