"""
Tests for the materials: block in sim_config.yaml (commit 3d5295d).

Covers:
  - Array lengths (validateOpticalArray requires exactly 13 entries)
  - Physical plausibility of every optical property
  - Material-specific physics constraints (LAr scintillation, pTP WLS peak, etc.)
  - resolveArray fallback contract: absent key → empty list (truthy check)

Wavelength grid (13 points, nm):
  idx: 0    1    2    3    4    5    6    7    8    9    10   11   12
  nm: 530  425  400  340  305  160  145  135  128  125  120  115  106
"""
import math
import yaml
import pytest

CONFIG_PATH = "sim_config.yaml"
N_POINTS = 13
WL_GRID_NM = [530, 425, 400, 340, 305, 160, 145, 135, 128, 125, 120, 115, 106]


@pytest.fixture(scope="module")
def materials():
    with open(CONFIG_PATH) as fh:
        doc = yaml.safe_load(fh)
    assert "materials" in doc, "sim_config.yaml must have a 'materials:' key"
    return doc["materials"]


# ── helpers ───────────────────────────────────────────────────────────────────

def _arr(materials, *keys):
    """Navigate nested dict by keys and return the list, or [] if absent."""
    node = materials
    for k in keys:
        if node is None or k not in node:
            return []
        node = node[k]
    return node if node is not None else []


def _scalar(materials, *keys):
    node = materials
    for k in keys:
        if node is None or k not in node:
            return None
        node = node[k]
    return node


# ── 1. All present arrays have exactly 13 entries ────────────────────────────

ARRAY_PATHS = [
    ("ptp", "rindex"),
    ("ptp", "abslen_m"),
    ("ptp", "wlsabslen_m"),
    ("ptp", "wlscomponent"),
    ("uvAcrylic", "rindex"),
    ("uvAcrylic", "abslen_m"),
    ("acrylicMcMaster", "rindex"),
    ("blueWLS", "rindex"),
    ("blueWLS", "wlsabslen_m"),
    ("blueWLS", "wlscomponent"),
    ("lar", "rindex"),
    ("lar", "abslen_m"),
    ("lar", "rayleigh_m"),
    ("lar", "scintcomponent"),
    ("vikuiti", "reflectivity"),
]


@pytest.mark.parametrize("path", ARRAY_PATHS, ids=[".".join(p) for p in ARRAY_PATHS])
def test_array_has_13_entries(materials, path):
    arr = _arr(materials, *path)
    if not arr:
        pytest.skip(f"{'.'.join(path)} absent — fallback to C++ default")
    assert len(arr) == N_POINTS, (
        f"{'.'.join(path)}: expected {N_POINTS} entries, got {len(arr)}"
    )


# ── 2. Refractive indices > 1.0 and physically reasonable ────────────────────

RINDEX_PATHS = [
    ("ptp", "rindex"),
    ("uvAcrylic", "rindex"),
    ("acrylicMcMaster", "rindex"),
    ("blueWLS", "rindex"),
    ("lar", "rindex"),
]


@pytest.mark.parametrize("path", RINDEX_PATHS, ids=[".".join(p) for p in RINDEX_PATHS])
def test_rindex_gt_one(materials, path):
    arr = _arr(materials, *path)
    if not arr:
        pytest.skip(f"{'.'.join(path)} absent")
    for i, v in enumerate(arr):
        assert v > 1.0, f"{'.'.join(path)}[{i}] = {v} must be > 1.0"
        assert v < 10.0, f"{'.'.join(path)}[{i}] = {v} unreasonably large"


# ── 3. Absorption lengths positive ───────────────────────────────────────────

ABSLEN_PATHS = [
    ("ptp", "abslen_m"),
    ("ptp", "wlsabslen_m"),
    ("uvAcrylic", "abslen_m"),
    ("blueWLS", "wlsabslen_m"),
    ("lar", "abslen_m"),
    ("lar", "rayleigh_m"),
]


@pytest.mark.parametrize("path", ABSLEN_PATHS, ids=[".".join(p) for p in ABSLEN_PATHS])
def test_abslen_positive(materials, path):
    arr = _arr(materials, *path)
    if not arr:
        pytest.skip(f"{'.'.join(path)} absent")
    for i, v in enumerate(arr):
        assert v > 0.0, f"{'.'.join(path)}[{i}] = {v} must be > 0"


