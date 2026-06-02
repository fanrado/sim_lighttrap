"""
Tests for the analysis logic in compare_runs.py.

compare_runs.py is an executable script that opens ROOT files, so we test the
pure-Python logic here by replicating the functions under test.  The boundary
detection and statistical functions are exercised with synthetic numpy arrays.
"""
import math
import numpy as np
import pytest
from unittest.mock import patch, MagicMock


# ── Replicate the pure-Python helpers from compare_runs.py ───────────────────
# (cannot import the script directly because top-level code opens ROOT files)

def load_tree(fname, treepath):
    try:
        import uproot
        f = uproot.open(fname)
        return f[treepath].arrays(library="np")
    except Exception:
        return None


def count_entries(fname, treepath):
    try:
        import uproot
        f = uproot.open(fname)
        return f[treepath].num_entries
    except Exception:
        return 0


def detect_unit_and_to_nm(arr_flat):
    """
    Replicate the boundary-check logic from compare_runs.py section 5.

    Returns (wl_nm, unit_label) where unit_label is 'nm', 'eV', or 'µm'.
    Returns (None, None) if the median doesn't match any known range.
    """
    HC = 1239.84193  # eV·nm
    med = np.median(arr_flat)
    if 100.0 < med < 200.0:
        return arr_flat.copy(), "nm"
    elif 8.0 < med < 11.0:
        return HC / arr_flat, "eV"
    elif 0.1 < med < 0.2:
        return arr_flat * 1000.0, "µm"
    return None, None


def z_score(n_a, n_b, n_primary_a, n_primary_b):
    """Reproduce the statistical z-score used in compare_runs.py."""
    if n_primary_a == 0 or n_primary_b == 0:
        return 0.0
    rate_a = n_a / n_primary_a
    rate_b = n_b / n_primary_b
    sigma_a = math.sqrt(n_a) / n_primary_a if n_a > 0 else 0.0
    sigma_b = math.sqrt(n_b) / n_primary_b if n_b > 0 else 0.0
    sigma_combined = math.sqrt(sigma_a**2 + sigma_b**2)
    return abs(rate_b - rate_a) / sigma_combined if sigma_combined > 0 else 0.0


# ── load_tree / count_entries error handling ──────────────────────────────────

class TestLoadTree:
    def test_returns_none_on_missing_file(self):
        result = load_tree("/nonexistent/file.root", "SomeTree")
        assert result is None

    def test_returns_none_on_bad_treepath(self, tmp_path):
        # uproot.open on a non-ROOT file raises; should return None
        fake = tmp_path / "bad.root"
        fake.write_bytes(b"not a root file")
        result = load_tree(str(fake), "SomeTree")
        assert result is None

    def test_returns_dict_on_mocked_tree(self):
        mock_arr = {"wl": np.array([127.0, 128.0, 129.0])}
        mock_tree = MagicMock()
        mock_tree.arrays.return_value = mock_arr
        mock_file = MagicMock()
        mock_file.__getitem__ = MagicMock(return_value=mock_tree)
        with patch("uproot.open", return_value=mock_file):
            result = load_tree("dummy.root", "Primary")
        assert result is not None
        assert "wl" in result


class TestCountEntries:
    def test_returns_zero_on_missing_file(self):
        assert count_entries("/nonexistent/file.root", "SomeTree") == 0

    def test_returns_count_on_mocked_tree(self):
        mock_tree = MagicMock()
        mock_tree.num_entries = 9999
        mock_file = MagicMock()
        mock_file.__getitem__ = MagicMock(return_value=mock_tree)
        with patch("uproot.open", return_value=mock_file):
            result = count_entries("dummy.root", "Primary")
        assert result == 9999


# ── Boundary detection unit tests ─────────────────────────────────────────────

