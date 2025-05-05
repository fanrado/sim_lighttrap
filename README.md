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

You can run the simulation in interactive or batch mode:

- **Interactive Mode (with Visualization):**

  ```bash
  ./sim_lighttrap
  ```

  This will launch the UI session and automatically execute the `vis.mac` macro.
- **Batch Mode:**

  ```bash
  ./sim_lighttrap run.mac
  ```

  You can also override the run setup by providing other macro files (e.g., `det.mac` or `scandet.mac`).

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
./simlighttrap
./simlighttrap run.mac # override run setup
./simlighttrap det.mac # scan det parameters
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
