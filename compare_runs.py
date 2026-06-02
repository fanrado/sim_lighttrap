#!/usr/bin/env python3
"""Compare mono-energy vs VUV spectrum simulation outputs."""
import uproot
import numpy as np
import sys

def load_tree(fname, treepath):
    try:
        f = uproot.open(fname)
        return f[treepath].arrays(library="np")
    except Exception as e:
        return None

def count_entries(fname, treepath):
    try:
        f = uproot.open(fname)
        return f[treepath].num_entries
    except:
        return 0

def list_trees(fname):
    f = uproot.open(fname)
    return list(f.keys())

# --- list available trees ---
mono_trees = list_trees("output_mono.root")
spec_trees = list_trees("output_spectrum.root")
print("Trees in mono:", mono_trees)
print("Trees in spectrum:", spec_trees)
print()

# --- Primary photon energy/wavelength ---
print("=" * 60)
print("1. PRIMARY PHOTON WAVELENGTH/ENERGY DISTRIBUTION")
print("=" * 60)

primary_mono = load_tree("output_mono.root", "Primary")
primary_spec = load_tree("output_spectrum.root", "Primary")

if primary_mono is None or primary_spec is None:
    # try different tree names
    for tname in mono_trees:
        if "primary" in tname.lower() or "prim" in tname.lower():
            primary_mono = load_tree("output_mono.root", tname)
            primary_spec = load_tree("output_spectrum.root", tname)
            print(f"  Using tree: {tname}")
            break

if primary_mono is not None:
    keys = list(primary_mono.keys())
    print(f"  Primary tree keys: {keys}")
    # look for energy or wavelength branch
    for key in keys:
        arr = primary_mono[key]
        if len(arr) > 0 and np.issubdtype(arr.dtype, np.floating):
            mn, mx, med = np.min(arr), np.max(arr), np.median(arr)
            print(f"  MONO  {key}: min={mn:.4f} max={mx:.4f} median={med:.4f} n={len(arr)}")
    for key in list(primary_spec.keys()):
        arr = primary_spec[key]
        if len(arr) > 0 and np.issubdtype(arr.dtype, np.floating):
            mn, mx, med = np.min(arr), np.max(arr), np.median(arr)
            print(f"  SPEC  {key}: min={mn:.4f} max={mx:.4f} median={med:.4f} n={len(arr)}")

# --- WLS conversion rate ---
print()
print("=" * 60)
print("2. WLS CONVERSION RATE")
print("=" * 60)

# WLSPhoton tree / Primary tree
n_primary_mono = count_entries("output_mono.root", "Primary")
n_primary_spec = count_entries("output_spectrum.root", "Primary")

wls_mono = None
wls_spec = None
for tname in mono_trees:
    if "wls" in tname.lower():
        wls_mono = count_entries("output_mono.root", tname)
        wls_spec = count_entries("output_spectrum.root", tname)
        print(f"  WLS tree: {tname}")
        break

if wls_mono is not None and n_primary_mono > 0:
    rate_mono = wls_mono / n_primary_mono
    rate_spec = wls_spec / n_primary_spec
    # statistical uncertainty: sqrt(N)/N_total
    sigma_mono = np.sqrt(wls_mono) / n_primary_mono
    sigma_spec = np.sqrt(wls_spec) / n_primary_spec
    sigma_combined = np.sqrt(sigma_mono**2 + sigma_spec**2)
    z = abs(rate_spec - rate_mono) / sigma_combined if sigma_combined > 0 else 0
    print(f"  Mono:     WLS hits={wls_mono}, primary={n_primary_mono}, rate={rate_mono:.4f} ± {sigma_mono:.4f}")
    print(f"  Spectrum: WLS hits={wls_spec}, primary={n_primary_spec}, rate={rate_spec:.4f} ± {sigma_spec:.4f}")
    print(f"  |Δrate|/σ_combined = {z:.2f}  {'✓ PASS (<2)' if z < 2 else '✗ FAIL (≥2)'}")

# --- SiPM Hits ---
print()
print("=" * 60)
print("3. SiPM HIT COUNT")
print("=" * 60)

hits_tree_name = None
for tname in mono_trees:
    if "hit" in tname.lower() and "back" not in tname.lower() and "edge" not in tname.lower():
        hits_tree_name = tname
        break
if hits_tree_name:
    n_hits_mono = count_entries("output_mono.root", hits_tree_name)
    n_hits_spec = count_entries("output_spectrum.root", hits_tree_name)
    sigma_mono = np.sqrt(n_hits_mono) / n_primary_mono if n_primary_mono > 0 else 0
    sigma_spec = np.sqrt(n_hits_spec) / n_primary_spec if n_primary_spec > 0 else 0
    rate_mono = n_hits_mono / n_primary_mono if n_primary_mono > 0 else 0
    rate_spec = n_hits_spec / n_primary_spec if n_primary_spec > 0 else 0
    sigma_combined = np.sqrt(sigma_mono**2 + sigma_spec**2)
    z = abs(rate_spec - rate_mono) / sigma_combined if sigma_combined > 0 else 0
    print(f"  Tree: {hits_tree_name}")
    print(f"  Mono:     hits={n_hits_mono}, rate={rate_mono:.4f} ± {sigma_mono:.4f}")
    print(f"  Spectrum: hits={n_hits_spec}, rate={rate_spec:.4f} ± {sigma_spec:.4f}")
    print(f"  |Δrate|/σ_combined = {z:.2f}  {'✓ PASS (<2)' if z < 2 else '✗ FAIL (≥2)'}")

