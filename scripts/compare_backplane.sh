#!/usr/bin/env bash
#
# compare_backplane.sh — run the LightTrap simulation with each backplane
# reflector option (vikuiti | ptfe | none) and print the efficiency chain for
# each, so the effect of the reflector on SiPM light collection can be compared.
#
# For each mode it:
#   1. derives a config from sim_config.yaml, overriding geometry.backplaneFoil,
#   2. runs ./sim_lighttrap on it (output goes to build/output_apexltsim0.root),
#   3. renames the output to build/out_<foil>.root,
#   4. runs analysis/analyze_efficiency.py on it.
#
# Usage:
#   scripts/compare_backplane.sh [nEvents] [foil ...]
#
#   nEvents   optional; override run.nEvents for all modes (e.g. 100000).
#             Omit (or pass "-") to use whatever sim_config.yaml specifies.
#   foil ...  optional; subset of {vikuiti ptfe none} (default: all three).
#
# Examples:
#   scripts/compare_backplane.sh                 # all three, YAML's nEvents
#   scripts/compare_backplane.sh 100000          # all three, 100k events each
#   scripts/compare_backplane.sh - vikuiti none  # just these two, YAML's nEvents
#
# Requires: a built build/sim_lighttrap and python3.13 (for the analyzer).

set -euo pipefail

# Resolve repo root from this script's location, so it runs from anywhere.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD="$REPO/build"
BASE_CFG="$REPO/sim_config.yaml"
BIN="$BUILD/sim_lighttrap"
ANALYZER="$REPO/analysis/analyze_efficiency.py"
PYTHON="${PYTHON:-python3.13}"

# ── Arguments ────────────────────────────────────────────────────────────────
NEVENTS="${1:--}"                      # "-" or empty => keep YAML value
shift || true
FOILS=("$@")
[ ${#FOILS[@]} -eq 0 ] && FOILS=(vikuiti ptfe none)

# ── Sanity checks ────────────────────────────────────────────────────────────
[ -x "$BIN" ]       || { echo "error: $BIN not found or not executable — build it first." >&2; exit 1; }
[ -f "$BASE_CFG" ]  || { echo "error: base config $BASE_CFG not found." >&2; exit 1; }

echo "Repo:     $REPO"
echo "Binary:   $BIN"
echo "Events:   ${NEVENTS/-/(from YAML)}"
echo "Modes:    ${FOILS[*]}"
echo

# ── Run each mode ────────────────────────────────────────────────────────────
for foil in "${FOILS[@]}"; do
  case "$foil" in
    vikuiti|ptfe|none) ;;
    *) echo "error: unknown foil '$foil' (want vikuiti|ptfe|none)" >&2; exit 1 ;;
  esac

  cfg="$BUILD/cfg_$foil.yaml"
  # Override the backplaneFoil line; optionally override nEvents too.
  sed "s/^  backplaneFoil: .*/  backplaneFoil: $foil/" "$BASE_CFG" > "$cfg"
  if [ "$NEVENTS" != "-" ] && [ -n "$NEVENTS" ]; then
    sed -i.bak "s/^  nEvents: .*/  nEvents: $NEVENTS/" "$cfg" && rm -f "$cfg.bak"
  fi

  echo "===== running backplane = $foil ====="
  # Run from build/ so output_apexltsim0.root lands there.
  ( cd "$BUILD" && "$BIN" "$cfg" >/dev/null )
  mv "$BUILD/output_apexltsim0.root" "$BUILD/out_$foil.root"
  echo "  -> build/out_$foil.root"
  echo
done

# ── Compare ──────────────────────────────────────────────────────────────────
for foil in "${FOILS[@]}"; do
  echo "===== efficiency: backplane = $foil ====="
  "$PYTHON" "$ANALYZER" "$BUILD/out_$foil.root"
  echo
done
