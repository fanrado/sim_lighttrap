"""
Tests for mac/run_vuv_spectrum.mac — verifies the GPS energy unit fix.

The bug: /gps/ene/unit eV is not a valid Geant4 GPS command, so energies were
silently interpreted as MeV (~9.7 MeV instead of ~9.7 eV).

The fix: all 13 hist/point energies now carry the ×1e-6 factor so they are in MeV.
"""
import re
import math
import pytest

MACRO_PATH = "mac/run_vuv_spectrum.mac"

HC_EV_NM = 1239.84193  # eV·nm  (hc in convenient units)


def parse_hist_points(path):
    """Return list of (energy_mev, weight) from /gps/hist/point lines."""
    points = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("/gps/hist/point"):
                parts = line.split()
                assert len(parts) == 3, f"Unexpected format: {line!r}"
                points.append((float(parts[1]), float(parts[2])))
    return points


@pytest.fixture(scope="module")
def hist_points():
    return parse_hist_points(MACRO_PATH)


# ── 1. Sanity: 13 points ─────────────────────────────────────────────────────

def test_thirteen_points(hist_points):
    assert len(hist_points) == 13, f"Expected 13 hist/points, got {len(hist_points)}"


# ── 2. Energies are in MeV (order ~1e-5), not eV (order ~10) ─────────────────

def test_energies_are_mev_not_ev(hist_points):
    for energy_mev, _ in hist_points:
        assert energy_mev < 1e-4, (
            f"Energy {energy_mev} looks like eV, not MeV — ×1e-6 conversion missing"
        )
        assert energy_mev > 1e-6, (
            f"Energy {energy_mev} is unexpectedly small"
        )


# ── 3. Each energy maps to a wavelength inside [115, 145] nm ─────────────────

def test_energies_within_vuv_window(hist_points):
    # Allow 0.1 nm tolerance at boundaries for floating-point rounding
    wl_min, wl_max = 115.0 - 0.1, 145.0 + 0.1
    for energy_mev, _ in hist_points:
        energy_ev = energy_mev * 1e6          # MeV → eV
        wl_nm = HC_EV_NM / energy_ev          # eV → nm
        assert wl_min <= wl_nm <= wl_max, (
            f"Wavelength {wl_nm:.2f} nm is outside [{wl_min:.1f}, {wl_max:.1f}] nm "
            f"(energy_mev={energy_mev})"
        )


# ── 4. Energies are monotonically increasing (λ decreasing) ──────────────────

def test_energies_monotonically_increasing(hist_points):
    energies = [e for e, _ in hist_points]
    for i in range(1, len(energies)):
        assert energies[i] > energies[i - 1], (
            f"Energy not monotonically increasing at index {i}: "
            f"{energies[i-1]} → {energies[i]}"
        )


# ── 5. Gaussian-shaped weights: peak near 128 nm (9.69 eV) ───────────────────

def test_weights_form_gaussian_peak(hist_points):
    """Peak weight should correspond to the energy closest to 128 nm."""
    peak_idx = max(range(len(hist_points)), key=lambda i: hist_points[i][1])
    peak_energy_ev = hist_points[peak_idx][0] * 1e6
    peak_wl_nm = HC_EV_NM / peak_energy_ev
    # peak should be within 5 nm of 128 nm (Gaussian centre)
    assert abs(peak_wl_nm - 128.0) < 5.0, (
        f"Peak at {peak_wl_nm:.2f} nm, expected near 128 nm"
    )


def test_weights_bounded(hist_points):
    for energy_mev, weight in hist_points:
        assert 0.0 <= weight <= 1.0, (
            f"Weight {weight} out of [0, 1] for energy {energy_mev}"
        )


def test_max_weight_close_to_one(hist_points):
    max_w = max(w for _, w in hist_points)
    assert max_w > 0.9, f"Max weight {max_w} unexpectedly low (should be ≈1)"


# ── 6. Cross-check: eV values match expected λ spacing (≈2.5 nm) ─────────────

def test_wavelength_spacing_approximately_2p5_nm(hist_points):
    """Adjacent points should differ by ≈2.5 nm in wavelength."""
    wl = [HC_EV_NM / (e * 1e6) for e, _ in hist_points]
    # wavelength decreases as energy increases
    spacings = [wl[i] - wl[i + 1] for i in range(len(wl) - 1)]
    for i, sp in enumerate(spacings):
        assert 1.0 < sp < 5.0, (
            f"Unexpected wavelength spacing {sp:.3f} nm between points {i} and {i+1}"
        )


# ── 7. No /gps/ene/unit line present (invalid in Geant4 11.x) ────────────────

def test_no_gps_ene_unit_command():
    with open(MACRO_PATH) as fh:
        for lineno, line in enumerate(fh, 1):
            stripped = line.strip()
            if stripped.startswith("/gps/ene/unit"):
                pytest.fail(
                    f"Line {lineno}: found invalid GPS command '/gps/ene/unit'. "
                    "This command is not recognised by Geant4 and silently falls "
                    "back to MeV — remove it and express energies in MeV directly."
                )
