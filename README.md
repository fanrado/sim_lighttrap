# LightTrapSimulation — first layer + PMT (branch `vuv_meas_pmt`)

Geant4 simulation of the LightTrap **first layer** (a p-terphenyl (pTP) WLS film
deposited on a UV-transparent acrylic carrier) read out by a **PMT**, as in the
VUV bench measurement. A 14 mm diameter parallel VUV beam (128 nm by default)
hits the pTP film; the shifted light crosses a LAr gap to a 23 mm photocathode
modelled with a flat quantum efficiency (100 % over 110–500 nm to start with).
Primary photons, WLS emission, first-layer escape counters and PMT hits are
written to ROOT ntuples.

The two-layer design (blue-WLS slab + edge SiPMs + reflector foils) is **not**
part of this branch; it lives in `develop` and is developed independently.

## Installation and Compilation

1. **Set up Geant4 Environment:** source the Geant4 environment script, or point
   CMake at the install (this laptop: Geant4 11.3.2 from spack):

   ```bash
   source /path/to/geant4-install/bin/geant4.sh
   # or, with spack:  export GEANT4_CMAKE_DIR=$(spack location -i geant4)/lib/cmake/Geant4
   ```
2. **Create a Build Directory:**

   ```bash
   mkdir build
   cd build
   ```
3. **Run CMake:**

   ```bash
   cmake ..
   # macOS with miniconda on PATH: force the system compiler
   # cmake -DCMAKE_C_COMPILER=/usr/bin/cc -DCMAKE_CXX_COMPILER=/usr/bin/c++ -DGeant4_DIR=$GEANT4_CMAKE_DIR ..
   ```

   This configures the project, locates all sources under `src/` and headers
   under `include/`, and copies the macros (`mac/`), input data (`input/`) and
   `sim_config.yaml` into the build directory.
4. **Build the Project:**

   ```bash
   make
   ```

   The executable `sim_lighttrap` will be created.

## Geometry

Along `+z` (the PMT front face sits at `z = 0`; the beam travels in `+z`):

```
beam (z = -2 cm) ──► pTP film (2 µm) / UV acrylic (3 mm) ──► [LAr gap, 3 mm] ──► [MgF2 window, optional] ──► photocathode (Ø 23 mm)
                     z = -6.002 .. -3 mm                                        z = 0 .. 0.1 mm
```

| YAML key (`geometry:`)   | Messenger                  | Default | Meaning |
|--------------------------|----------------------------|---------|---------|
| `pTPlayerThickness_mm`   | `/detector/pTPlayerthickness` | 0.002 | pTP WLS film thickness |
| `uvAcrylicThickness_mm`  | `/detector/uvAcrylicThick` | 3.0     | UV-transparent acrylic carrier |
| `LArThickness_mm`        | `/detector/LArthickness`   | 3.0     | LAr gap, first-layer back face → PMT front face |
| `lightTrapSize_cm`       | `/detector/lighttrapsize`  | 15.0    | square first-layer side |
| `pTPsigmaAlpha_rad`      | `/detector/pTPsigmaAlpha`  | 0.0     | pTP surface facet-slope RMS (0 = smooth) |
| `pmtDiameter_mm`         | `/detector/pmtDiameter`    | 23      | photocathode (sensitive) diameter |
| `pmtWindowThickness_mm`  | `/detector/pmtWindowThick` | 0       | MgF2 entrance window; 0 = bare photocathode |
| `pmtQE`                  | `/detector/pmtQE`          | 1.0     | flat quantum efficiency inside the QE band |
| `pmtQEmin_nm`            | `/detector/pmtQEmin`       | 110     | QE band lower edge [nm] |
| `pmtQEmax_nm`            | `/detector/pmtQEmax`       | 500     | QE band upper edge [nm]; QE = 0 outside |

The photocathode is a thin disc whose material matches the volume in front of
it (LAr, or MgF2 behind a window), so it adds no optical boundary: every photon
reaching it is killed and recorded in `PMTPhotons` (pre-QE), and with
probability `pmtQE` inside the band also in `PMTHits` (post-QE). Both trees
carry `eventID, fX, fY, fZ, fT, fwl, fcosTheta, primary`, where `primary = 1`
tags an unshifted beam photon and `0` a pTP-shifted WLS photon. Two
pass-through counters on the first layer (`FirstLayerBackplane` on its back
face, 0.01 mm behind the acrylic so TIR-trapped light is not counted, and
`FirstLayerEdges` on its ±x edges) record where the WLS light leaves layer 1.

## Running the Simulation

- **Interactive Mode (with Visualization):**

  ```bash
  ./sim_lighttrap
  ```

  Launches the Qt UI and executes `vis.mac` (geometry drawn, 14 mm beam
  preloaded; use the Run menu or `/run/beamOn 30` to see trajectories).

- **Batch Mode (macro file):**

  ```bash
  ./sim_lighttrap run.mac                 # 10 000 photons, 128 nm, 14 mm beam
  ./sim_lighttrap run_vuv_spectrum.mac    # same beam with the LAr scintillation spectrum
  ./sim_lighttrap run_285.mac             # measured lamp spectrum (input/spectrum.txt via create_macro.py)
  ```

