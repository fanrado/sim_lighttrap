"""
pytest configuration for the vuv_meas_pmt branch (first layer + PMT only).

The two-layer design (blue-WLS slab + edge SiPMs + reflector foils) was removed
from this branch; it lives in `develop`. Test files written for that design may
still be present in the working tree as untracked files — they are excluded
from collection here instead of being deleted, so nothing is lost.
"""

collect_ignore = [
    "test_analyze_efficiency.py",        # SiPM efficiency chain
    "test_analyze_out_macro.py",         # SiPM / SecondLayerBackplane trees
    "test_backplane_foil_config.py",     # vikuiti | ptfe | none backplane
    "test_firstlayer_backplane_standoff.py",  # references kBlueWLS* positions
    "test_firstlayer_edge_counters.py",  # ntuple ids 6/7/8 of the 5-region model
    "test_forward_direction_flag.py",    # ntuple ids 6/7/8 of the 5-region model
    "test_pass_through_counter.py",      # ntuple id 7 / blue-WLS wording
    "test_readme_backplane_docs.py",     # README backplane-comparison section
    "test_sipm_ntuple_rename.py",        # SiPMPhotons / SiPMHits
    "test_wls_emission_spectra.py",      # pTP + blue-WLS emission files
    "test_ptp_sigmaalpha_config.py",     # asserts /detector/nSiPMs ordering
    "test_create_macro_gps_arb.py",      # run_285.mac square source wording
]