# ── 4. WLS/scint component arrays: non-negative, ≤ 1 ──────────────────────────

COMPONENT_PATHS = [
    ("ptp", "wlscomponent"),
    ("blueWLS", "wlscomponent"),
    ("lar", "scintcomponent"),
]


@pytest.mark.parametrize("path", COMPONENT_PATHS, ids=[".".join(p) for p in COMPONENT_PATHS])
def test_component_bounded(materials, path):
    arr = _arr(materials, *path)
    if not arr:
        pytest.skip(f"{'.'.join(path)} absent")
    for i, v in enumerate(arr):
        assert 0.0 <= v <= 1.0, f"{'.'.join(path)}[{i}] = {v} must be in [0, 1]"


# ── 5. Vikuiti reflectivity ≥ 0.98 everywhere ────────────────────────────────

def test_vikuiti_reflectivity_ge_98pct(materials):
    arr = _arr(materials, "vikuiti", "reflectivity")
    if not arr:
        pytest.skip("vikuiti.reflectivity absent")
    for i, v in enumerate(arr):
        assert 0.0 <= v <= 1.0, f"vikuiti.reflectivity[{i}] = {v} out of [0,1]"
        assert v >= 0.98, f"vikuiti.reflectivity[{i}] = {v} < 0.98 (ESR spec)"


# ── 6. pTP WLS emission peaks at 340–400 nm (indices 2–3) ────────────────────

def test_ptp_wls_emission_peaks_at_340_400nm(materials):
    """pTP shifts VUV to 340–400 nm; emission must be zero in VUV (idx 5–12)."""
    arr = _arr(materials, "ptp", "wlscomponent")
    if not arr:
        pytest.skip("ptp.wlscomponent absent")
    # Visible/near-UV indices: 0(530 nm), 1(425 nm), 2(400 nm), 3(340 nm), 4(305 nm)
    peak_idx = max(range(N_POINTS), key=lambda i: arr[i])
    assert peak_idx in (2, 3), (
        f"pTP WLS peak at index {peak_idx} ({WL_GRID_NM[peak_idx]} nm), "
        "expected index 2 (400 nm) or 3 (340 nm)"
    )
    # VUV region (idx 5–12) should be zero
    for i in range(5, N_POINTS):
        assert arr[i] == 0.0, (
            f"ptp.wlscomponent[{i}] ({WL_GRID_NM[i]} nm) = {arr[i]}, expected 0 in VUV"
        )


# ── 7. blueWLS emission peaks at ~430 nm (index 1 = 425 nm) ──────────────────

def test_bluewls_emission_peaks_at_425_530nm(materials):
    arr = _arr(materials, "blueWLS", "wlscomponent")
    if not arr:
        pytest.skip("blueWLS.wlscomponent absent")
    peak_idx = max(range(N_POINTS), key=lambda i: arr[i])
    assert peak_idx in (0, 1), (
        f"blueWLS peak at index {peak_idx} ({WL_GRID_NM[peak_idx]} nm), "
        "expected index 0 (530 nm) or 1 (425 nm)"
    )


# ── 8. LAr scintcomponent peaks at 128 nm (index 8) ──────────────────────────

def test_lar_scintcomponent_peaks_at_128nm(materials):
    arr = _arr(materials, "lar", "scintcomponent")
    if not arr:
        pytest.skip("lar.scintcomponent absent")
    peak_idx = max(range(N_POINTS), key=lambda i: arr[i])
    assert peak_idx == 8, (
        f"LAr scint peak at index {peak_idx} ({WL_GRID_NM[peak_idx]} nm), "
        "expected index 8 (128 nm)"
    )


# ── 9. LAr Rayleigh scattering ~0.9 m at all wavelengths ─────────────────────

def test_lar_rayleigh_approx_90cm(materials):
    arr = _arr(materials, "lar", "rayleigh_m")
    if not arr:
        pytest.skip("lar.rayleigh_m absent")
    for i, v in enumerate(arr):
        assert abs(v - 0.9) < 0.2, (
            f"lar.rayleigh_m[{i}] = {v} m, expected ~0.9 m (±0.2)"
        )