- **YAML Configuration Mode:**

  Edit `sim_config.yaml` in the build directory, then run:

  ```bash
  ./sim_lighttrap sim_config.yaml           # geometry + source + event count from the YAML
  ./sim_lighttrap sim_config.yaml run.mac   # YAML geometry, macro source/run (macro overrides)
  ```

  | Section    | Parameters |
  |------------|------------|
  | `geometry` | layer thicknesses, first-layer size, pTP roughness, `pmt*` parameters (table above) |
  | `source`   | particle, energy, GPS position type/shape, `radius_cm` (Circle) or half-widths, direction |
  | `run`      | number of events |
  | `materials`| per-material optical properties: `ptp`, `uvAcrylic`, `lar`, `mgf2` |

  Example — thicker gap, 2 mm MgF2 window, 100k events:

  ```yaml
  geometry:
    LArThickness_mm: 10.0
    pmtWindowThickness_mm: 2.0
  run:
    nEvents: 100000
  ```

Output: `output_apexltsim<runID>.root` in the working directory, with trees
`Energy`, `Primary`, `WLSPhoton`, `OpticalValidation`, `FirstLayerBackplane`,
`FirstLayerEdges`, `PMTPhotons`, `PMTHits` (see `docs/analysis.org`). Note that
the sim always writes that fixed name: run verification jobs in a scratch
directory so you do not overwrite a long production run.

## Visualising and validating the geometry

```bash
cd build
./sim_lighttrap                       # interactive Qt viewer (vis.mac)
./sim_lighttrap draw_offscreen.mac    # headless: writes pmt_geom_*.png + prints the volume tree
```

`draw_offscreen.mac` renders the geometry with the TOOLSSG offscreen driver (no
display needed) from behind, from the side, and with 30 beam events, and dumps
the volume tree with ASCIITree. Reference renders are kept in
`docs/figures/pmt_mode/`. Two caveats of this Geant4 build: the `RayTracer`
driver segfaults, and the offscreen z-buffer renderer skips translucent
surfaces and needs `/vis/viewer/set/culling invisible true` (otherwise the
invisible world box is drawn and hides everything); the macro handles both.

A data-side check (beam footprint on the film, hit map on the photocathode, and
the z of every recorded photon point against the layer planes):

```bash
python3.13 analysis/plot_pmt_validation.py build/output_apexltsim0.root pmt_validation.png
```

(reference output: `docs/figures/pmt_mode/pmt_validation_2000evt.png`).

## Analysis

```bash
python3 analysis/analyze_efficiency.py build/output_apexltsim0.root   # efficiency chain (PyROOT)
root -l -b -q 'analysis/Analyze_out.C("build/output_apexltsim0.root")' # per-tree summary PDF
```

`analyze_efficiency.py` prints the chain beam → pTP WLS → escape from layer 1 →
photocathode → photo-electrons, each normalised to the previous stage and to
the number of primaries.

## Running the unit tests

Source-level checks (config parsing, messenger wiring, PMT sensitive detector,
ntuple layout, macros, docs) run with `pytest` and require no build:

```bash
python3.13 -m pytest tests/ -v                          # full suite
python3.13 -m pytest tests/test_pmt_detector_mode.py -v # PMT geometry/readout only
```

Tests of the two-layer design that are still present as untracked files are
excluded from collection in `tests/conftest.py`.

## Visualization

The `vis.mac` macro provides commands for rendering the simulation:

- It opens an OpenGL viewer.
- Sets an initial viewpoint (which can be changed using GUI buttons).
- Draws volumes, trajectories, axes, and displays event IDs.
- Allows you to capture snapshots if needed.

---

# Appendix

## Set up G4 on your local PC (linux/Mac)

Follow: https://www.youtube.com/playlist?list=PLLybgCU6QCGWgzNYOV0SKen9vqg4KXeVL

### Prerequisites (Linux)

* GCC 9 or higher
* X11 and openGL for visualization

### Download the source file

```
https://gitlab.cern.ch/geant4/geant4/-/archive/v11.3.2/geant4-v11.3.2.tar.gz
```

### Building and installing from source

* Unpack the Geant4 source
* configure the build:

  ```
  $ cd /path/to
  $ mkdir geant4-v11.3.0-build
  $ cmake -DCMAKE_INSTALL_PREFIX=/path/to/geant4-v11.3.0-install -DGEANT4_INSTALL_DATA=ON -DGEANT4_USE_OPENGL_X11=ON /path/to/geant4-v11.3.0
  ```
* Build the directory: `$ make -jN`
* Install Geant4 to the directory `path/to/geant4-v11.3.0-install` : `$ make install`

### Post installation:

Run: `$ source path/to/geant4-v11.3.0-install/bin/geant4.sh`

Then try to build and run an example of code.

---

## Usage at PC

```
[everytime]
cd /Users/weishi/Documents/Software/Geant4/geant4-v11.3.0-install/share/Geant4/geant4make
source <local install dir>/geant4make.sh

[work area]
# copy this <simlighttrap> folder to your pc
cd build
cmake .. [every time new .cc files are added]
make     [update changes]

[run]
./sim_lighttrap                        # interactive (vis.mac)
./sim_lighttrap run.mac                # batch via macro
./sim_lighttrap sim_config.yaml        # batch via YAML config
./sim_lighttrap sim_config.yaml run.mac # YAML geometry + macro source/run
./sim_lighttrap det.mac                # scan detector parameters
```

## Set up G4 on dunegpvm (Alma 9)

```
# dunepgvm alma9 binary 11.3.0
# do this everytime
source /exp/dune/app/users/weishi/G4BinaryAlma9/Geant4-11.3.0-Linux/bin/geant4.sh

cd B1
cmake .
make -f Makefile
./exampleB1
/run/beamOn 100

# may need to enable OpenGL (on Mac terminal and reboot)
defaults write org.xquartz.X11 enable_iglx -bool true
```

---
