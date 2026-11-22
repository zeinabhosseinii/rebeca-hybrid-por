#!/usr/bin/env bash
set -euo pipefail
rmc_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$rmc_root"
base_path="${1:-$rmc_root/tmp}"
python3 - "$base_path" <<'PY'
from pathlib import Path
import re,shutil,sys
base=Path(sys.argv[1]).resolve();src=base/'LoadBalancerSmall_aria_json';dst=base/'LoadBalancerSmall_reference_full'
if not src.is_dir():raise SystemExit('First generate LoadBalancerSmall_aria_json with compare_loadbalancer.sh')
dst.mkdir(parents=True,exist_ok=True)
for file in src.iterdir():
    if file.suffix in ('.cpp','.h'):shutil.copyfile(file,dst/file.name)
p=dst/'Config.h'
text,count=re.subn(r'^\s*#\s*define\s+PO\s*$','// Full reference: actor POR disabled; sender normalization retained',p.read_text(),flags=re.M)
if count!=1:raise SystemExit('Expected exactly one PO definition in copied generated configuration')
p.write_text(text)
PY
(
  cd "$base_path/LoadBalancerSmall_reference_full"
  g++ -std=c++11 -pthread -O2 -DEXPORT_STATE_SPACE *.cpp -o execute 2>compile.log
  ./execute > report.xml 2>errors.log
)
python3 tests/action_por_reference.py \
  --statespace "$base_path/LoadBalancerSmall_reference_full/statespace.xml" \
  --report "$base_path/LoadBalancerSmall_reference_full/report.xml" \
  --output "$base_path/LoadBalancerSmall_action_reference.json"
