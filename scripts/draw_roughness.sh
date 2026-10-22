#!/usr/bin/env bash
#
# draw_roughness.sh — headless side-view panels showing the effect of the pTP
# surface roughness (sigmaAlpha) on a 400 nm beam crossing the sample.
#
#   scripts/draw_roughness.sh [sigmaAlpha_rad ...]      (default: 0.0 0.3 0.8)
#
# Each value runs the simulation once (in its own scratch directory, so the
# fixed output_apexltsim0.root is never overwritten) with
# mac/draw_roughness_panel.mac and writes rough_sa<value>.png into ./roughness/.
# Requires a built build/sim_lighttrap.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
BIN="$REPO/build/sim_lighttrap"
[ -x "$BIN" ] || { echo "error: $BIN not found; build the project first" >&2; exit 1; }
OUT="$PWD/roughness"; mkdir -p "$OUT"
VALUES=("$@"); [ ${#VALUES[@]} -gt 0 ] || VALUES=(0.0 0.3 0.8)
for sa in "${VALUES[@]}"; do
  RUN="$(mktemp -d "${TMPDIR:-/tmp}/lt_rough_XXXXXX")"
  cp -f "$REPO/mac/draw_roughness_panel.mac" "$RUN/"
  [ -f "$REPO/build/ptp_emission.dat" ] && cp -f "$REPO/build/ptp_emission.dat" "$RUN/"
  printf '/control/alias sa %s\n/control/alias out %s/rough_sa%s.png\n/control/execute draw_roughness_panel.mac\n' \
         "$sa" "$OUT" "$sa" > "$RUN/panel.mac"
  ( cd "$RUN" && "$BIN" panel.mac > run.log 2>&1 ) || { echo "sigmaAlpha=$sa: run failed, see $RUN/run.log" >&2; continue; }
  echo "sigmaAlpha=$sa rad -> $OUT/rough_sa$sa.png"
  rm -rf "$RUN"
done
