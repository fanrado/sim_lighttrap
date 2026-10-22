"""
Tests for the output-ntuple data model in src/run.cc (first layer + PMT).

  0 Energy, 1 Primary, 2 WLSPhoton, 3 OpticalValidation,
  4 FirstLayerBackplane, 5 FirstLayerEdges, 6 PMTPhotons, 7 PMTHits

The fill sites in event.cc / tracking.cc / detector.cc / construction.cc must
use the same ids as the CreateNtuple/FinishNtuple definitions.
"""

import re

import pytest

RUN_CC = "src/run.cc"


def read(path):
    with open(path) as fh:
        return fh.read()


def strip_comments(code):
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", code)


@pytest.fixture(scope="module")
def run_cc():
    return strip_comments(read(RUN_CC))


def ntuple_ids(code):
    """{name: id} from CreateNtuple("name", ...) ... FinishNtuple(id) blocks."""
    out = {}
    for m in re.finditer(r'CreateNtuple\s*\(\s*"([^"]+)"', code):
        fin = re.search(r"FinishNtuple\s*\(\s*(\d+)\s*\)", code[m.end():])
        assert fin, f"no FinishNtuple after CreateNtuple({m.group(1)})"
        out[m.group(1)] = int(fin.group(1))
    return out


EXPECTED = {
    "Energy": 0, "Primary": 1, "WLSPhoton": 2, "OpticalValidation": 3,
    "FirstLayerBackplane": 4, "FirstLayerEdges": 5, "PMTPhotons": 6, "PMTHits": 7,
}


def test_ntuple_names_and_ids(run_cc):
    assert ntuple_ids(run_cc) == EXPECTED


def test_finishntuple_ids_are_unique_and_contiguous(run_cc):
    ids = [int(x) for x in re.findall(r"FinishNtuple\s*\(\s*(\d+)\s*\)", run_cc)]
    assert len(ids) == len(set(ids)), f"duplicate ntuple ids: {ids}"
    assert sorted(ids) == list(range(len(ids))), f"ids not contiguous from 0: {sorted(ids)}"


def test_no_two_layer_trees(run_cc):
    for name in ("SiPMPhotons", "SiPMHits", "SecondLayerBackplane"):
        assert f'"{name}"' not in run_cc, f"two-layer tree {name} must not exist on this branch"


def columns(code, name):
    start = code.index(f'CreateNtuple("{name}"')
    block = code[start:code.index("FinishNtuple", start)]
    return re.findall(r'CreateNtuple[IDS]Column\s*\(\s*"([^"]+)"', block)


@pytest.mark.parametrize("name", ["FirstLayerBackplane", "FirstLayerEdges"])
def test_counter_columns(run_cc, name):
    assert columns(run_cc, name) == ["eventID", "fX", "fY", "fZ", "fT", "fwl", "fcosTheta", "forward"]


@pytest.mark.parametrize("name", ["PMTPhotons", "PMTHits"])
def test_pmt_columns(run_cc, name):
    assert columns(run_cc, name) == ["eventID", "fX", "fY", "fZ", "fT", "fwl", "fcosTheta", "primary"]


# ── fill sites use the same ids ───────────────────────────────────────────────

def fill_ids(path):
    code = strip_comments(read(path))
    return sorted({int(x) for x in re.findall(r"AddNtupleRow\s*\(\s*(\d+)\s*\)", code)})


def test_event_action_fills_energy_and_primary():
    assert fill_ids("src/event.cc") == [EXPECTED["Energy"], EXPECTED["Primary"]]


def test_tracking_action_fills_wls_and_validation():
    assert fill_ids("src/tracking.cc") == [EXPECTED["WLSPhoton"], EXPECTED["OpticalValidation"]]


def test_pmt_detector_fills_pmt_trees():
    code = strip_comments(read("src/detector.cc"))
    body = code[code.index("MyPMTDetector::ProcessHits"):]
    assert sorted({int(x) for x in re.findall(r"AddNtupleRow\s*\(\s*(\d+)\s*\)", body)}) == \
        [EXPECTED["PMTPhotons"], EXPECTED["PMTHits"]]


def test_first_layer_counters_wired_to_their_ids():
    code = strip_comments(read("src/construction.cc"))
    sd = code[code.index("ConstructSDandField"):]
    assert re.search(r'MyLeakDetector\s*\(\s*"FirstLayerBackplaneDetector"\s*,\s*4\s*,\s*false\s*\)', sd)
    assert re.search(r'MyLeakDetector\s*\(\s*"FirstLayerEdgeDetector"\s*,\s*5\s*,\s*false\s*\)', sd)
    assert "BackplaneLeakDetector" not in sd


# ── end-of-run summary (viewer-independent validation) ────────────────────────

def test_run_summary_counters_wired():
    hh = read("include/counters.hh")
    for f in ("nPrimary", "nWLSpTP", "nLayer1Forward", "nLayer1Edges", "nPMTPhotons", "nPMTDirect", "nPMTHits"):
        assert f in hh, f"RunCounters.{f} missing"
    run = strip_comments(read(RUN_CC))
    assert "RunCounters::Instance().Reset()" in run, "counters must be reset at BeginOfRunAction"
    assert "summary ============" in run and "WLS photons born in pTP" in run and "PMT hits (after QE)" in run
    assert "NO wavelength shifting" in run
    trk = strip_comments(read("src/tracking.cc"))
    assert "nWLSpTP" in trk
    det = strip_comments(read("src/detector.cc"))
    assert "nPMTPhotons" in det and "nPMTHits" in det and "nLayer1Forward" in det
    assert "/vis/viewer/rebuild" in read("mac/vis.mac")
