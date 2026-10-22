# LightTrapSimulation — first layer + PMT (branch `vuv_meas_pmt`)

Geant4 simulation of the LightTrap **first layer** (a p-terphenyl (pTP) WLS film
deposited on a UV-transparent acrylic carrier) read out by a **PMT**, as in the
VUV bench transmission measurement in **argon gas**. A 14 mm diameter parallel
VUV beam (128 nm by default) hits the pTP film; the light leaving the back of
the acrylic crosses a 7 mm gap to a Hamamatsu **R6836** modelled as a physical cylinder
(Ø 28.2 mm × 92 mm, MgF2 faceplate, Ø 23 mm photocathode on its inner face,
vacuum interior, opaque glass envelope) with a flat quantum efficiency (100 %
over 110–500 nm to start with). Primary photons, WLS emission, first-layer
escape counters and PMT hits are written to ROOT ntuples.

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

Along `+z` (the PMT faceplate front sits at `z = 0`; the beam travels in `+z`):

```
beam (z = -2 cm) ──► pTP film (2 µm) / UV acrylic (3 mm) ──► [LAr gap, 7 mm] ──► MgF2 faceplate ──► photocathode (Ø 23 mm) ──► vacuum ──► glass end cap
                     z = -10.002 .. -7 mm                                        z = 0 .. 1.5 mm   z = 1.5 .. 1.6 mm                   z = 91 .. 92 mm
```

The PMT follows the Hamamatsu R6836 dimensional outline (datasheet TPMH1264E):
tube and faceplate Ø 28.2 ± 0.8 mm, photocathode Ø 23 mm minimum effective
area, body length 92 ± 2 mm, MgF2 window, Cs-Te photocathode. The faceplate
thickness is **not** on the datasheet; 1.5 mm is an assumption
(`pmtWindowThickness_mm`). The tube side wall and end cap are borosilicate
glass without optical properties, i.e. perfectly absorbing (dynodes and pins
are not modelled). Light entering the faceplate outside the 23 mm photocathode
refracts into the vacuum and is absorbed on the envelope.

| YAML key (`geometry:`)   | Messenger                  | Default | Meaning |
|--------------------------|----------------------------|---------|---------|
| `worldMedium`            | `/detector/worldMedium`    | `gar`   | medium of the beam path, gap and counters: `gar` (argon gas, 1 atm) \| `lar` (liquid argon) \| `vacuum` |
| `withSample`             | `/detector/withSample`     | `true`  | build the pTP-coated acrylic sample (`false` = reference run) |
| `pTPlayerThickness_mm`   | `/detector/pTPlayerthickness` | 0.002 | pTP WLS film thickness |
| `uvAcrylicThickness_mm`  | `/detector/uvAcrylicThick` | 3.0     | UV-transparent acrylic carrier |
| `LArThickness_mm`        | `/detector/LArthickness`   | 7.0     | gap (world medium), back of the acrylic → PMT faceplate |
| `lightTrapSize_cm`       | `/detector/lighttrapsize`  | 15.0    | square first-layer side |
| `pTPsigmaAlpha_rad`      | `/detector/pTPsigmaAlpha`  | 0.0     | pTP surface facet-slope RMS (0 = smooth) |
| `pmtDiameter_mm`         | `/detector/pmtDiameter`    | 23      | photocathode (sensitive) diameter |
| `pmtTubeDiameter_mm`     | `/detector/pmtTubeDiameter`| 28.2    | tube / faceplate outer diameter |
| `pmtLength_mm`           | `/detector/pmtLength`      | 92      | faceplate front → end of the glass body |
| `pmtWindowThickness_mm`  | `/detector/pmtWindowThick` | 1.5     | MgF2 faceplate thickness (assumption); 0 = bare photocathode |
| `pmtWallThickness_mm`    | `/detector/pmtWallThick`   | 1.0     | opaque envelope side wall / end cap |
| `pmtQE`                  | `/detector/pmtQE`          | 1.0     | flat quantum efficiency inside the QE band |
| `pmtQEmin_nm`            | `/detector/pmtQEmin`       | 110     | QE band lower edge [nm] |
| `pmtQEmax_nm`            | `/detector/pmtQEmax`       | 500     | QE band upper edge [nm]; QE = 0 outside |

