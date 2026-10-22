"""
Tests for GPS Arb spectrum generation in input/create_macro.py.

Feature (commit 8c9b6dc):
  create_macro.py reads input/spectrum.txt (wavelength[nm], counts) and writes
  mac/spectrum_macro.mac as a Geant4 GPS Arb energy distribution.  The fix
  enforces the GPS Arb contract that previously crashed run_285.mac with a
  stack-smashing SIGABRT:
    1. Energy points STRICTLY INCREASING (spectrum.txt is in decreasing energy).
    2. At most 1024 points (hard G4 buffer limit) via even downsampling that
       always keeps the endpoints.
    3. Duplicate energies dropped (zero-width segment breaks interpolation).
    4. Energies emitted in MeV via a literal 'e-6' suffix on the eV value.
    5. The stray '/gps/particle gamma' line removed so the caller's
       opticalphoton stands.
    6. Counts clamped at 0 then normalized to peak 1.0 (guarded against a
       zero/negative peak).

Unlike the Geant4 C++ features, this script is pure Python, so these tests run
the actual committed script in an isolated temp workspace with controlled input
and assert on the emitted macro.
"""

import os
import re
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "input", "create_macro.py")

# GPS Arb hard cap the script must not exceed (mirrors MAX_ARB_POINTS).
MAX_ARB_POINTS = 1024
HC_EV_NM = 1239.841939


