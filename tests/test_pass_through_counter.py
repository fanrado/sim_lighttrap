"""
Tests for the pass-through photon counter and first-layer exit ntuple.

Feature (commit 04d865c, beads sim_lighttrap-ahs):
  MyLeakDetector gains a killTrack flag. Terminal counters (killTrack=true, the
  default) still SetTrackStatus(fStopAndKill); pass-through counters
  (killTrack=false) record the hit but let the photon continue downstream. Each
  hit now also records cosTheta (momentum-z direction cosine) so analysis can
  separate forward-going from back-reflected photons. A new ntuple 7
  (FirstLayerExit) counts photons crossing out of the first layer into the LAr
  gap, wired to a non-killing MyLeakDetector on the LAr-gap slab.

These are static source-parsing tests (the Geant4 C++ cannot be compiled in this
environment), mirroring tests/test_cmakelists_geant4.py.
"""

import re

import pytest

DETECTOR_HH = "include/detector.hh"
DETECTOR_CC = "src/detector.cc"
RUN_CC = "src/run.cc"
CONSTRUCTION_CC = "src/construction.cc"


# ── helpers ───────────────────────────────────────────────────────────────────

def read(path):
    with open(path) as fh:
        return fh.read()


@pytest.fixture(scope="module")
def hh():
    return read(DETECTOR_HH)


@pytest.fixture(scope="module")
def det_cc():
    return read(DETECTOR_CC)


@pytest.fixture(scope="module")
def run_cc():
    return read(RUN_CC)


@pytest.fixture(scope="module")
def cons_cc():
    return read(CONSTRUCTION_CC)


