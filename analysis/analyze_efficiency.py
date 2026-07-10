#!/usr/bin/env python3
"""Compute WLS and SiPM-collection efficiencies from a LightTrap output ROOT file.

Two efficiencies are reported:

  1. First-layer (pTP) wavelength-shifting efficiency
        eps_WLS1 = N(WLS photons created in pTP) / N(primary photons)
     OpWLS emits ~1 photon per absorbed photon (WLSMEANNUMBERPHOTONS = 1), so this
     is the fraction of incident primaries that the pTP film absorbs and re-emits.

  2. Second-layer (blue-WLS) SiPM collection / detection efficiency
        eps_collect = N(photons arriving at SiPM) / N(blue-WLS photons)
        eps_detect  = N(SiPMHits, after PDE)      / N(blue-WLS photons)
     'collect' is the optical+geometric transport to the ±y-edge SiPMs; 'detect'
     folds in the per-wavelength photon-detection efficiency (pde_broadcom.dat)
     already applied when the SiPMHits ntuple is filled.

Data model (see src/run.cc, src/detector.cc, src/tracking.cc, include/namemap.hh):
  Primary   (ntuple 3) : one row per primary photon  -> N_primary
  WLSPhoton (ntuple 4) : one row per OpWLS/Scint photon; matName code identifies
                         the emitting material  (pTP = 1, bluewlsacrylic = 3)
  SiPMPhotons (ntuple 0) : one row per photon reaching a SiPM (before PDE)
  SiPMHits    (ntuple 1) : subset of SiPMPhotons that pass the PDE roll (photoelectrons)

Run it with the project's ROOT environment sourced (PyROOT):
    source ~/Software/setup.sh
    python3 analyze_efficiency.py [path/to/output.root]
"""

import sys
import math
import os

import ROOT

# NameMap codes (include/namemap.hh)
MAT_PTP = 1          # first-layer pTP film
MAT_BLUEWLS = 3      # second-layer blue-WLS acrylic slab

DEFAULT_FILE = "build/output_apexltsim0.root"


def wilson(k, n, z=1.0):
    """Binomial ratio p=k/n with a symmetric 1-sigma error.

    Uses sqrt(p(1-p)/n); k may exceed n (ratios like blue-WLS/pTP are not strict
    binomials) in which case the error term is only indicative and flagged by
    the caller via the >100% value itself.
    """
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    var = max(p * (1.0 - p), 0.0) / n
    return p, z * math.sqrt(var)


def get_tree(f, name):
    t = f.Get(name)
    if not t:
        raise RuntimeError("tree '%s' not found in file" % name)
    return t


def pct(p, e):
    if math.isnan(p):
        return "   n/a"
    return "%7.3f%% +/- %.3f%%" % (100.0 * p, 100.0 * e)


def main(argv):
    fname = argv[1] if len(argv) > 1 else DEFAULT_FILE
    if not os.path.exists(fname):
        sys.exit("error: ROOT file not found: %s" % fname)

    f = ROOT.TFile.Open(fname)
    if not f or f.IsZombie():
        sys.exit("error: could not open ROOT file: %s" % fname)

    primary = get_tree(f, "Primary")
    wls = get_tree(f, "WLSPhoton")
    photons = get_tree(f, "SiPMPhotons")
    hits = get_tree(f, "SiPMHits")

    n_primary = primary.GetEntries()
    n_wls_total = wls.GetEntries()
    n_ptp = wls.GetEntries("matName==%d" % MAT_PTP)
    n_bluewls = wls.GetEntries("matName==%d" % MAT_BLUEWLS)
    n_wls_other = n_wls_total - n_ptp - n_bluewls
    n_at_sipm = photons.GetEntries()
    n_detected = hits.GetEntries()

    if n_primary == 0:
        sys.exit("error: Primary tree is empty; nothing to normalize to.")

    # --- first-layer WLS efficiency -----------------------------------------
    eps_wls1, e_wls1 = wilson(n_ptp, n_primary)

    # --- second-layer conversion & collection -------------------------------
    # blue-WLS photons produced per pTP photon (2nd-stage conversion, may be <1
    # because not every pTP photon reaches / is absorbed by the blue slab)
    eps_wls2, e_wls2 = wilson(n_bluewls, n_ptp) if n_ptp else (float("nan"), float("nan"))
    eps_collect, e_collect = wilson(n_at_sipm, n_bluewls) if n_bluewls else (float("nan"), float("nan"))
    eps_detect, e_detect = wilson(n_detected, n_bluewls) if n_bluewls else (float("nan"), float("nan"))
    avg_pde, e_pde = wilson(n_detected, n_at_sipm) if n_at_sipm else (float("nan"), float("nan"))

    # --- overall chain ------------------------------------------------------
    eps_system, e_system = wilson(n_detected, n_primary)

    line = "-" * 68
    print(line)
    print("LightTrap efficiency analysis")
    print("  file: %s" % fname)
    print(line)
    print("Raw counts")
    print("  primary photons            N_primary  = %12d" % n_primary)
    print("  WLS photons (total)        N_wls      = %12d" % n_wls_total)
    print("    in pTP        (matName=1)            = %12d" % n_ptp)
    print("    in blue-WLS   (matName=3)            = %12d" % n_bluewls)
    if n_wls_other:
        print("    other material                       = %12d  (%.2e of total)"
              % (n_wls_other, n_wls_other / max(n_wls_total, 1)))
    print("  photons reaching SiPM      N_at_sipm  = %12d" % n_at_sipm)
    print("  detected (after PDE)       N_hits     = %12d" % n_detected)
    print(line)
    print("1. First layer -- pTP wavelength-shifting efficiency")
    print("     eps_WLS1 = N_pTP / N_primary        = %s" % pct(eps_wls1, e_wls1))
    print(line)
    print("2. Second layer -- blue-WLS + SiPM collection")
    print("     2nd-stage conversion  N_blue/N_pTP  = %s" % pct(eps_wls2, e_wls2))
    print("     collection  N_at_sipm / N_blue      = %s" % pct(eps_collect, e_collect))
    print("     detection   N_hits    / N_blue      = %s" % pct(eps_detect, e_detect))
    print("     average PDE N_hits    / N_at_sipm   = %s" % pct(avg_pde, e_pde))
    print(line)
    print("Overall chain")
    print("     photoelectrons per primary  N_hits/N_primary = %s" % pct(eps_system, e_system))
    print(line)

    f.Close()


if __name__ == "__main__":
    main(sys.argv)
