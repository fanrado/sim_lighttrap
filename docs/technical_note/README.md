# Technical note — validation of `sim_lighttrap`

`lighttrap_validation_note.tex` is an internal record of a code-level and
run-level validation of the package at commit `389e967` (branch `develop`).
It is **not** intended for publication.

## Building the PDF

The note uses the JINST template. `jinstpub.sty` is **not** in the repository and
was **not** available on the validation host — the note has therefore **not been
compiled or proof-read in rendered form**. Get the style file first:

```bash
cd docs/technical_note
curl -O https://jinst.sissa.it/jinst/help/JINST_TeXclass/jinstpub.sty
```

(or download the full author package from
<https://jinst.sissa.it/jinst/help/JINST_TeXclass.jsp>)

Then:

```bash
pdflatex lighttrap_validation_note
pdflatex lighttrap_validation_note      # twice, for cross-references
```

Required packages beyond the JINST template: `booktabs`, `amsmath`, `siunitx`,
`xcolor`, `listings` — all in a standard TeX Live installation.

## Reproducing the numbers in the note

Every figure in the note comes from the commands below. Run them from a scratch
directory, **never from `build/`** — the simulation writes a fixed filename
(`output_apexltsim0.root`) into the current working directory and will silently
overwrite an existing production file.

### 0. Environment

```bash
G4=$(spack location -i geant4)          # 11.3.2 on the validation host
SCRATCH=$(mktemp -d)
```

### 1. Clean build

The system compiler must be selected explicitly: a Miniconda `clang++` earlier on
`PATH` fails CMake's compiler check with
`ld: -lto_library library filename must be 'libLTO.dylib'`.

```bash
mkdir -p $SCRATCH/build && cd $SCRATCH/build
cmake -DCMAKE_C_COMPILER=/usr/bin/cc \
      -DCMAKE_CXX_COMPILER=/usr/bin/c++ \
      -DGeant4_DIR=$G4/lib/cmake/Geant4 \
      /path/to/sim_lighttrap
make -j8
```

Expected: exit 0, no warnings, no errors.

### 2. Unit tests

```bash
cd /path/to/sim_lighttrap
python3.13 -m pytest tests/ -q
```

Expected: `319 passed, 6 skipped`.

### 3. The three backplane configurations (table 4 of the note)

```bash
for foil in vikuiti ptfe none; do
  mkdir -p $SCRATCH/run_$foil && cd $SCRATCH/run_$foil
  cp $SCRATCH/build/*.dat .
  sed -e 's/nEvents: 10000/nEvents: 20000/' \
      -e "s/backplaneFoil: vikuiti/backplaneFoil: $foil/" \
      $SCRATCH/build/sim_config.yaml > sim_config.yaml
  $SCRATCH/build/sim_lighttrap sim_config.yaml > run.log 2>&1
  python3.13 /path/to/sim_lighttrap/analysis/analyze_efficiency.py \
      output_apexltsim0.root
done
```

Expected p.e./primary: `vikuiti` 3.08 %, `ptfe` 3.01 %, `none` 10.23 %.

### 4. Diagnostic — lossless mirror (finding F1, experiment i)

Vikuiti reflectivity raised to 1.0 at every grid point:

```bash
sed -e 's/nEvents: 10000/nEvents: 20000/' -e 's/0\.98/1.0/g' \
    $SCRATCH/build/sim_config.yaml > sim_config.yaml
```

Expected `SiPMHits`: 636 — i.e. unchanged from 616 at R = 0.98, so foil
absorption is not the loss channel.

### 5. Diagnostic — front-face leakage (finding F1, experiment ii; table 5)

```bash
root -l -b -q -e 'TFile f("output_apexltsim0.root");
  TTree*t=(TTree*)f.Get("FirstLayerBackplane");
  printf("fwd UV    %lld\n", t->GetEntries("forward==1 && fwl<400"));
  printf("fwd blue  %lld\n", t->GetEntries("forward==1 && fwl>400"));
  printf("back UV   %lld\n", t->GetEntries("forward==0 && fwl<400"));
  printf("back blue %lld\n", t->GetEntries("forward==0 && fwl>400"));'
```

Expected "back blue": `vikuiti` 8805, `ptfe` 8414, `none` 2521.

### 6. Diagnostic — PTFE is not diffuse (finding F2, table 6)

Run `ptfe` with its reflectivity raised from 0.95 to 0.98 so its only remaining
difference from `vikuiti` disappears. The seed is fixed, so an identical
reflection model gives bit-identical output:

```bash
sed -e 's/nEvents: 10000/nEvents: 20000/' \
    -e 's/backplaneFoil: vikuiti/backplaneFoil: ptfe/' \
    -e 's/0\.95/0.98/g' \
    $SCRATCH/build/sim_config.yaml > sim_config.yaml
```

Expected: `SiPMPhotons` 1019, `SiPMHits` 616, `SecondLayerBackplane` 0,
`FirstLayerBackplane` 21041, `FirstLayerEdges` 579 — identical to `vikuiti`
at R = 0.98 in every counter.

### 7. Reproducibility check (section 6)

Run the same configuration twice; both give `SiPMHits` = 616. No seed is set
anywhere in `src/`, `include/` or `mac/`.

## Status

All numbers in the note were produced by the runs above. The proposed
*mechanism* for finding F1 is an interpretation of that evidence and is pending
human confirmation — in particular the question of whether a dichroic filter
window belongs on the front face of the blue-WLS slab.
