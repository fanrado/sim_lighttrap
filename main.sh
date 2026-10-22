#!/usr/bin/env bash
# =============================================================================
# main.sh — run the LightTrap first-layer + PMT simulation with fixed settings.
#
#   ./main.sh            (from the repository root; needs a built build/sim_lighttrap)
#
# Edit the variables below, nothing else. Every run ends with a summary block
# (beam photons, WLS photons born in pTP, photons on the PMT, PMT hits).
# =============================================================================

# ---- Settings ---------------------------------------------------------------

# Sample in the beam?  on  = pTP-coated acrylic in place (measurement run)
#                      off = same geometry without the sample (reference run, I0)
WITH_SAMPLE=on

# Medium filling the beam path and the 7 mm gap:  gar = argon gas (bench, default)
#                                                 lar = liquid argon,  vacuum = n = 1
WORLD_MEDIUM=gar

# Rough pTP film?  off = flat film (physics runs; roughness = pTPsigmaAlpha in the YAML)
#                  on  = bumpy demonstrator film from mac/roughness_knobs.mac
#                        (only used by draw_offscreen.mac and vis_roughness.mac)
ROUGH=off

# Geant4 macro (in mac/, copied to build/ by cmake):
#   run.mac              10 000 photons, 128 nm, 14 mm beam          (batch)
#   run_vuv_spectrum.mac same beam with the LAr scintillation spectrum (batch)
#   run_285.mac          measured lamp spectrum from input/spectrum.txt (batch)
#   draw_offscreen.mac   headless PNG renders + volume tree          (batch)
#   vis.mac              interactive Qt viewer      vis_roughness.mac  viewer with the bumpy film
MACRO=run.mac

# YAML configuration (geometry, materials, PMT, source) applied before the macro;
# leave empty ("") to use the C++ defaults. Path relative to build/ or absolute.
YAML=sim_config.yaml

# PMT quantum efficiency table "<wavelength_nm> <QE>"; leave empty ("") for the
# flat ideal QE of the YAML (pmtQE / pmtQEmin_nm / pmtQEmax_nm).
#   e.g. PMT_QE=pmt_qe_r6836_example.dat   (illustrative R6836 curve, in build/)
PMT_QE=

# Name of the ROOT output after the run (the simulation itself always writes
# output_apexltsim0.root into build/; it is renamed to this so runs do not
# overwrite each other). Leave empty ("") to keep output_apexltsim0.root.
OUTPUT=output_${WITH_SAMPLE}_${WORLD_MEDIUM}.root

# Build directory containing sim_lighttrap and the copied macros / data files.
BUILD_DIR=build

# ---- Run (no need to edit below) --------------------------------------------
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/$BUILD_DIR"
[ -x ./sim_lighttrap ] || { echo "error: ./sim_lighttrap not found in $PWD — build the project first" >&2; exit 1; }

ARGS=()
[ -n "$YAML" ]   && ARGS+=("$YAML")
ARGS+=("$MACRO" "with_sample=$WITH_SAMPLE" "world_medium=$WORLD_MEDIUM" "rough=$ROUGH")
[ -n "$PMT_QE" ] && ARGS+=("pmt_qe=$PMT_QE")

echo "# $(date '+%F %T')  ./sim_lighttrap ${ARGS[*]}"
./sim_lighttrap "${ARGS[@]}"

if [ -n "$OUTPUT" ] && [ -f output_apexltsim0.root ] && [ "$OUTPUT" != output_apexltsim0.root ]; then
  mv -f output_apexltsim0.root "$OUTPUT"
  echo "# output: $PWD/$OUTPUT"
fi
