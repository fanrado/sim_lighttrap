"""
Tests for the forward-direction flag on MyLeakDetector counters.

Feature (commit 12d4324, beads sim_lighttrap-075):
  MyLeakDetector::ProcessHits records an explicit integer 'forward' column
  (index 7) alongside the existing cosTheta (index 6):
      forward = (mom.z() > 0.) ? 1 : 0;
  1 = forward (out of layer 1, mom.z()>0), 0 = backward (e.g. Vikuiti-reflected
  light travelling back -z).  Both directions are still recorded; the flag only
  tags them for trivial selection in analysis.  It is filled with
  FillNtupleIColumn(fNtupleID, 7, forward), so ntuples 6/7/8
  (SecondLayerBackplane, FirstLayerBackplane, FirstLayerEdges) each gain a
  CreateNtupleIColumn("forward") before their FinishNtuple.

These are static source-parsing tests (the Geant4 C++ cannot be compiled in this
environment), mirroring tests/test_pass_through_counter.py.
"""

import re

import pytest

DETECTOR_CC = "src/detector.cc"
RUN_CC = "src/run.cc"


def read(path):
    with open(path) as fh:
        return fh.read()


@pytest.fixture(scope="module")
def det_cc():
    return read(DETECTOR_CC)


@pytest.fixture(scope="module")
def run_cc():
    return read(RUN_CC)


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def leak_processhits_body(code):
    m = re.search(
        r"MyLeakDetector::ProcessHits\s*\([^)]*\)\s*\{(.*?)\n\}", code, re.DOTALL
    )
    assert m, "MyLeakDetector::ProcessHits definition not found"
    return m.group(1)


# ── detector.cc: forward computed from momentum-z sign ───────────────────────

def test_forward_computed_from_momentum_z_sign(det_cc):
    """forward is 1 when mom.z() > 0, else 0."""
    code = strip_comments(det_cc)
    m = re.search(
        r"G4int\s+forward\s*=\s*\(\s*mom\.z\(\)\s*>\s*0\.?\s*\)\s*\?\s*1\s*:\s*0\s*;",
        code,
    )
    assert m, "expected 'G4int forward = (mom.z() > 0.) ? 1 : 0;'"


def test_forward_filled_into_column_7(det_cc):
    """forward must be written to ntuple column index 7 as an integer."""
    code = strip_comments(det_cc)
    assert re.search(
        r"FillNtupleIColumn\s*\(\s*fNtupleID\s*,\s*7\s*,\s*forward\s*\)", code
    ), "forward should be filled with FillNtupleIColumn(fNtupleID, 7, forward)"


def test_forward_fill_is_after_costheta(det_cc):
    """Regression: cosTheta (col 6) is still filled, and forward (col 7) follows it."""
    body = leak_processhits_body(strip_comments(det_cc))
    cos_pos = body.find("FillNtupleDColumn(fNtupleID, 6, cosTheta)")
    fwd_pos = body.find("FillNtupleIColumn(fNtupleID, 7, forward)")
    assert cos_pos != -1, "cosTheta (col 6) fill missing"
    assert fwd_pos != -1, "forward (col 7) fill missing"
    assert fwd_pos > cos_pos, "forward (col 7) should be filled after cosTheta (col 6)"


def test_both_directions_still_recorded(det_cc):
    """The flag only tags direction — the hit must be recorded unconditionally (no direction gate)."""
    body = leak_processhits_body(strip_comments(det_cc))
    # AddNtupleRow must not sit behind an if(forward)/if(mom.z()...) guard.
    assert re.search(r"AddNtupleRow\s*\(\s*fNtupleID\s*\)", body), "AddNtupleRow missing"
    assert not re.search(
        r"if\s*\(\s*forward\s*\)[^;{]*AddNtupleRow", body
    ), "AddNtupleRow must not be gated on the forward flag — both directions are recorded"


# ── run.cc: ntuples 6/7/8 each gain the forward column ───────────────────────

@pytest.mark.parametrize(
    "name,finish_id",
    [
        ("SecondLayerBackplane", 6),
        ("FirstLayerBackplane", 7),
        ("FirstLayerEdges", 8),
    ],
)
def test_counter_ntuple_has_forward_int_column(run_cc, name, finish_id):
    """Each MyLeakDetector-backed ntuple declares an int 'forward' column before FinishNtuple."""
    code = strip_comments(run_cc)
    m = re.search(
        rf'CreateNtuple\s*\(\s*"{name}".*?FinishNtuple\s*\(\s*{finish_id}\s*\)',
        code,
        re.DOTALL,
    )
    assert m, f"could not isolate the {name} ntuple block"
    block = m.group(0)
    assert re.search(
        r'CreateNtupleIColumn\s*\(\s*"forward"\s*\)', block
    ), f'{name} ntuple should declare CreateNtupleIColumn("forward")'
    # forward is the 8th (last) column: eventID + 6 D + forward.
    names = re.findall(r'CreateNtuple[IDS]Column\s*\(\s*"([^"]+)"', block)
    assert names[-1] == "forward", f"{name}: forward should be the last column, got {names}"


def test_forward_column_only_on_leakdetector_ntuples(run_cc):
    """The forward column is scoped to ntuples 6/7/8; SiPM ntuples 0/1 must not gain it."""
    code = strip_comments(run_cc)
    for name, finish_id in [("SiPMPhotons", 0), ("SiPMHits", 1)]:
        m = re.search(
            rf'CreateNtuple\s*\(\s*"{name}".*?FinishNtuple\s*\(\s*{finish_id}\s*\)',
            code,
            re.DOTALL,
        )
        assert m, f"could not isolate {name}"
        assert '"forward"' not in m.group(0), f"{name} should NOT have a forward column"