def strip_comments(text):
    """Remove // line comments and /* */ block comments for structural checks."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


# ── header: killTrack flag on MyLeakDetector ─────────────────────────────────

def test_ctor_declares_killtrack_param_defaulting_true(hh):
    """MyLeakDetector(name, ntupleID, killTrack=true) — default preserves old behaviour."""
    m = re.search(r"MyLeakDetector\s*\(([^)]*)\)\s*;", hh)
    assert m, "MyLeakDetector constructor declaration not found in header"
    params = m.group(1)
    assert "G4bool killTrack" in params, "killTrack parameter missing from constructor"
    assert re.search(r"G4bool\s+killTrack\s*=\s*true", params), (
        "killTrack should default to true so existing terminal counters are unchanged"
    )


def test_killtrack_member_declared(hh):
    """A G4bool fKillTrack member must back the flag."""
    assert re.search(r"G4bool\s+fKillTrack\s*;", hh), "fKillTrack member missing"


# ── detector.cc: gating + cosTheta ───────────────────────────────────────────

def test_ctor_initializes_killtrack(det_cc):
    """The constructor init list must initialize fKillTrack from the argument."""
    m = re.search(
        r"MyLeakDetector::MyLeakDetector\s*\([^)]*\)\s*:([^{]*)\{", det_cc, re.DOTALL
    )
    assert m, "MyLeakDetector constructor definition not found"
    assert "fKillTrack(killTrack)" in m.group(1), (
        "constructor should initialize fKillTrack(killTrack)"
    )


def leak_processhits_body(code):
    """Isolate MyLeakDetector::ProcessHits body (not the SiPM SD, which also kills)."""
    m = re.search(
        r"MyLeakDetector::ProcessHits\s*\([^)]*\)\s*\{(.*?)\n\}", code, re.DOTALL
    )
    assert m, "MyLeakDetector::ProcessHits definition not found"
    return m.group(1)


def test_kill_is_gated_behind_killtrack(det_cc):
    """SetTrackStatus(fStopAndKill) must only run when fKillTrack is set."""
    body = leak_processhits_body(strip_comments(det_cc))
    m = re.search(
        r"if\s*\(\s*fKillTrack\s*\)\s*(\{[^}]*\}|[^;]*;)", body, re.DOTALL
    )
    assert m, "kill should be guarded by if(fKillTrack)"
    assert "fStopAndKill" in m.group(1), (
        "the fKillTrack branch must contain SetTrackStatus(fStopAndKill)"
    )
    # Within MyLeakDetector, the kill must not also happen unconditionally.
    kills = re.findall(r"SetTrackStatus\s*\(\s*fStopAndKill\s*\)", body)
    assert len(kills) == 1, (
        "expected exactly one SetTrackStatus(fStopAndKill) in MyLeakDetector::"
        f"ProcessHits, found {len(kills)}"
    )


def test_costheta_computed_from_momentum_z(det_cc):
    """cosTheta is the +z direction cosine of the pre-step momentum."""
    code = strip_comments(det_cc)
    assert re.search(
        r"cosTheta\s*=\s*mom\.unit\(\)\.z\(\)", code
    ), "cosTheta should be mom.unit().z()"


def test_costheta_filled_into_column_6(det_cc):
    """cosTheta must be written to ntuple column index 6."""
    code = strip_comments(det_cc)
    assert re.search(
        r"FillNtupleDColumn\s*\(\s*fNtupleID\s*,\s*6\s*,\s*cosTheta\s*\)", code
    ), "cosTheta should be filled into column 6 of fNtupleID"


def test_processhits_still_records_position_and_wavelength(det_cc):
    """Regression: existing columns 0–5 (evt,x,y,z,t,wl) still filled."""
    code = strip_comments(det_cc)
    for idx, needle in [(0, "evt"), (5, "wl")]:
        assert re.search(
            rf"FillNtuple[ID]Column\s*\(\s*fNtupleID\s*,\s*{idx}\s*,", code
        ), f"column {idx} ({needle}) fill missing"


# ── run.cc: ntuple 7 FirstLayerBackplane ─────────────────────────────────────
# (Renamed from FirstLayerExit in commit 53f5245 / beads sim_lighttrap-amr; the
#  ntuple id and column layout are unchanged, only the name.)

def test_firstlayerexit_ntuple_created(run_cc):
    assert re.search(
        r'CreateNtuple\s*\(\s*"FirstLayerBackplane"', run_cc
    ), 'CreateNtuple("FirstLayerBackplane", ...) missing'


def test_firstlayerexit_finished_as_id_7(run_cc):
    assert re.search(r"FinishNtuple\s*\(\s*7\s*\)", run_cc), "FinishNtuple(7) missing"


def test_firstlayerexit_has_seven_columns(run_cc):
    """FirstLayerBackplane ntuple: eventID + fX,fY,fZ,fT,fwl,fcosTheta + forward = 8 columns.

    The 'forward' int column (index 7) was added in commit 12d4324
    (beads sim_lighttrap-075); ntuples 6/7/8 now carry 2 I + 6 D columns.
    """
    code = strip_comments(run_cc)
    # Isolate the block from the FirstLayerBackplane CreateNtuple to its FinishNtuple(7).
    m = re.search(
        r'CreateNtuple\s*\(\s*"FirstLayerBackplane".*?FinishNtuple\s*\(\s*7\s*\)',
        code,
        re.DOTALL,
    )
    assert m, "could not isolate the FirstLayerBackplane ntuple block"
    block = m.group(0)
    icols = re.findall(r"CreateNtupleIColumn", block)
    dcols = re.findall(r"CreateNtupleDColumn", block)
    assert len(icols) == 2, f"expected 2 I columns (eventID, forward), found {len(icols)}"
    assert len(dcols) == 6, f"expected 6 D columns, found {len(dcols)}"
    assert "fcosTheta" in block, "fcosTheta column missing from FirstLayerBackplane ntuple"
    assert "forward" in block, "forward column missing from FirstLayerBackplane ntuple"


def test_ntuple_6_also_gained_costheta(run_cc):
    """The terminal ntuple 6 also records the new fcosTheta column."""
    code = strip_comments(run_cc)
    m = re.search(
        r'CreateNtupleDColumn\s*\(\s*"fcosTheta".*?FinishNtuple\s*\(\s*6\s*\)',
        code,
        re.DOTALL,
    )
    assert m, "ntuple 6 should also add the fcosTheta column before FinishNtuple(6)"


# ── construction.cc: wiring of the pass-through counter ──────────────────────

def test_firstlayerexit_sd_is_non_killing_on_ntuple_7(cons_cc):
    """FirstLayerBackplaneDetector wired to ntuple 7 with killTrack=false.

    The SD was renamed FirstLayerExitDetector -> FirstLayerBackplaneDetector in
    commit 1ba18e1 (beads sim_lighttrap-d8y); ntuple id and killTrack unchanged.
    """
    code = strip_comments(cons_cc)
    m = re.search(
        r'new\s+MyLeakDetector\s*\(\s*"FirstLayerBackplaneDetector"\s*,\s*7\s*,\s*false\s*\)',
        code,
    )
    assert m, 'expected new MyLeakDetector("FirstLayerBackplaneDetector", 7, false)'


def test_backplane_counter_remains_terminal_on_ntuple_6(cons_cc):
    """Regression: the backplane leak counter is still a terminal (killing) SD on ntuple 6."""
    code = strip_comments(cons_cc)
    m = re.search(
        r'new\s+MyLeakDetector\s*\(\s*"BackplaneLeakDetector"\s*,\s*6\s*(,\s*false\s*)?\)',
        code,
    )
    assert m, 'BackplaneLeakDetector(..., 6) construction not found'
    assert m.group(1) is None, (
        "backplane counter must stay terminal (must not pass killTrack=false)"
    )


def test_gap_detector_volume_gets_the_pass_through_sd(cons_cc):
    """The LAr-gap slab logical volume must receive the pass-through SD."""
    code = strip_comments(cons_cc)
    assert re.search(
        r"logicFirstLayerExitDet\s*->\s*SetSensitiveDetector\s*\(\s*gapEntryDet\s*\)",
        code,
    ), "logicFirstLayerExitDet should be assigned the FirstLayerExit SD"


def test_gap_detector_placed_at_acrylic_back_face(cons_cc):
    """The gap counter is a thin LAr slab in the gap, standing off the acrylic back face.

    Repositioned in commit 1ba18e1 (beads sim_lighttrap-d8y): its front face now
    stands kFirstLayerBackplaneStandoff (0.01 mm) behind the acrylic back (+z) face,
    so kGapDetCenterZ = kUVAcrylBackZ + kFirstLayerBackplaneStandoff + kGapDetThick/2.
    """
    code = strip_comments(cons_cc)
    assert re.search(
        r"kGapDetCenterZ\s*=\s*kUVAcrylBackZ\s*\+\s*kFirstLayerBackplaneStandoff"
        r"\s*\+\s*kGapDetThick\s*/\s*2\.",
        code,
    ), "gap detector should stand off the UV-acrylic back face by kFirstLayerBackplaneStandoff"
    # Placed at that z, built from worldMat (LAr) so it is optically invisible.
    m = re.search(
        r"physFirstLayerExitDet\s*=\s*new\s+G4PVPlacement\((.*?)\)\s*;",
        code,
        re.DOTALL,
    )
    assert m, "physFirstLayerExitDet placement not found"
    assert "kGapDetCenterZ" in m.group(1), "gap detector must be placed at kGapDetCenterZ"
    assert re.search(
        r"logicFirstLayerExitDet\s*=\s*new\s+G4LogicalVolume\([^)]*worldMat", code
    ), "gap detector slab should be built from worldMat (LAr) to stay optically invisible"
