"""
Tests for the TIR-aware first-layer backplane counter standoff in construction.cc.

Feature (commit 1ba18e1, beads sim_lighttrap-d8y):
  A new constant kFirstLayerBackplaneStandoff (0.01 mm) offsets the first-layer
  backplane pass-through counter's front face behind the first-layer back (+z)
  face (the UV-acrylic back face).  Photons TIR-reflected at that back face never
  cross the standoff, so only photons that genuinely escape layer 1 are counted.
  The counter/SD is relabelled FirstLayerBackplane(Detector). killTrack stays
  false (still a pass-through counter). ntuple id stays 7.

  Placement becomes:
    kGapDetCenterZ = kUVAcrylBackZ + kFirstLayerBackplaneStandoff + kGapDetThick/2.

These are static source-parsing tests (the Geant4 C++ cannot be compiled in this
environment), mirroring tests/test_pass_through_counter.py.
"""

import re

import pytest

CONSTRUCTION_CC = "src/construction.cc"


def read(path):
    with open(path) as fh:
        return fh.read()


@pytest.fixture(scope="module")
def cons_cc():
    return read(CONSTRUCTION_CC)


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


# ── the standoff constant ────────────────────────────────────────────────────

def test_standoff_constant_declared_as_0_01mm(cons_cc):
    """kFirstLayerBackplaneStandoff must be declared as 0.01*mm."""
    code = strip_comments(cons_cc)
    m = re.search(
        r"G4double\s+kFirstLayerBackplaneStandoff\s*=\s*0\.01\s*\*\s*mm", code
    )
    assert m, "expected 'const G4double kFirstLayerBackplaneStandoff = 0.01*mm'"


def test_standoff_is_positive_and_small(cons_cc):
    """Regression: the standoff must be a small positive value (< the 0.1 mm slab)."""
    code = strip_comments(cons_cc)
    m = re.search(
        r"kFirstLayerBackplaneStandoff\s*=\s*([0-9.]+)\s*\*\s*mm", code
    )
    assert m, "standoff constant not found"
    val = float(m.group(1))
    assert 0.0 < val < 0.1, f"standoff should be a small positive offset, got {val} mm"


# ── placement uses the standoff ──────────────────────────────────────────────

def test_gap_center_includes_standoff(cons_cc):
    """kGapDetCenterZ must add the standoff between the back face and the slab half-thickness."""
    code = strip_comments(cons_cc)
    m = re.search(
        r"kGapDetCenterZ\s*=\s*kUVAcrylBackZ\s*\+\s*kFirstLayerBackplaneStandoff"
        r"\s*\+\s*kGapDetThick\s*/\s*2\.",
        code,
    )
    assert m, (
        "kGapDetCenterZ should be kUVAcrylBackZ + kFirstLayerBackplaneStandoff + kGapDetThick/2."
    )


def test_gap_center_no_longer_flush(cons_cc):
    """The old flush placement (no standoff term) must be gone."""
    code = strip_comments(cons_cc)
    assert not re.search(
        r"kGapDetCenterZ\s*=\s*kUVAcrylBackZ\s*\+\s*kGapDetThick\s*/\s*2\.\s*;",
        code,
    ), "old flush placement 'kUVAcrylBackZ + kGapDetThick/2.' should be replaced by the standoff form"


# ── counter stays a pass-through (non-killing) SD on ntuple 7 ─────────────────

def test_counter_still_pass_through_on_ntuple_7(cons_cc):
    """Repositioning must not change the pass-through semantics: killTrack=false, ntuple 7."""
    code = strip_comments(cons_cc)
    m = re.search(
        r'new\s+MyLeakDetector\s*\(\s*"FirstLayerBackplaneDetector"\s*,\s*7\s*,\s*false\s*\)',
        code,
    )
    assert m, 'expected pass-through SD: MyLeakDetector("FirstLayerBackplaneDetector", 7, false)'


def test_old_sd_name_removed(cons_cc):
    """The SD instance was relabelled; the old name must be gone."""
    assert '"FirstLayerExitDetector"' not in cons_cc, (
        'stale SD name "FirstLayerExitDetector" should be renamed to FirstLayerBackplaneDetector'
    )


# ── slab stays optically invisible (built from LAr / worldMat) ───────────────

def test_gap_slab_still_built_from_worldmat(cons_cc):
    """Regression: the counter slab must stay LAr (worldMat) so it introduces no optical boundary."""
    code = strip_comments(cons_cc)
    assert re.search(
        r"logicFirstLayerExitDet\s*=\s*new\s+G4LogicalVolume\([^)]*worldMat", code
    ), "gap counter slab should remain worldMat (LAr) to stay optically invisible"
