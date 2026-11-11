#!/usr/bin/env bash
# tools/check.sh -- the six quality gates of scanbench, as numbered stages.
#
# Usage: tools/check.sh [--fast] [--full] [--json FILE] [--only GATE]
#   --fast       skip gate 5 (tests) while editing
#   --full       print the complete tool output of every gate inline
#   --json FILE  write a machine-readable summary (used by CI and scripts)
#   --only GATE  run one gate: privacy|format|lint|types|security|tests
#
# The same script runs locally, in the pre-push hook and in CI. It stops at
# the first failing gate. The full output of every gate is kept in
# .gates/<timestamp>/<n>-<gate>.log for drill-down.
# Privilege level: normal user; writes only below the repository directory.
set -euo pipefail

cd "$(dirname "$0")/.."

GATES=(privacy format lint types security tests)
declare -A CMD=(
  [privacy]="python3 tools/privacy_scan.py"
  [format]="pycodestyle --max-line-length=100 src tests tools"
  [lint]="pylint src tests tools"
  [types]="mypy"
  [security]="bandit -q -c pyproject.toml -r src"
  [tests]="python3 -m pytest -q -p no:cacheprovider --cov=scanbench --cov-report=term"
)
declare -A TOOL=(
  [privacy]="privacy_scan.py" [format]="pycodestyle, 100 columns"
  [lint]="pylint + docparams + mccabe" [types]="mypy --strict"
  [security]="bandit" [tests]="pytest, branch coverage >= 90 %"
)

FAST=0; FULL=0; JSON=""; ONLY=""
while (($#)); do
  case "$1" in
    --fast) FAST=1 ;;
    --full) FULL=1 ;;
    --json) JSON="${2:?--json needs a file}"; shift ;;
    --only) ONLY="${2:?--only needs a gate}"; shift ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done
if [[ -n "$ONLY" && -z "${CMD[$ONLY]:-}" ]]; then
  echo "unknown gate: $ONLY (${GATES[*]})" >&2; exit 2
fi

# Colours only on a terminal; CI logs and files stay plain.
if [[ -t 1 ]]; then G=$'\e[32m'; R=$'\e[31m'; Y=$'\e[33m'; N=$'\e[0m'; else G=""; R=""; Y=""; N=""; fi
LOGDIR=".gates/$(date +%Y-%m-%d_%H-%M-%S)"
mkdir -p "$LOGDIR"
RESULTS=()   # "n gate status seconds" per stage, for the JSON summary

rule() { printf '%s\n' "==== $1 $(printf '=%.0s' $(seq 1 $((72 - ${#1}))))"; }

# Print a short summary of a failed gate instead of the full output.
summarize() {
  local gate=$1 log=$2
  case "$gate" in
    lint)  grep -E 'rated at' "$log" | sed 's/^/       /' || true
           grep -E '^[^ ]+:[0-9]+:[0-9]+: ' "$log" | head -n 10 | sed 's/^/       /' ;;
    tests) grep -E '^(FAILED|ERROR)|TOTAL|Required test coverage|FAIL Required' "$log" \
             | head -n 12 | sed 's/^/       /' || true ;;
    *)     grep -v '^\s*$' "$log" | head -n 10 | sed 's/^/       /' ;;
  esac
  printf '       %d lines in total; full output: %s\n' "$(wc -l < "$log")" "$log"
}

run_stage() {
  local n=$1 gate=$2 log="$LOGDIR/$1-$2.log" start end secs status
  start=$EPOCHREALTIME
  [[ -n "${GITHUB_ACTIONS:-}" ]] && echo "::group::[$n] $gate -- full output"
  if ${CMD[$gate]} > "$log" 2>&1; then status=PASS; else status=FAIL; fi
  [[ -n "${GITHUB_ACTIONS:-}" ]] && { cat "$log"; echo "::endgroup::"; }
  end=$EPOCHREALTIME
  secs=$(awk -v a="$start" -v b="$end" 'BEGIN { printf "%.1f", b - a }')
  local colour=$G; [[ $status == FAIL ]] && colour=$R
  printf -- '-- [%d] %-9s %-32s %s%s%s %6s s\n' "$n" "$gate" "${TOOL[$gate]}" \
    "$colour" "$status" "$N" "$secs"
  ((FULL)) && sed 's/^/       /' "$log"
  [[ $status == FAIL && $FULL -eq 0 ]] && summarize "$gate" "$log"
  RESULTS+=("$n $gate $status $secs")
  [[ $status == PASS ]]
}

write_json() {
  [[ -z "$JSON" ]] && return 0
  {
    printf '{"logdir": "%s", "stages": [' "$LOGDIR"
    local sep="" n gate status secs
    for r in "${RESULTS[@]}"; do
      read -r n gate status secs <<< "$r"
      printf '%s{"n": %d, "gate": "%s", "status": "%s", "seconds": %s}' \
        "$sep" "$n" "$gate" "$status" "$secs"
      sep=", "
    done
    printf ']}\n'
  } > "$JSON"
}

T0=$EPOCHREALTIME
rule "scanbench quality gates  $(date '+%Y-%m-%d %H:%M:%S')"
failed=""
for n in "${!GATES[@]}"; do
  gate=${GATES[$n]}
  if [[ -n "$ONLY" && "$gate" != "$ONLY" ]]; then continue; fi
  if [[ -n "$failed" ]]; then
    printf -- '-- [%d] %-9s %s\n' "$n" "$gate" "${Y}skipped${N} (stopped at first failure)"
    continue
  fi
  if [[ $gate == tests && $FAST -eq 1 ]]; then
    printf -- '-- [%d] %-9s %s\n' "$n" "$gate" "${Y}skipped${N} (--fast)"
    continue
  fi
  run_stage "$n" "$gate" || failed="[$n] $gate"
done
write_json
TOTAL=$(awk -v a="$T0" -v b="$EPOCHREALTIME" 'BEGIN { printf "%.1f", b - a }')
if [[ -n "$failed" ]]; then
  rule "RESULT: ${R}FAIL${N} at $failed, ${#RESULTS[@]} stage(s) run, $TOTAL s"
  exit 1
fi
rule "RESULT: ${G}PASS${N}, ${#RESULTS[@]} stage(s) run, $TOTAL s"
