# LightTrapSimulation — first layer + PMT (branch `vuv_meas_pmt`)

Geant4 simulation of the LightTrap **first layer** — a p-terphenyl (pTP)
wavelength-shifting film on a UV-transparent acrylic carrier — read out by a
Hamamatsu **R6836** PMT across a 7 mm gap, as in the VUV bench transmission
measurement in argon gas. A VUV beam hits the film; the shifted light that
leaves the back of the acrylic and reaches the photocathode is recorded, with
the primaries, the WLS emission and the first-layer escape counters, in ROOT
ntuples. Every run ends with a summary block giving the chain
beam → WLS → layer-1 exit → photocathode → PMT hits.

The two-layer design (blue-WLS slab + edge SiPMs + reflector foils) lives in
`develop` and is not part of this branch.

## Build

Geant4 11.x (this laptop: 11.3.2 from spack), CMake ≥ 3.5, a C++17 compiler;
yaml-cpp is fetched if absent.

```bash
source /path/to/geant4-install/bin/geant4.sh      # or pass -DGeant4_DIR=... to cmake
mkdir build && cd build
cmake ..      # macOS with miniconda on PATH: add -DCMAKE_C_COMPILER=/usr/bin/cc -DCMAKE_CXX_COMPILER=/usr/bin/c++
make -j8
```

CMake copies the macros (`mac/`), the input data (`input/`), `sim_config.yaml`
and `main.sh` into `build/`.

## Run

```bash
cd build
./main.sh                                        # fixed settings at the top of the script: sample on/off, medium, rough film, macro, YAML
./sim_lighttrap                                  # interactive Qt viewer (vis.mac)
./sim_lighttrap sim_config.yaml                  # batch: geometry, source and event count from the YAML
./sim_lighttrap sim_config.yaml run.mac          # YAML geometry, macro source/run
./sim_lighttrap sim_config.yaml with_sample=off  # bare beam → PMT reference run (transmission denominator)
./sim_lighttrap --help
```

Output: `output_apexltsim<runID>.root` in the working directory. The name is
fixed, so run checks in a scratch directory. The film optics (scattering
length, anisotropy, quantum yield, surface model) and the Gaussian beam are
set in `sim_config.yaml` under `materials.ptp`, `geometry` and `source`; the
run summary prints the values in effect.

## Tests

```bash
python3.13 -m pytest tests/ -v     # source-level checks (config, messengers, detectors, macros, docs); no build needed
```

## Documentation

| File | Content |
|---|---|
| `docs/overview.org` | purpose, repository layout, simulation flow |
| `docs/geometry.org` | geometry and materials; every YAML key and `/detector/` command |
| `docs/physics.org` | physics list, pTP film optics (scattering, quantum yield, surface model), beam, tracking, sensitive detectors |
| `docs/running.org` | every run mode and switch, YAML configuration, rough film, end-of-run summary, transmission measurement, visualisation, analysis commands |
| `docs/analysis.org` | ROOT ntuple reference, analysis quantities, input data |
| `docs/geant4_setup.org` | installing Geant4 on a PC or on dunegpvm |

Reference renders are in `docs/figures/pmt_mode/`. The companion Python
package `wlseff_meas_setup_MC` (its `docs/GEANT4_COMPARISON.md`) compares
this simulation thickness by thickness with its own model of the same bench.
