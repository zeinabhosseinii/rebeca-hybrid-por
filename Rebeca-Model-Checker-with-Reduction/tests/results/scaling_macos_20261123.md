# macOS scaling measurements, 2026-11-23

User-supplied data; 10 measured runs per mode after one warmup. Native timing only.

| Family | Workers | Mode | States | Transitions | Median seconds | Min–max seconds | Peak RSS median MiB |
|---|---:|---|---:|---:|---:|---|---:|
| independent | 4 | full | 993 | 3233 | 0.1414 | 0.1320–0.1496 | 1159.36 |
| independent | 4 | static | 445 | 1353 | 0.1355 | 0.1260–0.1413 | 1165.30 |
| independent | 4 | dynamic | 624 | 2001 | 0.1382 | 0.1309–0.1530 | 1150.32 |
| independent | 6 | full | 27153 | 131569 | 0.3344 | 0.3315–0.3550 | 1162.27 |
| independent | 6 | static | 7525 | 34141 | 0.2446 | 0.2320–0.2644 | 1151.48 |
| independent | 6 | dynamic | 15624 | 75001 | 0.2940 | 0.2769–0.3130 | 1180.30 |
| independent | 8 | full | 715713 | 4606785 | 6.4410 | 6.4163–6.5090 | 905.17 |
| independent | 8 | static | 124765 | 752465 | 1.3193 | 1.3003–1.3561 | 887.27 |
| independent | 8 | dynamic | 390624 | 2500001 | 3.6933 | 3.6642–3.7447 | 898.62 |
| shared | 2 | full | 157 | 277 | 0.0724 | 0.0691–0.0830 | 897.33 |
| shared | 2 | static | 157 | 265 | 0.0708 | 0.0694–0.0840 | 897.33 |
| shared | 2 | dynamic | 117 | 145 | 0.0712 | 0.0695–0.0736 | 897.31 |
| shared | 4 | full | 8305 | 28609 | 0.1738 | 0.1694–0.1812 | 1209.18 |
| shared | 4 | static | 8305 | 25273 | 0.1725 | 0.1699–0.1850 | 1203.50 |
| shared | 4 | dynamic | 3069 | 4609 | 0.1543 | 0.1414–0.1604 | 1208.46 |
| shared | 6 | full | 188641 | 976825 | 1.3252 | 1.2872–1.4175 | 1109.03 |
| shared | 6 | static | 188641 | 815893 | 1.1788 | 1.1321–1.2308 | 1041.10 |
| shared | 6 | dynamic | 22527 | 36865 | 0.2762 | 0.2500–0.2906 | 1055.29 |