The photocathode is a thin disc on the inner faceplate surface whose material
matches the faceplate (MgF2; LAr if the faceplate is disabled), so it adds no
optical boundary: every photon
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

- **World medium (`world_medium=gar|lar|vacuum`):**

  ```bash
  ./sim_lighttrap sim_config.yaml world_medium=gar     # argon gas, 1 atm (bench; default)
  ./sim_lighttrap sim_config.yaml world_medium=lar     # liquid argon (Rayleigh scattering, n = 1.45 at 128 nm)
  ./sim_lighttrap run.mac world_medium=vacuum          # n = 1 everywhere outside the solids
  ```

  The beam path, the gap, the reference counters and a bare photocathode are
  all made of the selected medium; the PMT interior is always vacuum. Argon gas
  uses the Bideau-Méhu dispersion (n ≈ 1.00044 at 128 nm) with negligible
  absorption and scattering, so a `with_sample=off` beam goes straight to the
  faceplate; in liquid argon about 2 % of the beam Rayleigh-scatters over the
  2 cm path (0.9 m scattering length), which is what the stray tracks in a
  `lar` run are. Also `geometry.worldMedium` in the YAML and
  `/detector/worldMedium` in a macro.

- **With / without the sample (`with_sample=on|off`):**

  ```bash
  ./sim_lighttrap sim_config.yaml with_sample=on      # pTP-coated acrylic in the beam (default)
  ./sim_lighttrap sim_config.yaml with_sample=off     # bare beam → PMT reference, identical geometry
  ./sim_lighttrap run.mac with_sample=off             # also works macro-only
  ./sim_lighttrap --help
  ```

  `with_sample=off` removes the pTP film and the UV acrylic (and the first-layer
  edge counters) from the geometry — they are not built at all, so they are
  absent from the viewer, the volume tree and the run — and leaves everything
  else untouched: same beam, same 7 mm gap position, same PMT. The `FirstLayerBackplane` counter stays as a reference
  plane at the position of the acrylic back face. The transmission of the
  sample is then `N(PMTHits, on) / N(PMTHits, off)` for the same number of beam
  photons. The switch is also available as `geometry.withSample: true|false` in
  the YAML (the command line wins) and as `/detector/withSample true|false` in
  a macro (followed by `/run/reinitializeGeometry`).

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
  | `materials`| per-material optical properties: `ptp`, `uvAcrylic`, `gar`, `lar`, `mgf2` |

  Example — larger gap, 2 mm faceplate, 100k events:

  ```yaml
  geometry:
    LArThickness_mm: 10.0
    pmtWindowThickness_mm: 2.0
  run:
    nEvents: 100000
  ```

**Transmission spectrum scan.** The bench measurement scans the beam
wavelength; `scripts/scan_wavelength.py` runs the simulation per wavelength
with and without the sample (each run in its own scratch directory, so the
fixed output name is never overwritten), tabulates photocathode hits per beam
photon split into unshifted (transmitted) and pTP-shifted light, and prints the
transmission `T = hits(with sample) / hits(without)`:

```bash
python3.13 scripts/scan_wavelength.py --build build --events 5000 --wl 115 120 128 140 160 200 250 300
python3.13 scripts/scan_wavelength.py --build build --events 5000 --range 110 320 10   # 110..320 nm in 10 nm steps
python3.13 scripts/scan_wavelength.py --build build --events 5000 --wl 128 --sample on  # sample runs only
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
display needed) obliquely, from the PMT side, from the side (whole tube and a
close-up of the 7 mm gap), and with 30 beam events, and dumps
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
