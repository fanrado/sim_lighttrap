# Source of the Sharp Cuts in the Wavelength Distributions

This note explains the sharp edges and steps seen in the photon **wavelength**
distributions written to the output ROOT file (e.g. `build/output_apexltsim0.root`,
produced by `mac/run_285.mac`). The cuts are **artifacts of the optical-property
tabulation**, not physical features of the light. No fix is applied here — this
document only records where the cuts come from.

## Affected branches

| Tree | Branch | Contents |
|------|--------|----------|
| `Photons` | `fwl` | Wavelength of photons reaching the detector |
| `WLSPhoton` | `wl` | Wavelength of photons created by `OpWLS` / `Scintillation` (pTP + blue-WLS re-emission) — see `src/tracking.cc:24` |

Wavelength is computed from the photon kinetic energy as
`λ[nm] = 1239.841939 / E[eV]` (`src/tracking.cc:28`, `src/event.cc:38`).

## Root cause: a coarse, non-uniform property grid

Every material's optical properties are tabulated on the **same fixed 13-point
grid** defined in `src/construction.cc:60-69`:

```
wavelengths [nm] = { 530, 425, 400, 340, 305, 160, 145, 135, 128, 125, 120, 115, 106 }
```

Two consequences of how Geant4 uses this table create every cut:

1. **Bounded range.** Optical photons can only be generated and propagated within
   the photon-energy range where `RINDEX` (and the emission spectra) are defined.
   The endpoints of the grid are **530 nm (lowest energy)** and **106 nm (highest
   energy)**, so nothing can exist outside `[106, 530] nm`.
2. **Linear interpolation.** Geant4 linearly interpolates each property in photon
   energy between adjacent grid nodes. Where nodes are far apart, the straight line
   between them — not the physics — sets the shape, and every kink in the output
   lands exactly on a grid node.

## The individual features

### 1. Hard cut at 530 nm (both trees)
530 nm is the longest wavelength in every property table. No photon can be created
or transported beyond it. Observed: `max(fwl) = max(wl) = 529.999 nm`.

### 2. Step at 400 nm in detected `Photons`
The detected light forms a block from ~400 to 530 nm with only a thin tail below
400 nm. This is the **blue-WLS (EJ-286-type) emission table** (`src/construction.cc:178`):

```
WLSCOMPONENT = { 0.0005, 0.02, 0, 0, ... }   at { 530, 425, 400, 340, ... } nm
```

Non-zero only at 425 and 530 nm; zero at 400 nm and shorter. Interpolation makes
it emit across ~400–530 nm, peaked at 425 nm, so detected photons are hard-bounded
to that window. The small `fwl < 400 nm` tail is first-stage pTP light reaching the
SiPM directly.

### 3. Ramp 160→305 nm + step at 305 nm in `WLSPhoton`
This is the **pTP emission table** (`src/construction.cc:96`):

```
WLSCOMPONENT = { 0, 0.0005, 0.002, 0.022, 0.0005, 0, 0, ... }
               at { 530,  425,   400,  340,   305,  160, 145, ... } nm
```

- Main band 305–425 nm (peak at the 340 nm node) — the physical pTP hump.
- At 305 nm the value is tiny (0.0005), and the **next node is all the way down at
  160 nm (value 0)**. Linear interpolation across that large 305→160 nm gap
  produces a long, low, triangular ramp — spurious emission smeared over 160–305 nm
  with no physical basis.
- Below 160 nm the table is zero (all VUV nodes are 0 for pTP) → **hard cut at 160
  nm** (`min(wl) = 160.002 nm`).
- The abrupt rise near 305 nm (0.0005 → 0.022 between the 305 and 340 nodes) is the
  visible step.

## Summary

| Feature | Location | Origin |
|---------|----------|--------|
| Hard right cut | 530 nm | Upper bound of all property tables |
| Step in detected light | 400 nm | Blue-WLS `WLSCOMPONENT` lower edge |
| Step / kink | 305 nm | pTP `WLSCOMPONENT` grid node |
| Spurious ramp | 160–305 nm | Linear interpolation across the 305→160 nm gap |
| Hard left cut | 160 nm | pTP emission is 0 below this node |

All edges coincide with nodes of the 13-point grid in `src/construction.cc`. They
are properties of the tabulation and interpolation, not of the simulated physics.

## Related minor anomaly

`Photons.fwl` also has a `min ≈ 0.0003 nm` — a handful of entries with a near-zero
wavelength (i.e. an unphysically large energy). This is a separate, small
data-quality issue unrelated to the grid cuts and is worth a closer look if that
branch is used quantitatively.