class TestDetectUnitAndToNm:
    def test_nm_array_detected(self):
        arr = np.linspace(120.0, 140.0, 100)
        wl_nm, label = detect_unit_and_to_nm(arr)
        assert label == "nm"
        np.testing.assert_array_almost_equal(wl_nm, arr)

    def test_ev_array_detected(self):
        # 9.69 eV ≈ 128 nm
        arr = np.full(100, 9.69)
        wl_nm, label = detect_unit_and_to_nm(arr)
        assert label == "eV"
        expected = 1239.84193 / 9.69
        assert abs(np.median(wl_nm) - expected) < 0.1

    def test_um_array_detected(self):
        arr = np.full(100, 0.128)  # 128 nm in µm
        wl_nm, label = detect_unit_and_to_nm(arr)
        assert label == "µm"
        np.testing.assert_allclose(wl_nm, arr * 1000.0)

    def test_unknown_range_returns_none(self):
        arr = np.full(100, 5000.0)
        wl_nm, label = detect_unit_and_to_nm(arr)
        assert wl_nm is None
        assert label is None

    def test_nm_boundary_pass(self):
        # All within [115, 145]
        arr = np.linspace(115.5, 144.5, 500)
        wl_nm, _ = detect_unit_and_to_nm(arr)
        assert np.all(wl_nm >= 115) and np.all(wl_nm <= 145)

    def test_nm_boundary_fail_detects_overflow(self):
        arr = np.concatenate([np.linspace(120, 140, 990), [110.0, 150.0, 160.0, 105.0, 148.0]])
        wl_nm, _ = detect_unit_and_to_nm(arr)
        n_below = np.sum(wl_nm < 115)
        n_above = np.sum(wl_nm > 145)
        assert n_below > 0 or n_above > 0

    def test_ev_converts_correctly_to_vuv_range(self):
        # 8.55–10.78 eV → ~145–115 nm; allow 0.1 nm tolerance at boundaries
        ev_vals = np.linspace(8.55, 10.78, 13)
        wl_nm, label = detect_unit_and_to_nm(ev_vals)
        assert label == "eV"
        assert np.all(wl_nm >= 114.9) and np.all(wl_nm <= 145.1)

    def test_um_converts_correctly_to_vuv_range(self):
        um_vals = np.linspace(0.115, 0.145, 13)
        wl_nm, label = detect_unit_and_to_nm(um_vals)
        assert label == "µm"
        assert np.all(wl_nm >= 115) and np.all(wl_nm <= 145)


# ── Statistical z-score ───────────────────────────────────────────────────────

class TestZScore:
    def test_identical_rates_give_zero(self):
        z = z_score(100, 100, 1000, 1000)
        assert z == pytest.approx(0.0)

    def test_z_below_two_is_pass(self):
        # Validation: mono=1.4434, spec=1.4260, each ±0.012 → z≈1.03
        n_primary = 10000
        n_wls_mono = 14434
        n_wls_spec = 14260
        z = z_score(n_wls_mono, n_wls_spec, n_primary, n_primary)
        assert z < 2.0, f"z={z:.3f} should be < 2 (PASS threshold)"

    def test_sipm_comparison_from_commit(self):
        # mono=0.0307±0.0018, spec=0.0322±0.0018, z≈0.60
        n_primary = 10000
        n_hits_mono = 307
        n_hits_spec = 322
        z = z_score(n_hits_mono, n_hits_spec, n_primary, n_primary)
        assert z < 2.0

    def test_zero_primary_returns_zero(self):
        assert z_score(100, 100, 0, 1000) == 0.0
        assert z_score(100, 100, 1000, 0) == 0.0

    def test_large_discrepancy_exceeds_two_sigma(self):
        # Dramatically different rates should give z > 2
        z = z_score(5000, 100, 10000, 10000)
        assert z > 2.0, f"z={z:.3f} should be > 2 for very different rates"

    def test_symmetry(self):
        z1 = z_score(1000, 2000, 10000, 10000)
        z2 = z_score(2000, 1000, 10000, 10000)
        assert z1 == pytest.approx(z2, rel=1e-9)

    def test_zero_hits_in_one_branch(self):
        # zero hits → sigma_b=0 so combined sigma = sigma_a only
        z = z_score(100, 0, 10000, 10000)
        # rate_a=0.01, rate_b=0, sigma_a=sqrt(100)/10000=0.001, sigma_b=0
        # z = 0.01/0.001 = 10
        assert z == pytest.approx(10.0, rel=1e-6)


# ── Energy conversion math (eV → nm, MeV → eV) ───────────────────────────────

class TestEnergyConversion:
    HC = 1239.84193  # eV·nm

    def test_ev_to_nm_128(self):
        """128 nm → 9.686 eV."""
        eV = self.HC / 128.0
        assert abs(eV - 9.686) < 0.01

    def test_mev_scale_factor(self):
        """1 eV = 1e-6 MeV."""
        assert 9.7242e-6 == pytest.approx(9.7242 * 1e-6)

    @pytest.mark.parametrize("wl_nm, expected_ev", [
        (145.0, 1239.84 / 145.0),  # low-energy end
        (128.0, 1239.84 / 128.0),  # Gaussian peak
        (115.0, 1239.84 / 115.0),  # high-energy end
    ])
    def test_hc_over_lambda(self, wl_nm, expected_ev):
        assert self.HC / wl_nm == pytest.approx(expected_ev, rel=1e-3)

    def test_macro_point_peak_energy_in_nm(self):
        """The peak hist/point (9.7242e-6 MeV) converts to ≈127.5 nm."""
        energy_mev = 9.7242e-6
        energy_ev = energy_mev * 1e6
        wl_nm = self.HC / energy_ev
        assert 125.0 < wl_nm < 130.0, f"Peak wavelength {wl_nm:.2f} nm unexpected"
