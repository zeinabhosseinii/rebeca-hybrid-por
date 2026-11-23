# Existing Cell register benchmark, Linux 2026-11-23

10 measured runs per mode after one warmup. Native time only; error counts are first-error prefixes.

| Model | Mode | Result | States | Transitions | Median s | Min–max s | Peak RSS median MiB |
|---|---|---|---:|---:|---:|---|---:|
| CellRegisterBounds | full | satisfied | 11 | 25 | 0.1627 | 0.1559–0.9526 | 897.6 |
| CellRegisterBounds | static | satisfied | 9 | 12 | 0.1585 | 0.1474–0.5347 | 897.6 |
| CellRegisterBounds | dynamic | satisfied | 12 | 34 | 0.1655 | 0.1488–0.5242 | 897.6 |
| CellRegisterBounds | dynamic_no_por | satisfied | 12 | 28 | 0.1578 | 0.1512–0.3606 | 897.6 |
| CellRegisterInvalidClient | full | assertion failed | 6 | 9 | 0.1676 | 0.1525–0.5376 | 897.8 |
| CellRegisterInvalidClient | static | assertion failed | 6 | 7 | 0.1594 | 0.1507–0.3692 | 897.8 |
| CellRegisterInvalidClient | dynamic | assertion failed | 6 | 11 | 0.1656 | 0.1521–1.0449 | 897.8 |
| CellRegisterInvalidClient | dynamic_no_por | assertion failed | 6 | 9 | 0.1615 | 0.1513–0.8879 | 897.8 |
