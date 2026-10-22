"""
Tests for analysis/analyze_efficiency.py (commit b71276a).

The script computes WLS / SiPM-collection efficiencies from a ROOT file. Its
pure-Python helpers — wilson() (binomial ratio + 1-sigma error) and pct()
(percentage formatting) — carry the logic and are tested here.

The module does `import ROOT` at top level (PyROOT is unavailable in CI), so we
inject a stub `ROOT` module into sys.modules and load the real file by path.
This exercises the actual functions, not replicas. The relocation of
compare_runs.py into analysis/ is checked structurally.
"""

import importlib.util
import math
import os
import sys
from unittest.mock import MagicMock

import pytest

ANALYSIS_DIR = "analysis"
SCRIPT = os.path.join(ANALYSIS_DIR, "analyze_efficiency.py")


# ── load the real module with a stubbed ROOT dependency ──────────────────────

@pytest.fixture(scope="module")
def mod():
    sys.modules.setdefault("ROOT", MagicMock())
    spec = importlib.util.spec_from_file_location("analyze_efficiency", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ── wilson(): binomial ratio with symmetric 1-sigma error ────────────────────

def test_wilson_zero_denominator_is_nan(mod):
    p, e = mod.wilson(0, 0)
    assert math.isnan(p) and math.isnan(e), "n==0 must yield (nan, nan)"


def test_wilson_basic_ratio_and_error(mod):
    # p = 25/100 = 0.25 ; sigma = sqrt(0.25*0.75/100) = 0.043301...
    p, e = mod.wilson(25, 100)
    assert p == pytest.approx(0.25)
    assert e == pytest.approx(math.sqrt(0.25 * 0.75 / 100.0))


def test_wilson_z_scales_error(mod):
    _, e1 = mod.wilson(25, 100, z=1.0)
    _, e2 = mod.wilson(25, 100, z=2.0)
    assert e2 == pytest.approx(2.0 * e1), "z should linearly scale the error"


def test_wilson_p_zero_and_one_give_zero_error(mod):
    p0, e0 = mod.wilson(0, 50)
    p1, e1 = mod.wilson(50, 50)
    assert p0 == 0.0 and e0 == pytest.approx(0.0)
    assert p1 == 1.0 and e1 == pytest.approx(0.0)


def test_wilson_k_exceeds_n_error_floored_to_zero(mod):
    """k>n (e.g. blue/pTP ratio >1) → p>1, variance floored at 0 (indicative)."""
    p, e = mod.wilson(150, 100)
    assert p == pytest.approx(1.5)
    assert e == pytest.approx(0.0), "negative variance must be clamped to 0, not NaN"


# ── pct(): percentage formatting ─────────────────────────────────────────────

def test_pct_nan_returns_na(mod):
    assert mod.pct(float("nan"), float("nan")).strip() == "n/a"


def test_pct_formats_percentage(mod):
    s = mod.pct(0.25, 0.0433)
    assert "25.000%" in s
    assert "+/-" in s
    assert "4.330%" in s


# ── NameMap constants match the data model (src/namemap) ─────────────────────

def test_material_codes(mod):
    assert mod.MAT_PTP == 1, "pTP first-layer material code"
    assert mod.MAT_BLUEWLS == 3, "blue-WLS second-layer material code"


# ── relocation of the analysis scripts into analysis/ ────────────────────────

def test_scripts_live_in_analysis_dir():
    assert os.path.isfile(SCRIPT), "analyze_efficiency.py should be in analysis/"
    assert os.path.isfile(os.path.join(ANALYSIS_DIR, "compare_runs.py")), (
        "compare_runs.py should have moved into analysis/"
    )


def test_compare_runs_not_left_at_repo_root():
    assert not os.path.isfile("compare_runs.py"), (
        "compare_runs.py should no longer be at the repo root after the move"
    )