# --- Backplane Leak ---
print()
print("=" * 60)
print("4. BACKPLANE LEAK / EDGE STRIP")
print("=" * 60)

for tname in mono_trees:
    if "back" in tname.lower() or "edge" in tname.lower() or "leak" in tname.lower():
        n_mono = count_entries("output_mono.root", tname)
        n_spec = count_entries("output_spectrum.root", tname)
        rate_mono_l = n_mono / n_primary_mono if n_primary_mono > 0 else 0
        rate_spec_l = n_spec / n_primary_spec if n_primary_spec > 0 else 0
        sigma_mono_l = np.sqrt(n_mono) / n_primary_mono if n_primary_mono > 0 and n_mono > 0 else 0
        sigma_spec_l = np.sqrt(n_spec) / n_primary_spec if n_primary_spec > 0 and n_spec > 0 else 0
        sigma_combined_l = np.sqrt(sigma_mono_l**2 + sigma_spec_l**2)
        z = abs(rate_spec_l - rate_mono_l) / sigma_combined_l if sigma_combined_l > 0 else 0
        print(f"  {tname}: mono={n_mono} ({rate_mono_l:.4f}), spec={n_spec} ({rate_spec_l:.4f}), |Δ|/σ={z:.2f} {'✓' if z<2 else '✗'}")

# --- Boundary check: spectrum energy range ---
print()
print("=" * 60)
print("5. BOUNDARY WAVELENGTH CHECK (115 nm, 145 nm)")
print("=" * 60)

if primary_spec is not None:
    keys = list(primary_spec.keys())
    # look for wavelength (nm), energy (eV), or wavelength (µm) branch
    for key in keys:
        arr = primary_spec[key]
        if len(arr) == 0:
            continue
        arr_flat = np.array(arr).flatten()
        med = np.median(arr_flat)
        # wavelength in nm: median in [100, 200]
        if 100.0 < med < 200.0:
            wl_nm = arr_flat
            n_below_115 = np.sum(wl_nm < 115)
            n_above_145 = np.sum(wl_nm > 145)
            print(f"  Branch '{key}' (wavelength nm): median={med:.2f} nm")
            print(f"  Wavelength range: {np.min(wl_nm):.1f} – {np.max(wl_nm):.1f} nm")
            print(f"  Entries below 115 nm: {n_below_115}  (should be 0 or minimal)")
            print(f"  Entries above 145 nm: {n_above_145}  (should be 0 or minimal)")
            if n_below_115 == 0 and n_above_145 == 0:
                print("  ✓ PASS: No boundary overflow")
            else:
                print(f"  ✗ WARNING: {n_below_115+n_above_145} photons outside [115,145] nm range")
        # energy in eV: median in [8.5, 11.0]
        elif 8.0 < med < 11.0:
            wl_nm = 1239.8 / arr_flat
            n_below_115 = np.sum(wl_nm < 115)
            n_above_145 = np.sum(wl_nm > 145)
            print(f"  Branch '{key}' (energy eV): median={med:.4f} eV")
            print(f"  Wavelength range: {np.min(wl_nm):.1f} – {np.max(wl_nm):.1f} nm")
            print(f"  Entries below 115 nm: {n_below_115}  (should be 0 or minimal)")
            print(f"  Entries above 145 nm: {n_above_145}  (should be 0 or minimal)")
            if n_below_115 == 0 and n_above_145 == 0:
                print("  ✓ PASS: No boundary overflow")
            else:
                print(f"  ✗ WARNING: {n_below_115+n_above_145} photons outside [115,145] nm range")
        # wavelength in µm: median in [0.1, 0.2]
        elif 0.1 < med < 0.2:
            wl_nm = arr_flat * 1000
            n_below_115 = np.sum(wl_nm < 115)
            n_above_145 = np.sum(wl_nm > 145)
            print(f"  Branch '{key}' (wavelength µm): median={med*1000:.1f} nm")
            print(f"  Wavelength range: {np.min(wl_nm):.1f} – {np.max(wl_nm):.1f} nm")
            print(f"  Entries below 115 nm: {n_below_115}")
            print(f"  Entries above 145 nm: {n_above_145}")
            if n_below_115 == 0 and n_above_145 == 0:
                print("  ✓ PASS: No boundary overflow")
            else:
                print(f"  ✗ WARNING: {n_below_115+n_above_145} photons outside [115,145] nm range")

print()
print("=" * 60)
print("DONE")
