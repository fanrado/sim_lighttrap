"""
Tests for the 5-region output-ntuple data model in src/run.cc.

Feature (commit 53f5245, beads sim_lighttrap-amr):
  The output ROOT ntuples are restructured to reflect the five physical regions
  of the two-layer light trap:
    a) Primary              — primary particle info                (ntuple 3)
    b) FirstLayerBackplane  — photons through first-layer back face (ntuple 7,
                              renamed from FirstLayerExit)
    c) FirstLayerEdges      — NEW: photons at first-layer ±x edges  (ntuple 8)
    d) SecondLayerBackplane — Vikuiti backplane leak                (ntuple 6,
                              renamed from BackplaneLeak)
    e) SecondLayerEdges     — SiPM-detected photons (SiPMPhotons/SiPMHits ntuples 0/1)

  A documented ntuple-ID → region comment map heads MyRunAction::MyRunAction().
  The SiPM trees are named SiPMPhotons/SiPMHits (read by name in analyze_efficiency.py).

These are static source-parsing tests (the Geant4 C++ cannot be compiled in this
environment), mirroring tests/test_cmakelists_geant4.py and
tests/test_pass_through_counter.py.
"""

import re

import pytest

RUN_CC = "src/run.cc"


def read(path):
    with open(path) as fh:
        return fh.read()


@pytest.fixture(scope="module")
def run_cc():
    return read(RUN_CC)


def strip_comments(text):
    """Remove // line comments and /* */ block comments for structural checks."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def ntuple_block(code, name, finish_id):
    """Isolate the CreateNtuple("<name>", ...) ... FinishNtuple(<id>) block."""
    m = re.search(
        rf'CreateNtuple\s*\(\s*"{re.escape(name)}".*?FinishNtuple\s*\(\s*{finish_id}\s*\)',
        code,
        re.DOTALL,
    )
    return m.group(0) if m else None


# ── renames: old names must be gone ──────────────────────────────────────────

def test_old_firstlayerexit_name_removed(run_cc):
    """FirstLayerExit was renamed to FirstLayerBackplane."""
    assert not re.search(r'"FirstLayerExit"', run_cc), (
        'stale ntuple name "FirstLayerExit" still present; should be FirstLayerBackplane'
    )


def test_old_backplaneleak_name_removed(run_cc):
    """BackplaneLeak was renamed to SecondLayerBackplane."""
    assert not re.search(r'"BackplaneLeak"', run_cc), (
        'stale ntuple name "BackplaneLeak" still present; should be SecondLayerBackplane'
    )


# ── (d) SecondLayerBackplane — ntuple 6 (renamed, layout unchanged) ──────────

def test_secondlayerbackplane_created(run_cc):
    assert re.search(
        r'CreateNtuple\s*\(\s*"SecondLayerBackplane"', run_cc
    ), 'CreateNtuple("SecondLayerBackplane", ...) missing'


def test_secondlayerbackplane_is_id_6(run_cc):
    """SecondLayerBackplane must remain ntuple 6 to match the terminal SD wiring."""
    block = ntuple_block(strip_comments(run_cc), "SecondLayerBackplane", 6)
    assert block, "could not isolate SecondLayerBackplane ntuple block ending at FinishNtuple(6)"


def test_secondlayerbackplane_has_eight_columns(run_cc):
    """eventID + fX,fY,fZ,fT,fwl,fcosTheta + forward = 2 I columns + 6 D columns.

    The 'forward' int column (index 7) was added in commit 12d4324
    (beads sim_lighttrap-075).
    """
    block = ntuple_block(strip_comments(run_cc), "SecondLayerBackplane", 6)
    assert block, "SecondLayerBackplane block not found"
    assert len(re.findall(r"CreateNtupleIColumn", block)) == 2
    assert len(re.findall(r"CreateNtupleDColumn", block)) == 6
    assert "fcosTheta" in block
    assert "forward" in block


# ── (c) FirstLayerEdges — NEW ntuple 8 ───────────────────────────────────────

def test_firstlayeredges_created(run_cc):
    assert re.search(
        r'CreateNtuple\s*\(\s*"FirstLayerEdges"', run_cc
    ), 'CreateNtuple("FirstLayerEdges", ...) missing'


def test_firstlayeredges_finished_as_id_8(run_cc):
    assert re.search(r"FinishNtuple\s*\(\s*8\s*\)", run_cc), "FinishNtuple(8) missing"


def test_firstlayeredges_has_eight_columns(run_cc):
    """FirstLayerEdges: eventID + fX,fY,fZ,fT,fwl,fcosTheta + forward = 2 I + 6 D columns."""
    block = ntuple_block(strip_comments(run_cc), "FirstLayerEdges", 8)
    assert block, "could not isolate the FirstLayerEdges ntuple block"
    assert len(re.findall(r"CreateNtupleIColumn", block)) == 2, "expected 2 I columns (eventID, forward)"
    assert len(re.findall(r"CreateNtupleDColumn", block)) == 6, "expected 6 D columns"
    assert "fcosTheta" in block, "fcosTheta column missing from FirstLayerEdges ntuple"
    assert "forward" in block, "forward column missing from FirstLayerEdges ntuple"


def test_firstlayeredges_column_layout_matches_backplane(run_cc):
    """The new edge ntuple mirrors the backplane counters' column names/order (incl. forward)."""
    code = strip_comments(run_cc)
    block = ntuple_block(code, "FirstLayerEdges", 8)
    assert block
    names = re.findall(r'CreateNtuple[IDS]Column\s*\(\s*"([^"]+)"', block)
    assert names == ["eventID", "fX", "fY", "fZ", "fT", "fwl", "fcosTheta", "forward"], names


# ── ntuple-ID uniqueness / completeness across the 5-region model ────────────

def test_finishntuple_ids_are_unique_and_contiguous(run_cc):
    """FinishNtuple ids must be contiguous from 0 with no duplicates.

    The five-region model uses ids 0..8; the PMT readout mode (detectorType=pmt)
    appends 9 (PMTPhotons) and 10 (PMTHits) — see tests/test_pmt_detector_mode.py.
    """
    ids = [int(x) for x in re.findall(r"FinishNtuple\s*\(\s*(\d+)\s*\)", strip_comments(run_cc))]
    assert len(ids) == len(set(ids)), f"duplicate ntuple ids: {ids}"
    assert sorted(ids) == list(range(len(ids))), f"ids not contiguous from 0: {sorted(ids)}"
    assert set(range(9)) <= set(ids), f"five-region ids 0..8 must all be present, got {sorted(ids)}"


def test_sipm_ntuples_named_explicitly(run_cc):
    """SecondLayerEdges SiPM trees carry explicit SiPM names (read by name in analyze_efficiency)."""
    assert re.search(r'CreateNtuple\s*\(\s*"SiPMPhotons"', run_cc), '"SiPMPhotons" ntuple must exist'
    assert re.search(r'CreateNtuple\s*\(\s*"SiPMHits"', run_cc), '"SiPMHits" ntuple must exist'


# ── documented ID → region comment map ───────────────────────────────────────

def test_region_map_documents_all_regions(run_cc):
    """A comment map heading the ctor must name each of the five regions."""
    for region in (
        "FirstLayerBackplane",
        "FirstLayerEdges",
        "SecondLayerBackplane",
    ):
        assert region in run_cc, f"region {region} should appear in run.cc"
    # The map should also reference the second-layer edge (Hits) and primary regions.
    assert "Primary" in run_cc
    assert "SecondLayerEdges" in run_cc, "region-map comment should mention SecondLayerEdges"