# ── 10. LAr scalar properties ────────────────────────────────────────────────

def test_lar_scintillationyield(materials):
    v = _scalar(materials, "lar", "scintillationyield")
    if v is None:
        pytest.skip("lar.scintillationyield absent")
    assert v > 0, "scintillationyield must be positive"
    assert 10000 <= v <= 50000, f"scintillationyield {v} outside plausible range [10k, 50k]"


def test_lar_yield_fractions_sum_to_one(materials):
    y1 = _scalar(materials, "lar", "scintillationyield1")
    y2 = _scalar(materials, "lar", "scintillationyield2")
    if y1 is None or y2 is None:
        pytest.skip("lar yield fractions absent")
    assert abs(y1 + y2 - 1.0) < 1e-6, (
        f"yield1 ({y1}) + yield2 ({y2}) = {y1+y2}, must sum to 1.0"
    )


def test_lar_time_constants_positive(materials):
    tc1 = _scalar(materials, "lar", "scintillationtimeconstant1_ns")
    tc2 = _scalar(materials, "lar", "scintillationtimeconstant2_ns")
    if tc1 is None and tc2 is None:
        pytest.skip("lar time constants absent")
    if tc1 is not None:
        assert tc1 > 0, f"scintillationtimeconstant1_ns = {tc1} must be > 0"
    if tc2 is not None:
        assert tc2 > tc1, (
            f"slow τ ({tc2} ns) must be longer than fast τ ({tc1} ns)"
        )


def test_lar_resolutionscale(materials):
    v = _scalar(materials, "lar", "resolutionscale")
    if v is None:
        pytest.skip("lar.resolutionscale absent")
    assert v > 0, "resolutionscale must be positive"


# ── 11. WLS time constants positive ──────────────────────────────────────────

@pytest.mark.parametrize("path", [("ptp", "wlstimeconstant_ns"), ("blueWLS", "wlstimeconstant_ns")])
def test_wls_timeconstant_positive(materials, path):
    v = _scalar(materials, *path)
    if v is None:
        pytest.skip(f"{'.'.join(path)} absent")
    assert v > 0, f"{'.'.join(path)} = {v} must be > 0"


# ── 12. uvAcrylic: strongly absorbs VUV (idx 5+), transparent at visible ─────

def test_uvacrylic_vuv_absorption(materials):
    arr = _arr(materials, "uvAcrylic", "abslen_m")
    if not arr:
        pytest.skip("uvAcrylic.abslen_m absent")
    visible_avg = sum(arr[:4]) / 4          # indices 0–3 (530–340 nm)
    vuv_avg     = sum(arr[5:]) / (N_POINTS - 5)  # indices 5–12 (VUV)
    assert visible_avg > vuv_avg * 10, (
        f"uvAcrylic should be much more transparent at visible ({visible_avg:.3g} m) "
        f"than VUV ({vuv_avg:.3g} m); ratio = {visible_avg/vuv_avg:.1f}"
    )


# ── 13. pTP: VUV bulk absorption >> WLS absorption (WLS process dominates) ───

def test_ptp_bulk_vs_wls_vuv(materials):
    bulk = _arr(materials, "ptp", "abslen_m")
    wls  = _arr(materials, "ptp", "wlsabslen_m")
    if not bulk or not wls:
        pytest.skip("ptp bulk/wls arrays absent")
    for i in range(5, N_POINTS):  # VUV region
        assert bulk[i] > wls[i], (
            f"ptp: VUV bulk abslen ({bulk[i]} m) must exceed WLS abslen ({wls[i]} m) "
            f"at index {i} ({WL_GRID_NM[i]} nm) so WLS process dominates"
        )


# ── 14. resolveArray contract: absent sub-key → empty list ───────────────────

def test_absent_key_returns_empty(materials):
    """Simulates the C++ resolveArray fallback: missing YAML key → empty → use default."""
    fake = {}
    result = _arr(fake, "ptp", "rindex")
    assert result == [], "absent key must yield empty list (triggers C++ fallback)"


def test_present_key_returns_list(materials):
    arr = _arr(materials, "ptp", "rindex")
    assert isinstance(arr, list) and len(arr) == N_POINTS
