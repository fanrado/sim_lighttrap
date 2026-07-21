# LightTrapSimulation

LightTrapSimulation is a Geant4-based simulation project designed to model an optical light trap. The simulation includes wavelength-shifting processes in a pTP (p-terphenyl) material and tracks the emission of optical photons that interact with detector elements (e.g., SiPMs). Data such as primary particle information, remitted optical photon angles, and material properties are recorded in ROOT ntuples for analysis.

## Installation and Compilation

1. **Set up Geant4 Environment:**Source the Geant4 environment script (this might vary by installation):

   ```bash
   source /path/to/geant4-install/bin/geant4.sh
   ```
2. **Create a Build Directory:**

   ```bash
   mkdir build
   cd build
   ```
3. **Run CMake:**

   ```bash
   cmake ..
   ```

   This command configures the project and locates all source files under `src/`, headers under `include/`, and copies macro files from `mac/` to the build directory.
4. **Build the Project:**

   ```bash
   make
   ```

   The executable `sim_lighttrap` will be created.

## Running the Simulation

You can run the simulation in three modes:

- **Interactive Mode (with Visualization):**

  ```bash
  ./sim_lighttrap
  ```

  Launches the Qt UI and executes `vis.mac` automatically.

- **Batch Mode (macro file):**

  ```bash
  ./sim_lighttrap run.mac
  ```

  You can also use other macro files (e.g., `det.mac`, `scandet.mac`).

- **YAML Configuration Mode:**

  Edit `sim_config.yaml` in the build directory, then run:

  ```bash
  # YAML-only: geometry + source + event count all from the YAML file
  ./sim_lighttrap sim_config.yaml

  # YAML geometry + macro source/run: macro settings override the YAML ones
  ./sim_lighttrap sim_config.yaml run.mac
  ```

  The YAML file covers all tunable parameters:

  | Section    | Parameters |
  |------------|------------|
  | `geometry` | `nSiPMs`, layer thicknesses, module size, `backplaneFoil` (`vikuiti` \| `ptfe` \| `none`) |
  | `source`   | particle type, energy, position, shape, direction |
  | `run`      | number of events |
  | `materials`| per-material optical properties, incl. `vikuiti.reflectivity` and `ptfe.reflectivity` |

  Example — scan with 20 SiPMs and a smaller module:

  ```yaml
  geometry:
    nSiPMs: 20
    lightTrapSize_cm: 10.0
  run:
    nEvents: 50000
  ```

  The YAML config is applied first; any macro file provided afterward can still override individual settings via the usual `/detector/` and `/gps/` messenger commands.

## Comparing backplane reflectors (Vikuiti / PTFE / none)

The reflector foil on the back (`+z`) face of the blue WLS slab is selectable at
run time, so you can measure its effect on SiPM light collection:

| Value     | Foil                | Optical behaviour                     |
|-----------|---------------------|---------------------------------------|
| `vikuiti` | 3M ESR (default)    | specular reflector (~98 %)            |
| `ptfe`    | sintered PTFE       | diffuse / Lambertian reflector (~95 %)|
| `none`    | *(no foil)*         | bare face — no reflector (baseline)   |

Select it either in YAML (`geometry.backplaneFoil:`) or from a macro
(`/detector/backplaneFoil <value>` before `/run/beamOn`).

**Run the three-way comparison** with the helper script. It derives a config per
mode from `sim_config.yaml`, runs each (renaming `output_apexltsim0.root` →
`build/out_<foil>.root`), then prints the efficiency chain for each:

```bash
scripts/compare_backplane.sh                 # all three, nEvents from the YAML
scripts/compare_backplane.sh 100000          # all three, 100k events each
scripts/compare_backplane.sh - vikuiti none  # only these modes, YAML's nEvents
```

(Requires a built `build/sim_lighttrap`. Run it from the repo root; it resolves
paths relative to its own location, so it also works from anywhere.)

What to look at across the three runs:

- **Collection / detection efficiency** (`SiPMHits`, ntuple 1) — typically
  `vikuiti ≥ ptfe > none`. The `vikuiti`-vs-`ptfe` gap is the specular-vs-diffuse
  effect; `none` is the no-reflector baseline.
- **Back-face escape** (`SecondLayerBackplane`, ntuple 6) — typically
  `none ≫ ptfe ≳ vikuiti`.

For tighter statistics, raise `run.nEvents` in the YAML (the default is small for
a quick relative comparison).

## Running the unit tests

Source-level checks (config parsing, the `/detector/backplaneFoil` messenger, the
PTFE surface definition, the `none`-skips-foil logic, etc.) run with `pytest` and
require no build or simulation:

```bash
python3.13 -m pytest tests/ -v                            # full suite
python3.13 -m pytest tests/test_backplane_foil_config.py -v  # backplane feature only
```

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