def run_macro(tmp_path, rows):
    """Run the committed create_macro.py against `rows` (list of (wavelength, count)).

    The script uses relative paths ('spectrum.txt' in CWD, '../mac/...'), so we
    replicate that layout in tmp_path: input/ holds a copy of the script plus our
    spectrum.txt, and a sibling mac/ receives the output.  Returns the macro text.
    """
    input_dir = tmp_path / "input"
    mac_dir = tmp_path / "mac"
    input_dir.mkdir()
    mac_dir.mkdir()

    shutil.copy(SCRIPT, input_dir / "create_macro.py")
    spectrum = "\n".join(f"{w}\t{c}" for w, c in rows) + "\n"
    (input_dir / "spectrum.txt").write_text(spectrum)

    proc = subprocess.run(
        [sys.executable, "create_macro.py"],
        cwd=str(input_dir),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"script failed: {proc.stderr}"
    out = mac_dir / "spectrum_macro.mac"
    assert out.exists(), "spectrum_macro.mac was not written"
    return out.read_text()


def parse_points(macro):
    """Return list of (energy_str, energy_float_MeV, prob_float) from /gps/hist/point lines."""
    pts = []
    for m in re.finditer(r"/gps/hist/point\s+(\S+)\s+(\S+)", macro):
        e_str, p_str = m.group(1), m.group(2)
        pts.append((e_str, float(e_str), float(p_str)))
    return pts


# A simple descending-energy (ascending-wavelength) spectrum, like spectrum.txt.
BASIC_ROWS = [
    (200.0, 10.0),
    (300.0, 40.0),
    (400.0, 20.0),
    (500.0, 5.0),
]


@pytest.fixture(scope="module")
def basic_macro(tmp_path_factory):
    return run_macro(tmp_path_factory.mktemp("basic"), BASIC_ROWS)


# ── macro scaffolding ────────────────────────────────────────────────────────

def test_macro_has_arb_directives(basic_macro):
    """The Arb distribution directives must be present and in order."""
    for directive in ("/gps/ene/type Arb", "/gps/hist/type arb", "/gps/hist/inter Lin"):
        assert directive in basic_macro, f"missing directive: {directive}"


def test_no_particle_gamma_line(basic_macro):
    """The stray '/gps/particle gamma' must be gone so the caller's particle stands."""
    assert "/gps/particle" not in basic_macro, (
        "create_macro.py must not set a particle type"
    )


# ── energy ordering & units ──────────────────────────────────────────────────

def test_energy_strictly_increasing(basic_macro):
    """GPS Arb requires strictly increasing energy points."""
    energies = [e for _, e, _ in parse_points(basic_macro)]
    assert len(energies) >= 2
    assert all(b > a for a, b in zip(energies, energies[1:])), (
        f"energies not strictly increasing: {energies}"
    )


def test_energy_written_in_mev_with_e6_suffix(basic_macro):
    """Each energy is the eV value with a literal 'e-6' suffix (→ MeV)."""
    pts = parse_points(basic_macro)
    assert pts, "no /gps/hist/point lines found"
    for e_str, e_mev, _ in pts:
        assert e_str.endswith("e-6"), f"energy {e_str!r} lacks the e-6 (MeV) suffix"
        # 200..500 nm → ~2.48..6.20 eV → ~2.5e-6..6.2e-6 MeV.
        assert 1e-6 < e_mev < 1e-5, f"energy {e_mev} MeV outside plausible optical range"


def test_energy_matches_hc_over_wavelength(basic_macro):
    """The highest energy point corresponds to the shortest wavelength (200 nm)."""
    pts = parse_points(basic_macro)
    e_max_mev = pts[-1][1]
    expected_ev = HC_EV_NM / 200.0
    assert e_max_mev * 1e6 == pytest.approx(expected_ev, rel=1e-4)


# ── normalization ────────────────────────────────────────────────────────────

def test_probabilities_normalized_to_peak_one(basic_macro):
    """Peak count (40 at 300 nm) normalizes to 1.0; others scale proportionally."""
    probs = [p for _, _, p in parse_points(basic_macro)]
    assert max(probs) == pytest.approx(1.0)
    # count 10 -> 0.25, 20 -> 0.5, 5 -> 0.125 relative to peak 40.
    assert sorted(probs) == pytest.approx([0.125, 0.25, 0.5, 1.0])


def test_negative_counts_clamped_to_zero(tmp_path):
    """Negative counts become 0 before normalization (never negative probabilities)."""
    rows = [(200.0, -30.0), (300.0, 40.0), (400.0, -5.0)]
    macro = run_macro(tmp_path, rows)
    probs = [p for _, _, p in parse_points(macro)]
    assert all(p >= 0.0 for p in probs), f"negative probability emitted: {probs}"
    assert max(probs) == pytest.approx(1.0)
    # the two negative-count points are clamped to 0.
    assert probs.count(0.0) == 2


def test_all_nonpositive_counts_do_not_crash(tmp_path):
    """peak <= 0 must not divide by zero; script still emits points (all prob 0)."""
    rows = [(200.0, 0.0), (300.0, -1.0), (400.0, 0.0)]
    macro = run_macro(tmp_path, rows)
    probs = [p for _, _, p in parse_points(macro)]
    assert probs, "no points emitted"
    assert all(p == 0.0 for p in probs)


# ── duplicate energies ───────────────────────────────────────────────────────

def test_duplicate_energies_dropped(tmp_path):
    """Repeated wavelengths (→ equal energies) collapse to one point."""
    rows = [(200.0, 10.0), (200.0, 99.0), (300.0, 40.0), (300.0, 1.0)]
    macro = run_macro(tmp_path, rows)
    energies = [e for _, e, _ in parse_points(macro)]
    assert len(energies) == len(set(energies)), f"duplicate energies present: {energies}"
    assert len(energies) == 2, f"expected 2 unique energies, got {energies}"


# ── 1024-point cap ───────────────────────────────────────────────────────────

def test_point_count_capped_at_1024(tmp_path):
    """A 2048-point input downsamples to at most 1024 points."""
    rows = [(190.0 + i * 0.3, 100.0 + i) for i in range(2048)]
    macro = run_macro(tmp_path, rows)
    pts = parse_points(macro)
    assert len(pts) <= MAX_ARB_POINTS, f"got {len(pts)} points, cap is {MAX_ARB_POINTS}"
    assert len(pts) >= MAX_ARB_POINTS - 1, (
        f"downsample too aggressive: only {len(pts)} points"
    )


def test_downsample_preserves_endpoints(tmp_path):
    """Downsampling keeps the min and max energy so the spectral range is intact."""
    n = 2048
    rows = [(190.0 + i * 0.3, 100.0 + i) for i in range(n)]
    macro = run_macro(tmp_path, rows)
    energies = [e for _, e, _ in parse_points(macro)]

    wl_min, wl_max = 190.0, 190.0 + (n - 1) * 0.3
    e_hi_ev = HC_EV_NM / wl_min  # shortest wavelength → highest energy (last point)
    e_lo_ev = HC_EV_NM / wl_max  # longest wavelength → lowest energy (first point)
    assert energies[0] * 1e6 == pytest.approx(e_lo_ev, rel=1e-4)
    assert energies[-1] * 1e6 == pytest.approx(e_hi_ev, rel=1e-4)


def test_small_input_not_downsampled(basic_macro):
    """Inputs under the cap keep all their (unique) points."""
    assert len(parse_points(basic_macro)) == len(BASIC_ROWS)
