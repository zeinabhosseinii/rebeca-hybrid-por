#!/usr/bin/env bash
# Runs every model twice (original Aria vs. pruned) and compares the Aria output.
# Usage: ./compare.sh            (all .rebeca files in benchmarks/ and all benchmarks in benchmarks.json)
#        ./compare.sh case3      (only models whose name contains "case3")
cd "$(dirname "$0")" || exit 1
mkdir -p compare_out
FILTER="${1:-}"

printf "%-30s %6s %7s   %s\n" MODEL BASE PRUNED STATUS
printf "%-30s %6s %7s   %s\n" ------------------------------ ------ ------- ------

# $1 = model name (as Main names the output folder), remaining args = arguments for run.sh
run_one() {
  name="$1"; shift
  case "$name" in *"$FILTER"*) ;; *) return ;; esac

  ARIA_PRUNE=0 ./run.sh "$@" > "compare_out/$name.base.txt"   2>&1
  ARIA_PRUNE=1 ./run.sh "$@" > "compare_out/$name.pruned.txt" 2>&1

  b=$(grep -o 'RIG: [0-9]* dependency edges' "compare_out/$name.base.txt"   | grep -o '[0-9]*' | head -1)
  p=$(grep -o 'RIG: [0-9]* dependency edges' "compare_out/$name.pruned.txt" | grep -o '[0-9]*' | head -1)

  if [ -z "$b" ] || [ -z "$p" ]; then
    printf "%-30s %6s %7s   %s\n" "$name" "${b:--}" "${p:--}" "ERROR (see compare_out/$name.*.txt)"
    return
  fi

  if [ "$p" -gt "$b" ]; then
    status="BUG: pruning ADDED edges"
  elif [ "$p" -lt "$b" ]; then
    status="reduced by $((b - p))"
  elif diff -q "output/$name/${name}_annotated.rebeca" "output/${name}_pruned/${name}_annotated.rebeca" >/dev/null 2>&1; then
    status="identical"
  else
    status="same edges, annotated model differs (check)"
  fi
  printf "%-30s %6s %7s   %s\n" "$name" "$b" "$p" "$status"
}

# 1) stand-alone model files
for f in benchmarks/*.rebeca; do
  [ -e "$f" ] || continue
  run_one "$(basename "$f" .rebeca)" file "$f"
done

# 2) benchmarks listed in benchmarks.json (names taken from the 'list' command)
for n in $(./run.sh list 2>/dev/null | awk '/^ *\[[0-9]+\]/ {print $2}'); do
  run_one "$n" run "$n"
done