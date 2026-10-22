#!/usr/bin/env python3
"""Compute the first-layer -> PMT efficiency chain from a LightTrap output ROOT file.

Stages (each normalised to the previous one and to the number of primaries):

  1. pTP wavelength-shifting efficiency
        eps_WLS = N(WLS photons created in pTP) / N(primary photons)
     OpWLS emits ~1 photon per absorbed photon, so this is the fraction of
     incident beam photons absorbed and re-emitted by the pTP film.
  2. First-layer escape through the back face (toward the PMT)
        eps_escape = N(FirstLayerBackplane, forward) / N(pTP WLS photons)
  3. Geometric collection on the photocathode
        eps_geo = N(PMTPhotons) / N(FirstLayerBackplane, forward)
  4. PMT quantum efficiency (flat pmtQE inside [pmtQEmin, pmtQEmax])
        QE_avg = N(PMTHits) / N(PMTPhotons)

Data model (see src/run.cc, src/detector.cc, src/tracking.cc, include/namemap.hh):
  Primary             (ntuple 1): one row per primary photon            -> N_primary
  WLSPhoton           (ntuple 2): one row per OpWLS/Scint photon; matName code
                                  identifies the emitting material (pTP = 1)
  FirstLayerBackplane (ntuple 4): photons crossing the first-layer back face
                                  ('forward' = 1 when travelling toward the PMT)
  FirstLayerEdges     (ntuple 5): photons reaching the first-layer +/-x edges
  PMTPhotons          (ntuple 6): one row per photon reaching the photocathode (pre-QE)
  PMTHits             (ntuple 7): subset of PMTPhotons passing the QE roll

Run it with the project's ROOT environment sourced (PyROOT):
    python3 analysis/analyze_efficiency.py [path/to/output.root]
"""

import sys
import math
import os

import ROOT

# NameMap codes (include/namemap.hh)
MAT_PTP = 1          # pTP film

DEFAULT_FILE = "build/output_apexltsim0.root"


def wilson(k, n, z=1.0):
    """Binomial ratio p=k/n with a symmetric 1-sigma error sqrt(p(1-p)/n)."""
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
    back = get_tree(f, "FirstLayerBackplane")
    edges = get_tree(f, "FirstLayerEdges")
    photons = get_tree(f, "PMTPhotons")
    hits = get_tree(f, "PMTHits")

    n_primary = primary.GetEntries()
    n_wls_total = wls.GetEntries()
    n_ptp = wls.GetEntries("matName==%d" % MAT_PTP)
    n_wls_other = n_wls_total - n_ptp
    n_back_fwd = back.GetEntries("forward==1")
    n_back_bwd = back.GetEntries("forward==0")
    n_edges = edges.GetEntries()
    n_at_pmt = photons.GetEntries()
    n_at_pmt_direct = photons.GetEntries("primary==1")
    n_detected = hits.GetEntries()

    if n_primary == 0:
        sys.exit("error: Primary tree is empty; nothing to normalize to.")

    eps_wls, e_wls = wilson(n_ptp, n_primary)
    eps_escape, e_escape = wilson(n_back_fwd, n_ptp)
    eps_edge, e_edge = wilson(n_edges, n_ptp)
    eps_geo, e_geo = wilson(n_at_pmt, n_back_fwd)
    qe_avg, e_qe = wilson(n_detected, n_at_pmt)
    eps_system, e_system = wilson(n_detected, n_primary)

    line = "-" * 68
    print(line)
    print("LightTrap first layer + PMT efficiency analysis")
    print("  file: %s" % fname)
    print(line)
    print("Raw counts")
    print("  primary photons            N_primary  = %12d" % n_primary)
    print("  WLS photons (total)        N_wls      = %12d" % n_wls_total)
    print("    in pTP        (matName=1)            = %12d" % n_ptp)
    if n_wls_other:
        print("    other material                       = %12d  (%.2e of total)"
              % (n_wls_other, n_wls_other / max(n_wls_total, 1)))
    print("  layer-1 back face, forward N_back_fwd = %12d" % n_back_fwd)
    print("  layer-1 back face, backward            = %12d" % n_back_bwd)
    print("  layer-1 +/-x edges         N_edges    = %12d" % n_edges)
    print("  photons on photocathode    N_at_pmt   = %12d  (direct VUV: %d)" % (n_at_pmt, n_at_pmt_direct))
    print("  detected (after QE)        N_hits     = %12d" % n_detected)
    print(line)
    print("1. pTP wavelength-shifting efficiency")
    print("     eps_WLS    = N_pTP / N_primary         = %s" % pct(eps_wls, e_wls))
    print(line)
    print("2. First-layer escape")
    print("     back face  = N_back_fwd / N_pTP        = %s" % pct(eps_escape, e_escape))
    print("     edges      = N_edges / N_pTP           = %s" % pct(eps_edge, e_edge))
    print(line)
    print("3. PMT")
    print("     geometric  = N_at_pmt / N_back_fwd     = %s" % pct(eps_geo, e_geo))
    print("     QE (avg)   = N_hits / N_at_pmt         = %s" % pct(qe_avg, e_qe))
    print(line)
    print("Overall chain")
    print("     photoelectrons per primary  N_hits/N_primary = %s" % pct(eps_system, e_system))
    print(line)

    f.Close()


if __name__ == "__main__":
    main(sys.argv)
